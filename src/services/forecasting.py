from datetime import date, timedelta
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.models import Transaction, RecurringTransaction, Account, RecurrencePattern
from dateutil.relativedelta import relativedelta

@dataclass
class CashFlowProjection:
    date: date
    inflows_cents: int
    outflows_cents: int
    net_cents: int
    projected_balance_cents: int

@dataclass
class SafeToSpendResult:
    current_balance_cents: int
    safe_to_spend_cents: int
    upcoming_bills_cents: int
    days_until_low_balance: int | None

class ForecastingService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _next_occurrence(self, current: date, pattern: RecurrencePattern) -> date:
        match pattern:
            case RecurrencePattern.DAILY:
                return current + timedelta(days=1)
            case RecurrencePattern.WEEKLY:
                return current + timedelta(weeks=1)
            case RecurrencePattern.BIWEEKLY:
                return current + timedelta(weeks=2)
            case RecurrencePattern.MONTHLY:
                return current + relativedelta(months=1)
            case RecurrencePattern.YEARLY:
                return current + relativedelta(years=1)
    
    async def get_recurring_transactions(self, user_id: UUID) -> list[RecurringTransaction]:
        result = await self.db.execute(
            select(RecurringTransaction).where(
                RecurringTransaction.user_id == user_id,
                RecurringTransaction.is_active == True
            )
        )
        return list(result.scalars().all())
    
    async def project_cash_flow(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        current_balance_cents: int = 0
    ) -> list[CashFlowProjection]:
        recurring = await self.get_recurring_transactions(user_id)
        
        projections = []
        balance = current_balance_cents
        current = start_date
        
        while current <= end_date:
            inflows = 0
            outflows = 0
            
            for r in recurring:
                if r.next_occurrence <= current:
                    if r.amount_cents > 0:
                        inflows += r.amount_cents
                    else:
                        outflows += abs(r.amount_cents)
            
            net = inflows - outflows
            balance += net
            
            projections.append(CashFlowProjection(
                date=current,
                inflows_cents=inflows,
                outflows_cents=outflows,
                net_cents=net,
                projected_balance_cents=balance
            ))
            
            current += timedelta(days=1)
        
        return projections
    
    async def get_upcoming_bills(
        self,
        user_id: UUID,
        days_ahead: int = 30
    ) -> list[dict]:
        recurring = await self.get_recurring_transactions(user_id)
        bills = []
        end_date = date.today() + timedelta(days=days_ahead)
        
        for r in recurring:
            next_date = r.next_occurrence
            while next_date <= end_date:
                if next_date >= date.today():
                    bills.append({
                        "id": str(r.id),
                        "description": r.description,
                        "amount_cents": abs(r.amount_cents),
                        "date": next_date,
                        "is_inflow": r.amount_cents > 0,
                        "payee": r.payee
                    })
                next_date = self._next_occurrence(next_date, r.recurrence_pattern)
        
        return sorted(bills, key=lambda b: b["date"])
    
    async def calculate_safe_to_spend(
        self,
        user_id: UUID,
        cash_buffer_cents: int = 0,
        low_balance_threshold_cents: int = 0
    ) -> SafeToSpendResult:
        result = await self.db.execute(
            select(Account).where(Account.user_id == user_id, Account.is_active == True)
        )
        accounts = list(result.scalars().all())
        
        current_balance = 0
        for acc in accounts:
            if acc.account_type.value in ["checking", "savings", "cash"]:
                q = select(Transaction).where(
                    Transaction.account_id == acc.id
                ).order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(1)
                r = await self.db.execute(q)
                latest = r.scalar_one_or_none()
                if latest:
                    current_balance += latest.balance_after_cents
        
        bills = await self.get_upcoming_bills(user_id, 30)
        upcoming_cents = sum(b["amount_cents"] for b in bills if not b["is_inflow"])
        
        available = max(0, current_balance - cash_buffer_cents - low_balance_threshold_cents - upcoming_cents)
        
        days_until_low = None
        if current_balance > 0:
            projections = await self.project_cash_flow(
                user_id, date.today(), date.today() + timedelta(days=30), current_balance
            )
            for p in projections:
                if p.projected_balance_cents <= low_balance_threshold_cents:
                    days_until_low = (p.date - date.today()).days
                    break
        
        return SafeToSpendResult(
            current_balance_cents=current_balance,
            safe_to_spend_cents=available,
            upcoming_bills_cents=upcoming_cents,
            days_until_low_balance=days_until_low
        )
    
    async def get_low_balance_forecast(
        self,
        user_id: UUID,
        threshold_cents: int
    ) -> list[dict]:
        result = await self.db.execute(
            select(Account).where(Account.user_id == user_id, Account.is_active == True)
        )
        accounts = list(result.scalars().all())
        
        total_balance = 0
        for acc in accounts:
            if acc.account_type.value in ["checking", "savings", "cash"]:
                q = select(Transaction).where(
                    Transaction.account_id == acc.id
                ).order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(1)
                r = await self.db.execute(q)
                latest = r.scalar_one_or_none()
                if latest:
                    total_balance += latest.balance_after_cents
        
        projections = await self.project_cash_flow(
            user_id, date.today(), date.today() + timedelta(days=90), total_balance
        )
        
        return [
            {"date": p.date, "balance": p.projected_balance_cents, "below_threshold": p.projected_balance_cents < threshold_cents}
            for p in projections if p.projected_balance_cents < threshold_cents
        ]