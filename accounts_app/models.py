import json
import random
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from datetime import datetime


class UserProfile(models.Model):
    """Extended user profile linked to Django's User model."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    avatar_data = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    is_contacted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile: {self.user.email}"

    @property
    def avatar_src(self):
        if self.avatar_data:
            return self.avatar_data
        if self.avatar:
            try:
                return self.avatar.url
            except Exception:
                pass
        return None

    @property
    def is_over_7_days(self):
        return self.user.date_joined <= timezone.now() - timezone.timedelta(days=7)

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.email.split('@')[0]

    @property
    def subscription(self):
        try:
            return self.user.subscription
        except Subscription.DoesNotExist:
            return None

    @property
    def plan(self):
        sub = self.subscription
        if sub and sub.is_active:
            return sub.plan
        return 'free'

    @property
    def plan_limits(self):
        return settings.PLAN_LIMITS.get(self.plan, settings.PLAN_LIMITS['free'])

    @property
    def is_certified(self):
        """Returns True if student has completed any course and earned a certificate."""
        return self.user.enrollments.filter(is_completed=True).exists()


class Subscription(models.Model):
    """User subscription to a plan."""

    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('business', 'Business'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('past_due', 'Past Due'),
        ('trialing', 'Trialing'),
        ('incomplete', 'Incomplete'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Stripe fields
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)

    # Billing cycle
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} — {self.plan} ({self.status})"

    @property
    def is_active(self):
        return self.status in ('active', 'trialing')

    @property
    def limits(self):
        return settings.PLAN_LIMITS.get(self.plan, settings.PLAN_LIMITS['free'])

    def applications_this_month(self):
        """Count applications submitted this calendar month."""
        from dashboard.models import JobApplication
        now = timezone.now()
        return JobApplication.objects.filter(
            user=self.user,
            date_applied__year=now.year,
            date_applied__month=now.month,
            status='applied',
        ).count()

    def can_apply(self):
        """Returns (bool, reason) — whether user can submit another application."""
        limit = self.limits['applications_per_month']
        used = self.applications_this_month()
        if used >= limit:
            return False, f"You've used {used}/{limit} applications this month. Upgrade to apply more."
        return True, ""

    def applications_remaining(self):
        limit = self.limits['applications_per_month']
        used = self.applications_this_month()
        return max(0, limit - used)


class UsageLog(models.Model):
    """Tracks usage events for billing / analytics."""

    EVENT_CHOICES = [
        ('application_submitted', 'Application Submitted'),
        ('profile_synced', 'Profile Synced'),
        ('resume_uploaded', 'Resume Uploaded'),
        ('agent_run', 'Agent Run'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usage_logs')
    event = models.CharField(max_length=50, choices=EVENT_CHOICES)
    metadata = models.TextField(blank=True)  # JSON
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.event}"

    def get_metadata(self):
        try:
            return json.loads(self.metadata)
        except Exception:
            return {}


class ServiceBooking(models.Model):
    """Booking requests submitted by clients from the floating widget or book service page."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_bookings')
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    service_category = models.CharField(max_length=100)  # e.g. Website Dev, Mobile App, SaaS Product, AI Agent
    service_type = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking: {self.name} - {self.service_category} ({self.status})"


from decimal import Decimal

from django.utils.text import slugify

