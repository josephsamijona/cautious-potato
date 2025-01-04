from django.template.loader import render_to_string
from weasyprint import HTML
from docx import Document
from PIL import Image
import io
from django.core.mail import EmailMessage
from django.conf import settings
import os

class DocumentGenerator:
    def __init__(self, translation_request):
        self.translation = translation_request
        self.context = self._get_base_context()

    def _get_base_context(self):
        """Prépare le contexte de base pour les templates"""
        return {
            'translation': self.translation,
            'company_name': 'Translation Platform',
            'company_address': settings.COMPANY_ADDRESS,
            'company_email': settings.COMPANY_EMAIL,
            'company_phone': settings.COMPANY_PHONE,
            'company_logo': settings.COMPANY_LOGO_PATH,
            'date': self.translation.created_at.strftime('%Y-%m-%d'),
            'invoice_number': f"INV-{self.translation.id:06d}",
            'quote_number': f"QTE-{self.translation.id:06d}",
        }

    def generate_pdf(self, template_name):
        """Génère un PDF à partir d'un template HTML"""
        html_string = render_to_string(template_name, self.context)
        pdf_file = io.BytesIO()
        HTML(string=html_string).write_pdf(pdf_file)
        return pdf_file

    def generate_docx(self, template_name):
        """Génère un document Word"""
        doc = Document()
        # Ajouter le contenu formaté
        doc.add_heading(f'{self.context["company_name"]}', 0)
        # ... (ajout du contenu formaté)
        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer

    def generate_image(self, template_name):
        """Génère une image JPG"""
        pdf = self.generate_pdf(template_name)
        # Conversion PDF en image
        image = Image.open(pdf)
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG')
        return img_buffer

    def send_email(self, subject, template_name, recipient_email):
        """Envoie le document par email"""
        pdf_file = self.generate_pdf(template_name)
        
        email = EmailMessage(
            subject=subject,
            body=render_to_string('emails/document_email.html', self.context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )
        
        email.attach(
            f'{subject}.pdf',
            pdf_file.getvalue(),
            'application/pdf'
        )
        email.send()

class QuoteGenerator(DocumentGenerator):
    def __init__(self, translation_request):
        super().__init__(translation_request)
        self.context.update({
            'document_type': 'Quote',
            'document_number': self.context['quote_number'],
        })

    def generate_and_send(self):
        self.send_email(
            subject=f'Translation Quote #{self.context["quote_number"]}',
            template_name='documents/quote.html',
            recipient_email=self.translation.client.email
        )

class InvoiceGenerator(DocumentGenerator):
    def __init__(self, translation_request):
        super().__init__(translation_request)
        self.context.update({
            'document_type': 'Invoice',
            'document_number': self.context['invoice_number'],
        })

    def generate_and_send(self):
        self.send_email(
            subject=f'Translation Invoice #{self.context["invoice_number"]}',
            template_name='documents/invoice.html',
            recipient_email=self.translation.client.email
        )

class PayslipGenerator(DocumentGenerator):
    def __init__(self, translation_request):
        super().__init__(translation_request)
        self.context.update({
            'document_type': 'Payslip',
            'payslip_number': f"PAY-{self.translation.id:06d}",
        })

    def generate_and_send(self):
        self.send_email(
            subject=f'Translation Payment Slip #{self.context["payslip_number"]}',
            template_name='documents/payslip.html',
            recipient_email=self.translation.translator.email
        )