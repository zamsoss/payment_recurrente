
{
    'name': 'Recurrente Payment Provider',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Payment Provider: Recurrente Implementation for Guatemala',
    'description': """
Recurrente Payment Provider
===========================

This module integrates Recurrente payment gateway with Odoo 18.

Features:
---------
* One-time payments via Payment Intents
* Recurring payments and subscriptions
* Webhook handling for real-time status updates
* Refund processing from Odoo
* Multi-currency support (GTQ, USD)
* Digital dollar transactions (USDT, USDC)
* Electronic invoicing integration (Factura Electrónica)
* PCI compliant hosted payment pages
* 3D Secure authentication support

Recurrente is a leading fintech platform in Guatemala providing streamlined
payment solutions for businesses with transparent pricing and no monthly fees.
    """,
    'author': 'Odoo Community',
    'website': 'https://www.recurrente.com',
    'license': 'LGPL-3',
    'depends': [
        'account_payment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/payment_method_data.xml',
        'views/payment_recurrente_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_recurrente/static/src/js/payment_form.js',
            'payment_recurrente/static/src/css/payment_form.css',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
