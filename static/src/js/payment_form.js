
odoo.define('payment_recurrente.payment_form', function (require) {
    'use strict';

    var core = require('web.core');
    var PaymentForm = require('payment.payment_form');

    var _t = core._t;

    PaymentForm.include({

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            if (provider !== 'recurrente') {
                return this._super.apply(this, arguments);
            }
            // Recurrente uses redirect flow, no inline form needed
            return Promise.resolve();
        },

        /**
         * @override
         */
        _processRedirectPayment: function (provider, paymentOptionId, processingValues) {
            if (provider !== 'recurrente') {
                return this._super.apply(this, arguments);
            }
            
            // Show loading state
            this._displayLoading(true);
            
            // Submit the form to initiate Recurrente payment
            return this._rpc({
                route: processingValues.landing_route,
                params: processingValues,
            }).then(function (result) {
                if (result.redirect_url) {
                    // Redirect to Recurrente payment page
                    window.location.href = result.redirect_url;
                } else {
                    // Handle error
                    this._displayError(
                        _t("Payment Error"),
                        _t("Unable to redirect to payment page. Please try again.")
                    );
                }
            }.bind(this)).catch(function (error) {
                this._displayError(
                    _t("Payment Error"),
                    _t("An error occurred while processing your payment. Please try again.")
                );
            }.bind(this));
        },

        /**
         * Display loading state
         */
        _displayLoading: function (show) {
            var $payButton = this.$('.recurrente-pay-button');
            if (show) {
                $payButton.prop('disabled', true);
                $payButton.html('<i class="fa fa-spinner fa-spin"></i> Procesando...');
            } else {
                $payButton.prop('disabled', false);
                $payButton.html('<i class="fa fa-credit-card"></i> Pagar Ahora');
            }
        },

        /**
         * Display error message
         */
        _displayError: function (title, message) {
            this._displayLoading(false);
            this.displayNotification({
                type: 'danger',
                title: title,
                message: message,
                sticky: true,
            });
        },

    });

    // Handle payment button click
    $(document).ready(function () {
        $(document).on('click', '.recurrente-pay-button', function (e) {
            e.preventDefault();
            var $form = $('form[name="recurrente_payment_form"]');
            if ($form.length) {
                $form.submit();
            }
        });
    });

});
