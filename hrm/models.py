import uuid
from django.db import models
from django.conf import settings
from django_cryptography.fields import encrypt


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='sub_departments')
    module_linking = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, default='')
    status = models.CharField(max_length=50, default='Active')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return self.name


class Position(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    title = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True, related_name='positions')
    sub_department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True, related_name='sub_positions')
    status = models.CharField(max_length=50, default='Active')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Position'
        verbose_name_plural = 'Positions'

    def __str__(self):
        return self.title


class Employee(models.Model):
    EMPLOYEE_TYPE_CHOICES = [
        ('Permanent', 'Permanent'),
        ('Probation', 'Probation'),
        ('Contractual', 'Contractual'),
        ('Intern', 'Intern'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('On Leave', 'On Leave'),
        ('Resigned', 'Resigned'),
        ('Inactive', 'Inactive'),
    ]
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    MARITAL_STATUS_CHOICES = [
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    contact_id = models.CharField(max_length=255, blank=True, null=True)
    emp_id = models.CharField(max_length=50, unique=True, verbose_name='Employee ID')
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    alt_phone = models.CharField(max_length=50, blank=True, null=True)
    national_id = encrypt(models.CharField(max_length=100, blank=True, null=True, verbose_name='National ID'))
    city = models.CharField(max_length=255, blank=True, null=True)
    zip = models.CharField(max_length=50, blank=True, null=True)
    account_holder = models.CharField(max_length=255, blank=True, null=True)
    account_number = encrypt(models.CharField(max_length=100, blank=True, null=True))
    branch_name = models.CharField(max_length=255, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    basic_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    house_rent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    conveyance_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    utility = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    mobile_bill = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True, related_name='employees')
    sub_department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True, related_name='sub_employees')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, blank=True, null=True, related_name='employees')
    additional_roles = models.JSONField(default=list, blank=True)
    employee_type = models.CharField(max_length=50, choices=EMPLOYEE_TYPE_CHOICES, default='Permanent')
    joining_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Active')
    exit_date = models.DateField(blank=True, null=True)
    exit_type = models.CharField(max_length=100, blank=True, null=True)
    exit_reason = models.TextField(blank=True, null=True)
    dob = models.DateField(blank=True, null=True, verbose_name='Date of Birth')
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)
    religion = models.CharField(max_length=100, blank=True, null=True)
    ec_primary_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Emergency Contact - Name')
    ec_primary_relation = models.CharField(max_length=100, blank=True, null=True, verbose_name='Emergency Contact - Relation')
    ec_primary_mobile = models.CharField(max_length=50, blank=True, null=True, verbose_name='Emergency Contact - Mobile')
    ec_secondary_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Secondary Emergency - Name')
    ec_secondary_relation = models.CharField(max_length=100, blank=True, null=True, verbose_name='Secondary Emergency - Relation')
    ec_secondary_mobile = models.CharField(max_length=50, blank=True, null=True, verbose_name='Secondary Emergency - Mobile')
    ec_tertiary_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Third Emergency - Name')
    ec_tertiary_relation = models.CharField(max_length=100, blank=True, null=True, verbose_name='Third Emergency - Relation')
    ec_tertiary_mobile = models.CharField(max_length=50, blank=True, null=True, verbose_name='Third Emergency - Mobile')
    nationality = models.CharField(max_length=100, blank=True, null=True)
    blood_group = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-'),
    ])
    work_permit_number = encrypt(models.CharField(max_length=100, blank=True, null=True))
    work_permit_expiry = models.DateField(blank=True, null=True)
    linkedin_url = models.URLField(max_length=500, blank=True, null=True)
    reporting_to = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='direct_reports',
        help_text="The manager/supervisor this employee reports to"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='hrm_employee_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='hrm_employee_updated')

    class Meta:
        ordering = ['emp_id']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'

    @property
    def name(self):
        return f'{self.first_name} {self.last_name}'

    def __str__(self):
        return f'{self.emp_id} - {self.name}'


