from rest_framework import serializers
from billing.models import (
    ChartOfAccount, JournalEntry, JournalEntryLine,
    Invoice, InvoiceLine, VendorBill, VendorBillLine,
    Payment, TaxCode, AuditTrail,
)


class ChartOfAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartOfAccount
        fields = '__all__'


class JournalEntryLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntryLine
        fields = '__all__'


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalEntryLineSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = '__all__'


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'


class VendorBillLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorBillLine
        fields = '__all__'


class VendorBillSerializer(serializers.ModelSerializer):
    lines = VendorBillLineSerializer(many=True, read_only=True)

    class Meta:
        model = VendorBill
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


class TaxCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxCode
        fields = '__all__'


class AuditTrailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditTrail
        fields = '__all__'
