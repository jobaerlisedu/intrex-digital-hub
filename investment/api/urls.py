from django.urls import path, include
from rest_framework.routers import DefaultRouter
from investment.api.viewsets import (
    InvestorViewSet,
    TransactionViewSet,
    LoanViewSet,
    LoanScheduleViewSet,
    OutboundPlacementViewSet,
    FinancialInstrumentViewSet,
    InstrumentPriceViewSet,
    PLLedgerViewSet,
    NavHistoryViewSet,
    InvestorHoldingViewSet,
    FeeStructureViewSet,
    FeeAccrualViewSet,
    PortalHoldingViewSet,
    PortalTransactionViewSet,
)

router = DefaultRouter()
router.register(r'investors', InvestorViewSet, basename='investment-investor')
router.register(r'transactions', TransactionViewSet, basename='investment-transaction')
router.register(r'loans', LoanViewSet, basename='investment-loan')
router.register(r'loan-schedules', LoanScheduleViewSet, basename='investment-loanschedule')
router.register(r'outbound-placements', OutboundPlacementViewSet, basename='investment-outboundplacement')
router.register(r'financial-instruments', FinancialInstrumentViewSet, basename='investment-financialinstrument')
router.register(r'instrument-prices', InstrumentPriceViewSet, basename='investment-instrumentprice')
router.register(r'pl-ledger', PLLedgerViewSet, basename='investment-plledger')
router.register(r'nav-history', NavHistoryViewSet, basename='investment-navhistory')
router.register(r'investor-holdings', InvestorHoldingViewSet, basename='investment-investorholding')
router.register(r'fee-structures', FeeStructureViewSet, basename='investment-feestructure')
router.register(r'fee-accruals', FeeAccrualViewSet, basename='investment-feeaccrual')
router.register(r'portal/holdings', PortalHoldingViewSet, basename='portal-holdings')
router.register(r'portal/transactions', PortalTransactionViewSet, basename='portal-transactions')

urlpatterns = [
    path('', include(router.urls)),
]