class RecruitmentCandidate(models.Model):
    SOURCE_CHOICES = [
        ('LinkedIn', 'LinkedIn'), ('Job Board', 'Job Board'), ('Referral', 'Referral'),
        ('Company Website', 'Company Website'), ('Agency', 'Agency'),
        ('Social Media', 'Social Media'), ('Campus', 'Campus Recruitment'),
        ('Walk-in', 'Walk-in'), ('Other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Shortlisted', 'Shortlisted'),
        ('Interview', 'Interview'),
        ('Selected', 'Selected'),
        ('Rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    cand_id = models.CharField(max_length=50, unique=True, verbose_name='Candidate ID')
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='New')
    notes = models.TextField(blank=True, null=True)
    date_applied = models.DateField(blank=True, null=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, blank=True, null=True, help_text='Sourcing channel')
    rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True, help_text='Candidate rating (1-5)')
    resume = models.FileField(upload_to='hrm/resumes/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Recruitment Candidate'
        verbose_name_plural = 'Recruitment Candidates'

    def __str__(self):
        return f'{self.cand_id} - {self.name}'


class RecruitmentShortlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    candidate = models.ForeignKey(RecruitmentCandidate, on_delete=models.CASCADE, related_name='shortlists')
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    rating = models.CharField(max_length=50, blank=True, null=True)
    experience = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Recruitment Shortlist'
        verbose_name_plural = 'Recruitment Shortlists'

    def __str__(self):
        return f'{self.name} - {self.position}'


class RecruitmentInterview(models.Model):
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    candidate = models.ForeignKey(RecruitmentCandidate, on_delete=models.CASCADE, related_name='interviews')
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    interviewer = models.CharField(max_length=255, blank=True, null=True)
    date_time = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Scheduled')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_time']
        verbose_name = 'Recruitment Interview'
        verbose_name_plural = 'Recruitment Interviews'

    def __str__(self):
        return f'{self.name} - {self.position} ({self.status})'


