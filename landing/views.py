from django.shortcuts import render
from django.conf import settings
from django.contrib import messages


def landing(request):
    """Main Agency Landing Page for Qrious Tech Academy."""
    return render(request, 'landing/index.html', {'plans': settings.PLAN_LIMITS})


def job_agent_landing(request):
    """Dedicated product page for LinkedIn AI Job Agent."""
    return render(request, 'landing/job_agent.html', {'plans': settings.PLAN_LIMITS})


def about_us(request):
    """About Us page explaining Qrious Tech Academy story, mission, team, and tech stack."""
    return render(request, 'landing/about.html')


from django.core.mail import send_mail
from .models import ContactSubmission

def contact_us(request):
    """Contact Us page displaying email mdsiamh77@gmail.com, WhatsApp +971 566631501, and message form."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', 'General Inquiry').strip()
        message_text = request.POST.get('message', '').strip()

        if name and email and message_text:
            # 1. Save permanently in Database
            ContactSubmission.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message_text
            )

            # 2. Compose notification email for Qrious Admin
            email_subject = f"[Qrious Tech Academy Inquiry] {subject} - From {name}"
            email_body = f"""
New Contact Submission on Qrious Tech Academy:

Sender Name: {name}
Sender Email: {email}
Subject: {subject}

Message:
--------------------------------------------------
{message_text}
--------------------------------------------------
            """

            try:
                from django.core.mail import EmailMultiAlternatives
                html_contact = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#070913;font-family:'Inter',sans-serif;color:#f8fafc;">
<table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#070913;padding:40px 10px;">
<tr><td align="center">
<table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width:600px;background-color:#0d1222;border:1px solid rgba(255,255,255,0.12);border-radius:20px;overflow:hidden;box-shadow:0 25px 50px -12px rgba(0,0,0,0.7);">
<tr><td style="height:5px;background:linear-gradient(90deg,#3b82f6,#0284c7,#ccff00);"></td></tr>
<tr>
<td style="padding:28px 32px;border-bottom:1px solid rgba(255,255,255,0.08);">
    <table width="100%">
    <tr>
        <td>
            <table role="presentation" border="0" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="vertical-align: middle; padding-right: 12px;">
                        <img src="http://127.0.0.1:8001/static/images/logo.png" alt="Qrious Tech" width="38" height="38" style="width: 38px; height: 38px; display: block; border: 0; object-fit: contain;">
                    </td>
                    <td style="vertical-align: middle;">
                        <div style="font-size:20px;font-weight:900;color:#ffffff;line-height:1.2;">Qrious Tech</div>
                    </td>
                </tr>
            </table>
        </td>
        <td align="right" style="vertical-align: middle;"><span style="font-size:11px;font-weight:700;color:#38bdf8;background:rgba(56,189,248,0.15);border:1px solid rgba(56,189,248,0.3);padding:5px 14px;border-radius:20px;">📩 CONTACT INQUIRY</span></td>
    </tr>
    </table>
</td>
</tr>
<tr>
<td style="padding:36px 32px;">
    <h1 style="font-size:22px;font-weight:800;color:#ffffff;margin:0 0 16px 0;">New Contact Form Submission 📬</h1>
    
    <div style="background-color:#131b2e;border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:20px;margin-bottom:24px;">
        <table width="100%" style="font-size:13.5px;color:#cbd5e1;">
            <tr><td style="padding:6px 0;color:#64748b;">Sender Name:</td><td align="right" style="font-weight:800;color:#ffffff;">{name}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Sender Email:</td><td align="right" style="font-weight:700;color:#38bdf8;">{email}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Subject:</td><td align="right" style="font-weight:700;color:#f59e0b;">{subject}</td></tr>
        </table>
    </div>

    <div style="background-color:#131b2e;border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:20px;margin-bottom:24px;">
        <div style="font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:8px;">Message Content:</div>
        <div style="font-size:14px;color:#f8fafc;line-height:1.6;white-space:pre-wrap;">{message_text}</div>
    </div>
</td>
</tr>
<tr>
<td style="padding:20px 32px;background-color:#070913;text-align:center;font-size:11px;color:#64748b;">
    Qrious Tech Engineering & Client Support<br>
    Email: mdsiamh77@gmail.com | WhatsApp: +971 566631501
</td>
</tr>
</table>
</td></tr>
</table>
</body>
</html>"""
                msg = EmailMultiAlternatives(
                    subject=email_subject,
                    body=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=['mdsiamh77@gmail.com']
                )
                msg.attach_alternative(html_contact, "text/html")
                msg.send(fail_silently=False)
                messages.success(request, f"Thank you, {name}! Your message has been sent directly to mdsiamh77@gmail.com. Our team will get back to you at {email}.")
            except Exception as e:
                messages.success(request, f"Thank you, {name}! Your message has been saved into our system database.")

    return render(request, 'landing/contact.html')


