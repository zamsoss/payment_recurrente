
import logging
import requests
import json
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

RECURRENTE_CURRENCIES = ['GTQ', 'USD', 'USDT', 'USDC']


class PaymentProvider(models.Model):
    """Payment Provider model for Recurrente integration in Odoo 18"""
    _name = 'payment.provider'
    _description = 'Payment Provider'
    _order = 'name'

    name = fields.Char(string='Provider Name', required=True)
    code = fields.Selection([
        ('recurrente', 'Recurrente'),
        ('manual', 'Manual'),
        ('test', 'Test'),
    ], string='Provider Code', required=True)
    state = fields.Selection([
        ('disabled', 'Disabled'),
        ('enabled', 'Enabled'),
        ('test', 'Test Mode'),
    ], string='State', default='disabled', required=True)
    
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        default=lambda self: self.env.company,
        required=True
    )
    
    # Recurrente specific fields
    recurrente_public_key = fields.Char(
        string="Recurrente Public Key",
        help="The public key provided by Recurrente (pk_live_... or pk_test_...)",
        groups='base.group_user'
    )
    recurrente_secret_key = fields.Char(
        string="Recurrente Secret Key",
        help="The secret key provided by Recurrente (sk_live_... or sk_test_...)",
        groups='base.group_system'
    )
    recurrente_webhook_secret = fields.Char(
        string="Webhook Signing Secret",
        help="The webhook signing secret provided by Recurrente for webhook verification",
        groups='base.group_system'
    )

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """ Filter Recurrente provider based on supported currencies. """
        providers = self.search([('state', '!=', 'disabled')])
        
        currency = self.env['res.currency'].browse(currency_id) if currency_id else None
        if currency and currency.name not in RECURRENTE_CURRENCIES:
            providers = providers.filtered(lambda p: p.code != 'recurrente')
        
        return providers

    def _recurrente_get_api_url(self):
        """ Return the API URL based on the provider state. """
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
        """ Return the default payment method codes. """
        if self.code != 'recurrente':
            return []
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

    @api.model
    def _get_validation_amount(self):
        """ Return the validation amount for Recurrente. """
        return 1.0

    @api.model
    def _get_validation_currency(self):
        """ Return the validation currency for Recurrente. """
        return 'GTQ'

    def _recurrente_process_refund(self, payment_intent_id, amount=None):
        """ Process a refund through Recurrente API. """
        data = {
            'payment_intent': payment_intent_id,
        }
        if amount:
            data['amount'] = int(amount * 100)  # Convert to cents
        
        return self._recurrente_make_request('/api/refunds', data)


class PaymentTransaction(models.Model):
    """Payment Transaction model for handling Recurrente transactions"""
    _name = 'payment.transaction'
    _description = 'Payment Transaction'
    _order = 'create_date desc'

    name = fields.Char(string='Transaction Reference', required=True)
    provider_id = fields.Many2one('payment.provider', string='Payment Provider', required=True)
    amount = fields.Monetary(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('error', 'Error'),
    ], string='Status', default='draft', required=True)
    
    provider_reference = fields.Char(string='Provider Reference')
    
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        default=lambda self: self.env.company,
        required=True
    )

    def _process_notification_data(self, notification_data):
        """ Process notification data from Recurrente webhook. """
        self.ensure_one()
        
        if self.provider_id.code != 'recurrente':
            return
        
        status = notification_data.get('status')
        if status == 'succeeded':
            self.state = 'done'
        elif status == 'failed':
            self.state = 'error'
        elif status == 'pending':
            self.state = 'pending'
        
        self.provider_reference = notification_data.get('id')
