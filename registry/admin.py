from django.contrib import admin
from .models import Person, Organization, PersonOrganization


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'email', 'phone', 'person_type', 'is_active', 'created_at')
    list_filter = ('person_type', 'is_active')
    search_fields = ('display_name', 'email', 'phone')


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'org_type', 'email', 'phone', 'is_active')
    list_filter = ('org_type', 'is_active')
    search_fields = ('name', 'email')


@admin.register(PersonOrganization)
class PersonOrganizationAdmin(admin.ModelAdmin):
    list_display = ('person', 'organization', 'role', 'is_primary')
    list_filter = ('role', 'is_primary')