from accounts_app.models import ServiceBooking
from accounts_app.views import create_notification
from django.shortcuts import redirect

def book_service(request):
    """Dedicated Book a Service page where users schedule web, app, SaaS, or AI service requests."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        category = request.POST.get('service_category', '').strip()
        service_type = request.POST.get('service_type', '').strip()
        notes = request.POST.get('notes', '').strip()

        if name and phone and category:
            booking = ServiceBooking.objects.create(
                user=request.user if request.user.is_authenticated else None,
                name=name,
                phone=phone,
                email=email,
                service_category=category,
                service_type=service_type,
                notes=notes
            )

            # Notifications
            if request.user.is_authenticated:
                create_notification(
                    user=request.user,
                    title="🎉 Service Booking Received",
                    message=f"Your booking request for '{category}' ({service_type or 'Standard'}) has been logged. Our technical team will contact you at {phone}.",
                    notification_type="booking",
                    category="success",
                    link="/superadmin/bookings/" if request.user.is_superuser else "#"
                )
            
            create_notification(
                user=None,
                title=f"🔔 New Service Booking: {name}",
                message=f"New booking for '{category}' ({service_type or 'General'}) submitted by {name} ({phone}).",
                notification_type="booking",
                category="info",
                link="/superadmin/bookings/"
            )

            # Send HTML email notification to mdsiamh77@gmail.com
            try:
                from django.core.mail import EmailMultiAlternatives
                email_subject = f"[New Service Booking] {category} - From {name}"
                text_body = f"New Service Booking Request:\n\nName: {name}\nPhone: {phone}\nEmail: {email}\nCategory: {category}\nService Type: {service_type}\nNotes: {notes}"
                
                html_booking = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#070913;font-family:'Inter',sans-serif;color:#f8fafc;">
<table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#070913;padding:40px 10px;">
<tr><td align="center">
<table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width:600px;background-color:#0d1222;border:1px solid rgba(255,255,255,0.12);border-radius:20px;overflow:hidden;box-shadow:0 25px 50px -12px rgba(0,0,0,0.7);">
<tr><td style="height:5px;background:linear-gradient(90deg,#0284c7,#38bdf8,#ccff00);"></td></tr>
<tr>
<td style="padding:28px 32px;border-bottom:1px solid rgba(255,255,255,0.08);">
    <table width="100%">
    <tr>
        <td>
            <table role="presentation" border="0" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="vertical-align: middle; padding-right: 12px;">
                        <img src="http://127.0.0.1:8001/static/images/logo.png" alt="Qrious Tech" width="38" height="38" style="width: 38px; height: 38px; display: block; border: 0; object-fit: contain;">
                    </td>
                    <td style="vertical-align: middle;">
                        <div style="font-size:20px;font-weight:900;color:#ffffff;line-height:1.2;">Qrious Tech</div>
                    </td>
                </tr>
            </table>
        </td>
        <td align="right" style="vertical-align: middle;"><span style="font-size:11px;font-weight:700;color:#ccff00;background:rgba(204,255,0,0.15);border:1px solid rgba(204,255,0,0.3);padding:5px 14px;border-radius:20px;">⚡ NEW SERVICE BOOKING</span></td>
    </tr>
    </table>
</td>
</tr>
<tr>
<td style="padding:36px 32px;">
    <h1 style="font-size:22px;font-weight:800;color:#ffffff;margin:0 0 16px 0;">New Project Booking Request 🚀</h1>
    
    <div style="background-color:#131b2e;border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:20px;margin-bottom:24px;">
        <table width="100%" style="font-size:13.5px;color:#cbd5e1;">
            <tr><td style="padding:6px 0;color:#64748b;">Client Name:</td><td align="right" style="font-weight:800;color:#ffffff;">{name}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Phone / WhatsApp:</td><td align="right" style="font-weight:800;color:#38bdf8;font-family:monospace;">{phone}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Email Address:</td><td align="right" style="font-weight:700;color:#cbd5e1;">{email or 'N/A'}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Service Category:</td><td align="right" style="font-weight:800;color:#ccff00;">{category}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;">Service Type:</td><td align="right" style="font-weight:700;color:#ffffff;">{service_type or 'General'}</td></tr>
        </table>
    </div>

    <div style="background-color:#131b2e;border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:20px;margin-bottom:24px;">
        <div style="font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:8px;">Project Requirements / Notes:</div>
        <div style="font-size:14px;color:#f8fafc;line-height:1.6;white-space:pre-wrap;">{notes or 'None provided'}</div>
    </div>
</td>
</tr>
<tr>
<td style="padding:20px 32px;background-color:#070913;text-align:center;font-size:11px;color:#64748b;">
    Qrious Tech Engineering & Client Support<br>
    Email: mdsiamh77@gmail.com | WhatsApp: +971 566631501
</td>
</tr>
</table>
</td></tr>
</table>
</body>
</html>"""

                msg = EmailMultiAlternatives(
                    subject=email_subject,
                    body=text_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=['mdsiamh77@gmail.com']
                )
                msg.attach_alternative(html_booking, "text/html")
                msg.send(fail_silently=True)
            except Exception:
                pass

            messages.success(request, f"🎉 Service Booking Received! Thank you {name}, our technical team will contact you shortly at {phone}.")
            return redirect('book_service')

    return render(request, 'landing/book_service.html')


