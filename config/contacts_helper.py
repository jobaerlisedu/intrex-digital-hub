from registry.models import Person


def get_or_create_contact(name, email, phone, role):
    if not email:
        return None
    email = email.lower().strip()
    name = name.strip()
    phone = phone.strip()

    person = Person.objects.filter(email=email).first()
    if person:
        roles = person.roles or []
        updated = False
        if role not in roles:
            roles.append(role)
            person.roles = roles
            updated = True
        if not person.legal_name and name:
            person.legal_name = name
            updated = True
        if not person.phone and phone:
            person.phone = phone
            updated = True
        if updated:
            person.save()
        return str(person.pk)
    else:
        person = Person.objects.create(
            display_name=name,
            legal_name=name,
            email=email,
            phone=phone,
            person_type='other',
            roles=[role],
        )
        return str(person.pk)
