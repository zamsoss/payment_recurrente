
from . import models
from . import controllers

def post_init_hook(env):
    """Post-installation hook to set up Recurrente payment method."""
    # Create payment method if it doesn't exist
    payment_method = env['account.payment.method'].search([('code', '=', 'recurrente')])
    if not payment_method:
        env['account.payment.method'].create({
            'name': 'Recurrente',
            'code': 'recurrente',
            'payment_type': 'inbound',
        })

def uninstall_hook(env):
    """Pre-uninstallation hook to clean up Recurrente data."""
    # Remove payment method
    payment_method = env['account.payment.method'].search([('code', '=', 'recurrente')])
    if payment_method:
        payment_method.unlink()
