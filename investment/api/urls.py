from django.urls import path, include
from rest_framework.routers import DefaultRouter
from investment.api.viewsets import (
    InvestorViewSet,
    TransactionViewSet,
    LoanViewSet,
    LoanScheduleViewSet,
    OutboundPlacementViewSet,
    FinancialInstrumentViewSet,
    PLLedgerViewSet,
)

router = DefaultRouter()
router.register(r'investors', InvestorViewSet, basename='investment-investor')
router.register(r'transactions', TransactionViewSet, basename='investment-transaction')
router.register(r'loans', LoanViewSet, basename='investment-loan')
router.register(r'loan-schedules', LoanScheduleViewSet, basename='investment-loanschedule')
router.register(r'outbound-placements', OutboundPlacementViewSet, basename='investment-outboundplacement')
router.register(r'financial-instruments', FinancialInstrumentViewSet, basename='investment-financialinstrument')
router.register(r'pl-ledger', PLLedgerViewSet, basename='investment-plledger')

urlpatterns = [
    path('', include(router.urls)),
]
