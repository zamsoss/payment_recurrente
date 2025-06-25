
import logging
import pprint
import werkzeug

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class RecurrenteController(http.Controller):

    @http.route('/payment/recurrente/payment_intent', type='json', auth='public')
    def recurrente_create_payment_intent(self, **kwargs):
        """ Create a payment intent for Recurrente. """
        try:
            # Get payment provider
            provider = request.env['payment.provider'].sudo().search([
                ('code', '=', 'recurrente'),
                ('state', '!=', 'disabled')
            ], limit=1)
            
            if not provider:
                raise ValidationError(_("Recurrente payment provider not found or disabled"))

            # Create payment intent
            payment_intent = provider._recurrente_create_payment_intent(
                amount=kwargs.get('amount'),
                currency=request.env['res.currency'].browse(kwargs.get('currency_id')),
                reference=kwargs.get('reference'),
                return_url=f"{request.httprequest.url_root}payment/recurrente/return",
                cancel_url=f"{request.httprequest.url_root}payment/recurrente/cancel",
                partner_id=kwargs.get('partner_id'),
                transaction_id=kwargs.get('transaction_id'),
            )

            return {
                'recurrente_payment_intent_id': payment_intent.get('id'),
                'checkout_url': payment_intent.get('checkout_url'),
                'client_secret': payment_intent.get('client_secret'),
            }

        except Exception as e:
            _logger.error("Error creating Recurrente payment intent: %s", str(e))
            raise ValidationError(_("Unable to create payment intent. Please try again."))

    @http.route('/payment/recurrente/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def recurrente_webhook(self, **kwargs):
        """ Handle Recurrente webhook notifications. """
        try:
            # Get the raw POST data
            data = request.httprequest.get_data()
            
            # Verify webhook signature (implement signature verification)
            # signature = request.httprequest.headers.get('Recurrente-Signature')
            
            # Parse webhook data
            import json
            webhook_data = json.loads(data.decode('utf-8'))
            
            _logger.info("Received Recurrente webhook: %s", pprint.pformat(webhook_data))

            # Find the transaction
            transaction_ref = webhook_data.get('metadata', {}).get('odoo_reference')
            if transaction_ref:
                transaction = request.env['payment.transaction'].sudo().search([
                    ('reference', '=', transaction_ref)
                ], limit=1)
                
                if transaction:
                    transaction._process_notification_data(webhook_data)
                else:
                    _logger.warning("Transaction not found for reference: %s", transaction_ref)

            return werkzeug.wrappers.Response(status=200)

        except Exception as e:
            _logger.error("Error processing Recurrente webhook: %s", str(e))
            return werkzeug.wrappers.Response(status=400)

    @http.route('/payment/recurrente/return', type='http', auth='public')
    def recurrente_return(self, **kwargs):
        """ Handle return from Recurrente checkout. """
        try:
            # Process return parameters
            payment_intent_id = kwargs.get('payment_intent')
            
            if payment_intent_id:
                # Find transaction by payment intent ID
                transaction = request.env['payment.transaction'].sudo().search([
                    ('recurrente_payment_intent_id', '=', payment_intent_id)
                ], limit=1)
                
                if transaction:
                    # Redirect to transaction status page
                    return request.redirect(f'/payment/status/{transaction.id}')

            # Fallback redirect
            return request.redirect('/payment/process')

        except Exception as e:
            _logger.error("Error processing Recurrente return: %s", str(e))
            return request.redirect('/payment/process')

    @http.route('/payment/recurrente/cancel', type='http', auth='public')
    def recurrente_cancel(self, **kwargs):
        """ Handle cancellation from Recurrente checkout. """
        try:
            payment_intent_id = kwargs.get('payment_intent')
            
            if payment_intent_id:
                # Find transaction by payment intent ID
                transaction = request.env['payment.transaction'].sudo().search([
                    ('recurrente_payment_intent_id', '=', payment_intent_id)
                ], limit=1)
                
                if transaction:
                    transaction._set_canceled()

            # Redirect to payment form with error message
            return request.redirect('/payment/process?error=cancelled')

        except Exception as e:
            _logger.error("Error processing Recurrente cancellation: %s", str(e))
            return request.redirect('/payment/process')
