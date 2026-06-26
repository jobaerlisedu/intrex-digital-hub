from config.firebase import db
from google.cloud import firestore

def get_or_create_contact(name, email, phone, role):
    """
    Search contacts collection by unique email.
    If contact exists, appends role to roles list if missing and returns contact_id.
    If contact does not exist, creates a new contact entry and returns contact_id.
    """
    if not email:
        return None
    email = email.lower().strip()
    name = name.strip()
    phone = phone.strip()

    contacts_ref = db.collection('contacts')
    docs = list(contacts_ref.where('email', '==', email).stream())

    if docs:
        contact_doc = docs[0]
        contact_id = contact_doc.id
        data = contact_doc.to_dict() or {}
        roles = data.get('roles', [])
        updated = False
        
        if role not in roles:
            roles.append(role)
            updated = True
        
        # Keep name and phone updated if they are currently blank
        update_fields = {}
        if not data.get('legal_name') and name:
            update_fields['legal_name'] = name
            updated = True
        if not data.get('phone') and phone:
            update_fields['phone'] = phone
            updated = True
            
        if updated:
            update_fields['roles'] = roles
            contacts_ref.document(contact_id).update(update_fields)
            
        return contact_id
    else:
        # Create a new contact
        _, new_ref = contacts_ref.add({
            'legal_name': name,
            'email': email,
            'phone': phone,
            'roles': [role],
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return new_ref.id
