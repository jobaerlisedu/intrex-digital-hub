from rest_framework.routers import DefaultRouter
from inventory.api.viewsets import (
    ProductViewSet, VendorViewSet, RequisitionViewSet,
    RFQViewSet, QuotationViewSet, PurchaseOrderViewSet,
    GoodsReceiptViewSet, InventoryLedgerViewSet, DeliveryViewSet,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='inv-product')
router.register(r'vendors', VendorViewSet, basename='inv-vendor')
router.register(r'requisitions', RequisitionViewSet, basename='inv-requisition')
router.register(r'rfqs', RFQViewSet, basename='inv-rfq')
router.register(r'quotations', QuotationViewSet, basename='inv-quotation')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='inv-purchaseorder')
router.register(r'goods-receipts', GoodsReceiptViewSet, basename='inv-goodsreceipt')
router.register(r'ledger', InventoryLedgerViewSet, basename='inv-inventoryledger')
router.register(r'deliveries', DeliveryViewSet, basename='inv-delivery')

urlpatterns = router.urls
