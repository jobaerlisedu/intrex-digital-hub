from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from investment.models import (
    Investor, Transaction, Loan, LoanSchedule,
    OutboundPlacement, FinancialInstrument, InstrumentPrice,
    PLLedger, NavHistory, InvestorHolding,
    FeeStructure, FeeAccrual,
)
from investment.api.serializers import (
    InvestorSerializer,
    TransactionSerializer,
    LoanSerializer,
    LoanScheduleSerializer,
    OutboundPlacementSerializer,
    FinancialInstrumentSerializer,
    InstrumentPriceSerializer,
    PLLedgerSerializer,
    NavHistorySerializer,
    InvestorHoldingSerializer,
    FeeStructureSerializer,
    FeeAccrualSerializer,
    PortalHoldingSerializer,
    PortalTransactionSerializer,
)


class InvestorViewSet(viewsets.ViewSet):
    """API for investors."""

    def list(self, request):
        queryset = Investor.objects.filter(is_active=True)
        data = [_investor_to_dict(i) for i in queryset]
        serializer = InvestorSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = InvestorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = Investor.objects.create(**serializer.validated_data)
        created = _investor_to_dict(obj)
        return Response(InvestorSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Investor, pk=pk)
        return Response(InvestorSerializer(_investor_to_dict(obj)).data)

    def update(self, request, pk=None):
        obj = get_object_or_404(Investor, pk=pk)
        serializer = InvestorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        Investor.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(InvestorSerializer(_investor_to_dict(obj)).data)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(Investor, pk=pk)
        serializer = InvestorSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        Investor.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(InvestorSerializer(_investor_to_dict(obj)).data)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(Investor, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionViewSet(viewsets.ViewSet):
    """API for transactions."""

    def list(self, request):
        qs = Transaction.objects.filter(is_active=True).select_related('investor')
        data = [_tx_to_dict(t) for t in qs]
        serializer = TransactionSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = TransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = Transaction.objects.create(**serializer.validated_data)
        created = _tx_to_dict(obj)
        return Response(TransactionSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Transaction, pk=pk)
        return Response(TransactionSerializer(_tx_to_dict(obj)).data)

    def update(self, request, pk=None):
        obj = get_object_or_404(Transaction, pk=pk)
        serializer = TransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        Transaction.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(TransactionSerializer(_tx_to_dict(obj)).data)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(Transaction, pk=pk)
        serializer = TransactionSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        Transaction.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(TransactionSerializer(_tx_to_dict(obj)).data)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(Transaction, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoanViewSet(viewsets.ViewSet):
    """API for loans."""

    def list(self, request):
        qs = Loan.objects.filter(is_active=True).select_related('investor')
        data = [_loan_to_dict(l) for l in qs]
        serializer = LoanSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = LoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = Loan.objects.create(**serializer.validated_data)
        created = _loan_to_dict(obj)
        return Response(LoanSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Loan, pk=pk)
        return Response(LoanSerializer(_loan_to_dict(obj)).data)

    def update(self, request, pk=None):
        obj = get_object_or_404(Loan, pk=pk)
        serializer = LoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        Loan.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(LoanSerializer(_loan_to_dict(obj)).data)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(Loan, pk=pk)
        serializer = LoanSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        Loan.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(LoanSerializer(_loan_to_dict(obj)).data)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(Loan, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoanScheduleViewSet(viewsets.ViewSet):
    """API for loan schedules."""

    def list(self, request):
        qs = LoanSchedule.objects.filter(is_active=True)
        data = [_schedule_to_dict(s) for s in qs]
        serializer = LoanScheduleSerializer(data, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(LoanSchedule, pk=pk)
        return Response(LoanScheduleSerializer(_schedule_to_dict(obj)).data)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(LoanSchedule, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OutboundPlacementViewSet(viewsets.ViewSet):
    """API for outbound placements."""

    def list(self, request):
        qs = OutboundPlacement.objects.filter(is_active=True)
        data = [_outbound_to_dict(o) for o in qs]
        serializer = OutboundPlacementSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = OutboundPlacementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = OutboundPlacement.objects.create(**serializer.validated_data)
        created = _outbound_to_dict(obj)
        return Response(OutboundPlacementSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(OutboundPlacement, pk=pk)
        return Response(OutboundPlacementSerializer(_outbound_to_dict(obj)).data)

    def update(self, request, pk=None):
        obj = get_object_or_404(OutboundPlacement, pk=pk)
        serializer = OutboundPlacementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        OutboundPlacement.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(OutboundPlacementSerializer(_outbound_to_dict(obj)).data)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(OutboundPlacement, pk=pk)
        serializer = OutboundPlacementSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        OutboundPlacement.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(OutboundPlacementSerializer(_outbound_to_dict(obj)).data)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(OutboundPlacement, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FinancialInstrumentViewSet(viewsets.ViewSet):
    """API for financial instruments."""

    def list(self, request):
        qs = FinancialInstrument.objects.filter(is_active=True)
        data = [_instrument_to_dict(i) for i in qs]
        serializer = FinancialInstrumentSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = FinancialInstrumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = FinancialInstrument.objects.create(**serializer.validated_data)
        return Response(FinancialInstrumentSerializer(_instrument_to_dict(obj)).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(FinancialInstrument, pk=pk)
        return Response(FinancialInstrumentSerializer(_instrument_to_dict(obj)).data)

    def update(self, request, pk=None):
        obj = get_object_or_404(FinancialInstrument, pk=pk)
        serializer = FinancialInstrumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        FinancialInstrument.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(FinancialInstrumentSerializer(_instrument_to_dict(obj)).data)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(FinancialInstrument, pk=pk)
        serializer = FinancialInstrumentSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        FinancialInstrument.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(FinancialInstrumentSerializer(_instrument_to_dict(obj)).data)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(FinancialInstrument, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InstrumentPriceViewSet(viewsets.ViewSet):
    """API for instrument prices."""

    def list(self, request):
        qs = InstrumentPrice.objects.filter(is_active=True).select_related('instrument')
        data = [_price_to_dict(p) for p in qs]
        serializer = InstrumentPriceSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = InstrumentPriceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = InstrumentPrice.objects.create(**serializer.validated_data)
        created = _price_to_dict(obj)
        return Response(InstrumentPriceSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(InstrumentPrice, pk=pk)
        return Response(InstrumentPriceSerializer(_price_to_dict(obj)).data)

    def update(self, request, pk=None):
        obj = get_object_or_404(InstrumentPrice, pk=pk)
        serializer = InstrumentPriceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        InstrumentPrice.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(InstrumentPriceSerializer(_price_to_dict(obj)).data)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(InstrumentPrice, pk=pk)
        serializer = InstrumentPriceSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        InstrumentPrice.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(InstrumentPriceSerializer(_price_to_dict(obj)).data)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(InstrumentPrice, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PLLedgerViewSet(viewsets.ViewSet):
    """API for P&L ledger entries."""

    def list(self, request):
        qs = PLLedger.objects.filter(is_active=True)
        data = [_pl_to_dict(p) for p in qs]
        serializer = PLLedgerSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = PLLedgerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = PLLedger.objects.create(**serializer.validated_data)
        return Response(PLLedgerSerializer(_pl_to_dict(obj)).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(PLLedger, pk=pk)
        return Response(PLLedgerSerializer(_pl_to_dict(obj)).data)

    def update(self, request, pk=None):
        obj = get_object_or_404(PLLedger, pk=pk)
        serializer = PLLedgerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PLLedger.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(PLLedgerSerializer(_pl_to_dict(obj)).data)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(PLLedger, pk=pk)
        serializer = PLLedgerSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        PLLedger.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(PLLedgerSerializer(_pl_to_dict(obj)).data)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(PLLedger, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NavHistoryViewSet(viewsets.ViewSet):
    """API for NAV history."""

    def list(self, request):
        qs = NavHistory.objects.filter(is_active=True).order_by('-nav_date')
        data = [_nav_to_dict(n) for n in qs]
        serializer = NavHistorySerializer(data, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(NavHistory, pk=pk)
        return Response(NavHistorySerializer(_nav_to_dict(obj)).data)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        from investment.services import NavService
        nav = NavService.get_current_nav()
        if not nav:
            return Response({'nav_per_unit': '0.0000', 'total_aum': '0.00', 'total_units': '0.0000'})
        return Response(NavHistorySerializer(nav).data)


class NavHistoryViewSet(viewsets.ViewSet):
    """API for NAV history."""

    def list(self, request):
        qs = NavHistory.objects.filter(is_active=True).order_by('-nav_date')
        serializer = NavHistorySerializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(NavHistory, pk=pk)
        return Response(NavHistorySerializer(obj).data)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        from investment.services import NavService
        nav = NavService.get_current_nav()
        if not nav:
            return Response({'nav_per_unit': '0.0000', 'total_aum': '0.00', 'total_units': '0.0000'})
        return Response(NavHistorySerializer(nav).data)


class InvestorHoldingViewSet(viewsets.ViewSet):
    """API for investor holdings."""

    def list(self, request):
        qs = InvestorHolding.objects.filter(is_active=True).select_related('investor')
        data = [_holding_to_dict(h) for h in qs]
        serializer = InvestorHoldingSerializer(data, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(InvestorHolding, pk=pk)
        return Response(InvestorHoldingSerializer(_holding_to_dict(obj)).data)

    @action(detail=False, methods=['post'])
    def issue(self, request):
        from investment.services import NavService
        investor_id = request.data.get('investor_id')
        amount = request.data.get('amount', '0.00')
        if not investor_id:
            return Response({'error': 'investor_id required'}, status=status.HTTP_400_BAD_REQUEST)
        result = NavService.issue_units(investor_id, amount)
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def redeem(self, request):
        from investment.services import NavService
        investor_id = request.data.get('investor_id')
        units = request.data.get('units', '0.0000')
        if not investor_id:
            return Response({'error': 'investor_id required'}, status=status.HTTP_400_BAD_REQUEST)
        result = NavService.redeem_units(investor_id, units)
        return Response(result)


class FeeStructureViewSet(viewsets.ViewSet):
    """API for fee structures."""

    def list(self, request):
        qs = FeeStructure.objects.filter(is_active=True)
        data = [_fee_structure_to_dict(f) for f in qs]
        serializer = FeeStructureSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = FeeStructureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = FeeStructure.objects.create(**serializer.validated_data)
        return Response(FeeStructureSerializer(_fee_structure_to_dict(obj)).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(FeeStructure, pk=pk)
        return Response(FeeStructureSerializer(_fee_structure_to_dict(obj)).data)

    def update(self, request, pk=None):
        obj = get_object_or_404(FeeStructure, pk=pk)
        serializer = FeeStructureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        FeeStructure.objects.filter(pk=pk).update(**serializer.validated_data)
        obj.refresh_from_db()
        return Response(FeeStructureSerializer(_fee_structure_to_dict(obj)).data)


class FeeAccrualViewSet(viewsets.ViewSet):
    """API for fee accruals."""

    def list(self, request):
        qs = FeeAccrual.objects.filter(is_active=True).order_by('-accrual_date')
        data = [_fee_accrual_to_dict(f) for f in qs]
        serializer = FeeAccrualSerializer(data, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(FeeAccrual, pk=pk)
        return Response(FeeAccrualSerializer(_fee_accrual_to_dict(obj)).data)


# ── Portal ViewSets ──────────────────────────────────────────

class PortalHoldingViewSet(viewsets.ViewSet):
    """API for investor portal — holdings (token-authenticated)."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        investor_id = request.query_params.get('investor_id')
        if not investor_id:
            return Response({'error': 'investor_id required'}, status=400)
        qs = InvestorHolding.objects.filter(investor__id=investor_id, is_active=True)
        data = [_holding_to_dict(h) for h in qs]
        serializer = PortalHoldingSerializer(data, many=True)
        return Response(serializer.data)


class PortalTransactionViewSet(viewsets.ViewSet):
    """API for investor portal — transactions (token-authenticated)."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        investor_id = request.query_params.get('investor_id')
        if not investor_id:
            return Response({'error': 'investor_id required'}, status=400)
        qs = Transaction.objects.filter(
            investor__id=investor_id, status='Cleared', is_active=True
        ).order_by('-value_date')
        data = [_tx_to_dict(t) for t in qs]
        serializer = PortalTransactionSerializer(data, many=True)
        return Response(serializer.data)


# ── Helper: model → dict converters ──────────────────────────

def _investor_to_dict(obj):
    from investment.services import money_to_float
    d = {
        'id': str(obj.id),
        'investor_code': obj.investor_code,
        'name': obj.name,
        'category': obj.category,
        'kyc_status': obj.kyc_status,
        'tax_id': obj.tax_id or '',
        'email': obj.email or '',
        'phone': obj.phone or '',
        'bank_account_name': obj.bank_account_name or '',
        'bank_account_number': obj.bank_account_number or '',
        'bank_routing_code': obj.bank_routing_code or '',
        'contact_id': obj.contact_id or '',
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
        'created_by': obj.created_by or '',
        'updated_by': obj.updated_by or '',
        'transactions': [],
        'loans': [],
    }
    return d


def _tx_to_dict(obj):
    from investment.services import money_to_str
    return {
        'id': str(obj.id),
        'investor_id': str(obj.investor_id) if obj.investor_id else '',
        'investor_name': obj.investor.name if obj.investor else '',
        'transaction_type': obj.transaction_type,
        'amount': float(obj.amount),
        'payment_method': obj.payment_method,
        'value_date': obj.value_date.isoformat() if obj.value_date else '',
        'status': obj.status,
        'notes': obj.notes or '',
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
        'created_by': obj.created_by or '',
        'updated_by': obj.updated_by or '',
    }


def _loan_to_dict(obj):
    return {
        'id': str(obj.id),
        'investor_id': str(obj.investor_id) if obj.investor_id else '',
        'investor_name': obj.investor.name if obj.investor else '',
        'principal_amount': float(obj.principal_amount),
        'outstanding_balance': float(obj.outstanding_balance),
        'interest_rate': float(obj.interest_rate),
        'tenure_months': obj.tenure_months,
        'disbursement_date': obj.disbursement_date.isoformat() if obj.disbursement_date else '',
        'status': obj.status,
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
        'created_by': obj.created_by or '',
        'updated_by': obj.updated_by or '',
    }


def _schedule_to_dict(obj):
    return {
        'id': str(obj.id),
        'loan_id': str(obj.loan_id) if obj.loan_id else '',
        'installment_number': obj.installment_number,
        'due_date': obj.due_date.isoformat() if obj.due_date else '',
        'scheduled_principal': float(obj.scheduled_principal),
        'scheduled_interest': float(obj.scheduled_interest),
        'paid_amount': float(obj.paid_amount),
        'payment_status': obj.payment_status,
        'actual_payment_date': obj.actual_payment_date.isoformat() if obj.actual_payment_date else None,
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
    }


def _outbound_to_dict(obj):
    return {
        'id': str(obj.id),
        'project_name': obj.project_name,
        'entity_type': obj.entity_type,
        'allocated_capital': float(obj.allocated_capital),
        'current_valuation': float(obj.current_valuation),
        'roi_expected_annual': float(obj.roi_expected_annual),
        'placement_date': obj.placement_date.isoformat() if obj.placement_date else '',
        'status': obj.status,
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
        'created_by': obj.created_by or '',
        'updated_by': obj.updated_by or '',
    }


def _price_to_dict(obj):
    return {
        'id': str(obj.id),
        'instrument_id': str(obj.instrument_id) if obj.instrument_id else '',
        'price_date': obj.price_date.isoformat() if obj.price_date else '',
        'price': float(obj.price),
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
        'created_by': obj.created_by or '',
        'updated_by': obj.updated_by or '',
    }


def _holding_to_dict(obj):
    return {
        'id': str(obj.id),
        'investor_id': str(obj.investor_id) if obj.investor_id else '',
        'units_held': str(obj.units_held),
        'avg_cost_per_unit': str(obj.avg_cost_per_unit),
        'total_invested': str(obj.total_invested),
        'current_value': str(obj.current_value),
        'unrealized_pl': str(obj.unrealized_pl),
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
    }


def _instrument_to_dict(obj):
    return {
        'id': str(obj.id),
        'instrument_code': obj.instrument_code,
        'type': obj.instrument_type,
        'face_value': float(obj.face_value),
        'coupon_rate': float(obj.coupon_rate),
        'total_units_issued': obj.total_units_issued,
        'units_outstanding': obj.units_outstanding,
        'issue_date': obj.issue_date.isoformat() if obj.issue_date else '',
        'maturity_date': obj.maturity_date.isoformat() if obj.maturity_date else '',
        'isin': obj.isin or '',
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
        'created_by': obj.created_by or '',
        'updated_by': obj.updated_by or '',
    }


def _pl_to_dict(obj):
    return {
        'id': str(obj.id),
        'month': obj.month,
        'revenue': float(obj.revenue),
        'opex': float(obj.opex),
        'interest_expense': float(obj.interest_expense),
        'net_profit': float(obj.net_profit),
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
        'created_by': obj.created_by or '',
        'updated_by': obj.updated_by or '',
    }


def _nav_to_dict(obj):
    return {
        'id': str(obj.id),
        'nav_date': obj.nav_date.isoformat() if obj.nav_date else '',
        'nav_per_unit': str(obj.nav_per_unit),
        'total_units': str(obj.total_units),
        'total_aum': str(obj.total_aum),
        'total_assets': str(obj.total_assets),
        'total_liabilities': str(obj.total_liabilities),
        'management_fee_accrued': str(obj.management_fee_accrued),
        'performance_fee_accrued': str(obj.performance_fee_accrued),
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
        'created_by': obj.created_by or '',
        'updated_by': obj.updated_by or '',
    }


def _fee_structure_to_dict(obj):
    return {
        'id': str(obj.id),
        'management_fee_annual_pct': str(obj.management_fee_annual_pct) if obj.management_fee_annual_pct else '2.00',
        'performance_fee_pct': str(obj.performance_fee_pct) if obj.performance_fee_pct else '20.00',
        'hurdle_rate_pct': str(obj.hurdle_rate_pct) if obj.hurdle_rate_pct else '5.00',
        'high_water_mark': str(obj.high_water_mark) if obj.high_water_mark else '0.0000',
        'fee_frequency': obj.fee_frequency,
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
        'created_by': obj.created_by or '',
        'updated_by': obj.updated_by or '',
    }


def _fee_accrual_to_dict(obj):
    return {
        'id': str(obj.id),
        'accrual_date': obj.accrual_date.isoformat() if obj.accrual_date else '',
        'fee_type': obj.fee_type,
        'amount': str(obj.amount),
        'nav_before_fee': str(obj.nav_before_fee),
        'nav_after_fee': str(obj.nav_after_fee),
        'is_settled': obj.is_settled,
        'settled_date': obj.settled_date.isoformat() if obj.settled_date else None,
        'is_active': obj.is_active,
        'created_at': obj.created_at,
        'updated_at': obj.updated_at,
        'created_by': obj.created_by or '',
        'updated_by': obj.updated_by or '',
    }
