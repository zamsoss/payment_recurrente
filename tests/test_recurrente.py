
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock

from odoo.tests import tagged
from odoo.tests.common import HttpCase
from odoo.addons.payment.tests.common import PaymentCommon


@tagged('post_install', '-at_install')
class TestRecurrente(PaymentCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.recurrente = cls._prepare_provider('recurrente', update_values={
            'recurrente_public_key': 'pk_test_dummy_public_key',
            'recurrente_secret_key': 'sk_test_dummy_secret_key',
            'recurrente_webhook_secret': 'whsec_test_dummy_webhook_secret',
        })

    def test_provider_configuration(self):
        """Test that the Recurrente provider is properly configured."""
        self.assertEqual(self.recurrente.provider, 'recurrente')
        self.assertTrue(self.recurrente.recurrente_public_key)
        self.assertTrue(self.recurrente.recurrente_secret_key)
        self.assertTrue(self.recurrente.recurrente_webhook_secret)

    def test_compatible_providers_currency_filtering(self):
        """Test that Recurrente is filtered out for unsupported currencies."""
        # Test with supported currency (GTQ)
        gtq_currency = self.env.ref('base.GTQ')
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            currency_id=gtq_currency.id
        )
        self.assertIn(self.recurrente, compatible_providers)
        
        # Test with unsupported currency (EUR)
        eur_currency = self.env.ref('base.EUR')
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            currency_id=eur_currency.id
        )
        self.assertNotIn(self.recurrente, compatible_providers)

    @patch('requests.post')
    def test_create_payment_intent(self, mock_post):
        """Test creating a Payment Intent."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'pa_test_payment_intent_id',
            'redirect_url': 'https://checkout.recurrente.com/pay/pa_test_payment_intent_id'
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Create payment intent
        result = self.recurrente._recurrente_create_payment_intent(
            amount=100.0,
            currency=self.env.ref('base.GTQ'),
            reference='TEST-001',
            return_url='https://example.com/return',
            cancel_url='https://example.com/cancel'
        )
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], 'https://api.recurrente.com/api/payment_intents')
        
        # Verify request data
        request_data = call_args[1]['json']
        self.assertEqual(request_data['amount'], 10000)  # 100.0 * 100
        self.assertEqual(request_data['currency'], 'GTQ')
        self.assertEqual(request_data['reference'], 'TEST-001')
        
        # Verify response
        self.assertEqual(result['id'], 'pa_test_payment_intent_id')
        self.assertIn('redirect_url', result)

    def test_transaction_creation(self):
        """Test creating a payment transaction."""
        tx = self._create_transaction('redirect', provider=self.recurrente)
        
        self.assertEqual(tx.provider, 'recurrente')
        self.assertEqual(tx.provider_id, self.recurrente)
        self.assertFalse(tx.recurrente_payment_intent_id)  # Not set until processing

    def test_transaction_feedback_processing(self):
        """Test processing transaction feedback data."""
        tx = self._create_transaction('redirect', provider=self.recurrente)
        
        # Simulate successful payment feedback
        feedback_data = {
            'id': 'pa_test_payment_intent_id',
            'status': 'succeeded',
            'amount': 10000,
            'currency': 'GTQ',
            'metadata': {
                'odoo_reference': tx.reference
            }
        }
        
        tx._process_feedback_data(feedback_data)
        
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.recurrente_payment_intent_id, 'pa_test_payment_intent_id')
        self.assertEqual(tx.provider_reference, 'pa_test_payment_intent_id')

    def test_webhook_signature_verification(self):
        """Test webhook signature verification."""
        # Prepare test data
        payload = json.dumps({
            'event_type': 'payment_intent.succeeded',
            'data': {
                'id': 'pa_test_payment_intent_id',
                'status': 'succeeded'
            }
        })
        
        timestamp = '1640995200'  # Example timestamp
        webhook_secret = self.recurrente.recurrente_webhook_secret
        
        # Create signature
        signed_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            webhook_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Test signature verification
        headers = {
            'svix-signature': f'v1={signature}',
            'svix-timestamp': timestamp
        }
        
        controller = self.env['ir.http']._get_controller_class('RecurrenteController')()
        is_valid = controller._verify_webhook_signature(payload, headers)
        
        self.assertTrue(is_valid)

    def test_webhook_endpoint(self):
        """Test webhook endpoint processing."""
        tx = self._create_transaction('redirect', provider=self.recurrente)
        tx.recurrente_payment_intent_id = 'pa_test_payment_intent_id'
        
        # Prepare webhook payload
        webhook_data = {
            'event_type': 'payment_intent.succeeded',
            'data': {
                'id': 'pa_test_payment_intent_id',
                'status': 'succeeded',
                'amount': 10000,
                'currency': 'GTQ'
            }
        }
        
        payload = json.dumps(webhook_data)
        timestamp = '1640995200'
        
        # Create valid signature
        signed_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            self.recurrente.recurrente_webhook_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Make webhook request
        response = self.url_open(
            '/payment/recurrente/webhook',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'svix-signature': f'v1={signature}',
                'svix-timestamp': timestamp
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify transaction was updated
        tx.refresh()
        self.assertEqual(tx.state, 'done')

    @patch('requests.post')
    def test_refund_processing(self, mock_post):
        """Test processing refunds."""
        # Create a successful transaction
        tx = self._create_transaction('redirect', provider=self.recurrente)
        tx.recurrente_payment_intent_id = 'pa_test_payment_intent_id'
        tx._set_done()
        
        # Mock refund API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 'rf_test_refund_id',
            'status': 'succeeded',
            'amount': 5000,
            'payment_intent': 'pa_test_payment_intent_id'
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Process refund
        refund_tx = tx._recurrente_create_refund(50.0)
        
        # Verify refund transaction
        self.assertEqual(refund_tx.operation, 'refund')
        self.assertEqual(refund_tx.amount, -50.0)
        self.assertEqual(refund_tx.source_transaction_id, tx)
        self.assertEqual(refund_tx.recurrente_refund_id, 'rf_test_refund_id')
        self.assertEqual(refund_tx.state, 'done')

    def test_status_mapping(self):
        """Test Recurrente status mapping to Odoo states."""
        from odoo.addons.payment_recurrente.models.payment_transaction import RECURRENTE_STATUS_MAPPING
        
        # Test all status mappings
        test_cases = [
            ('pending', 'pending'),
            ('processing', 'pending'),
            ('succeeded', 'done'),
            ('failed', 'error'),
            ('canceled', 'cancel'),
            ('requires_action', 'pending'),
        ]
        
        for recurrente_status, expected_odoo_status in test_cases:
            odoo_status = RECURRENTE_STATUS_MAPPING.get(recurrente_status)
            self.assertEqual(odoo_status, expected_odoo_status,
                           f"Status mapping failed for {recurrente_status}")

    def test_api_url_generation(self):
        """Test API URL generation based on provider state."""
        # Test mode
        self.recurrente.state = 'test'
        api_url = self.recurrente._recurrente_get_api_url()
        self.assertEqual(api_url, 'https://api.recurrente.com')
        
        # Live mode
        self.recurrente.state = 'enabled'
        api_url = self.recurrente._recurrente_get_api_url()
        self.assertEqual(api_url, 'https://api.recurrente.com')

    def test_validation_amount_and_currency(self):
        """Test validation amount and currency for Recurrente."""
        validation_amount = self.recurrente._get_validation_amount()
        validation_currency = self.recurrente._get_validation_currency()
        
        self.assertEqual(validation_amount, 1.0)
        self.assertEqual(validation_currency, 'GTQ')
