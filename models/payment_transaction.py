
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    recurrente_payment_intent_id = fields.Char(
        string='Recurrente Payment Intent ID',
        help='The Payment Intent ID from Recurrente'
    )
    recurrente_checkout_session_id = fields.Char(
        string='Recurrente Checkout Session ID',
        help='The Checkout Session ID from Recurrente'
    )

    def _get_specific_rendering_values(self, processing_values):
        """ Override to return Recurrente-specific rendering values. """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'recurrente':
            return res

        # Create payment intent or checkout session
        try:
            if self.provider_id.code == 'recurrente':
                payment_intent = self.provider_id._recurrente_create_payment_intent(
                    amount=self.amount,
                    currency=self.currency_id,
                    reference=self.reference,
                    return_url=processing_values.get('return_url'),
                    cancel_url=processing_values.get('cancel_url'),
                    partner_id=self.partner_id.id,
                    transaction_id=self.id,
                )
                
                self.recurrente_payment_intent_id = payment_intent.get('id')
                
                res.update({
                    'recurrente_payment_intent_id': payment_intent.get('id'),
                    'recurrente_client_secret': payment_intent.get('client_secret'),
                    'recurrente_public_key': self.provider_id.recurrente_public_key,
                })
        
        except Exception as e:
            _logger.error("Error creating Recurrente payment intent: %s", str(e))
            raise ValidationError(_("Unable to create payment. Please try again."))

        return res

    def _process_notification_data(self, notification_data):
        """ Override to process Recurrente-specific notification data. """
        super()._process_notification_data(notification_data)
        
        if self.provider_code != 'recurrente':
            return

        # Process Recurrente webhook data
        payment_intent_id = notification_data.get('payment_intent_id')
        if payment_intent_id:
            self.recurrente_payment_intent_id = payment_intent_id

        status = notification_data.get('status')
        if status == 'succeeded':
            self._set_done()
        elif status == 'failed':
            self._set_error("Payment failed")
        elif status == 'canceled':
            self._set_canceled()

    @property
    def provider_code(self):
        """ Return the provider code. """
        return self.provider_id.code if self.provider_id else None
