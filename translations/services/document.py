from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from django.conf import settings

class DocumentService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        # Add custom styles if needed
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            fontSize=20,
            spaceAfter=30,
            alignment=1  # center
        ))

    def _create_header(self, canvas, doc, title):
        """Create header for PDF documents"""
        canvas.saveState()
        canvas.setFont('Helvetica-Bold', 16)
        canvas.drawString(doc.leftMargin, doc.height + doc.topMargin, title)
        canvas.setFont('Helvetica', 9)
        canvas.drawString(doc.leftMargin, doc.height + doc.topMargin - 20,
                         f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        canvas.drawImage(
            settings.LOGO_PATH,
            doc.width - inch,
            doc.height + doc.topMargin - inch/2,
            width=inch,
            height=inch/2
        )
        canvas.restoreState()

    def generate_quote_pdf(self, quote):
        """
        Generate PDF quote document
        Args:
            quote: TranslationRequest instance
        Returns:
            BytesIO object containing the PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Prepare document elements
        elements = []

        # Add title
        elements.append(Paragraph(f"Translation Quote #{quote.id}", self.styles['CustomTitle']))
        elements.append(Spacer(1, 12))

        # Client information
        client_info = [
            ['Client Information'],
            ['Name:', quote.client.get_full_name()],
            ['Email:', quote.client.email],
            ['Company:', quote.client.profile.company_name or 'N/A'],
        ]
        client_table = Table(client_info, colWidths=[100, 300])
        client_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(client_table)
        elements.append(Spacer(1, 20))

        # Translation details
        translation_info = [
            ['Translation Details'],
            ['Service Type:', quote.get_translation_type_display()],
            ['Source Language:', quote.source_language.name],
            ['Target Language:', quote.target_language.name],
            ['Deadline:', quote.deadline.strftime('%Y-%m-%d')],
        ]
        translation_table = Table(translation_info, colWidths=[100, 300])
        translation_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmock),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(translation_table)
        elements.append(Spacer(1, 20))

        # Pricing
        pricing_info = [
            ['Pricing Details'],
            ['Translation Cost:', f'${quote.client_price}'],
        ]
        pricing_table = Table(pricing_info, colWidths=[100, 300])
        pricing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmock),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(pricing_table)

        # Build PDF
        doc.build(elements, onFirstPage=lambda x, y: self._create_header(x, y, "Translation Quote"))
        buffer.seek(0)
        return buffer

    def generate_invoice_pdf(self, translation):
        """
        Generate PDF invoice
        Args:
            translation: TranslationRequest instance
        Returns:
            BytesIO object containing the PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        elements = []

        # Add title
        elements.append(Paragraph(f"Invoice #{translation.id}", self.styles['CustomTitle']))
        elements.append(Spacer(1, 12))

        # Client and Service Information
        info_data = [
            ['Bill To:', 'Service Details:'],
            [f'{translation.client.get_full_name()}', 'Translation Service'],
            [translation.client.email, f'Project: {translation.title}'],
            [translation.client.profile.company_name or '', f'Type: {translation.get_translation_type_display()}'],
            ['', f'Status: {translation.get_status_display()}']
        ]

        info_table = Table(info_data, colWidths=[200, 200])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # Service details
        service_data = [
            ['Description', 'Amount'],
            [f'Translation from {translation.source_language.name} to {translation.target_language.name}', 
             f'${translation.client_price}'],
            ['Total:', f'${translation.client_price}']
        ]

        service_table = Table(service_data, colWidths=[300, 100])
        service_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ]))
        elements.append(service_table)

        # Build PDF
        doc.build(elements, onFirstPage=lambda x, y: self._create_header(x, y, "Invoice"))
        buffer.seek(0)
        return buffer

    def generate_payment_slip_pdf(self, payment):
        """
        Generate PDF payment slip/receipt
        Args:
            payment: Payment instance
        Returns:
            BytesIO object containing the PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        elements = []

        # Add title
        elements.append(Paragraph(f"Payment Receipt #{payment.id}", self.styles['CustomTitle']))
        elements.append(Spacer(1, 12))

        # Payment details
        payment_info = [
            ['Payment Information'],
            ['Date:', payment.created_at.strftime('%Y-%m-%d %H:%M')],
            ['Transaction ID:', payment.stripe_payment_id],
            ['Amount:', f'${payment.amount}'],
            ['Status:', 'Paid'],
            ['Payment Method:', 'Credit Card']
        ]

        payment_table = Table(payment_info, colWidths=[120, 280])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(payment_table)
        elements.append(Spacer(1, 20))

        # Build PDF
        doc.build(elements, onFirstPage=lambda x, y: self._create_header(x, y, "Payment Receipt"))
        buffer.seek(0)
        return buffer