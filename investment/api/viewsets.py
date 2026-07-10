from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from investment.services import FirestoreService as fs, audit_create, audit_update
from investment.services import (
    COLL_INVESTORS, COLL_TRANSACTIONS, COLL_LOANS,
    COLL_LOAN_SCHEDULES, COLL_OUTBOUND, COLL_INSTRUMENTS,
    COLL_PL_LEDGER,
)
from investment.api.serializers import (
    InvestorSerializer,
    TransactionSerializer,
    LoanSerializer,
    LoanScheduleSerializer,
    OutboundPlacementSerializer,
    FinancialInstrumentSerializer,
    PLLedgerSerializer,
)


class InvestorViewSet(viewsets.ViewSet):
    """Firestore-backed API for investors."""

    def list(self, request):
        data = fs.get_collection(COLL_INVESTORS)
        serializer = InvestorSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = InvestorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc_id = fs.create_document(COLL_INVESTORS, {
            **serializer.validated_data,
            **audit_create(request.user),
        })
        if not doc_id:
            return Response({'error': 'Failed to create investor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        created = fs.get_document(COLL_INVESTORS, doc_id)
        return Response(InvestorSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        doc = fs.get_document(COLL_INVESTORS, pk)
        if not doc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(InvestorSerializer(doc).data)

    def update(self, request, pk=None):
        existing = fs.get_document(COLL_INVESTORS, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = InvestorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_INVESTORS, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_INVESTORS, pk)
        return Response(InvestorSerializer(updated).data)

    def partial_update(self, request, pk=None):
        existing = fs.get_document(COLL_INVESTORS, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = InvestorSerializer(data={**existing, **request.data}, partial=True)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_INVESTORS, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_INVESTORS, pk)
        return Response(InvestorSerializer(updated).data)

    def destroy(self, request, pk=None):
        if not fs.get_document(COLL_INVESTORS, pk):
            return Response(status=status.HTTP_404_NOT_FOUND)
        fs.delete_document(COLL_INVESTORS, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionViewSet(viewsets.ViewSet):
    """Firestore-backed API for transactions."""

    def list(self, request):
        data = fs.get_collection(COLL_TRANSACTIONS)
        serializer = TransactionSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = TransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc_id = fs.create_document(COLL_TRANSACTIONS, {
            **serializer.validated_data,
            **audit_create(request.user),
        })
        if not doc_id:
            return Response({'error': 'Failed to create transaction'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        created = fs.get_document(COLL_TRANSACTIONS, doc_id)
        return Response(TransactionSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        doc = fs.get_document(COLL_TRANSACTIONS, pk)
        if not doc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(TransactionSerializer(doc).data)

    def update(self, request, pk=None):
        existing = fs.get_document(COLL_TRANSACTIONS, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_TRANSACTIONS, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_TRANSACTIONS, pk)
        return Response(TransactionSerializer(updated).data)

    def partial_update(self, request, pk=None):
        existing = fs.get_document(COLL_TRANSACTIONS, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TransactionSerializer(data={**existing, **request.data}, partial=True)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_TRANSACTIONS, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_TRANSACTIONS, pk)
        return Response(TransactionSerializer(updated).data)

    def destroy(self, request, pk=None):
        if not fs.get_document(COLL_TRANSACTIONS, pk):
            return Response(status=status.HTTP_404_NOT_FOUND)
        fs.delete_document(COLL_TRANSACTIONS, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoanViewSet(viewsets.ViewSet):
    """Firestore-backed API for loans."""

    def list(self, request):
        data = fs.get_collection(COLL_LOANS)
        serializer = LoanSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = LoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc_id = fs.create_document(COLL_LOANS, {
            **serializer.validated_data,
            **audit_create(request.user),
        })
        if not doc_id:
            return Response({'error': 'Failed to create loan'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        created = fs.get_document(COLL_LOANS, doc_id)
        return Response(LoanSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        doc = fs.get_document(COLL_LOANS, pk)
        if not doc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(LoanSerializer(doc).data)

    def update(self, request, pk=None):
        existing = fs.get_document(COLL_LOANS, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = LoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_LOANS, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_LOANS, pk)
        return Response(LoanSerializer(updated).data)

    def partial_update(self, request, pk=None):
        existing = fs.get_document(COLL_LOANS, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = LoanSerializer(data={**existing, **request.data}, partial=True)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_LOANS, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_LOANS, pk)
        return Response(LoanSerializer(updated).data)

    def destroy(self, request, pk=None):
        if not fs.get_document(COLL_LOANS, pk):
            return Response(status=status.HTTP_404_NOT_FOUND)
        fs.delete_document(COLL_LOANS, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoanScheduleViewSet(viewsets.ViewSet):
    """Firestore-backed API for loan schedules."""

    def list(self, request):
        data = fs.get_collection(COLL_LOAN_SCHEDULES)
        serializer = LoanScheduleSerializer(data, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        doc = fs.get_document(COLL_LOAN_SCHEDULES, pk)
        if not doc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(LoanScheduleSerializer(doc).data)

    def destroy(self, request, pk=None):
        if not fs.get_document(COLL_LOAN_SCHEDULES, pk):
            return Response(status=status.HTTP_404_NOT_FOUND)
        fs.delete_document(COLL_LOAN_SCHEDULES, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OutboundPlacementViewSet(viewsets.ViewSet):
    """Firestore-backed API for outbound placements."""

    def list(self, request):
        data = fs.get_collection(COLL_OUTBOUND)
        serializer = OutboundPlacementSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = OutboundPlacementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc_id = fs.create_document(COLL_OUTBOUND, {
            **serializer.validated_data,
            **audit_create(request.user),
        })
        if not doc_id:
            return Response({'error': 'Failed to create outbound placement'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        created = fs.get_document(COLL_OUTBOUND, doc_id)
        return Response(OutboundPlacementSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        doc = fs.get_document(COLL_OUTBOUND, pk)
        if not doc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(OutboundPlacementSerializer(doc).data)

    def update(self, request, pk=None):
        existing = fs.get_document(COLL_OUTBOUND, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = OutboundPlacementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_OUTBOUND, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_OUTBOUND, pk)
        return Response(OutboundPlacementSerializer(updated).data)

    def partial_update(self, request, pk=None):
        existing = fs.get_document(COLL_OUTBOUND, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = OutboundPlacementSerializer(data={**existing, **request.data}, partial=True)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_OUTBOUND, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_OUTBOUND, pk)
        return Response(OutboundPlacementSerializer(updated).data)

    def destroy(self, request, pk=None):
        if not fs.get_document(COLL_OUTBOUND, pk):
            return Response(status=status.HTTP_404_NOT_FOUND)
        fs.delete_document(COLL_OUTBOUND, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FinancialInstrumentViewSet(viewsets.ViewSet):
    """Firestore-backed API for financial instruments."""

    def list(self, request):
        data = fs.get_collection(COLL_INSTRUMENTS)
        serializer = FinancialInstrumentSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = FinancialInstrumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc_id = fs.create_document(COLL_INSTRUMENTS, {
            **serializer.validated_data,
            **audit_create(request.user),
        })
        if not doc_id:
            return Response({'error': 'Failed to create instrument'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        created = fs.get_document(COLL_INSTRUMENTS, doc_id)
        return Response(FinancialInstrumentSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        doc = fs.get_document(COLL_INSTRUMENTS, pk)
        if not doc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(FinancialInstrumentSerializer(doc).data)

    def update(self, request, pk=None):
        existing = fs.get_document(COLL_INSTRUMENTS, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = FinancialInstrumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_INSTRUMENTS, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_INSTRUMENTS, pk)
        return Response(FinancialInstrumentSerializer(updated).data)

    def partial_update(self, request, pk=None):
        existing = fs.get_document(COLL_INSTRUMENTS, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = FinancialInstrumentSerializer(data={**existing, **request.data}, partial=True)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_INSTRUMENTS, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_INSTRUMENTS, pk)
        return Response(FinancialInstrumentSerializer(updated).data)

    def destroy(self, request, pk=None):
        if not fs.get_document(COLL_INSTRUMENTS, pk):
            return Response(status=status.HTTP_404_NOT_FOUND)
        fs.delete_document(COLL_INSTRUMENTS, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PLLedgerViewSet(viewsets.ViewSet):
    """Firestore-backed API for P&L ledger entries."""

    def list(self, request):
        data = fs.get_collection(COLL_PL_LEDGER)
        serializer = PLLedgerSerializer(data, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = PLLedgerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc_id = fs.create_document(COLL_PL_LEDGER, {
            **serializer.validated_data,
            **audit_create(request.user),
        })
        if not doc_id:
            return Response({'error': 'Failed to create PL entry'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        created = fs.get_document(COLL_PL_LEDGER, doc_id)
        return Response(PLLedgerSerializer(created).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        doc = fs.get_document(COLL_PL_LEDGER, pk)
        if not doc:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(PLLedgerSerializer(doc).data)

    def update(self, request, pk=None):
        existing = fs.get_document(COLL_PL_LEDGER, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = PLLedgerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_PL_LEDGER, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_PL_LEDGER, pk)
        return Response(PLLedgerSerializer(updated).data)

    def partial_update(self, request, pk=None):
        existing = fs.get_document(COLL_PL_LEDGER, pk)
        if not existing:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = PLLedgerSerializer(data={**existing, **request.data}, partial=True)
        serializer.is_valid(raise_exception=True)
        fs.update_document(COLL_PL_LEDGER, pk, {
            **serializer.validated_data,
            **audit_update(request.user),
        })
        updated = fs.get_document(COLL_PL_LEDGER, pk)
        return Response(PLLedgerSerializer(updated).data)

    def destroy(self, request, pk=None):
        if not fs.get_document(COLL_PL_LEDGER, pk):
            return Response(status=status.HTTP_404_NOT_FOUND)
        fs.delete_document(COLL_PL_LEDGER, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
