from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    ChartOfAccountViewSet, JournalEntryViewSet, JournalEntryLineViewSet,
    InvoiceViewSet, InvoiceLineViewSet, VendorBillViewSet, VendorBillLineViewSet,
    PaymentViewSet, TaxCodeViewSet, AuditTrailViewSet,
)

router = DefaultRouter()
router.register(r'chart-of-accounts', ChartOfAccountViewSet, basename='billing-chart-of-account')
router.register(r'journal-entries', JournalEntryViewSet, basename='billing-journal-entry')
router.register(r'journal-entry-lines', JournalEntryLineViewSet, basename='billing-journal-entry-line')
router.register(r'invoices', InvoiceViewSet, basename='billing-invoice')
router.register(r'invoice-lines', InvoiceLineViewSet, basename='billing-invoice-line')
router.register(r'vendor-bills', VendorBillViewSet, basename='billing-vendor-bill')
router.register(r'vendor-bill-lines', VendorBillLineViewSet, basename='billing-vendor-bill-line')
router.register(r'payments', PaymentViewSet, basename='billing-payment')
router.register(r'tax-codes', TaxCodeViewSet, basename='billing-tax-code')
router.register(r'audit-trails', AuditTrailViewSet, basename='billing-audit-trail')

urlpatterns = [
    path('', include(router.urls)),
]
