import uuid
from django.db import models
from django.conf import settings


class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    title = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)
    target = models.CharField(max_length=255, blank=True, default='')
    trainer = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    duration = models.CharField(max_length=255, blank=True, default='')
    fee = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=50, default='Active')
    icon = models.CharField(max_length=100, default='bi bi-book')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['title']
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'

    def __str__(self):
        return f'{self.code or ""} - {self.title}'


class Batch(models.Model):
    STATUS_CHOICES = [
        ('Upcoming', 'Upcoming'),
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    batch_id = models.CharField(max_length=100, unique=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='batches')
    schedule = models.CharField(max_length=255, blank=True, null=True)
    class_days = models.CharField(max_length=255, blank=True, null=True, verbose_name='Class Days')
    capacity = models.IntegerField(default=10)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Upcoming')
    trainer = models.CharField(max_length=255, blank=True, default='')
    trainer_id = models.CharField(max_length=255, blank=True, default='')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    total_classes = models.IntegerField(default=12)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'

    def __str__(self):
        return self.batch_id


class Registration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    student_id = models.CharField(max_length=100, unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=50)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='registrations')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, blank=True, null=True, related_name='registrations')
    education = models.CharField(max_length=255, blank=True, null=True)
    schedule = models.CharField(max_length=255, blank=True, null=True)
    class_days = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField(blank=True, default='')
    is_job_holder = models.BooleanField(default=False)
    company_name = models.CharField(max_length=255, blank=True, default='')
    designation = models.CharField(max_length=255, blank=True, default='')
    kam = models.CharField(max_length=255, blank=True, null=True)
    is_free_batch = models.BooleanField(default=False)
    contact_id = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Registration'
        verbose_name_plural = 'Registrations'

    def __str__(self):
        return f'{self.student_id} - {self.full_name}'


class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Mobile Banking', 'Mobile Banking'),
        ('Card', 'Card'),
    ]
    STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Partially Paid', 'Partially Paid'),
        ('Fully Paid', 'Fully Paid'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    registration = models.OneToOneField(Registration, on_delete=models.CASCADE, related_name='payment')
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, blank=True, null=True)
    course_name = models.CharField(max_length=255)
    batch = models.CharField(max_length=255, blank=True, null=True)
    total_fee = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Unpaid')
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE_CHOICES, default='Cash')
    transaction_id = models.CharField(max_length=255, blank=True, default='')
    registration_fee = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    installments = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f'{self.student_id} - {self.status}'


class Expense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    category = models.CharField(max_length=255)
    sub_category = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateField()
    payment_method = models.CharField(max_length=100, default='Cash')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-date']
        verbose_name = 'Training Expense'
        verbose_name_plural = 'Training Expenses'

    def __str__(self):
        return f'{self.category} - {self.amount}'


class Inquiry(models.Model):
    SOURCE_CHOICES = [
        ('Direct', 'Direct'),
        ('Website', 'Website'),
        ('Referral', 'Referral'),
        ('Social Media', 'Social Media'),
        ('Other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Converted', 'Converted'),
        ('Lost', 'Lost'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    inquiry_key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=50)
    subject = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='Direct')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='New')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Inquiry'
        verbose_name_plural = 'Inquiries'

    def __str__(self):
        return f'{self.inquiry_key} - {self.name}'


class Institute(models.Model):
    INSTITUTE_TYPE_CHOICES = [
        ('University', 'University'),
        ('College', 'College'),
        ('School', 'School'),
        ('Training Center', 'Training Center'),
        ('Corporate', 'Corporate'),
        ('Other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    institute_type = models.CharField(max_length=50, choices=INSTITUTE_TYPE_CHOICES, default='University', verbose_name='Type')
    location = models.CharField(max_length=255, blank=True, null=True)
    website = models.URLField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default='Active')
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['name']
        verbose_name = 'Institute'
        verbose_name_plural = 'Institutes'

    def __str__(self):
        return self.name


class Ambassador(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=50)
    region = models.CharField(max_length=255, blank=True, null=True)
    commission_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='Commission Rate (%)')
    status = models.CharField(max_length=50, default='Active')
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['name']
        verbose_name = 'Brand Ambassador'
        verbose_name_plural = 'Brand Ambassadors'

    def __str__(self):
        return self.name


class Commission(models.Model):
    STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    agent = models.ForeignKey(Ambassador, on_delete=models.CASCADE, related_name='commissions')
    agent_name = models.CharField(max_length=255)
    month = models.CharField(max_length=20)
    year = models.CharField(max_length=10)
    referral_count = models.IntegerField(default=0)
    payout_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Unpaid')
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Commission'
        verbose_name_plural = 'Commissions'

    def __str__(self):
        return f'{self.agent_name} - {self.month}/{self.year}'


class Assessment(models.Model):
    GRADE_CHOICES = [
        ('A+', 'A+'),
        ('A', 'A'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B', 'B'),
        ('B-', 'B-'),
        ('C', 'C'),
        ('D', 'D'),
        ('F', 'F'),
    ]
    STATUS_CHOICES = [
        ('Not Started', 'Not Started'),
        ('In Progress', 'In Progress'),
        ('Passed', 'Passed'),
        ('Failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    registration = models.OneToOneField(Registration, on_delete=models.CASCADE, related_name='assessment')
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=255)
    course_name = models.CharField(max_length=255)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, blank=True, null=True, related_name='assessments')
    theory_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    practical_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    grade = models.CharField(max_length=5, choices=GRADE_CHOICES, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Not Started')
    remarks = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Assessment'
        verbose_name_plural = 'Assessments'

    def __str__(self):
        return f'{self.student_id} - {self.grade or "N/A"}'


class Certificate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    certificate_id = models.CharField(max_length=100, unique=True)
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='certificates')
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=255)
    course_name = models.CharField(max_length=255)
    issue_date = models.DateField()
    grade = models.CharField(max_length=10, blank=True, null=True)
    status = models.CharField(max_length=50, default='Issued')
    batch = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-issue_date']
        verbose_name = 'Certificate'
        verbose_name_plural = 'Certificates'

    def __str__(self):
        return self.certificate_id


class JobPlacement(models.Model):
    PLACEMENT_TYPE_CHOICES = [
        ('Full-time', 'Full-time'),
        ('Part-time', 'Part-time'),
        ('Internship', 'Internship'),
        ('Contract', 'Contract'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='job_placements')
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=255)
    course_name = models.CharField(max_length=255)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, blank=True, null=True, related_name='job_placements')
    company = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    placement_date = models.DateField()
    salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    placement_type = models.CharField(max_length=50, choices=PLACEMENT_TYPE_CHOICES, default='Full-time')
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-placement_date']
        verbose_name = 'Job Placement'
        verbose_name_plural = 'Job Placements'

    def __str__(self):
        return f'{self.student_name} @ {self.company}'


class ClassSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    class_title = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='class_sessions')
    date = models.DateField()
    time = models.CharField(max_length=50, blank=True, null=True)
    classroom_or_link = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['date', 'time']
        verbose_name = 'Class Session'
        verbose_name_plural = 'Class Sessions'

    def __str__(self):
        return f'{self.class_title} - {self.date}'
