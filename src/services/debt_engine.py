from datetime import date, timedelta
from uuid import UUID
from dataclasses import dataclass
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.models import Debt, Transaction
from src.services.exceptions import NotFoundError

@dataclass
class PayoffProjection:
    debt_id: UUID
    name: str
    months_to_payoff: int
    total_interest_cents: int
    total_cost_cents: int
    payoff_date: date
    monthly_schedule: list[dict]

@dataclass
class DebtSummary:
    total_debt_cents: int
    total_minimum_payment_cents: int
    weighted_avg_rate: int
    debt_count: int

class DebtEngineService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_debt(
        self,
        user_id: UUID,
        name: str,
        initial_amount_cents: int,
        interest_rate: int,
        minimum_payment_cents: int,
        current_balance_cents: int | None = None,
        due_day: int | None = None,
        account_id: UUID | None = None
    ) -> Debt:
        debt = Debt(
            user_id=user_id,
            name=name,
            initial_amount_cents=initial_amount_cents,
            current_balance_cents=current_balance_cents or initial_amount_cents,
            interest_rate=interest_rate,
            minimum_payment_cents=minimum_payment_cents,
            due_day=due_day,
            account_id=account_id
        )
        self.db.add(debt)
        await self.db.commit()
        await self.db.refresh(debt)
        return debt
    
    async def get_debts(self, user_id: UUID) -> list[Debt]:
        result = await self.db.execute(
            select(Debt).where(Debt.user_id == user_id).order_by(Debt.current_balance_cents.desc())
        )
        return list(result.scalars().all())
    
    async def update_debt_balance(self, debt_id: UUID, user_id: UUID, new_balance_cents: int) -> Debt:
        result = await self.db.execute(
            select(Debt).where(Debt.id == debt_id, Debt.user_id == user_id)
        )
        debt = result.scalar_one_or_none()
        if not debt:
            raise NotFoundError(f"Debt {debt_id} not found")
        
        debt.current_balance_cents = new_balance_cents
        await self.db.commit()
        await self.db.refresh(debt)
        return debt
    
    def calculate_monthly_interest(self, balance_cents: int, annual_rate_bps: int) -> int:
        monthly_rate = Decimal(annual_rate_bps) / 10000 / 12
        return int(Decimal(balance_cents) * monthly_rate)
    
    async def project_payoff(
        self,
        debt_id: UUID,
        monthly_payment_cents: int | None = None,
        extra_payment_cents: int = 0
    ) -> PayoffProjection | None:
        result = await self.db.execute(select(Debt).where(Debt.id == debt_id))
        debt = result.scalar_one_or_none()
        if not debt:
            return None
        
        payment = monthly_payment_cents or debt.minimum_payment_cents
        balance = debt.current_balance_cents
        month = 0
        schedule = []
        
        while balance > 0 and month < 360:
            month += 1
            interest = self.calculate_monthly_interest(balance, debt.interest_rate)
            total_payment = payment + extra_payment_cents
            principal = total_payment - interest
            
            if principal <= 0:
                break
            
            balance = max(0, balance - principal)
            schedule.append({
                "month": month,
                "payment_cents": total_payment,
                "interest_cents": interest,
                "principal_cents": principal,
                "balance_cents": balance
            })
        
        total_interest = sum(s["interest_cents"] for s in schedule)
        
        return PayoffProjection(
            debt_id=debt.id,
            name=debt.name,
            months_to_payoff=len(schedule),
            total_interest_cents=total_interest,
            total_cost_cents=debt.current_balance_cents + total_interest,
            payoff_date=date.today() + timedelta(days=len(schedule) * 30),
            monthly_schedule=schedule
        )
    
    async def simulate_snowball(self, user_id: UUID, extra_payment_cents: int = 0) -> list[PayoffProjection]:
        debts = await self.get_debts(user_id)
        if not debts:
            return []
        
        debts = sorted(debts, key=lambda d: d.current_balance_cents)
        return self._simulate_payoff_order(debts, extra_payment_cents)
    
    async def simulate_avalanche(self, user_id: UUID, extra_payment_cents: int = 0) -> list[PayoffProjection]:
        debts = await self.get_debts(user_id)
        if not debts:
            return []
        
        debts = sorted(debts, key=lambda d: -d.interest_rate)
        return self._simulate_payoff_order(debts, extra_payment_cents)
    
    def _simulate_payoff_order(self, debts: list[Debt], extra_payment_cents: int) -> list[PayoffProjection]:
        total_min_payment = sum(d.minimum_payment_cents for d in debts)
        available_extra = extra_payment_cents
        debt_balances = {d.id: d.current_balance_cents for d in debts}
        
        month = 0
        total_interest_paid = {d.id: 0 for d in debts}
        payoff_months = {d.id: None for d in debts}
        
        while any(balance > 0 for balance in debt_balances.values()) and month < 360:
            month += 1
            rollover = 0
            
            for debt in debts:
                if debt_balances[debt.id] <= 0:
                    rollover += debt.minimum_payment_cents + (extra_payment_cents if payoff_months[debt.id] is None else 0)
                    continue
                
                interest = self.calculate_monthly_interest(debt_balances[debt.id], debt.interest_rate)
                total_interest_paid[debt.id] += interest
                
                if payoff_months[debt.id] is None:
                    payment = debt.minimum_payment_cents + extra_payment_cents
                else:
                    payment = debt.minimum_payment_cents
                
                if month > 1:
                    payment += rollover
                
                principal = payment - interest
                if principal <= 0:
                    continue
                
                debt_balances[debt.id] = max(0, debt_balances[debt.id] - principal)
                
                if debt_balances[debt.id] <= 0 and payoff_months[debt.id] is None:
                    payoff_months[debt.id] = month
                    rollover += debt.minimum_payment_cents
        
        projections = []
        for debt in debts:
            projections.append(PayoffProjection(
                debt_id=debt.id,
                name=debt.name,
                months_to_payoff=payoff_months[debt.id] or month,
                total_interest_cents=total_interest_paid[debt.id],
                total_cost_cents=debt.current_balance_cents + total_interest_paid[debt.id],
                payoff_date=date.today() + timedelta(days=(payoff_months[debt.id] or month) * 30),
                monthly_schedule=[]
            ))
        
        return projections
    
    async def get_debt_summary(self, user_id: UUID) -> DebtSummary:
        debts = await self.get_debts(user_id)
        
        if not debts:
            return DebtSummary(
                total_debt_cents=0,
                total_minimum_payment_cents=0,
                weighted_avg_rate=0,
                debt_count=0
            )
        
        total = sum(d.current_balance_cents for d in debts)
        total_min = sum(d.minimum_payment_cents for d in debts)
        
        if total > 0:
            weighted_rate = sum(d.current_balance_cents * d.interest_rate for d in debts) // total
        else:
            weighted_rate = 0
        
        return DebtSummary(
            total_debt_cents=total,
            total_minimum_payment_cents=total_min,
            weighted_avg_rate=int(weighted_rate),
            debt_count=len(debts)
        )