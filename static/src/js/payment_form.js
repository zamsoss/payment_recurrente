
/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { PaymentForm } from "@payment/js/payment_form";

PaymentForm.include({
    
    /**
     * Handle Recurrente payment form submission
     */
    async _processRecurrentePayment(providerCode, paymentOptionId, flow) {
        if (providerCode !== 'recurrente') {
            return this._super(...arguments);
        }

        // Show loading state
        this._displayLoading(true);

        try {
            // Get payment intent from server
            const processingValues = await this._rpc({
                route: '/payment/recurrente/payment_intent',
                params: {
                    'reference': this.txContext.reference,
                    'amount': this.txContext.amount,
                    'currency_id': this.txContext.currency_id,
                    'partner_id': this.txContext.partner_id,
                    'flow': flow,
                    'tokenization_requested': this._isTokenizationRequested(),
                    'landing_route': this.txContext.landing_route,
                    'is_validation': this.txContext.is_validation,
                },
            });

            if (processingValues.recurrente_payment_intent_id) {
                // Redirect to Recurrente checkout
                window.location.href = processingValues.checkout_url;
            } else {
                throw new Error(_t("Unable to create payment intent"));
            }

        } catch (error) {
            this._displayError(
                _t("Payment Error"),
                _t("We are not able to process your payment. Please try again.")
            );
        } finally {
            this._displayLoading(false);
        }
    },

    /**
     * Override to handle Recurrente-specific processing
     */
    async _processPayment(providerCode, paymentOptionId, flow) {
        if (providerCode === 'recurrente') {
            return this._processRecurrentePayment(providerCode, paymentOptionId, flow);
        }
        return this._super(...arguments);
    },

});
