"""
HRM API Base Classes

Standard DRF ModelSerializer and ModelViewSet backed by Django ORM.
All data operations use Django ORM.
"""

from rest_framework import serializers, viewsets, permissions


class ORMModelSerializer(serializers.ModelSerializer):
    """Standard ModelSerializer backed by Django ORM."""

    class Meta:
        model = None
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data.pop('collection_name', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('collection_name', None)
        return super().update(instance, validated_data)


class ORMViewSet(viewsets.ModelViewSet):
    """Standard ModelViewSet backed by Django ORM."""

    permission_classes = [permissions.IsAuthenticated]
    ordering = '-created_at'

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self, 'filterset_fields') and self.filterset_fields:
            for field in self.filterset_fields:
                val = self.request.query_params.get(field)
                if val is not None:
                    qs = qs.filter(**{field: val})
        search_param = self.request.query_params.get('search')
        search_fields = getattr(self, 'search_fields', None)
        if search_param and search_fields:
            from django.db.models import Q
            query = Q()
            for field in search_fields:
                query |= Q(**{f'{field}__icontains': search_param})
            qs = qs.filter(query)
        ordering_param = self.request.query_params.get('ordering')
        if ordering_param:
            qs = qs.order_by(ordering_param)
        return qs
