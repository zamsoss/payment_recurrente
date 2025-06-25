
import logging
import requests
import json
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment import const

_logger = logging.getLogger(__name__)

RECURRENTE_CURRENCIES = ['GTQ', 'USD', 'USDT', 'USDC']


class PaymentAcquirer(models.Model):
    _inherit = 'payment.provider'

    provider = fields.Selection(
        selection_add=[('recurrente', 'Recurrente')],
        ondelete={'recurrente': 'set default'}
    )
    recurrente_public_key = fields.Char(
        string="Recurrente Public Key",
        help="The public key provided by Recurrente (pk_live_... or pk_test_...)",
        required_if_provider='recurrente',
        groups='base.group_user'
    )
    recurrente_secret_key = fields.Char(
        string="Recurrente Secret Key",
        help="The secret key provided by Recurrente (sk_live_... or sk_test_...)",
        required_if_provider='recurrente',
        groups='base.group_system'
    )
    recurrente_webhook_secret = fields.Char(
        string="Webhook Signing Secret",
        help="The webhook signing secret provided by Recurrente for webhook verification",
        required_if_provider='recurrente',
        groups='base.group_system'
    )

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """ Override to filter Recurrente acquirer based on supported currencies. """
        acquirers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)
        
        currency = self.env['res.currency'].browse(currency_id) if currency_id else None
        if currency and currency.name not in RECURRENTE_CURRENCIES:
            acquirers = acquirers.filtered(lambda acq: acq.provider != 'recurrente')
        
        return acquirers

    def _recurrente_get_api_url(self):
        """ Return the API URL based on the acquirer state. """
        if self.state == 'test':
            return 'https://api.recurrente.com'  # Test environment
        else:
            return 'https://api.recurrente.com'  # Live environment (same URL)

    def _recurrente_make_request(self, endpoint, data=None, method='POST'):
        """ Make authenticated request to Recurrente API. """
        url = f"{self._recurrente_get_api_url()}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.recurrente_secret_key}',
            'Content-Type': 'application/json',
        }
        
        try:
            if method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            _logger.error("Recurrente API request failed: %s", str(e))
            raise UserError(_("Payment communication error. Please try again later."))

    def _get_default_payment_method_codes(self):
        """ Override to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.provider != 'recurrente':
            return default_codes
        return ['card']

    def _recurrente_create_payment_intent(self, amount, currency, reference, return_url, cancel_url, **kwargs):
        """ Create a Payment Intent in Recurrente. """
        data = {
            'amount': int(amount * 100),  # Convert to cents
            'currency': currency.name,
            'reference': reference,
            'return_url': return_url,
            'cancel_url': cancel_url,
            'metadata': {
                'odoo_reference': reference,
                'odoo_transaction_id': kwargs.get('transaction_id'),
            }
        }
        
        # Add customer information if available
        if kwargs.get('partner_id'):
            partner = self.env['res.partner'].browse(kwargs['partner_id'])
            data['customer'] = {
                'name': partner.name,
                'email': partner.email,
                'phone': partner.phone,
            }
        
        return self._recurrente_make_request('/api/payment_intents', data)

    def _recurrente_create_checkout_session(self, amount, currency, reference, return_url, cancel_url, **kwargs):
        """ Create a Checkout Session in Recurrente. """
        data = {
            'amount': int(amount * 100),  # Convert to cents
            'currency': currency.name,
            'reference': reference,
            'success_url': return_url,
            'cancel_url': cancel_url,
            'metadata': {
                'odoo_reference': reference,
                'odoo_transaction_id': kwargs.get('transaction_id'),
            }
        }
        
        # Add customer information if available
        if kwargs.get('partner_id'):
            partner = self.env['res.partner'].browse(kwargs['partner_id'])
            data['customer'] = {
                'name': partner.name,
                'email': partner.email,
                'phone': partner.phone,
            }
        
        return self._recurrente_make_request('/api/checkout/sessions', data)

    @api.model
    def _get_validation_amount(self):
        """ Override to return the validation amount for Recurrente. """
        return 1.0

    @api.model
    def _get_validation_currency(self):
        """ Override to return the validation currency for Recurrente. """
        return 'GTQ'

    def _recurrente_process_refund(self, payment_intent_id, amount=None):
        """ Process a refund through Recurrente API. """
        data = {
            'payment_intent': payment_intent_id,
        }
        if amount:
            data['amount'] = int(amount * 100)  # Convert to cents
        
        return self._recurrente_make_request('/api/refunds', data)

    def _recurrente_update_payment_intent_invoice(self, payment_intent_id, invoice_url):
        """ Update Payment Intent with electronic invoice URL. """
        data = {
            'tax_invoice_url': invoice_url
        }
        return self._recurrente_make_request(f'/api/payment_intents/{payment_intent_id}', data, method='PATCH')


class PaymentAcquirerRecurrente(models.Model):
    """ Specific model for Recurrente configuration if needed for additional fields. """
    _name = 'payment.provider.recurrente'
    _description = 'Recurrente Payment Acquirer Configuration'

    provider_id = fields.Many2one('payment.provider', string='Payment Acquirer', required=True)
    enable_subscriptions = fields.Boolean(
        string='Enable Subscriptions',
        default=True,
        help='Enable recurring payments and subscription management'
    )
    enable_digital_dollars = fields.Boolean(
        string='Enable Digital Dollars',
        default=False,
        help='Enable USDT and USDC transactions'
    )
    webhook_url = fields.Char(
        string='Webhook URL',
        compute='_compute_webhook_url',
        help='URL to configure in Recurrente dashboard for webhook notifications'
    )

    @api.depends('provider_id')
    def _compute_webhook_url(self):
        """ Compute the webhook URL for this acquirer. """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.provider_id:
                record.webhook_url = f"{base_url}/payment/recurrente/webhook"
            else:
                record.webhook_url = False
