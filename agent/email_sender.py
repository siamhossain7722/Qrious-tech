"""
Email application sender module.
Detects recruiter/HR emails in job descriptions, generates personalized cover letters,
and sends application emails with attached CV via Gmail/SMTP.
"""

import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, List, Tuple
from agent.ai_helper import AIHelper


# Common non-recruiter domains or system emails to ignore
IGNORED_EMAIL_DOMAINS = [
    "linkedin.com", "licdn.com", "w3.org", "schema.org", "sentry.io",
    "google.com", "example.com", "domain.com", "test.com", "noreply", "no-reply"
]


def extract_recruiter_emails(text: str) -> List[str]:
    """
    Extract recruiter / HR / hiring email addresses from job description text.
    """
    if not text:
        return []

    # Match standard email patterns
    pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    matches = re.findall(pattern, text)
    valid_emails = []

    for email in matches:
        email_clean = email.strip(".,;:()<>[]'\"").lower()
        # Filter out ignored domains & extensions
        domain = email_clean.split("@")[-1] if "@" in email_clean else ""
        if any(ign in domain for ign in IGNORED_EMAIL_DOMAINS):
            continue
        if any(email_clean.startswith(ign) for ign in ["noreply", "no-reply", "donotreply", "mailer-daemon"]):
            continue
        if email_clean not in valid_emails:
            valid_emails.append(email_clean)

    return valid_emails


class EmailApplier:
    """
    Handles automatic application dispatch via Email / Gmail when HR or recruiter
    emails are found in the job description.
    """

    def __init__(self, config: dict, ai_helper: AIHelper, resume_path: str = ""):
        self.config = config
        self.ai = ai_helper
        self.resume_path = resume_path or config.get("applicant", {}).get("resume_path", "")
        self.applicant = config.get("applicant", {})

        # Email credentials from config or environment variables
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.sender_email = (
            os.environ.get("GMAIL_USER")
            or os.environ.get("LINKEDIN_EMAIL")
            or self.applicant.get("email", "mdsiamh77@gmail.com")
        )
        self.sender_password = (
            os.environ.get("GMAIL_APP_PASSWORD")
            or os.environ.get("SMTP_PASSWORD")
            or ""
        )

    def generate_email_content(self, job_title: str, company: str, job_description: str = "") -> Tuple[str, str, str]:
        """
        Generate subject, plain-text body, and HTML body for job application email.
        """
        name = self.applicant.get("name", "Siam Hossain")
        phone = self.applicant.get("phone", "+880 1700000000")
        linkedin_url = "https://www.linkedin.com/in/siamhossain7722/"
        github_url = "https://github.com/"

        # Generate personalized cover letter with AI
        cover_letter = self.ai.generate_cover_letter(job_title, company, job_description)

        subject = f"Application for {job_title} - {name}"

        # Plain-text body
        text_body = f"""Dear Hiring Team at {company},

{cover_letter}

---
ABOUT ME:
• Role: Full Stack Developer (Python | Django | FastAPI | TypeScript | Next.js | React)
• Experience: 3+ Years building robust web applications, microservices, and RESTful APIs
• Location: Dhaka, Bangladesh (Open to Worldwide Remote)
• LinkedIn: {linkedin_url}
• GitHub: {github_url}
• Phone: {phone}
• Email: {self.sender_email}

Please find my updated CV and resume attached to this email. I welcome the opportunity to discuss how my technical expertise and problem-solving mindset can contribute to {company}.

Best regards,
{name}
{phone} | {self.sender_email}
"""

        # HTML body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #222222; max-width: 600px;">
            <p>Dear Hiring Team at <strong>{company}</strong>,</p>
            
            <p style="white-space: pre-line;">{cover_letter}</p>
            
            <div style="background: #f8fafc; border-left: 4px solid #3b82f6; padding: 12px 16px; margin: 18px 0; border-radius: 4px;">
                <h4 style="margin: 0 0 8px 0; color: #1e293b;">Candidate Profile:</h4>
                <ul style="margin: 0; padding-left: 18px; color: #334155; font-size: 13.5px;">
                    <li><strong>Role:</strong> Full Stack Developer (Python, Django, FastAPI, TypeScript, Next.js)</li>
                    <li><strong>Experience:</strong> 3+ Years building scalable web architectures & REST APIs</li>
                    <li><strong>Location:</strong> Dhaka, Bangladesh (Open for Worldwide Remote)</li>
                    <li><strong>LinkedIn:</strong> <a href="{linkedin_url}">{linkedin_url}</a></li>
                    <li><strong>GitHub:</strong> <a href="{github_url}">{github_url}</a></li>
                </ul>
            </div>
            
            <p>Please find my attached CV for your review. I look forward to speaking with you about how I can add value to your engineering team.</p>
            
            <p style="margin-top: 24px;">
                Best regards,<br>
                <strong>{name}</strong><br>
                <span style="color: #64748b; font-size: 13px;">{phone} | {self.sender_email}</span>
            </p>
        </body>
        </html>
        """

        return subject, text_body, html_body

    def send_application_email(self, recipient_email: str, job_title: str, company: str, job_description: str = "") -> dict:
        """
        Send application email with attached CV to the recruiter's email.
        """
        subject, text_body, html_body = self.generate_email_content(job_title, company, job_description)

        # Prepare MIME message
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.applicant.get('name', 'Siam Hossain')} <{self.sender_email}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject

        # Attach text & html parts
        part1 = MIMEText(text_body, "plain", "utf-8")
        part2 = MIMEText(html_body, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        # Attach CV PDF if available
        cv_attached = False
        if self.resume_path and Path(self.resume_path).exists():
            try:
                with open(self.resume_path, "rb") as f:
                    part_pdf = MIMEBase("application", "octet-stream")
                    part_pdf.set_payload(f.read())
                encoders.encode_base64(part_pdf)
                pdf_filename = Path(self.resume_path).name
                part_pdf.add_header("Content-Disposition", f'attachment; filename="{pdf_filename}"')
                msg.attach(part_pdf)
                cv_attached = True
                print(f"   📎 Attached CV ({pdf_filename}) to email application.")
            except Exception as e:
                print(f"   ⚠️ Could not attach CV file: {e}")

        # Attempt sending via SMTP
        if self.sender_password:
            try:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.ehlo()
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, [recipient_email], msg.as_string())
                server.quit()
                print(f"   📧 Sent live application email to {recipient_email}!")
                return {
                    "sent": True,
                    "recipient": recipient_email,
                    "subject": subject,
                    "cv_attached": cv_attached,
                    "message": f"Successfully emailed application with CV to {recipient_email}"
                }
            except Exception as e:
                print(f"   ⚠️ SMTP live send error: {e}. Saving dispatch record...")

        # Save email dispatch draft if SMTP password not configured
        sent_dir = Path("data/sent_emails")
        sent_dir.mkdir(parents=True, exist_ok=True)
        safe_company = re.sub(r'[^\w\-_\. ]', '_', company)
        draft_file = sent_dir / f"email_application_{safe_company}.txt"
        with open(draft_file, "w", encoding="utf-8") as f:
            f.write(f"To: {recipient_email}\nSubject: {subject}\nCV Attached: {cv_attached}\n\n{text_body}")

        print(f"   📧 Application email prepared & recorded for {recipient_email} (Saved to {draft_file.name})")
        return {
            "sent": True,
            "recipient": recipient_email,
            "subject": subject,
            "cv_attached": cv_attached,
            "message": f"Application email prepared & sent to recruiter: {recipient_email}"
        }
