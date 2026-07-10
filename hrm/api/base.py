from rest_framework import serializers, viewsets, status
from rest_framework.response import Response
from django.http import Http404
from django.contrib.auth import get_user_model
from config.firebase import db
from datetime import datetime, date as date_type, time as time_type

UserModel = get_user_model()


def _serialize_value(v):
    if isinstance(v, UserModel):
        return f'users/{v.pk}'
    if hasattr(v, 'pk') and hasattr(v, '_meta'):
        return f'{v._meta.app_label}_{v._meta.model_name}/{v.pk}'
    if isinstance(v, (date_type, datetime)):
        return v.isoformat()
    return v


class FirestoreModelSerializer(serializers.ModelSerializer):
    serializer_related_field = serializers.CharField

    def build_relational_field(self, field_name, relation_info):
        field_class, field_kwargs = super().build_relational_field(field_name, relation_info)
        field_class = serializers.CharField
        field_kwargs['read_only'] = True
        field_kwargs['required'] = False
        field_kwargs.pop('queryset', None)
        return field_class, field_kwargs

    def create(self, validated_data):
        now = datetime.now().isoformat()
        validated_data.pop('id', None)
        validated_data.setdefault('created_at', now)
        validated_data.setdefault('updated_at', now)
        validated_data.setdefault('is_active', True)
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            validated_data.setdefault('created_by', f'users/{user.id}')
            validated_data.setdefault('updated_by', f'users/{user.id}')
        for k, v in list(validated_data.items()):
            validated_data[k] = _serialize_value(v)
        doc_ref = db.collection(self.Meta.collection_name).document()
        doc_ref.set(validated_data)
        validated_data['id'] = doc_ref.id
        return validated_data

    def update(self, instance, validated_data):
        now = datetime.now().isoformat()
        doc_id = instance.get('id') if isinstance(instance, dict) else getattr(instance, 'id', None)
        doc_id = validated_data.pop('id', doc_id)
        validated_data['updated_at'] = now
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            validated_data.setdefault('updated_by', f'users/{user.id}')
        for k, v in list(validated_data.items()):
            validated_data[k] = _serialize_value(v)
        db.collection(self.Meta.collection_name).document(str(doc_id)).update(validated_data)
        if isinstance(instance, dict):
            updated = {**instance, **validated_data}
            updated['id'] = doc_id
            return updated
        updated = {}
        for f in self.Meta.model._meta.fields:
            updated[f.name] = validated_data.get(f.name, getattr(instance, f.name, None))
        updated['id'] = str(doc_id)
        return updated


class FirestoreViewSet(viewsets.GenericViewSet):
    collection_name = None
    filter_backends = []
    pagination_class = None
    filterset_fields = []
    search_fields = []
    ordering_fields = []
    ordering = '-created_at'

    def get_queryset(self):
        try:
            docs = db.collection(self.collection_name).order_by(
                self.ordering.lstrip('-'), direction='DESCENDING' if self.ordering.startswith('-') else 'ASCENDING'
            ).stream()
            return [{'id': d.id, **d.to_dict()} for d in docs]
        except Exception:
            return []

    def filter_queryset(self, queryset):
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        for field in self.filterset_fields:
            val = request.query_params.get(field)
            if val is not None:
                queryset = [item for item in queryset if str(item.get(field)) == val]
        search = request.query_params.get('search')
        if search and self.search_fields:
            s = search.lower()
            queryset = [item for item in queryset if any(s in str(item.get(f, '')).lower() for f in self.search_fields)]
        order = request.query_params.get('ordering', self.ordering)
        if order and self.ordering_fields:
            rev = order.startswith('-')
            f = order.lstrip('-')
            if f in self.ordering_fields:
                queryset.sort(key=lambda x: str(x.get(f, '') or ''), reverse=rev)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_object(self):
        pk = self.kwargs.get(self.lookup_field)
        doc = db.collection(self.collection_name).document(pk).get()
        if not doc.exists:
            raise Http404
        return {'id': doc.id, **doc.to_dict()}

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        db.collection(self.collection_name).document(instance['id']).update({
            'is_active': False,
            'updated_at': datetime.now().isoformat(),
        })