class RecruitmentSelection(models.Model):
    OFFER_STATUS_CHOICES = [
        ('Offered', 'Offered'),
        ('Accepted', 'Accepted'),
        ('Joined', 'Joined'),
        ('Rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    candidate = models.ForeignKey(RecruitmentCandidate, on_delete=models.CASCADE, related_name='selections')
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    offer_status = models.CharField(max_length=50, choices=OFFER_STATUS_CHOICES, default='Offered')
    offer_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Recruitment Selection'
        verbose_name_plural = 'Recruitment Selections'

    def __str__(self):
        return f'{self.name} - {self.offer_status}'


class CandidateDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ('resume', 'Resume/CV'), ('cover_letter', 'Cover Letter'),
        ('certificate', 'Certificate'), ('id_proof', 'ID Proof'),
        ('reference', 'Reference Letter'), ('other', 'Other'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(RecruitmentCandidate, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOC_TYPE_CHOICES, default='resume')
    file = models.FileField(upload_to='hrm/candidate_docs/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Candidate Document'
        verbose_name_plural = 'Candidate Documents'
        managed = False

    def __str__(self):
        return f'{self.candidate.name} - {self.get_document_type_display()}'


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
        ('Half Day', 'Half Day'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    check_in = models.TimeField(blank=True, null=True)
    check_out = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Present')
    resolved = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-date', 'employee']
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        unique_together = ['employee', 'date']

    def __str__(self):
        return f'{self.employee.name} - {self.date} ({self.status})'


class Leave(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('Annual', 'Annual'),
        ('Sick', 'Sick'),
        ('Casual', 'Casual'),
        ('Maternity', 'Maternity'),
        ('Paternity', 'Paternity'),
        ('Unpaid', 'Unpaid'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPE_CHOICES, verbose_name='Type')
    from_date = models.DateField()
    to_date = models.DateField()
    duration = models.CharField(max_length=50, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-from_date']
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'

    def __str__(self):
        return f'{self.employee.name} - {self.leave_type} ({self.status})'


class Holiday(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    holiday_name = models.CharField(max_length=255)
    from_date = models.DateField()
    to_date = models.DateField()
    holiday_type = models.CharField(max_length=100, default='Public', verbose_name='Type')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['from_date']
        verbose_name = 'Holiday'
        verbose_name_plural = 'Holidays'

    def __str__(self):
        return self.holiday_name


class AdvanceSalary(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Deducted', 'Deducted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='advance_salaries')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    deduct_month = models.CharField(max_length=7, verbose_name='Deduction Month (YYYY-MM)')
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Advance Salary'
        verbose_name_plural = 'Advance Salaries'

    def __str__(self):
        return f'{self.employee.name} - {self.amount} ({self.status})'


class Payroll(models.Model):
    STATUS_CHOICES = [
        ('Generated', 'Generated'),
        ('Disbursed', 'Disbursed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    period = models.CharField(max_length=50, verbose_name='Pay Period')
    employee_count = models.IntegerField(default=0)
    total_net_pay = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Generated')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payroll Record'
        verbose_name_plural = 'Payroll Records'

    def __str__(self):
        return f'{self.period} ({self.status})'


class PayrollEmployee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='employees')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payroll_entries')
    basic_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    house_rent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    conveyance_allowance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    utility = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    mobile_bill = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gross_pay = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['employee']
        verbose_name = 'Payroll Employee'
        verbose_name_plural = 'Payroll Employees'
        managed = False
        unique_together = ['payroll', 'employee']

    def __str__(self):
        return f'{self.payroll.period} - {self.employee.name}'


class EmployeeShift(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='shifts')
    shift_name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Employee Shift'
        verbose_name_plural = 'Employee Shifts'

    def __str__(self):
        return f'{self.employee.name} - {self.shift_name}'


class OnboardingTask(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='onboarding_tasks')
    task_name = models.CharField(max_length=255)
    due_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']
        verbose_name = 'Onboarding Task'
        verbose_name_plural = 'Onboarding Tasks'

    def __str__(self):
        return f'{self.employee.name} - {self.task_name}'


class ExitClearance(models.Model):
    CLEARANCE_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Cleared', 'Cleared'),
    ]
    OVERALL_STATUS_CHOICES = [
        ('In Progress', 'In Progress'),
        ('Cleared', 'Cleared'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='exit_clearances')
    exit_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    it_clearance = models.CharField(max_length=50, choices=CLEARANCE_STATUS_CHOICES, default='Pending')
    finance_clearance = models.CharField(max_length=50, choices=CLEARANCE_STATUS_CHOICES, default='Pending')
    hr_clearance = models.CharField(max_length=50, choices=CLEARANCE_STATUS_CHOICES, default='Pending')
    status = models.CharField(max_length=50, choices=OVERALL_STATUS_CHOICES, default='In Progress')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Exit Clearance'
        verbose_name_plural = 'Exit Clearances'

    def __str__(self):
        return f'{self.employee.name} - {self.status}'


class ExpenseClaim(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='expense_claims')
    category = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Expense Claim'
        verbose_name_plural = 'Expense Claims'

    def __str__(self):
        return f'{self.employee.name} - {self.amount} ({self.status})'


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=255)
    document_number = models.CharField(max_length=255, blank=True, default='')
    expiry_date = models.DateField(blank=True, null=True)
    file = models.FileField(upload_to='hrm/documents/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['document_type']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        return f'{self.employee.name} - {self.document_type}'


class Asset(models.Model):
    STATUS_CHOICES = [
        ('Assigned', 'Assigned'),
        ('Returned', 'Returned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='assets')
    asset_name = models.CharField(max_length=255)
    asset_tag = models.CharField(max_length=255, blank=True, default='')
    serial_number = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Assigned')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['asset_name']
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'

    def __str__(self):
        return f'{self.asset_name} - {self.employee.name}'


class HRMSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=255, unique=True)
    value = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['key']
        verbose_name = 'HRM Setting'
        verbose_name_plural = 'HRM Settings'
        managed = False

    def __str__(self):
        return self.key


# ── Performance Management ─────────────────────────────────────────────

class ReviewCycle(models.Model):
    STATUS_CHOICES = [('Draft', 'Draft'), ('Active', 'Active'), ('Closed', 'Closed')]
    TYPE_CHOICES = [('Quarterly', 'Quarterly'), ('Half-Yearly', 'Half-Yearly'), ('Annual', 'Annual')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    review_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='Half-Yearly')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Review Cycle'
        verbose_name_plural = 'Review Cycles'

    def __str__(self):
        return self.name


class RatingTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Rating Template'
        verbose_name_plural = 'Rating Templates'

    def __str__(self):
        return self.name


class RatingScale(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    template = models.ForeignKey(RatingTemplate, on_delete=models.CASCADE, related_name='scales')
    label = models.CharField(max_length=100)
    value = models.DecimalField(max_digits=3, decimal_places=1)
    definition = models.TextField(blank=True, default='')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template', 'order']
        verbose_name = 'Rating Scale Value'
        verbose_name_plural = 'Rating Scale Values'

    def __str__(self):
        return f'{self.template.name}: {self.label} ({self.value})'


class KPI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    unit = models.CharField(max_length=50, blank=True, default='')
    target_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    default_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'KPI Definition'
        verbose_name_plural = 'KPI Definitions'

    def __str__(self):
        return self.name


class EmployeeKPI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='kpis')
    review_cycle = models.ForeignKey(ReviewCycle, on_delete=models.CASCADE, related_name='employee_kpis')
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE, related_name='assignments')
    target_value = models.DecimalField(max_digits=14, decimal_places=2)
    actual_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comments = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee', 'review_cycle']
        verbose_name = 'Employee KPI'
        verbose_name_plural = 'Employee KPIs'
        unique_together = ['employee', 'review_cycle', 'kpi']

    def __str__(self):
        return f'{self.employee.name} - {self.kpi.name} ({self.review_cycle.name})'


class PerformanceReview(models.Model):
    STATUS_CHOICES = [
        ('Self-Assessment', 'Self-Assessment'),
        ('Manager-Review', 'Manager Review'),
        ('HR-Review', 'HR Review'),
        ('Completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reviews_given')
    review_cycle = models.ForeignKey(ReviewCycle, on_delete=models.CASCADE, related_name='reviews')
    rating_template = models.ForeignKey(RatingTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rating = models.ForeignKey(RatingScale, on_delete=models.SET_NULL, null=True, blank=True)
    strengths = models.TextField(blank=True, default='')
    improvements = models.TextField(blank=True, default='')
    goals = models.TextField(blank=True, default='')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Self-Assessment')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Performance Review'
        verbose_name_plural = 'Performance Reviews'
        unique_together = ['employee', 'review_cycle']

    def __str__(self):
        return f'{self.employee.name} - {self.review_cycle.name} ({self.status})'


class PerformanceImprovementPlan(models.Model):
    STATUS_CHOICES = [('Open', 'Open'), ('In Progress', 'In Progress'), ('Completed', 'Completed'), ('Failed', 'Failed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='pips')
    review = models.ForeignKey(PerformanceReview, on_delete=models.SET_NULL, null=True, blank=True, related_name='pips')
    issue_description = models.TextField()
    improvement_goals = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Open')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Performance Improvement Plan'
        verbose_name_plural = 'Performance Improvement Plans'

    def __str__(self):
        return f'{self.employee.name} - {self.status}'


class PIPMilestone(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Achieved', 'Achieved'), ('Missed', 'Missed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    pip = models.ForeignKey(PerformanceImprovementPlan, on_delete=models.CASCADE, related_name='milestones')
    description = models.CharField(max_length=255)
    due_date = models.DateField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pip', 'due_date']
        verbose_name = 'PIP Milestone'
        verbose_name_plural = 'PIP Milestones'

    def __str__(self):
        return f'{self.pip.employee.name} - {self.description}'


# ── Leave Balance Tracking ─────────────────────────────────────────────

class LeavePolicy(models.Model):
    EMPLOYEE_TYPE_CHOICES = [
        ('Permanent', 'Permanent'), ('Probation', 'Probation'),
        ('Contractual', 'Contractual'), ('Intern', 'Intern'),
    ]
    LEAVE_TYPE_CHOICES = [
        ('Annual', 'Annual'), ('Sick', 'Sick'), ('Casual', 'Casual'),
        ('Maternity', 'Maternity'), ('Paternity', 'Paternity'), ('Unpaid', 'Unpaid'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee_type = models.CharField(max_length=50, choices=EMPLOYEE_TYPE_CHOICES)
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPE_CHOICES)
    entitled_days = models.DecimalField(max_digits=5, decimal_places=1)
    carry_forward_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee_type', 'leave_type']
        verbose_name = 'Leave Policy'
        verbose_name_plural = 'Leave Policies'
        unique_together = ['employee_type', 'leave_type']

    def __str__(self):
        return f'{self.employee_type} - {self.leave_type} ({self.entitled_days}d)'


class LeaveBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.CharField(max_length=50)
    entitled = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    available = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    period = models.CharField(max_length=7, verbose_name='Year (YYYY)')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee', 'leave_type']
        verbose_name = 'Leave Balance'
        verbose_name_plural = 'Leave Balances'
        unique_together = ['employee', 'leave_type', 'period']

    def save(self, *args, **kwargs):
        self.available = self.entitled - self.used - self.pending
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.employee.name} - {self.leave_type} {self.period} ({self.available}d)'


# ── Training & Development ──────────────────────────────────────────

class TrainingNeed(models.Model):
    PRIORITY_CHOICES = [('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')]
    STATUS_CHOICES = [('Identified', 'Identified'), ('Approved', 'Approved'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_needs')
    skill_gap = models.CharField(max_length=255, help_text='Skill or knowledge gap identified')
    recommended_training = models.CharField(max_length=255, blank=True, default='')
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Identified')
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Training Need'
        verbose_name_plural = 'Training Needs'

    def __str__(self):
        return f'{self.employee.name} - {self.skill_gap}'


class DevelopmentPlan(models.Model):
    STATUS_CHOICES = [('Draft', 'Draft'), ('Active', 'Active'), ('Completed', 'Completed'), ('On Hold', 'On Hold')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='development_plans')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    goals = models.TextField(blank=True, default='')
    start_date = models.DateField()
    target_end_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Development Plan'
        verbose_name_plural = 'Development Plans'

    def __str__(self):
        return f'{self.employee.name} - {self.title}'


class TrainingNomination(models.Model):
    STATUS_CHOICES = [('Nominated', 'Nominated'), ('Enrolled', 'Enrolled'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_nominations')
    course_name = models.CharField(max_length=255)
    provider = models.CharField(max_length=255, blank=True, default='')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Nominated')
    certificate_issued = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Training Nomination'
        verbose_name_plural = 'Training Nominations'

    def __str__(self):
        return f'{self.employee.name} - {self.course_name}'


# ── Notifications ─────────────────────────────────────────────────────

class Notification(models.Model):
    CHANNEL_CHOICES = [('in_app', 'In-App'), ('email', 'Email'), ('push', 'Push')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    channel = models.CharField(max_length=50, choices=CHANNEL_CHOICES, default='in_app')
    notification_type = models.CharField(max_length=100, blank=True, default='', db_index=True, help_text='e.g. leave_approved, review_assigned')
    link = models.CharField(max_length=500, blank=True, default='')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f'{self.recipient.username} - {self.title[:50]}'


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_prefs')
    notify_in_app = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=False)
    notify_push = models.BooleanField(default=False)
    digest_frequency = models.CharField(max_length=50, default='instant', choices=[
        ('instant', 'Instant'), ('daily', 'Daily Digest'), ('weekly', 'Weekly Digest')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
        managed = False

    def __str__(self):
        return f'{self.user.username} prefs'


class DeviceToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_tokens')
    fcm_token = models.CharField(max_length=500)
    platform = models.CharField(max_length=50, blank=True, default='', help_text='web/android/ios')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Device Token'
        verbose_name_plural = 'Device Tokens'
        managed = False
        unique_together = ['user', 'fcm_token']

    def __str__(self):
        return f'{self.user.username} - {self.platform or "unknown"}'


# ── Succession Planning ───────────────────────────────────────────────

class KeyPosition(models.Model):
    RISK_CHOICES = [('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Critical', 'Critical')]
    STATUS_CHOICES = [('Active', 'Active'), ('Filled', 'Filled'), ('On Hold', 'On Hold'), ('Inactive', 'Inactive')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    position_title = models.CharField(max_length=255)
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name='key_positions')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='key_positions')
    incumbent = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='incumbent_positions')
    risk_of_vacancy = models.CharField(max_length=50, choices=RISK_CHOICES, default='Medium')
    readiness_gap = models.TextField(blank=True, default='', help_text='Skills/experience gap if incumbent leaves')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Active')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['position_title']
        verbose_name = 'Key Position'
        verbose_name_plural = 'Key Positions'

    def __str__(self):
        return self.position_title


class SuccessorCandidate(models.Model):
    READINESS_CHOICES = [
        ('Now', 'Ready Now'),
        ('1-2 Years', 'Ready in 1-2 Years'),
        ('3-5 Years', 'Ready in 3-5 Years'),
        ('Long Term', 'Long Term Potential'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    key_position = models.ForeignKey(KeyPosition, on_delete=models.CASCADE, related_name='candidates')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='successor_candidates')
    readiness = models.CharField(max_length=50, choices=READINESS_CHOICES, default='3-5 Years')
    strengths = models.TextField(blank=True, default='')
    development_needs = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    is_primary = models.BooleanField(default=False, help_text='Primary successor recommendation')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['key_position', '-is_primary', 'readiness']
        verbose_name = 'Successor Candidate'
        verbose_name_plural = 'Successor Candidates'
        unique_together = ['key_position', 'employee']

    def __str__(self):
        return f'{self.employee.name} -> {self.key_position.position_title}'


class SuccessionPlan(models.Model):
    STATUS_CHOICES = [('Draft', 'Draft'), ('Active', 'Active'), ('Completed', 'Completed'), ('On Hold', 'On Hold')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='succession_plans')
    review_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Succession Plan'
        verbose_name_plural = 'Succession Plans'

    def __str__(self):
        return self.title


# ── Employee Skills & Education ─────────────────────────────────────────

class EmployeeEducation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='education')
    degree = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    field_of_study = models.CharField(max_length=255, blank=True, default='')
    start_year = models.IntegerField(blank=True, null=True)
    end_year = models.IntegerField(blank=True, null=True)
    grade = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-end_year', 'degree']
        verbose_name = 'Education History'
        verbose_name_plural = 'Education Histories'
        managed = False

    def __str__(self):
        return f'{self.employee.name} - {self.degree} ({self.institution})'


class EmployeeExperience(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='experiences')
    company = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Work Experience'
        verbose_name_plural = 'Work Experiences'
        managed = False

    def __str__(self):
        return f'{self.employee.name} - {self.job_title} @ {self.company}'


class EmployeeSkill(models.Model):
    PROFICIENCY_CHOICES = [
        ('Beginner', 'Beginner'), ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'), ('Expert', 'Expert'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='skills')
    skill_name = models.CharField(max_length=255)
    proficiency = models.CharField(max_length=50, choices=PROFICIENCY_CHOICES, default='Intermediate')
    years_of_experience = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee', '-proficiency']
        verbose_name = 'Employee Skill'
        verbose_name_plural = 'Employee Skills'
        managed = False
        unique_together = ['employee', 'skill_name']

    def __str__(self):
        return f'{self.employee.name} - {self.skill_name}'


class Competency(models.Model):
    CATEGORY_CHOICES = [
        ('Technical', 'Technical'), ('Behavioral', 'Behavioral'),
        ('Leadership', 'Leadership'), ('Functional', 'Functional'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Technical')
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Competency'
        verbose_name_plural = 'Competencies'
        managed = False

    def __str__(self):
        return f'{self.name} ({self.category})'


class CompetencyRating(models.Model):
    RATING_CHOICES = [(1, '1 - Needs Improvement'), (2, '2 - Developing'), (3, '3 - Proficient'), (4, '4 - Advanced'), (5, '5 - Expert')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='competency_ratings')
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(choices=RATING_CHOICES)
    assessed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    assessment_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-assessment_date']
        verbose_name = 'Competency Rating'
        verbose_name_plural = 'Competency Ratings'
        managed = False
        unique_together = ['employee', 'competency', 'assessment_date']

    def __str__(self):
        return f'{self.employee.name} - {self.competency.name}: {self.rating}'


# ── 360° Feedback ────────────────────────────────────────────────────────

class FeedbackQuestion(models.Model):
    CATEGORY_CHOICES = [
        ('Collaboration', 'Collaboration'), ('Communication', 'Communication'),
        ('Leadership', 'Leadership'), ('Technical', 'Technical Skills'),
        ('Reliability', 'Reliability'), ('Innovation', 'Innovation'),
        ('Culture', 'Culture Fit'), ('General', 'General'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    question_text = models.TextField()
    is_required = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'order']
        verbose_name = 'Feedback Question'
        verbose_name_plural = 'Feedback Questions'
        managed = False

    def __str__(self):
        return f'[{self.category}] {self.question_text[:60]}'


class FeedbackRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'), ('In Progress', 'In Progress'),
        ('Completed', 'Completed'), ('Cancelled', 'Cancelled'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedback_reviews')
    reviewee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='feedback_received')
    review_cycle = models.ForeignKey('ReviewCycle', on_delete=models.SET_NULL, null=True, blank=True, related_name='feedback_requests')
    relationship = models.CharField(max_length=50, blank=True, default='', help_text='Manager / Peer / Subordinate / Self')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    due_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '360 Feedback Request'
        verbose_name_plural = '360 Feedback Requests'
        managed = False
        unique_together = ['reviewer', 'reviewee', 'review_cycle']

    def __str__(self):
        return f'{self.reviewer.username} {self.reviewee.name} ({self.status})'


class FeedbackResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(FeedbackRequest, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(FeedbackQuestion, on_delete=models.CASCADE, related_name='responses')
    rating = models.IntegerField(blank=True, null=True, help_text='Rating 1-5')
    response_text = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['request', 'question__order']
        verbose_name = 'Feedback Response'
        verbose_name_plural = 'Feedback Responses'
        managed = False
        unique_together = ['request', 'question']

    def __str__(self):
        return f'{self.request.reviewer.username} Q:{self.question.id}'


# ── Engagement Surveys ──────────────────────────────────────────────────

class EngagementSurvey(models.Model):
    STATUS_CHOICES = [('Draft', 'Draft'), ('Open', 'Open'), ('Closed', 'Closed')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_anonymous = models.BooleanField(default=False, help_text='Responses are anonymous')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Engagement Survey'
        verbose_name_plural = 'Engagement Surveys'
        managed = False

    def __str__(self):
        return self.title


class SurveyQuestion(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('rating', 'Rating (1-5)'), ('text', 'Text'),
        ('multiple_choice', 'Multiple Choice'), ('yes_no', 'Yes/No'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.ForeignKey(EngagementSurvey, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPE_CHOICES, default='rating')
    options_json = models.JSONField(default=list, blank=True, help_text='Options for multiple_choice')
    order = models.IntegerField(default=0)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['survey', 'order']
        verbose_name = 'Survey Question'
        verbose_name_plural = 'Survey Questions'
        managed = False

    def __str__(self):
        return f'{self.survey.title} - Q{self.order}'


class SurveyResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.ForeignKey(EngagementSurvey, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name='responses')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, blank=True, null=True, related_name='survey_responses')
    response_text = models.TextField(blank=True, default='')
    response_value = models.IntegerField(blank=True, null=True, help_text='Numeric rating')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['survey', 'question']
        verbose_name = 'Survey Response'
        verbose_name_plural = 'Survey Responses'
        managed = False
        unique_together = [['survey', 'question', 'employee']]

    def __str__(self):
        return f'{self.survey.title} - Q{self.question.order}'


# ── HR Compliance Calendar ──────────────────────────────────────────────

class ComplianceReminder(models.Model):
    REMINDER_TYPE_CHOICES = [
        ('visa', 'Visa Renewal'), ('work_permit', 'Work Permit'),
        ('contract', 'Contract Renewal'), ('certification', 'Certification Renewal'),
        ('probation', 'Probation Review'), ('medical', 'Medical Checkup'),
        ('training', 'Mandatory Training'), ('other', 'Other'),
    ]
    STATUS_CHOICES = [('Pending', 'Pending'), ('Overdue', 'Overdue'), ('Completed', 'Completed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='compliance_reminders')
    reminder_type = models.CharField(max_length=50, choices=REMINDER_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    due_date = models.DateField()
    completed_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']
        verbose_name = 'Compliance Reminder'
        verbose_name_plural = 'Compliance Reminders'
        managed = False

    def __str__(self):
        return f'{self.employee.name} - {self.title} ({self.due_date})'

    def mark_completed(self):
        from django.utils import timezone
        self.status = 'Completed'
        self.completed_date = timezone.now().date()
        self.save(update_fields=['status', 'completed_date'])

    @classmethod
    def auto_create_from_document(cls, document):
        """Create or update a compliance reminder from a Document with expiry_date."""
        if not document.expiry_date:
            return None
        reminder, created = cls.objects.get_or_create(
            employee=document.employee,
            reminder_type='other',
            title=f"{document.document_type} Expiry",
            defaults={
                'description': f"Document #{document.document_number} expires on {document.expiry_date}",
                'due_date': document.expiry_date,
            }
        )
        if not created:
            reminder.due_date = document.expiry_date
            reminder.description = f"Document #{document.document_number} expires on {document.expiry_date}"
            reminder.is_active = True
            reminder.save(update_fields=['due_date', 'description', 'is_active'])
        return reminder


# ── Talent Review & 9-Box Grid ──────────────────────────────────────────

class TalentReviewMeeting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    meeting_date = models.DateField()
    notes = models.TextField(blank=True, default='')
    status = models.CharField(max_length=50, default='Draft', choices=[
        ('Draft', 'Draft'), ('Completed', 'Completed'),
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ['-meeting_date']
        verbose_name = 'Talent Review Meeting'
        verbose_name_plural = 'Talent Review Meetings'
        managed = False

    def __str__(self):
        return f'{self.title} ({self.meeting_date})'


class NineBoxCell(models.Model):
    RATING_CHOICES = [('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    talent_review = models.ForeignKey(TalentReviewMeeting, on_delete=models.CASCADE, related_name='nine_box_cells')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='nine_box_ratings')
    performance = models.CharField(max_length=50, choices=RATING_CHOICES)
    potential = models.CharField(max_length=50, choices=RATING_CHOICES)
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['talent_review', 'employee']
        verbose_name = '9-Box Cell'
        verbose_name_plural = '9-Box Cells'
        managed = False
        unique_together = ['talent_review', 'employee']

    def __str__(self):
        return f'{self.employee.name} (P:{self.performance} / Pot:{self.potential})'


# ── Disciplinary Management ──────────────────────────────────────

class DisciplinaryCase(models.Model):
    SEVERITY_CHOICES = [
        ('Minor', 'Minor'),
        ('Major', 'Major'),
        ('Gross', 'Gross Misconduct'),
    ]
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Under Investigation', 'Under Investigation'),
        ('Hearing Scheduled', 'Hearing Scheduled'),
        ('Resolved', 'Resolved'),
        ('Dismissed', 'Dismissed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='disciplinary_cases')
    case_number = models.CharField(max_length=50, unique=True)
    incident_date = models.DateField()
    nature_of_offense = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='Minor')
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Open')
    resolution = models.TextField(blank=True, default='')
    resolved_date = models.DateField(null=True, blank=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_cases')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Disciplinary Case'
        verbose_name_plural = 'Disciplinary Cases'
        managed = False

    def __str__(self):
        return f'{self.case_number} - {self.employee}'

    def save(self, *args, **kwargs):
        if not self.case_number:
            import datetime
            year = datetime.datetime.now().strftime('%Y')
            prefix = f'DC-{year}-'
            last = DisciplinaryCase.objects.filter(case_number__startswith=prefix).order_by('case_number').last()
            num = int(last.case_number.split('-')[-1]) + 1 if last else 1
            self.case_number = f'{prefix}{num:04d}'
        super().save(*args, **kwargs)


class DisciplinaryHearing(models.Model):
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Postponed', 'Postponed'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(DisciplinaryCase, on_delete=models.CASCADE, related_name='hearings')
    hearing_date = models.DateTimeField()
    panel_members = models.TextField(blank=True, default='', help_text='Comma-separated names of panel members')
    location = models.CharField(max_length=255, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    outcome = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-hearing_date']
        verbose_name = 'Disciplinary Hearing'
        verbose_name_plural = 'Disciplinary Hearings'
        managed = False

    def __str__(self):
        return f'Hearing for {self.case.case_number} on {self.hearing_date.date()}'


class DisciplinaryAction(models.Model):
    ACTION_CHOICES = [
        ('Verbal Warning', 'Verbal Warning'),
        ('Written Warning', 'Written Warning'),
        ('Final Written Warning', 'Final Written Warning'),
        ('Suspension', 'Suspension'),
        ('Pay Cut', 'Pay Cut'),
        ('Demotion', 'Demotion'),
        ('Termination', 'Termination'),
        ('Other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Issued', 'Issued'),
        ('Under Appeal', 'Under Appeal'),
        ('Enforced', 'Enforced'),
        ('Overturned', 'Overturned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(DisciplinaryCase, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()
    issued_date = models.DateField()
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True, help_text='For warnings/suspensions with limited duration')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_actions')
    supporting_document = models.TextField(blank=True, default='', help_text='URL or reference to supporting document')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issued_date']
        verbose_name = 'Disciplinary Action'
        verbose_name_plural = 'Disciplinary Actions'
        managed = False

    def __str__(self):
        return f'{self.action_type} - {self.case.case_number}'


class DisciplinaryAppeal(models.Model):
    STATUS_CHOICES = [
        ('Submitted', 'Submitted'),
        ('Under Review', 'Under Review'),
        ('Upheld', 'Upheld'),
        ('Overturned', 'Overturned'),
        ('Rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.ForeignKey(DisciplinaryAction, on_delete=models.CASCADE, related_name='appeals')
    appeal_date = models.DateField()
    grounds = models.TextField(help_text='Reasons for the appeal')
    supporting_evidence = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Submitted')
    decision_date = models.DateField(null=True, blank=True)
    decision_notes = models.TextField(blank=True, default='')
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='appeal_decisions')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appeal_date']
        verbose_name = 'Disciplinary Appeal'
        verbose_name_plural = 'Disciplinary Appeals'
        managed = False

    def __str__(self):
        return f'Appeal against {self.action} on {self.appeal_date}'
