from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from inventory.models import (
    Product, Vendor, Requisition, RFQ, Quotation,
    PurchaseOrder, GoodsReceipt, InventoryLedger, Delivery,
)
from inventory.api.serializers import (
    ProductSerializer, VendorSerializer, RequisitionSerializer,
    RFQSerializer, QuotationSerializer, PurchaseOrderSerializer,
    GoodsReceiptSerializer, InventoryLedgerSerializer, DeliverySerializer,
)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'is_active', 'storage_location']
    search_fields = ['item_name', 'sku']
    ordering_fields = ['item_name', 'quantity', 'unit_price', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'payment_terms']
    search_fields = ['name', 'vendor_code', 'email', 'contact_name']
    ordering_fields = ['name', 'created_at', 'performance_rating']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class RequisitionViewSet(viewsets.ModelViewSet):
    queryset = Requisition.objects.all()
    serializer_class = RequisitionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority', 'is_active']
    search_fields = ['requisition_code', 'client_name', 'requested_by']
    ordering_fields = ['created_at', 'requisition_date', 'expected_delivery_date', 'priority']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class RFQViewSet(viewsets.ModelViewSet):
    queryset = RFQ.objects.all()
    serializer_class = RFQSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'is_active', 'requisition']
    search_fields = ['rfq_code']
    ordering_fields = ['created_at', 'deadline']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.all()
    serializer_class = QuotationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'is_active', 'rfq', 'vendor']
    search_fields = ['quotation_reference']
    ordering_fields = ['created_at', 'grand_total', 'lead_time_days']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'is_active', 'vendor', 'requisition', 'quotation']
    search_fields = ['po_code']
    ordering_fields = ['created_at', 'grand_total']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class GoodsReceiptViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceipt.objects.all()
    serializer_class = GoodsReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'is_active', 'purchase_order']
    search_fields = ['grn_code', 'delivery_note_ref']
    ordering_fields = ['created_at', 'received_date']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class InventoryLedgerViewSet(viewsets.ModelViewSet):
    queryset = InventoryLedger.objects.all()
    serializer_class = InventoryLedgerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['transaction_type', 'is_active', 'product']
    search_fields = ['product_name', 'reference']
    ordering_fields = ['created_at', 'quantity_change']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['delivery_status', 'is_active', 'requisition']
    search_fields = ['challan_code', 'client_name', 'dispatched_by']
    ordering_fields = ['created_at', 'dispatch_date']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