def services_overview(request):
    """Overview of all agency services (Webites, Apps, SaaS Products, AI Solutions)."""
    return render(request, 'landing/services.html')


def courses_overview(request):
    """Overview of Qrious Tech Academy courses (Digital Marketing, Full Stack Web Dev)."""
    return render(request, 'landing/courses.html')


def digital_marketing_detail(request):
    """Detailed course syllabus and enrollment page for Digital Marketing Masterclass."""
    return render(request, 'landing/digital_marketing_detail.html')


def full_stack_web_detail(request):
    """Detailed course syllabus, batch limits (10 seats), and enrollment page for Full-Stack Web Development."""
    return render(request, 'landing/full_stack_web_detail.html')


def pricing(request):
    """Pricing page."""
    return render(request, 'landing/pricing.html', {'plans': settings.PLAN_LIMITS})


from django.http import HttpResponse

def robots_txt(request):
    """Dynamic robots.txt for Search Engine Crawlers."""
    content = """User-agent: *
Allow: /
Allow: /about/
Allow: /contact/
Allow: /courses/
Allow: /services/
Allow: /job-agent/
Allow: /book-service/
Allow: /pricing/

Disallow: /admin/
Disallow: /superadmin/
Disallow: /dashboard/
Disallow: /student/
Disallow: /billing/
Disallow: /auth/

Sitemap: https://qrioussolution.com/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")


def sitemap_xml(request):
    """Dynamic XML Sitemap for Google Search Console indexing."""
    domain = request.build_absolute_uri('/')[:-1]
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{domain}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{domain}/about/</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>{domain}/services/</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>{domain}/courses/</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>{domain}/job-agent/</loc>
    <changefreq>weekly</changefreq>
    <priority>0.95</priority>
  </url>
  <url>
    <loc>{domain}/contact/</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>{domain}/book-service/</loc>
    <changefreq>weekly</changefreq>
    <priority>0.85</priority>
  </url>
  <url>
    <loc>{domain}/pricing/</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
"""
    return HttpResponse(sitemap, content_type="application/xml")


from django.http import HttpResponse, JsonResponse
from django.core.management import call_command
from django.contrib.auth.models import User
from accounts_app.models import UserProfile

def run_migrations_setup_view(request):
    """Run database migrations and create Super Admin account on Vercel deployment."""
    logs = []
    try:
        import io
        out = io.StringIO()
        call_command('migrate', '--fake-initial', interactive=False, stdout=out)
        logs.append(out.getvalue())

        admin_email = os.getenv('ADMIN_EMAIL', 'mdsiamh77@gmail.com')
        admin_pass = os.getenv('ADMIN_PASSWORD', 'Admin123456!')

        # Create/Update both 'admin' and email-based usernames
        for uname in ['admin', admin_email]:
            u = User.objects.filter(username=uname).first()
            if not u:
                u = User.objects.create_superuser(
                    username=uname,
                    email=admin_email,
                    password=admin_pass,
                    first_name='Super',
                    last_name='Admin'
                )
                logs.append(f"Created Super Admin ({uname})!")
            else:
                u.is_superuser = True
                u.is_staff = True
                u.email = admin_email
                u.set_password(admin_pass)
                u.save()
                logs.append(f"Updated Super Admin ({uname}) password!")

            profile, _ = UserProfile.objects.get_or_create(user=u)
            profile.role = 'super_admin'
            profile.plan = 'enterprise'
            profile.save()

            try:
                from allauth.account.models import EmailAddress
                ea, _ = EmailAddress.objects.get_or_create(user=u, email=admin_email)
                ea.verified = True
                ea.primary = True
                ea.save()
            except Exception:
                pass

        return JsonResponse({'status': 'success', 'message': 'All migrations completed & Super Admin created!', 'logs': logs})
    except Exception as e:
        import traceback
        return JsonResponse({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}, status=500)

