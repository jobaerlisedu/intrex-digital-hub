from config.firebase import db
from config.tenants import fs_add_org, fs_scope_query, get_current_organization


def fs_create(collection, data, doc_id=None):
    data = fs_add_org(dict(data))
    ref = db.collection(collection)
    if doc_id:
        ref.document(doc_id).set(data)
        return doc_id
    _, doc = ref.add(data)
    return doc.id


def fs_update(collection, doc_id, data):
    data = dict(data)
    ref = db.collection(collection).document(doc_id)
    ref.update(data)
    return doc_id


def fs_delete(collection, doc_id):
    db.collection(collection).document(doc_id).delete()


def fs_get(collection, doc_id):
    doc = db.collection(collection).document(doc_id).get()
    if doc.exists:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None


def fs_query(collection):
    return fs_scope_query(db.collection(collection))


def fs_stream(collection, order_by=None, limit=None):
    q = fs_query(collection)
    if order_by:
        q = q.order_by(order_by)
    if limit:
        q = q.limit(limit)
    docs = q.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        results.append(data)
    return results


def fs_get_by_field(collection, field, value):
    q = fs_query(collection).where(field, '==', value).limit(1)
    docs = list(q.stream())
    if docs:
        data = docs[0].to_dict()
        data['id'] = docs[0].id
        return data
    return None
