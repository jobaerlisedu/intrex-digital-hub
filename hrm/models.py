import uuid
from django.db import models
from django.conf import settings


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
    national_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='National ID')
    city = models.CharField(max_length=255, blank=True, null=True)
    zip = models.CharField(max_length=50, blank=True, null=True)
    account_holder = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
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

    def __str__(self):
        return self.key
