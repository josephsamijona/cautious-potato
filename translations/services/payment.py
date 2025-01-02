import stripe
from django.conf import settings
from django.urls import reverse
from decimal import Decimal
from datetime import datetime

from .models import TranslationRequest
from ..services.notification import NotificationService

stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentService:
    def __init__(self):
        self.notification_service = NotificationService()

    def create_payment_session(self, translation, success_url, cancel_url):
        """
        Create Stripe payment session for a translation
        """
        try:
            # Create Stripe session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Translation Service: {translation.title}',
                            'description': self._generate_description(translation),
                        },
                        'unit_amount': int(translation.client_price * 100),  # Convert to cents
                    },
                    'quantity': 1,
                }],
                metadata={
                    'translation_id': translation.id,
                    'client_id': translation.client.id,
                },
                client_reference_id=str(translation.id),
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
            )
            
            return session
            
        except stripe.error.StripeError as e:
            # Log the error and raise it for handling in the view
            print(f"Stripe error: {str(e)}")
            raise

    def handle_payment_success(self, session):
        """
        Handle successful payment
        """
        try:
            translation_id = session.metadata.get('translation_id')
            translation = TranslationRequest.objects.get(id=translation_id)
            
            # Update translation status
            translation.status = 'PAID'
            translation.is_paid = True
            translation.stripe_payment_id = session.payment_intent
            translation.save()
            
            # Record payment details
            payment = self.create_payment_record(translation, session)
            
            # Send notifications
            self.notification_service.send_payment_received_notification(payment)
            
            return payment
            
        except TranslationRequest.DoesNotExist:
            raise ValueError(f"Translation {translation_id} not found")
        except Exception as e:
            print(f"Error handling payment success: {str(e)}")
            raise

    def handle_payment_failure(self, session):
        """
        Handle failed payment
        """
        try:
            translation_id = session.metadata.get('translation_id')
            translation = TranslationRequest.objects.get(id=translation_id)
            
            # Update translation status if needed
            if translation.status == 'PAYMENT_PENDING':
                translation.status = 'QUOTED'
                translation.save()
            
            # Record failed payment attempt
            self.record_failed_payment(translation, session)
            
        except TranslationRequest.DoesNotExist:
            raise ValueError(f"Translation {translation_id} not found")
        except Exception as e:
            print(f"Error handling payment failure: {str(e)}")
            raise

    def create_payment_record(self, translation, session):
        """
        Create payment record in database
        """
        from ..models import Payment
        
        return Payment.objects.create(
            translation=translation,
            stripe_payment_id=session.payment_intent,
            amount=translation.client_price,
            status='COMPLETED',
            payment_method='card',
            payment_date=datetime.now(),
            metadata=session.metadata
        )

    def record_failed_payment(self, translation, session):
        """
        Record failed payment attempt
        """
        from ..models import Payment
        
        return Payment.objects.create(
            translation=translation,
            stripe_payment_id=session.payment_intent,
            amount=translation.client_price,
            status='FAILED',
            payment_method='card',
            payment_date=datetime.now(),
            metadata=session.metadata
        )

    def calculate_platform_fee(self, amount):
        """
        Calculate platform fee
        """
        # Example: Platform takes 20% of the total amount
        return Decimal(amount) * Decimal('0.20')

    def calculate_translator_payment(self, amount):
        """
        Calculate translator payment amount
        """
        # Example: Translator receives 80% of the total amount
        return Decimal(amount) * Decimal('0.80')

    def process_translator_payment(self, translation):
        """
        Process payment to translator
        """
        try:
            # Calculate translator payment
            payment_amount = self.calculate_translator_payment(translation.client_price)
            
            # Create transfer to translator's Stripe account
            transfer = stripe.Transfer.create(
                amount=int(payment_amount * 100),  # Convert to cents
                currency='usd',
                destination=translation.translator.profile.stripe_account_id,
                transfer_group=f'Translation_{translation.id}',
                metadata={
                    'translation_id': translation.id,
                    'translator_id': translation.translator.id,
                }
            )
            
            # Update payment record
            self.update_translator_payment_record(translation, transfer)
            
            return transfer
            
        except stripe.error.StripeError as e:
            print(f"Stripe error processing translator payment: {str(e)}")
            raise
        except Exception as e:
            print(f"Error processing translator payment: {str(e)}")
            raise

    def update_translator_payment_record(self, translation, transfer):
        """
        Update payment record with translator payment details
        """
        from ..models import Payment
        
        payment = Payment.objects.get(
            translation=translation,
            status='COMPLETED'
        )
        payment.translator_payment_id = transfer.id
        payment.translator_payment_status = 'PAID'
        payment.translator_payment_date = datetime.now()
        payment.save()

    def _generate_description(self, translation):
        """
        Generate payment description
        """
        return (
            f"Translation from {translation.source_language.name} to "
            f"{translation.target_language.name}\n"
            f"Type: {translation.get_translation_type_display()}\n"
            f"Deadline: {translation.deadline.strftime('%Y-%m-%d')}"
        )

    def refund_payment(self, translation):
        """
        Process refund for a translation
        """
        try:
            # Create refund through Stripe
            refund = stripe.Refund.create(
                payment_intent=translation.stripe_payment_id,
                metadata={
                    'translation_id': translation.id,
                    'client_id': translation.client.id,
                }
            )
            
            # Update translation status
            translation.status = 'REFUNDED'
            translation.save()
            
            # Update payment record
            self.update_refund_record(translation, refund)
            
            # Send notification
            self.notification_service.send_refund_notification(translation)
            
            return refund
            
        except stripe.error.StripeError as e:
            print(f"Stripe error processing refund: {str(e)}")
            raise
        except Exception as e:
            print(f"Error processing refund: {str(e)}")
            raise

    def update_refund_record(self, translation, refund):
        """
        Update payment record with refund details
        """
        from ..models import Payment
        
        payment = Payment.objects.get(
            translation=translation,
            status='COMPLETED'
        )
        payment.refund_id = refund.id
        payment.status = 'REFUNDED'
        payment.refund_date = datetime.now()
        payment.save()