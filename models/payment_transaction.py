
import logging
import json
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)

RECURRENTE_STATUS_MAPPING = {
    'pending': 'pending',
    'processing': 'pending',
    'succeeded': 'done',
    'failed': 'error',
    'canceled': 'cancel',
    'requires_action': 'pending',
    'requires_payment_method': 'pending',
    'requires_confirmation': 'pending',
    'requires_capture': 'pending',
}


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    recurrente_payment_intent_id = fields.Char(
        string='Recurrente Payment Intent ID',
        help='The Payment Intent ID from Recurrente (pa_...)',
        readonly=True
    )
    recurrente_checkout_session_id = fields.Char(
        string='Recurrente Checkout Session ID',
        help='The Checkout Session ID from Recurrente',
        readonly=True
    )
    recurrente_refund_id = fields.Char(
        string='Recurrente Refund ID',
        help='The Refund ID from Recurrente if this transaction was refunded',
        readonly=True
    )
    recurrente_webhook_data = fields.Text(
        string='Webhook Data',
        help='Raw webhook data received from Recurrente',
        readonly=True
    )

    def _get_specific_rendering_values(self, processing_values):
        """ Override to return Recurrente-specific rendering values. """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'recurrente':
            return res

        # Create checkout session or payment intent
        try:
            if self.acquirer_id.capture_manually:
                # Use Payment Intent for manual capture
                result = self.acquirer_id._recurrente_create_payment_intent(
                    amount=self.amount,
                    currency=self.currency_id,
                    reference=self.reference,
                    return_url=processing_values['return_url'],
                    cancel_url=processing_values['cancel_url'],
                    transaction_id=self.id,
                    partner_id=self.partner_id.id if self.partner_id else None
                )
                self.recurrente_payment_intent_id = result.get('id')
                redirect_url = result.get('redirect_url')
            else:
                # Use Checkout Session for automatic capture
                result = self.acquirer_id._recurrente_create_checkout_session(
                    amount=self.amount,
                    currency=self.currency_id,
                    reference=self.reference,
                    return_url=processing_values['return_url'],
                    cancel_url=processing_values['cancel_url'],
                    transaction_id=self.id,
                    partner_id=self.partner_id.id if self.partner_id else None
                )
                self.recurrente_checkout_session_id = result.get('id')
                redirect_url = result.get('url')

            if not redirect_url:
                raise UserError(_("No redirect URL received from Recurrente"))

            res.update({
                'redirect_url': redirect_url,
                'recurrente_public_key': self.acquirer_id.recurrente_public_key,
            })

        except Exception as e:
            _logger.error("Error creating Recurrente payment: %s", str(e))
            raise UserError(_("Unable to create payment. Please try again later."))

        return res

    def _get_tx_from_feedback_data(self, provider, data):
        """ Override to find transaction from Recurrente feedback data. """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'recurrente':
            return tx

        # Try to find transaction by Payment Intent ID
        payment_intent_id = data.get('payment_intent_id') or data.get('id')
        if payment_intent_id:
            tx = self.search([
                ('recurrente_payment_intent_id', '=', payment_intent_id),
                ('provider', '=', 'recurrente')
            ], limit=1)

        # Try to find by checkout session ID
        if not tx:
            checkout_session_id = data.get('checkout_session_id')
            if checkout_session_id:
                tx = self.search([
                    ('recurrente_checkout_session_id', '=', checkout_session_id),
                    ('provider', '=', 'recurrente')
                ], limit=1)

        # Try to find by reference in metadata
        if not tx:
            metadata = data.get('metadata', {})
            odoo_reference = metadata.get('odoo_reference')
            if odoo_reference:
                tx = self.search([
                    ('reference', '=', odoo_reference),
                    ('provider', '=', 'recurrente')
                ], limit=1)

        return tx

    def _process_feedback_data(self, data):
        """ Override to process Recurrente feedback data. """
        super()._process_feedback_data(data)
        if self.provider != 'recurrente':
            return

        # Store webhook data for debugging
        self.recurrente_webhook_data = json.dumps(data, indent=2)

        # Extract status and map to Odoo status
        recurrente_status = data.get('status', 'pending')
        odoo_status = RECURRENTE_STATUS_MAPPING.get(recurrente_status, 'pending')

        # Update transaction status
        if odoo_status == 'done':
            self._set_done()
        elif odoo_status == 'pending':
            self._set_pending()
        elif odoo_status == 'cancel':
            self._set_canceled()
        elif odoo_status == 'error':
            error_message = data.get('failure_reason') or data.get('last_payment_error', {}).get('message', 'Unknown error')
            self._set_error(error_message)

        # Store additional Recurrente data
        if data.get('id') and data['id'].startswith('pa_'):
            self.recurrente_payment_intent_id = data['id']

        # Update acquirer reference
        if not self.acquirer_reference and self.recurrente_payment_intent_id:
            self.acquirer_reference = self.recurrente_payment_intent_id

    def _recurrente_create_refund(self, amount_to_refund=None):
        """ Create a refund in Recurrente. """
        if not self.recurrente_payment_intent_id:
            raise UserError(_("Cannot refund: No Recurrente Payment Intent ID found"))

        if self.state != 'done':
            raise UserError(_("Cannot refund: Transaction is not in 'done' state"))

        try:
            refund_data = self.acquirer_id._recurrente_process_refund(
                self.recurrente_payment_intent_id,
                amount_to_refund
            )
            
            # Create refund transaction
            refund_tx = self.create({
                'acquirer_id': self.acquirer_id.id,
                'reference': f"R-{self.reference}",
                'amount': -(amount_to_refund or self.amount),
                'currency_id': self.currency_id.id,
                'partner_id': self.partner_id.id,
                'operation': 'refund',
                'source_transaction_id': self.id,
                'recurrente_refund_id': refund_data.get('id'),
                'state': 'done',
            })
            
            return refund_tx

        except Exception as e:
            _logger.error("Error creating Recurrente refund: %s", str(e))
            raise UserError(_("Unable to process refund. Please try again later."))

    def action_recurrente_refund(self):
        """ Action to create a refund for this transaction. """
        if self.provider != 'recurrente':
            return

        return {
            'name': _('Refund Transaction'),
            'type': 'ir.actions.act_window',
            'res_model': 'payment.transaction.refund.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_transaction_id': self.id,
                'default_amount': self.amount,
            }
        }

    def _recurrente_update_invoice_url(self, invoice_url):
        """ Update the Payment Intent with electronic invoice URL. """
        if not self.recurrente_payment_intent_id:
            _logger.warning("Cannot update invoice URL: No Payment Intent ID")
            return

        try:
            self.acquirer_id._recurrente_update_payment_intent_invoice(
                self.recurrente_payment_intent_id,
                invoice_url
            )
            _logger.info("Updated Payment Intent %s with invoice URL", self.recurrente_payment_intent_id)
        except Exception as e:
            _logger.error("Error updating Payment Intent with invoice URL: %s", str(e))


class PaymentTransactionRefundWizard(models.TransientModel):
    """ Wizard for processing refunds. """
    _name = 'payment.transaction.refund.wizard'
    _description = 'Payment Transaction Refund Wizard'

    transaction_id = fields.Many2one('payment.transaction', string='Transaction', required=True)
    amount = fields.Float(string='Refund Amount', required=True)
    reason = fields.Text(string='Refund Reason')

    def action_process_refund(self):
        """ Process the refund. """
        if self.amount <= 0:
            raise ValidationError(_("Refund amount must be positive"))
        
        if self.amount > self.transaction_id.amount:
            raise ValidationError(_("Refund amount cannot exceed original transaction amount"))

        refund_tx = self.transaction_id._recurrente_create_refund(self.amount)
        
        return {
            'name': _('Refund Transaction'),
            'type': 'ir.actions.act_window',
            'res_model': 'payment.transaction',
            'res_id': refund_tx.id,
            'view_mode': 'form',
            'target': 'current',
        }
