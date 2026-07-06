import uuid
from django.db import models
from django.conf import settings


class Project(models.Model):
    STATUS_CHOICES = [
        ('Not Started', 'Not Started'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('On Hold', 'On Hold'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    project_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True, null=True)
    client_name = models.CharField(max_length=255, blank=True, null=True)
    total_budget = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Not Started')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return f'{self.project_code} - {self.name}'


class ProjectPhase(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='phases')
    phase_name = models.CharField(max_length=255)
    budget_allocation = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['phase_name']
        verbose_name = 'Project Phase'
        verbose_name_plural = 'Project Phases'

    def __str__(self):
        return f'{self.project.name} - {self.phase_name}'


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('Todo', 'Todo'),
        ('In Progress', 'In Progress'),
        ('Review', 'Review'),
        ('Completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    phase = models.ForeignKey(ProjectPhase, on_delete=models.CASCADE, related_name='tasks')
    task_name = models.CharField(max_length=255)
    assigned_to = models.CharField(max_length=255, default='Unassigned')
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Todo')
    due_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['due_date']
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    def __str__(self):
        return self.task_name


class ProjectRequisition(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Approved', 'Approved'),
        ('Procured', 'Procured'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='requisitions')
    phase = models.ForeignKey(ProjectPhase, on_delete=models.SET_NULL, blank=True, null=True, related_name='requisitions')
    item_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    estimated_cost = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    requisition_ref = models.CharField(max_length=255, blank=True, null=True, verbose_name='Inventory Requisition Ref')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project Requisition'
        verbose_name_plural = 'Project Requisitions'

    def __str__(self):
        return f'{self.project.name} - {self.item_name}'


class SoftwareLicense(models.Model):
    SUBSCRIPTION_TIER_CHOICES = [
        ('Basic', 'Basic'),
        ('Standard', 'Standard'),
        ('Premium', 'Premium'),
        ('Enterprise', 'Enterprise'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Expired', 'Expired'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='licenses')
    license_name = models.CharField(max_length=255)
    license_key = models.CharField(max_length=255, blank=True, null=True)
    subscription_tier = models.CharField(max_length=50, choices=SUBSCRIPTION_TIER_CHOICES, default='Standard')
    renewal_date = models.DateField(blank=True, null=True)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Active')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['license_name']
        verbose_name = 'Software License'
        verbose_name_plural = 'Software Licenses'

    def __str__(self):
        return f'{self.license_name} ({self.status})'


class ProjectStakeholder(models.Model):
    ROLE_CHOICES = [
        ('Primary Client Contact', 'Primary Client Contact'),
        ('Project Sponsor', 'Project Sponsor'),
        ('Technical Lead', 'Technical Lead'),
        ('Business Analyst', 'Business Analyst'),
        ('End User', 'End User'),
        ('Other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='stakeholders')
    contact_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    role = models.CharField(max_length=100, choices=ROLE_CHOICES, default='Primary Client Contact')
    contact_id = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['contact_name']
        verbose_name = 'Project Stakeholder'
        verbose_name_plural = 'Project Stakeholders'

    def __str__(self):
        return f'{self.contact_name} ({self.role})'


class Meeting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firestore_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='meetings')
    title = models.CharField(max_length=255)
    meeting_date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    video_link = models.URLField(max_length=500, blank=True, default='')
    agenda = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='%(app_label)s_%(class)s_updated')

    class Meta:
        ordering = ['-meeting_date']
        verbose_name = 'Meeting'
        verbose_name_plural = 'Meetings'

    def __str__(self):
        return f'{self.title} - {self.meeting_date}'
