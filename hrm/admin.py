from django.contrib import admin
from . import models


@admin.register(models.Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'status', 'is_active', 'created_at']
    list_filter = ['status', 'is_active']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['parent']


@admin.register(models.Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'status', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['department', 'sub_department']


class PayrollEmployeeInline(admin.TabularInline):
    model = models.PayrollEmployee
    extra = 1
    raw_id_fields = ['employee']


@admin.register(models.Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['emp_id', 'name', 'department', 'position', 'status', 'is_active']
    list_filter = ['status', 'employee_type', 'gender', 'department', 'is_active']
    search_fields = ['emp_id', 'first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['department', 'sub_department', 'position', 'created_by', 'updated_by']
    fieldsets = [
        ('Identification', {'fields': ['emp_id', 'first_name', 'last_name', 'email', 'phone', 'alt_phone', 'national_id']}),
        ('Employment', {'fields': ['employee_type', 'department', 'sub_department', 'position', 'additional_roles', 'joining_date', 'status', 'exit_date', 'exit_type', 'exit_reason']}),
        ('Salary', {'fields': ['basic_salary', 'house_rent', 'medical_allowance', 'conveyance_allowance', 'utility', 'mobile_bill', 'gross_salary']}),
        ('Bank Details', {'fields': ['account_holder', 'account_number', 'bank_name', 'branch_name']}),
        ('Personal', {'fields': ['dob', 'gender', 'marital_status', 'religion', 'city', 'zip']}),
        ('Emergency Contact', {'fields': ['ec_primary_name', 'ec_primary_relation', 'ec_primary_mobile', 'ec_secondary_name', 'ec_secondary_relation', 'ec_secondary_mobile']}),
        ('Metadata', {'fields': ['id', 'contact_id', 'firestore_id', 'is_active', 'created_by', 'updated_by', 'created_at', 'updated_at']}),
    ]


@admin.register(models.RecruitmentCandidate)
class RecruitmentCandidateAdmin(admin.ModelAdmin):
    list_display = ['cand_id', 'name', 'position', 'status', 'date_applied']
    list_filter = ['status']
    search_fields = ['name', 'cand_id', 'position']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.RecruitmentShortlist)
class RecruitmentShortlistAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['name', 'position']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.RecruitmentInterview)
class RecruitmentInterviewAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'interviewer', 'date_time', 'status']
    list_filter = ['status']
    search_fields = ['name', 'interviewer']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.RecruitmentSelection)
class RecruitmentSelectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'offer_status', 'offer_date']
    list_filter = ['offer_status']
    search_fields = ['name', 'position']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'status']
    list_filter = ['status', 'date']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'from_date', 'to_date', 'duration', 'status']
    list_filter = ['status', 'leave_type']
    search_fields = ['employee__first_name', 'employee__last_name', 'reason']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['holiday_name', 'from_date', 'to_date', 'holiday_type']
    list_filter = ['holiday_type']
    search_fields = ['holiday_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.AdvanceSalary)
class AdvanceSalaryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'amount', 'deduct_month', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['period', 'employee_count', 'total_net_pay', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['period']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [PayrollEmployeeInline]


@admin.register(models.PayrollEmployee)
class PayrollEmployeeAdmin(admin.ModelAdmin):
    list_display = ['payroll', 'employee', 'gross_pay', 'net_pay']
    list_filter = ['payroll__period']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['payroll', 'employee']


@admin.register(models.EmployeeShift)
class EmployeeShiftAdmin(admin.ModelAdmin):
    list_display = ['employee', 'shift_name', 'start_date', 'end_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'shift_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = ['employee', 'task_name', 'due_date', 'status']
    list_filter = ['status']
    search_fields = ['employee__first_name', 'employee__last_name', 'task_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.ExitClearance)
class ExitClearanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'exit_date', 'it_clearance', 'finance_clearance', 'hr_clearance', 'status']
    list_filter = ['status', 'it_clearance', 'finance_clearance', 'hr_clearance']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.ExpenseClaim)
class ExpenseClaimAdmin(admin.ModelAdmin):
    list_display = ['employee', 'category', 'amount', 'status', 'created_at']
    list_filter = ['status', 'category']
    search_fields = ['employee__first_name', 'employee__last_name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'document_type', 'document_number', 'expiry_date']
    list_filter = ['document_type']
    search_fields = ['employee__first_name', 'employee__last_name', 'document_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['asset_name', 'asset_tag', 'employee', 'status']
    list_filter = ['status']
    search_fields = ['asset_name', 'asset_tag', 'serial_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.HRMSetting)
class HRMSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'is_active']
    search_fields = ['key']
    readonly_fields = ['id', 'created_at', 'updated_at']
