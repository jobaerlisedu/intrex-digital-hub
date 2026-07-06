from django.contrib import admin
from . import models


@admin.register(models.Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'duration', 'fee', 'status', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['title', 'code']
    readonly_fields = ['id', 'created_at', 'updated_at']


class BatchInline(admin.TabularInline):
    model = models.Batch
    extra = 0
    fields = ['batch_id', 'status', 'start_date', 'end_date']


@admin.register(models.Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['batch_id', 'course', 'schedule', 'capacity', 'status', 'start_date', 'end_date']
    list_filter = ['status']
    search_fields = ['batch_id', 'course__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['course']


class PaymentInline(admin.StackedInline):
    model = models.Payment
    extra = 0
    can_delete = False


class AssessmentInline(admin.StackedInline):
    model = models.Assessment
    extra = 0
    can_delete = False


class CertificateInline(admin.StackedInline):
    model = models.Certificate
    extra = 0
    can_delete = False


class JobPlacementInline(admin.TabularInline):
    model = models.JobPlacement
    extra = 0


@admin.register(models.Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'full_name', 'course', 'batch', 'email', 'created_at']
    list_filter = ['is_free_batch', 'created_at']
    search_fields = ['student_id', 'full_name', 'email', 'phone']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['course', 'batch']
    inlines = [PaymentInline, AssessmentInline, CertificateInline, JobPlacementInline]


@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'student_name', 'total_fee', 'amount_paid', 'due_amount', 'status']
    list_filter = ['status', 'payment_type']
    search_fields = ['student_id', 'student_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['registration']


@admin.register(models.Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['category', 'sub_category', 'amount', 'date', 'payment_method']
    list_filter = ['category', 'payment_method']
    search_fields = ['category', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ['inquiry_key', 'name', 'email', 'subject', 'source', 'status', 'created_at']
    list_filter = ['status', 'source']
    search_fields = ['name', 'email', 'subject', 'inquiry_key']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.Institute)
class InstituteAdmin(admin.ModelAdmin):
    list_display = ['name', 'institute_type', 'location', 'status', 'is_active']
    list_filter = ['institute_type', 'status']
    search_fields = ['name', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.Ambassador)
class AmbassadorAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'region', 'commission_rate', 'status']
    list_filter = ['status', 'region']
    search_fields = ['name', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ['agent_name', 'month', 'year', 'referral_count', 'payout_amount', 'status']
    list_filter = ['status', 'month', 'year']
    search_fields = ['agent_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['agent']


@admin.register(models.Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'student_name', 'course_name', 'total_marks', 'grade', 'status']
    list_filter = ['status', 'grade']
    search_fields = ['student_id', 'student_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['registration', 'batch']


@admin.register(models.Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_id', 'student_name', 'course_name', 'issue_date', 'grade']
    list_filter = ['status']
    search_fields = ['certificate_id', 'student_name', 'student_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['registration']


@admin.register(models.JobPlacement)
class JobPlacementAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'company', 'job_title', 'placement_date', 'placement_type']
    list_filter = ['placement_type']
    search_fields = ['student_name', 'company', 'job_title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['registration', 'batch']


@admin.register(models.ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ['class_title', 'course', 'date', 'time', 'classroom_or_link']
    list_filter = ['date']
    search_fields = ['class_title', 'course__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['course']
