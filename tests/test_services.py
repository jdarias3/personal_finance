import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from src.services.financial_ledger import FinancialLedgerService
from src.services.debt_engine import DebtEngineService
from src.services.forecasting import ForecastingService
from src.services.insights import InsightsService
from src.domain.models import Account, Transaction, Category, Debt, AccountType, TransactionType, RecurrencePattern, RecurringTransaction

@pytest.mark.asyncio
async def test_create_account(db_session):
    service = FinancialLedgerService(db_session)
    user_id = uuid4()
    
    account = await service.create_account(user_id, "Test Checking", AccountType.CHECKING, "Test Bank")
    
    assert account.name == "Test Checking"
    assert account.account_type == AccountType.CHECKING
    assert account.institution == "Test Bank"
    assert account.user_id == user_id

@pytest.mark.asyncio
async def test_record_transaction_updates_balance(db_session):
    service = FinancialLedgerService(db_session)
    user_id = uuid4()
    
    account = await service.create_account(user_id, "Test", AccountType.CHECKING)
    
    await service.record_transaction(
        user_id=user_id,
        account_id=account.id,
        amount_cents=10000,
        date=date.today(),
        description="Initial deposit",
        transaction_type=TransactionType.INFLOW
    )
    
    balance = await service.get_account_balance(account.id)
    assert balance == 10000
    
    await service.record_transaction(
        user_id=user_id,
        account_id=account.id,
        amount_cents=3000,
        date=date.today(),
        description="Coffee",
        transaction_type=TransactionType.OUTFLOW
    )
    
    balance = await service.get_account_balance(account.id)
    assert balance == 7000

@pytest.mark.asyncio
async def test_cannot_record_zero_amount(db_session):
    service = FinancialLedgerService(db_session)
    user_id = uuid4()
    account = await service.create_account(user_id, "Test", AccountType.CHECKING)
    
    with pytest.raises(Exception):
        await service.record_transaction(
            user_id=user_id,
            account_id=account.id,
            amount_cents=0,
            date=date.today(),
            description="Zero transaction",
            transaction_type=TransactionType.INFLOW
        )

@pytest.mark.asyncio
async def test_reverse_transaction(db_session):
    service = FinancialLedgerService(db_session)
    user_id = uuid4()
    account = await service.create_account(user_id, "Test", AccountType.CHECKING)
    
    original = await service.record_transaction(
        user_id=user_id,
        account_id=account.id,
        amount_cents=5000,
        date=date.today(),
        description="Test",
        transaction_type=TransactionType.INFLOW
    )
    
    reversed_txn = await service.reverse_transaction(original.id, user_id, "Testing reversal")
    
    assert reversed_txn.amount_cents == original.amount_cents
    assert reversed_txn.transaction_type == TransactionType.OUTFLOW
    assert reversed_txn.compensating_transaction_id == original.id

@pytest.mark.asyncio
async def test_create_and_project_debt(db_session):
    debt_svc = DebtEngineService(db_session)
    user_id = uuid4()
    
    debt = await debt_svc.create_debt(
        user_id=user_id,
        name="Credit Card",
        initial_amount_cents=500000,
        current_balance_cents=500000,
        interest_rate=1999,
        minimum_payment_cents=15000
    )
    
    projection = await debt_svc.project_payoff(debt.id)
    
    assert projection is not None
    assert projection.months_to_payoff > 0
    assert projection.total_interest_cents > 0

@pytest.mark.asyncio
async def test_interest_calculation(db_session):
    debt_svc = DebtEngineService(db_session)
    
    interest = debt_svc.calculate_monthly_interest(100000, 2400)
    assert interest == 2000

@pytest.mark.asyncio
async def test_forecasting_recurring(db_session):
    forecast_svc = ForecastingService(db_session)
    user_id = uuid4()
    account = Account(
        id=uuid4(),
        user_id=user_id,
        name="Checking",
        account_type=AccountType.CHECKING,
        is_active=True
    )
    db_session.add(account)
    
    recurring = RecurringTransaction(
        id=uuid4(),
        user_id=user_id,
        account_id=account.id,
        amount_cents=-50000,
        description="Rent",
        recurrence_pattern=RecurrencePattern.MONTHLY,
        start_date=date.today(),
        next_occurrence=date.today(),
        is_active=True
    )
    db_session.add(recurring)
    await db_session.commit()
    
    projections = await forecast_svc.project_cash_flow(
        user_id, date.today(), date.today() + timedelta(days=60), 100000
    )
    
    rent_days = [p for p in projections if p.outflows_cents > 0]
    assert len(rent_days) > 0

@pytest.mark.asyncio
async def test_safe_to_spend_calculation(db_session):
    forecast_svc = ForecastingService(db_session)
    user_id = uuid4()
    
    result = await forecast_svc.calculate_safe_to_spend(user_id, 10000, 5000)
    
    assert result.safe_to_spend_cents >= 0
    assert result.upcoming_bills_cents >= 0

@pytest.mark.asyncio
async def test_category_management(db_session):
    service = FinancialLedgerService(db_session)
    user_id = uuid4()
    
    cat = await service.create_category(user_id, "Groceries", "🛒", "#22c55e")
    
    assert cat.name == "Groceries"
    assert cat.icon == "🛒"
    
    categories = await service.list_categories(user_id)
    assert len(categories) == 1
    assert categories[0].name == "Groceries"

@pytest.mark.asyncio
async def test_debt_summary(db_session):
    debt_svc = DebtEngineService(db_session)
    user_id = uuid4()
    
    await debt_svc.create_debt(
        user_id=user_id,
        name="Card 1",
        initial_amount_cents=100000,
        interest_rate=2000,
        minimum_payment_cents=2500
    )
    
    await debt_svc.create_debt(
        user_id=user_id,
        name="Card 2",
        initial_amount_cents=50000,
        interest_rate=1500,
        minimum_payment_cents=1500
    )
    
    summary = await debt_svc.get_debt_summary(user_id)
    
    assert summary.debt_count == 2
    assert summary.total_debt_cents == 150000
    assert summary.weighted_avg_rate > 0