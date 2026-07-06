from rest_framework import serializers
from investment.models import Investor, Transaction, Loan, LoanSchedule, OutboundPlacement, FinancialInstrument, PLLedger


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = '__all__'


class LoanScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanSchedule
        fields = '__all__'


class OutboundPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutboundPlacement
        fields = '__all__'


class FinancialInstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialInstrument
        fields = '__all__'


class PLLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PLLedger
        fields = '__all__'


class InvestorSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)
    loans = LoanSerializer(many=True, read_only=True)

    class Meta:
        model = Investor
        fields = '__all__'