class CourseBatch(models.Model):
    """Course Batch (e.g. Batch 01, Batch 02, Batch 03)."""
    name = models.CharField(max_length=100)  # e.g., "Batch 01"
    code = models.CharField(max_length=50, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            base_code = slugify(self.name) or "batch"
            code = base_code
            counter = 1
            while CourseBatch.objects.filter(code=code).exclude(pk=self.pk).exists():
                code = f"{base_code}-{counter}"
                counter += 1
            self.code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class StudentEnrollment(models.Model):
    """Student course enrollment managed by Super Admin."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    batch = models.ForeignKey(CourseBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrollments')
    student_id = models.CharField(max_length=30, unique=True, blank=True)
    course_name = models.CharField(max_length=200)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)  # Negotiated course fee
    progress_percent = models.IntegerField(default=0)  # 0 to 100
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    certificate_id = models.CharField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def total_paid(self):
        payments = self.payments.filter(status='approved')
        return sum(p.amount for p in payments) if payments.exists() else Decimal('0.00')

    @property
    def pending_paid(self):
        payments = self.payments.filter(status='pending')
        return sum(p.amount for p in payments) if payments.exists() else Decimal('0.00')

    @property
    def due_amount(self):
        due = Decimal(str(self.total_fee)) - Decimal(str(self.total_paid))
        return max(Decimal('0.00'), due)

    @property
    def payment_status(self):
        paid = self.total_paid
        fee = Decimal(str(self.total_fee))
        if paid >= fee and fee > 0:
            return 'paid'
        elif paid > 0:
            return 'partial'
        return 'unpaid'

    def save(self, *args, **kwargs):
        if not self.student_id:
            num = random.randint(1000, 9999)
            self.student_id = f"QS-STU-{num}"
        if not self.certificate_id:
            num = random.randint(10000, 99999)
            self.certificate_id = f"QS-CERT-{num}"
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} — {self.student_id} ({self.course_name})"


class StudentPayment(models.Model):
    """Payment transaction record for student course fee / installments."""
    STATUS_CHOICES = [
        ('approved', 'Verified & Approved'),
        ('pending', 'Pending Verification'),
        ('rejected', 'Declined / Rejected'),
    ]
    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='payments')
    invoice_id = models.CharField(max_length=50, unique=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='bKash')  # bKash, Nagad, Bank, Cash, Card
    transaction_ref = models.CharField(max_length=100, blank=True)
    payment_proof = models.FileField(upload_to='payment_proofs/', blank=True, null=True)
    proof_image_data = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    admin_notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def proof_image_src(self):
        if self.proof_image_data:
            return self.proof_image_data
        if self.payment_proof:
            try:
                return self.payment_proof.url
            except Exception:
                pass
        return None

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            num = random.randint(10000, 99999)
            self.invoice_id = f"INV-{timezone.now().strftime('%Y')}-{num}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice_id} — {self.enrollment.student_id} (৳{self.amount})"


class CourseModule(models.Model):
    """LMS Course Module (e.g., Phase 1 Foundation, Module 2 Copywriting Mastery)."""
    course_slug = models.CharField(max_length=100, default='digital-marketing')
    module_number = models.IntegerField(default=1)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'module_number']

    def __str__(self):
        return f"Module {self.module_number}: {self.title}"


class CourseLesson(models.Model):
    """LMS Recorded Video Class Lesson under a Course Module."""
    VIDEO_TYPE_CHOICES = [
        ('youtube', 'YouTube Embed / Link'),
        ('vimeo', 'Vimeo Embed'),
        ('gdrive', 'Google Drive Video'),
        ('direct', 'Direct MP4 Video URL'),
    ]

    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='lessons')
    batch = models.ForeignKey(CourseBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='lessons')
    title = models.CharField(max_length=255)
    video_url = models.URLField(max_length=500)
    video_type = models.CharField(max_length=20, choices=VIDEO_TYPE_CHOICES, default='youtube')
    duration = models.CharField(max_length=50, default='01:00:00')
    order = models.IntegerField(default=1)
    notes = models.TextField(blank=True)
    resources_url = models.URLField(max_length=500, blank=True)
    is_free_preview = models.BooleanField(default=False)
    scheduled_at = models.DateTimeField(blank=True, null=True, help_text="Optional future date and time to auto-publish this lesson")
    is_published = models.BooleanField(default=True)
    auto_email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.module.title} — {self.title}"

    @property
    def embed_video_url(self):
        """Returns browser-friendly iframe embed URL for YouTube/Vimeo/GDrive/Direct."""
        url = self.video_url.strip()
        if not url:
            return ""
        
        # YouTube Shorts & Standard Videos
        if 'youtube.com' in url or 'youtu.be' in url:
            video_id = ""
            if 'shorts/' in url:
                video_id = url.split('shorts/')[1].split('?')[0].split('/')[0]
            elif 'v=' in url:
                video_id = url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in url:
                video_id = url.split('youtu.be/')[1].split('?')[0]
            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"

        # Google Drive Video Files
        if 'drive.google.com' in url:
            if '/file/d/' in url:
                file_id = url.split('/file/d/')[1].split('/')[0]
                return f"https://drive.google.com/file/d/{file_id}/preview"
            elif 'id=' in url:
                file_id = url.split('id=')[1].split('&')[0]
                return f"https://drive.google.com/file/d/{file_id}/preview"
            return url.replace('/view', '/preview')

        # Vimeo Videos
        if 'vimeo.com' in url:
            video_id = url.split('/')[-1]
            return f"https://player.vimeo.com/video/{video_id}"

        return url

    @property
    def is_mp4_video(self):
        url = self.video_url.strip().lower()
        return url.endswith('.mp4') or url.endswith('.webm') or url.endswith('.ogg')


class StudentLessonProgress(models.Model):
    """Tracks lesson completion for each enrolled student."""
    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='lesson_progresses')
    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, related_name='student_progresses')
    is_completed = models.BooleanField(default=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('enrollment', 'lesson')

    def __str__(self):
        return f"{self.enrollment.user.email} — {self.lesson.title} (Completed)"


class Notification(models.Model):
    """System-wide notification for users and superadmins across all services and automated tasks."""
    NOTIFICATION_TYPES = [
        ('payment', 'Payment & Billing'),
        ('booking', 'Service Booking'),
        ('course', 'Course & LMS'),
        ('agent', 'AI Agent Task'),
        ('system', 'System Alert'),
    ]

    CATEGORY_CHOICES = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True, help_text="Target user, or NULL for superadmin broadcast")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='system')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='info')
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.user.email if self.user else "Admins / Broadcast"
        return f"[{self.notification_type.upper()}] {self.title} -> {target}"


class LiveClassSchedule(models.Model):
    """Batch Live Class Meeting Schedule & Invitation System."""
    batch = models.ForeignKey(CourseBatch, on_delete=models.CASCADE, related_name='live_classes')
    title = models.CharField(max_length=255)
    meeting_link = models.URLField(max_length=500, help_text="Google Meet, Zoom, or Teams URL")
    scheduled_at = models.DateTimeField(help_text="Scheduled date and time for the live class")
    duration = models.CharField(max_length=50, default="1 Hour")
    agenda = models.TextField(blank=True, help_text="Class outline, topics covered, or mentor instructions")
    instructor_name = models.CharField(max_length=100, default="Qrious Tech Senior Mentor")
    recording_url = models.URLField(max_length=500, blank=True, null=True, help_text="Recorded Class Video Link (Google Drive, YouTube, Vimeo, etc.)")
    recorded_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    auto_email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"{self.batch.name} - {self.title} ({self.scheduled_at.strftime('%b %d, %Y %I:%M %p')})"


