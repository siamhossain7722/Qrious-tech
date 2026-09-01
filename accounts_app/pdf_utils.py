import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_invoice_pdf(payment):
    """Generate professional PDF invoice binary buffer using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0f172a')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#ccff00')
    )
    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    bold_style = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#0f172a')
    )

    enrollment = payment.enrollment
    student_user = enrollment.user

    import os
    from reportlab.platypus import Image as RLImage

    from django.conf import settings
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    logo_flowable = Paragraph("<b>Qrious Tech Academy</b><br/><font size=8.5 color='#64748b'>Official Tuition Payment Receipt & Invoice</font>", title_style)
    if os.path.exists(logo_path):
        try:
            img_el = RLImage(logo_path, width=42, height=44)
            text_para = Paragraph("<b><font size=15 color='#0f172a'>Qrious Tech Academy</font></b><br/><font size=8.5 color='#64748b'>Official Tuition Payment Receipt & Invoice</font>", title_style)
            logo_table = Table([[img_el, text_para]], colWidths=[48, 300])
            logo_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            logo_flowable = logo_table
        except Exception:
            pass

    # Header section
    header_data = [
        [
            logo_flowable,
            Paragraph(f"<b>INVOICE RECEIPT</b><br/><font size=11 color='#ccff00'><b>#{payment.invoice_id}</b></font><br/><font size=8.5 color='#64748b'>Date: {payment.created_at.strftime('%B %d, %Y')}</font>", ParagraphStyle('RHead', parent=normal_style, alignment=2))
        ]
    ]
    t_header = Table(header_data, colWidths=[300, 220])
    t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t_header)
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))

    # Student & Invoice Summary Info Table
    info_data = [
        [
            Paragraph("<b>STUDENT DETAILS:</b>", subtitle_style),
            Paragraph("<b>ACADEMY DETAILS:</b>", subtitle_style)
        ],
        [
            Paragraph(f"<b>Name:</b> {student_user.get_full_name() or student_user.email}<br/><b>Student ID:</b> {enrollment.student_id}<br/><b>Email:</b> {student_user.email}<br/><b>Course:</b> {enrollment.course_name}", normal_style),
            Paragraph("<b>Organization:</b> Qrious Tech Academy<br/><b>Email:</b> mdsiamh77@gmail.com<br/><b>Phone / WhatsApp:</b> +971 566631501<br/><b>Portal:</b> http://localhost:8001/", normal_style)
        ]
    ]
    t_info = Table(info_data, colWidths=[260, 260])
    t_info.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t_info)
    story.append(Spacer(1, 18))

    # Payment Line Item Table
    items_data = [
        [Paragraph("<b>Description</b>", bold_style), Paragraph("<b>Payment Method</b>", bold_style), Paragraph("<b>Transaction Ref</b>", bold_style), Paragraph("<b>Amount Paid</b>", ParagraphStyle('RBold', parent=bold_style, alignment=2))]
    ]
    desc = f"Tuition Fee Payment — {enrollment.course_name}"
    if payment.notes:
        desc += f"<br/><font size=8 color='#64748b'>Notes: {payment.notes}</font>"

    items_data.append([
        Paragraph(desc, normal_style),
        Paragraph(payment.payment_method, normal_style),
        Paragraph(payment.transaction_ref or "N/A", normal_style),
        Paragraph(f"<b>BDT {payment.amount:,.2f}</b>", ParagraphStyle('RNorm', parent=normal_style, alignment=2))
    ])

    t_items = Table(items_data, colWidths=[240, 90, 90, 100])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,1), (-1,-1), 10),
        ('TOPPADDING', (0,1), (-1,-1), 10),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 18))

    # Financial Summary Table
    status_text = "PAID IN FULL 🟢" if enrollment.due_amount == 0 else "PARTIAL / INSTALLMENTS 🟡"
    status_color = "#10b981" if enrollment.due_amount == 0 else "#d97706"

    fin_data = [
        [Paragraph("Total Tuition Fee:", normal_style), Paragraph(f"BDT {enrollment.total_fee:,.2f}", ParagraphStyle('R1', parent=normal_style, alignment=2))],
        [Paragraph("Total Amount Paid to Date:", normal_style), Paragraph(f"<b>BDT {enrollment.total_paid:,.2f}</b>", ParagraphStyle('R2', parent=normal_style, alignment=2))],
        [Paragraph("<b>Remaining Due Balance:</b>", bold_style), Paragraph(f"<b>BDT {enrollment.due_amount:,.2f}</b>", ParagraphStyle('R3', parent=bold_style, alignment=2))],
        [Paragraph("<b>Account Payment Status:</b>", bold_style), Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", ParagraphStyle('R4', parent=bold_style, alignment=2))]
    ]
    t_fin = Table(fin_data, colWidths=[320, 200])
    t_fin.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.HexColor('#ccff00')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_fin)
    story.append(Spacer(1, 24))

    # Footer note
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceAfter=12))
    story.append(Paragraph(
        "<b>THANK YOU FOR YOUR PAYMENT!</b><br/>This is an official computer-generated PDF invoice receipt issued by Qrious Tech Academy.<br/>For billing support: <u>mdsiamh77@gmail.com</u> | WhatsApp: +971 566631501",
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, leading=11, alignment=1, textColor=colors.HexColor('#64748b'))
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_users_report_pdf(users_qs):
    """Generate professional PDF Users & Subscriptions Report binary buffer using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#ccff00')
    )
    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    header_table_style = ParagraphStyle(
        'HeaderTh',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#ffffff')
    )

    from django.utils import timezone
    from datetime import timedelta
    seven_days_ago = timezone.now() - timedelta(days=7)

    # Title & Header
    story.append(Paragraph("Qrious Tech Academy — Super Admin Console", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Registered Users & Subscriptions Report", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Generated: {timezone.now().strftime('%B %d, %Y - %H:%M')} UTC | Total Matching Records: {users_qs.count()}", normal_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=10))

    # Table Header
    table_data = [[
        Paragraph("#", header_table_style),
        Paragraph("ID", header_table_style),
        Paragraph("Full Name & Email", header_table_style),
        Paragraph("Phone / WhatsApp", header_table_style),
        Paragraph("Plan", header_table_style),
        Paragraph("Date Joined", header_table_style),
        Paragraph("Contact Status", header_table_style),
    ]]

    for idx, u in enumerate(users_qs, 1):
        is_over = u.date_joined <= seven_days_ago
        c_status = "Contact Completed" if u.profile.is_contacted else ("Need Contact (>7D)" if is_over else "New (<7 Days)")
        table_data.append([
            Paragraph(str(idx), normal_style),
            Paragraph(f"#{u.id}", normal_style),
            Paragraph(f"<b>{u.get_full_name() or u.email}</b><br/><font color='#64748b'>{u.email}</font>", normal_style),
            Paragraph(u.profile.phone or 'N/A', normal_style),
            Paragraph(u.profile.plan.upper(), normal_style),
            Paragraph(u.date_joined.strftime('%b %d, %Y'), normal_style),
            Paragraph(f"<b>{c_status}</b>", normal_style),
        ])

    t = Table(table_data, colWidths=[20, 30, 180, 80, 50, 70, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_bookings_report_pdf(bookings_qs):
    """Generate professional PDF Service Bookings Report binary buffer using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#ccff00')
    )
    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    header_table_style = ParagraphStyle(
        'HeaderTh',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#ffffff')
    )

    from django.utils import timezone

    story.append(Paragraph("Qrious Tech Academy — Service Booking System", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Client Service Booking Requests Report", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Generated: {timezone.now().strftime('%B %d, %Y - %H:%M')} UTC | Total Records: {bookings_qs.count()}", normal_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=10))

    table_data = [[
        Paragraph("#", header_table_style),
        Paragraph("ID", header_table_style),
        Paragraph("Client Name & Email", header_table_style),
        Paragraph("Phone", header_table_style),
        Paragraph("Category / Service", header_table_style),
        Paragraph("Status", header_table_style),
        Paragraph("Date", header_table_style),
    ]]

    for idx, b in enumerate(bookings_qs, 1):
        table_data.append([
            Paragraph(str(idx), normal_style),
            Paragraph(f"#{b.id}", normal_style),
            Paragraph(f"<b>{b.name}</b><br/><font color='#64748b'>{b.email or 'N/A'}</font>", normal_style),
            Paragraph(b.phone or 'N/A', normal_style),
            Paragraph(f"<b>{b.service_category}</b><br/><font color='#64748b'>{b.service_type or ''}</font>", normal_style),
            Paragraph(f"<b>{b.status.upper()}</b>", normal_style),
            Paragraph(b.created_at.strftime('%b %d, %Y'), normal_style),
        ])

    t = Table(table_data, colWidths=[20, 30, 170, 80, 110, 60, 60])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
