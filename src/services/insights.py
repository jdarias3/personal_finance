from datetime import date, timedelta
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy import select, func, and_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.models import Transaction, Category, Account, TransactionType

@dataclass
class SpendingInsight:
    category: str
    current_period_cents: int
    previous_period_cents: int
    percent_change: float
    trend: str

@dataclass
class AnomalyAlert:
    description: str
    severity: str
    suggested_action: str

class InsightsService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_spending_by_category(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> list[SpendingInsight]:
        outflow_value = TransactionType.OUTFLOW.value
        
        current_q = select(
            Category.name,
            func.sum(Transaction.amount_cents).label("total")
        ).join(Transaction, Transaction.category_id == Category.id).where(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            cast(Transaction.transaction_type, String) == outflow_value
        ).group_by(Category.id, Category.name)
        
        prev_start = start_date - (end_date - start_date)
        prev_end = start_date - timedelta(days=1)
        
        prev_q = select(
            Category.name,
            func.sum(Transaction.amount_cents).label("total")
        ).join(Transaction, Transaction.category_id == Category.id).where(
            Transaction.user_id == user_id,
            Transaction.date >= prev_start,
            Transaction.date <= prev_end,
            cast(Transaction.transaction_type, String) == outflow_value
        ).group_by(Category.id, Category.name)
        
        current_result = await self.db.execute(current_q)
        prev_result = await self.db.execute(prev_q)
        
        current_by_cat = {r.name: r.total for r in current_result}
        prev_by_cat = {r.name: r.total for r in prev_result}
        
        insights = []
        all_cats = set(current_by_cat.keys()) | set(prev_by_cat.keys())
        
        for cat in all_cats:
            curr = current_by_cat.get(cat, 0)
            prev = prev_by_cat.get(cat, 0)
            pct = ((curr - prev) / prev * 100) if prev > 0 else 0
            
            trend = "up" if curr > prev else "down" if curr < prev else "stable"
            
            insights.append(SpendingInsight(
                category=cat,
                current_period_cents=curr,
                previous_period_cents=prev,
                percent_change=pct,
                trend=trend
            ))
        
        return sorted(insights, key=lambda i: -abs(i.percent_change))
    
    async def detect_unusual_spending(self, user_id: UUID, threshold_pct: float = 50) -> list[AnomalyAlert]:
        today = date.today()
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        last_month_end = month_start - timedelta(days=1)
        
        insights = await self.get_spending_by_category(user_id, month_start, today)
        
        alerts = []
        for insight in insights:
            if abs(insight.percent_change) >= threshold_pct:
                alerts.append(AnomalyAlert(
                    description=f"Spending in '{insight.category}' is {insight.trend} {abs(insight.percent_change):.0f}% compared to last month",
                    severity="warning" if insight.trend == "up" else "info",
                    suggested_action=f"Review your {insight.category} spending patterns"
                ))
        
        return alerts
    
    async def get_monthly_summary(self, user_id: UUID, year: int, month: int) -> dict:
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        inflow_value = TransactionType.INFLOW.value
        outflow_value = TransactionType.OUTFLOW.value
        
        inflow_q = select(func.sum(Transaction.amount_cents)).where(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            cast(Transaction.transaction_type, String) == inflow_value
        )
        
        outflow_q = select(func.sum(Transaction.amount_cents)).where(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            cast(Transaction.transaction_type, String) == outflow_value
        )
        
        inflow_r = await self.db.execute(inflow_q)
        outflow_r = await self.db.execute(outflow_q)
        
        inflows = inflow_r.scalar() or 0
        outflows = outflow_r.scalar() or 0
        
        category_breakdown = await self.get_spending_by_category(user_id, start_date, end_date)
        
        return {
            "period": f"{year}-{month:02d}",
            "total_inflow_cents": inflows,
            "total_outflow_cents": outflows,
            "net_cents": inflows - outflows,
            "category_breakdown": [
                {"category": c.category, "amount_cents": c.current_period_cents}
                for c in category_breakdown
            ]
        }
    
    async def generate_recommendations(self, user_id: UUID) -> list[str]:
        recommendations = []
        
        debt_summary = await self.db.execute(
            select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
        )
        transaction_count = debt_summary.scalar() or 0
        
        if transaction_count < 5:
            recommendations.append("Start by adding your first account and transactions to get personalized insights")
        
        alerts = await self.detect_unusual_spending(user_id)
        if alerts:
            for alert in alerts[:2]:
                recommendations.append(alert.suggested_action)
        
        return recommendations