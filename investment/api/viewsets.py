from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from investment.models import Investor, Transaction, Loan, LoanSchedule, OutboundPlacement, FinancialInstrument, PLLedger
from investment.api.serializers import (
    InvestorSerializer,
    TransactionSerializer,
    LoanSerializer,
    LoanScheduleSerializer,
    OutboundPlacementSerializer,
    FinancialInstrumentSerializer,
    PLLedgerSerializer,
)


class InvestorViewSet(viewsets.ModelViewSet):
    queryset = Investor.objects.all()
    serializer_class = InvestorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'kyc_status', 'is_active']
    search_fields = ['name', 'investor_code', 'email']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['investor', 'transaction_type', 'payment_method', 'status', 'is_active']
    search_fields = ['investor_name', 'notes']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['investor', 'status', 'is_active']
    search_fields = ['investor_name']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class LoanScheduleViewSet(viewsets.ModelViewSet):
    queryset = LoanSchedule.objects.all()
    serializer_class = LoanScheduleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['loan', 'payment_status', 'is_active']
    search_fields = []
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class OutboundPlacementViewSet(viewsets.ModelViewSet):
    queryset = OutboundPlacement.objects.all()
    serializer_class = OutboundPlacementSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['entity_type', 'status', 'is_active']
    search_fields = ['project_name']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class FinancialInstrumentViewSet(viewsets.ModelViewSet):
    queryset = FinancialInstrument.objects.all()
    serializer_class = FinancialInstrumentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['instrument_type', 'is_active']
    search_fields = ['instrument_code']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PLLedgerViewSet(viewsets.ModelViewSet):
    queryset = PLLedger.objects.all()
    serializer_class = PLLedgerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['month', 'is_active']
    search_fields = ['month']
    ordering_fields = '__all__'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
