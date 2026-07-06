from rest_framework import viewsets
from billing.models import (
    ChartOfAccount, JournalEntry, JournalEntryLine,
    Invoice, InvoiceLine, VendorBill, VendorBillLine,
    Payment, TaxCode, AuditTrail,
)
from .serializers import (
    ChartOfAccountSerializer, JournalEntrySerializer, JournalEntryLineSerializer,
    InvoiceSerializer, InvoiceLineSerializer, VendorBillSerializer, VendorBillLineSerializer,
    PaymentSerializer, TaxCodeSerializer, AuditTrailSerializer,
)


class ChartOfAccountViewSet(viewsets.ModelViewSet):
    queryset = ChartOfAccount.objects.all()
    serializer_class = ChartOfAccountSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class JournalEntryViewSet(viewsets.ModelViewSet):
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class JournalEntryLineViewSet(viewsets.ModelViewSet):
    queryset = JournalEntryLine.objects.all()
    serializer_class = JournalEntryLineSerializer


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class InvoiceLineViewSet(viewsets.ModelViewSet):
    queryset = InvoiceLine.objects.all()
    serializer_class = InvoiceLineSerializer


class VendorBillViewSet(viewsets.ModelViewSet):
    queryset = VendorBill.objects.all()
    serializer_class = VendorBillSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class VendorBillLineViewSet(viewsets.ModelViewSet):
    queryset = VendorBillLine.objects.all()
    serializer_class = VendorBillLineSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class TaxCodeViewSet(viewsets.ModelViewSet):
    queryset = TaxCode.objects.all()
    serializer_class = TaxCodeSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class AuditTrailViewSet(viewsets.ModelViewSet):
    queryset = AuditTrail.objects.all()
    serializer_class = AuditTrailSerializer

    def perform_create(self, serializer):
        serializer.save(performed_by=self.request.user)
