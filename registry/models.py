from django.db import models
from django.contrib.auth.models import User


class Person(models.Model):
    PERSON_TYPES = [
        ('employee', 'Employee'),
        ('student', 'Student'),
        ('trainer', 'Trainer'),
        ('client', 'Client'),
        ('vendor_contact', 'Vendor Contact'),
        ('investor', 'Investor'),
        ('stakeholder', 'Stakeholder'),
        ('candidate', 'Candidate'),
        ('other', 'Other'),
    ]

    display_name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(max_length=254, unique=True, db_index=True)
    phone = models.CharField(max_length=50, blank=True)
    alt_phone = models.CharField(max_length=50, blank=True)
    person_type = models.CharField(max_length=30, choices=PERSON_TYPES, default='other')
    roles = models.JSONField(default=list, blank=True, help_text='Additional roles across modules')

    auth_user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registry_person'
    )

    firestore_contact_id = models.CharField(max_length=255, blank=True, help_text='sys_contacts doc ID')
    firestore_employee_id = models.CharField(max_length=255, blank=True, help_text='hrm_employees doc ID')
    firestore_student_id = models.CharField(max_length=255, blank=True, help_text='trn_registrations doc ID')
    firestore_investor_id = models.CharField(max_length=255, blank=True, help_text='invst_investors doc ID')

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'People'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['person_type']),
        ]

    def __str__(self):
        return self.display_name


class Organization(models.Model):
    ORG_TYPES = [
        ('vendor', 'Vendor'),
        ('institute', 'Training Institute'),
        ('client_company', 'Client Company'),
        ('partner', 'Partner'),
        ('investor_company', 'Investor Company'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=255, db_index=True)
    org_type = models.CharField(max_length=30, choices=ORG_TYPES, default='other')
    email = models.EmailField(max_length=254, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)

    firestore_vendor_id = models.CharField(max_length=255, blank=True, help_text='inv_vendors doc ID')
    firestore_institute_id = models.CharField(max_length=255, blank=True, help_text='trn_institutes doc ID')

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['org_type']),
        ]

    def __str__(self):
        return self.name


class PersonOrganization(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='organizations')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='people')
    role = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('person', 'organization', 'role')]
        verbose_name_plural = 'Person-Organization Links'

    def __str__(self):
        return f"{self.person} → {self.organization} ({self.role})"
