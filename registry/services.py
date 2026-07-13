from django.contrib.auth.models import User
from .models import Person, Organization


def get_or_create_person(email, display_name, person_type='other',
                         phone='', roles=None, auth_user=None):
    if not email:
        return None, False
    email = email.lower().strip()
    person, created = Person.objects.get_or_create(
        email=email,
        defaults={
            'display_name': display_name or email.split('@')[0],
            'phone': phone,
            'person_type': person_type,
            'roles': roles or [],
            'auth_user': auth_user,
        }
    )
    if not created:
        changed = False
        if display_name and person.display_name != display_name:
            person.display_name = display_name
            changed = True
        if phone and not person.phone:
            person.phone = phone
            changed = True
        if roles:
            existing_roles = set(person.roles)
            new_roles = [r for r in roles if r not in existing_roles]
            if new_roles:
                person.roles = person.roles + new_roles
                changed = True
        if auth_user and not person.auth_user:
            person.auth_user = auth_user
            changed = True
        if changed:
            person.save()
    return person, created


def get_or_create_organization(name, org_type='other', email='', phone=''):
    if not name:
        return None, False
    name = name.strip()
    org, created = Organization.objects.get_or_create(
        name=name,
        defaults={
            'org_type': org_type,
            'email': email,
            'phone': phone,
        }
    )
    return org, created


def link_person_to_organization(person, organization, role='', is_primary=False):
    from .models import PersonOrganization
    link, _ = PersonOrganization.objects.get_or_create(
        person=person,
        organization=organization,
        role=role or 'member',
        defaults={'is_primary': is_primary}
    )
    if is_primary:
        PersonOrganization.objects.filter(
            person=person, organization=organization
        ).exclude(id=link.id).update(is_primary=False)
    return link


def lookup_person_by_auth_user(user):
    if not user or not user.is_authenticated:
        return None
    try:
        return Person.objects.get(auth_user=user)
    except Person.DoesNotExist:
        return None


def get_all_employees():
    return Person.objects.filter(
        person_type='employee', is_active=True
    ).select_related('auth_user')


def get_all_students():
    return Person.objects.filter(
        person_type='student', is_active=True
    )
