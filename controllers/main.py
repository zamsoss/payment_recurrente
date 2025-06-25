
import json
import logging
import hmac
import hashlib
from werkzeug.exceptions import Forbidden

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class RecurrenteController(http.Controller):

    @http.route('/payment/recurrente/return', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def recurrente_return(self, **kwargs):
        """ Handle return from Recurrente payment page. """
        _logger.info("Recurrente return with data: %s", kwargs)
        
        # Extract transaction reference or ID
        tx_reference = kwargs.get('reference') or kwargs.get('tx_reference')
        payment_intent_id = kwargs.get('payment_intent_id') or kwargs.get('payment_intent')
        
        if not tx_reference and not payment_intent_id:
            _logger.error("No transaction reference or payment intent ID in return data")
            return request.redirect('/payment/process')
        
        # Find the transaction
        tx_sudo = None
        if payment_intent_id:
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('recurrente_payment_intent_id', '=', payment_intent_id)
            ], limit=1)
        
        if not tx_sudo and tx_reference:
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('reference', '=', tx_reference)
            ], limit=1)
        
        if not tx_sudo:
            _logger.error("Transaction not found for reference: %s, payment_intent: %s", tx_reference, payment_intent_id)
            return request.redirect('/payment/process')
        
        # Process the return data (preliminary status update)
        try:
            tx_sudo._process_feedback_data(kwargs)
        except Exception as e:
            _logger.error("Error processing return data: %s", str(e))
        
        # Redirect to payment process page
        return request.redirect('/payment/status')

    @http.route('/payment/recurrente/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def recurrente_webhook(self, **kwargs):
        """ Handle webhook notifications from Recurrente. """
        try:
            # Get raw request data
            data = request.httprequest.get_data(as_text=True)
            headers = request.httprequest.headers
            
            _logger.info("Received Recurrente webhook with headers: %s", dict(headers))
            
            # Verify webhook signature (Svix format)
            if not self._verify_webhook_signature(data, headers):
                _logger.error("Invalid webhook signature")
                return http.Response("Invalid signature", status=400)
            
            # Parse JSON data
            try:
                webhook_data = json.loads(data)
            except json.JSONDecodeError as e:
                _logger.error("Invalid JSON in webhook data: %s", str(e))
                return http.Response("Invalid JSON", status=400)
            
            _logger.info("Webhook data: %s", webhook_data)
            
            # Extract event information
            event_type = webhook_data.get('event_type') or webhook_data.get('type')
            event_data = webhook_data.get('data', {})
            
            if not event_type:
                _logger.error("No event type in webhook data")
                return http.Response("No event type", status=400)
            
            # Process different event types
            if event_type in ['payment_intent.succeeded', 'payment_intent.payment_failed', 'payment_intent.canceled']:
                self._handle_payment_intent_event(event_type, event_data)
            elif event_type in ['checkout.session.completed', 'checkout.session.expired']:
                self._handle_checkout_session_event(event_type, event_data)
            elif event_type.startswith('refund.'):
                self._handle_refund_event(event_type, event_data)
            else:
                _logger.info("Unhandled webhook event type: %s", event_type)
            
            return http.Response("OK", status=200)
            
        except Exception as e:
            _logger.error("Error processing webhook: %s", str(e))
            return http.Response("Internal error", status=500)

    def _verify_webhook_signature(self, payload, headers):
        """ Verify webhook signature using Svix format. """
        try:
            # Get signature from headers (Svix format)
            signature_header = headers.get('svix-signature') or headers.get('Svix-Signature')
            if not signature_header:
                _logger.error("No signature header found")
                return False
            
            # Get timestamp
            timestamp = headers.get('svix-timestamp') or headers.get('Svix-Timestamp')
            if not timestamp:
                _logger.error("No timestamp header found")
                return False
            
            # Get webhook secret from provider
            provider = request.env['payment.provider'].sudo().search([
                ('provider', '=', 'recurrente'),
                ('state', 'in', ['enabled', 'test'])
            ], limit=1)
            
            if not provider or not provider.recurrente_webhook_secret:
                _logger.error("No webhook secret configured")
                return False
            
            # Create signed payload (Svix format: timestamp.payload)
            signed_payload = f"{timestamp}.{payload}"
            
            # Calculate expected signature
            expected_signature = hmac.new(
                provider.recurrente_webhook_secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Parse signature header (format: v1=signature1,v1=signature2,...)
            signatures = {}
            for sig_pair in signature_header.split(','):
                if '=' in sig_pair:
                    version, signature = sig_pair.strip().split('=', 1)
                    signatures[version] = signature
            
            # Verify signature (constant time comparison)
            v1_signature = signatures.get('v1')
            if not v1_signature:
                _logger.error("No v1 signature found")
                return False
            
            return hmac.compare_digest(expected_signature, v1_signature)
            
        except Exception as e:
            _logger.error("Error verifying webhook signature: %s", str(e))
            return False

    def _handle_payment_intent_event(self, event_type, event_data):
        """ Handle Payment Intent webhook events. """
        payment_intent_id = event_data.get('id')
        if not payment_intent_id:
            _logger.error("No payment intent ID in event data")
            return
        
        # Find transaction
        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('recurrente_payment_intent_id', '=', payment_intent_id)
        ], limit=1)
        
        if not tx_sudo:
            _logger.error("Transaction not found for payment intent: %s", payment_intent_id)
            return
        
        # Map event type to status
        status_mapping = {
            'payment_intent.succeeded': 'succeeded',
            'payment_intent.payment_failed': 'failed',
            'payment_intent.canceled': 'canceled',
        }
        
        # Update event data with mapped status
        event_data['status'] = status_mapping.get(event_type, event_data.get('status'))
        
        # Process the feedback
        try:
            tx_sudo._process_feedback_data(event_data)
            _logger.info("Processed webhook for transaction %s: %s", tx_sudo.reference, event_type)
            
            # Handle post-payment electronic invoicing
            if event_type == 'payment_intent.succeeded':
                self._handle_post_payment_invoicing(tx_sudo)
                
        except Exception as e:
            _logger.error("Error processing payment intent webhook: %s", str(e))

    def _handle_checkout_session_event(self, event_type, event_data):
        """ Handle Checkout Session webhook events. """
        session_id = event_data.get('id')
        if not session_id:
            _logger.error("No session ID in event data")
            return
        
        # Find transaction
        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('recurrente_checkout_session_id', '=', session_id)
        ], limit=1)
        
        if not tx_sudo:
            _logger.error("Transaction not found for checkout session: %s", session_id)
            return
        
        # Map event type to status
        status_mapping = {
            'checkout.session.completed': 'succeeded',
            'checkout.session.expired': 'canceled',
        }
        
        # Update event data with mapped status
        event_data['status'] = status_mapping.get(event_type, event_data.get('status'))
        
        # Process the feedback
        try:
            tx_sudo._process_feedback_data(event_data)
            _logger.info("Processed webhook for transaction %s: %s", tx_sudo.reference, event_type)
            
            # Handle post-payment electronic invoicing
            if event_type == 'checkout.session.completed':
                self._handle_post_payment_invoicing(tx_sudo)
                
        except Exception as e:
            _logger.error("Error processing checkout session webhook: %s", str(e))

    def _handle_refund_event(self, event_type, event_data):
        """ Handle refund webhook events. """
        refund_id = event_data.get('id')
        payment_intent_id = event_data.get('payment_intent')
        
        if not refund_id or not payment_intent_id:
            _logger.error("Missing refund ID or payment intent ID in refund event")
            return
        
        # Find the refund transaction
        refund_tx = request.env['payment.transaction'].sudo().search([
            ('recurrente_refund_id', '=', refund_id)
        ], limit=1)
        
        if refund_tx:
            # Update refund status
            if event_type == 'refund.succeeded':
                refund_tx._set_done()
            elif event_type == 'refund.failed':
                refund_tx._set_error("Refund failed")
            
            _logger.info("Updated refund transaction %s: %s", refund_tx.reference, event_type)

    def _handle_post_payment_invoicing(self, tx_sudo):
        """ Handle electronic invoicing after successful payment. """
        try:
            # Check if the transaction has an associated invoice
            if tx_sudo.invoice_ids:
                for invoice in tx_sudo.invoice_ids:
                    # Generate electronic invoice if needed
                    if hasattr(invoice, 'l10n_gt_generate_electronic_invoice'):
                        invoice.l10n_gt_generate_electronic_invoice()
                        
                        # Update Payment Intent with invoice URL if available
                        if invoice.l10n_gt_electronic_invoice_url:
                            tx_sudo._recurrente_update_invoice_url(invoice.l10n_gt_electronic_invoice_url)
            
        except Exception as e:
            _logger.error("Error handling post-payment invoicing: %s", str(e))

    @http.route('/payment/recurrente/test', type='http', auth='user', methods=['GET'])
    def recurrente_test(self, **kwargs):
        """ Test endpoint for Recurrente integration (development only). """
        if not request.env.user.has_group('base.group_system'):
            raise Forbidden()
        
        provider = request.env['payment.provider'].search([
            ('provider', '=', 'recurrente')
        ], limit=1)
        
        if not provider:
            return "No Recurrente provider found"
        
        test_data = {
            'provider': provider.name,
            'state': provider.state,
            'public_key': provider.recurrente_public_key[:10] + '...' if provider.recurrente_public_key else 'Not set',
            'secret_key': 'Set' if provider.recurrente_secret_key else 'Not set',
            'webhook_secret': 'Set' if provider.recurrente_webhook_secret else 'Not set',
            'webhook_url': f"{request.httprequest.host_url}payment/recurrente/webhook",
        }
        
        return f"<pre>{json.dumps(test_data, indent=2)}</pre>"
