from fastapi import APIRouter, Depends, Request, Response, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
import structlog

from src.infrastructure.database import get_db
from src.services.financial_ledger import FinancialLedgerService
from src.services.debt_engine import DebtEngineService
from src.services.forecasting import ForecastingService
from src.api.templates import render_template

router = APIRouter()
logger = structlog.get_logger()

from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import date, timedelta
from src.domain.models import Category, Debt, UserProfile
from fastapi import HTTPException

@router.get("/debts", response_class=HTMLResponse)
async def list_debts(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    debt_svc = DebtEngineService(db)
    summary = await debt_svc.get_debt_summary(user.id)
    debts = await debt_svc.get_debts(user.id)
    
    debts_data = [
        {
            'id': d.id,
            'name': d.name,
            'initial_amount_cents': d.initial_amount_cents,
            'current_balance_cents': d.current_balance_cents,
            'interest_rate': d.interest_rate,
            'minimum_payment_cents': d.minimum_payment_cents,
            'due_day': d.due_day,
            'account_id': d.account_id
        }
        for d in debts
    ]
    
    return render_template("debts/list.html", {
        "user": user,
        "request": request,
        "debts": debts_data,
        "summary": {
            'total_debt_cents': summary.total_debt_cents,
            'total_minimum_payment_cents': summary.total_minimum_payment_cents,
            'weighted_avg_rate': summary.weighted_avg_rate
        }
    })

@router.get("/debts/new", response_class=HTMLResponse)
async def new_debt(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    ledger = FinancialLedgerService(db)
    accounts = await ledger.list_accounts(user.id)
    
    return render_template("debts/form.html", {
        "user": user,
        "request": request,
        "debt": None,
        "accounts": [{'id': a.id, 'name': a.name} for a in accounts]
    })

@router.post("/debts/new")
async def create_debt(
    request: Request,
    name: str = Form(...),
    initial_amount: float = Form(...),
    current_balance: float = Form(...),
    interest_rate: float = Form(...),
    minimum_payment: float = Form(...),
    due_day: Optional[int] = Form(None),
    account_id: Optional[UUID] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    debt_svc = DebtEngineService(db)
    await debt_svc.create_debt(
        user_id=user.id,
        name=name,
        initial_amount_cents=int(initial_amount * 100),
        current_balance_cents=int(current_balance * 100),
        interest_rate=int(interest_rate * 100),
        minimum_payment_cents=int(minimum_payment * 100),
        due_day=due_day,
        account_id=account_id
    )
    
    return RedirectResponse("/debts", status_code=303)

@router.get("/debts/{debt_id}/edit", response_class=HTMLResponse)
async def edit_debt(request: Request, debt_id: UUID, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    result = await db.execute(select(Debt).where(Debt.id == debt_id, Debt.user_id == user.id))
    debt = result.scalar_one_or_none()
    if not debt:
        return RedirectResponse("/debts", status_code=303)
    
    ledger = FinancialLedgerService(db)
    accounts = await ledger.list_accounts(user.id)
    
    return render_template("debts/form.html", {
        "user": user,
        "request": request,
        "debt": {
            'id': debt.id,
            'name': debt.name,
            'initial_amount_cents': debt.initial_amount_cents,
            'current_balance_cents': debt.current_balance_cents,
            'interest_rate': debt.interest_rate,
            'minimum_payment_cents': debt.minimum_payment_cents,
            'due_day': debt.due_day,
            'account_id': debt.account_id
        },
        "accounts": [{'id': a.id, 'name': a.name} for a in accounts]
    })

@router.post("/debts/{debt_id}/edit")
async def update_debt(
    request: Request,
    debt_id: UUID,
    name: str = Form(...),
    initial_amount: float = Form(...),
    current_balance: float = Form(...),
    interest_rate: float = Form(...),
    minimum_payment: float = Form(...),
    due_day: Optional[int] = Form(None),
    account_id: Optional[UUID] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    result = await db.execute(select(Debt).where(Debt.id == debt_id, Debt.user_id == user.id))
    debt = result.scalar_one_or_none()
    if not debt:
        raise HTTPException(status_code=404)
    
    debt.name = name
    debt.initial_amount_cents = int(initial_amount * 100)
    debt.current_balance_cents = int(current_balance * 100)
    debt.interest_rate = int(interest_rate * 100)
    debt.minimum_payment_cents = int(minimum_payment * 100)
    debt.due_day = due_day
    debt.account_id = account_id
    await db.commit()
    
    return RedirectResponse("/debts", status_code=303)

@router.post("/debts/{debt_id}/delete")
async def delete_debt(request: Request, debt_id: UUID, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    result = await db.execute(select(Debt).where(Debt.id == debt_id, Debt.user_id == user.id))
    debt = result.scalar_one_or_none()
    if not debt:
        raise HTTPException(status_code=404)
    
    await db.delete(debt)
    await db.commit()
    
    return RedirectResponse("/debts", status_code=303)

@router.get("/debts/{debt_id}", response_class=HTMLResponse)
async def simulate_debt(request: Request, debt_id: UUID, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    debt_svc = DebtEngineService(db)
    projection = await debt_svc.project_payoff(debt_id)
    
    if not projection:
        raise HTTPException(status_code=404)
    
    debt_data = {
        'id': debt_id,
        'name': projection.name,
        'current_balance_cents': 0,
        'interest_rate': 0,
        'minimum_payment_cents': 0
    }
    
    result = await db.execute(select(Debt).where(Debt.id == debt_id, Debt.user_id == user.id))
    debt = result.scalar_one_or_none()
    if debt:
        debt_data = {
            'id': debt.id,
            'name': debt.name,
            'current_balance_cents': debt.current_balance_cents,
            'interest_rate': debt.interest_rate,
            'minimum_payment_cents': debt.minimum_payment_cents
        }
    
    return render_template("debts/simulate.html", {
        "user": user,
        "request": request,
        "debt": debt_data,
        "projection": {
            'months_to_payoff': projection.months_to_payoff,
            'total_interest_cents': projection.total_interest_cents,
            'total_cost_cents': projection.total_cost_cents,
            'payoff_date': projection.payoff_date,
            'monthly_schedule': projection.monthly_schedule
        }
    })

@router.post("/debts/{debt_id}/project", response_class=HTMLResponse)
async def project_debt(
    request: Request,
    debt_id: UUID,
    monthly_payment: float = Form(0),
    extra_payment: float = Form(0),
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    logger.info("project_debt_called", debt_id=debt_id, monthly_payment=monthly_payment, extra_payment=extra_payment)
    
    debug_info = f"Received: monthly_payment={monthly_payment}, extra_payment={extra_payment}, in_cents: monthly={int(monthly_payment * 100)}, extra={int(extra_payment * 100)}"
    
    debt_svc = DebtEngineService(db)
    projection = await debt_svc.project_payoff(
        debt_id,
        monthly_payment_cents=int(monthly_payment * 100) if monthly_payment is not None and monthly_payment > 0 else None,
        extra_payment_cents=int(extra_payment * 100)
    )
    
    if not projection:
        return Response(content="<p>Error calculating projection</p>", media_type="text/html")
    
    schedule_html = ""
    for i, p in enumerate(projection.monthly_schedule[:12], 1):
        payment_str = f"${p['payment_cents'] / 100:,.2f}"
        principal_str = f"${p['principal_cents'] / 100:,.2f}"
        interest_str = f"${p['interest_cents'] / 100:,.2f}"
        balance_str = f"${p['balance_cents'] / 100:,.2f}"
        schedule_html += f"""<tr style="border-bottom: 1px solid var(--border);">
            <td style="padding: 0.75rem;">{p['month']}</td>
            <td style="text-align: right; padding: 0.75rem;">{payment_str}</td>
            <td style="text-align: right; padding: 0.75rem; color: var(--success);">{principal_str}</td>
            <td style="text-align: right; padding: 0.75rem; color: var(--danger);">{interest_str}</td>
            <td style="text-align: right; padding: 0.75rem;">{balance_str}</td>
        </tr>"""
    
    total_months = projection.months_to_payoff
    show_note = f"<p style='text-align: center; color: var(--text-muted); font-size: 0.875rem; margin-top: 1rem;'>Showing first 12 months. Full schedule has {total_months} months.</p>" if total_months > 12 else ""
    
    months_str = str(projection.months_to_payoff)
    payoff_date_str = str(projection.payoff_date)
    total_interest_str = f"${projection.total_interest_cents / 100:,.2f}"
    total_cost_str = f"${projection.total_cost_cents / 100:,.2f}"
    
    html = f"""<pre id="debug-info" style="font-size: 0.75rem; background: #333; color: #0f0; padding: 0.5rem; border-radius: 4px; margin-bottom: 1rem;">{debug_info}</pre>
    <div class="grid grid-2" style="margin-bottom: 2rem;">
        <div class="card stat-card">
            <div class="stat-label">Months to Payoff</div>
            <div class="stat-value">{months_str}</div>
            <div style="font-size: 0.875rem; color: var(--text-muted);">{payoff_date_str}</div>
        </div>
        <div class="card stat-card">
            <div class="stat-label">Total Interest</div>
            <div class="stat-value negative">{total_interest_str}</div>
            <div class="stat-change down">of {total_cost_str} total</div>
        </div>
    </div>
    
    <div class="card">
        <h2 style="font-size: 1.125rem; margin: 0 0 1rem;">Payment Schedule</h2>
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--border);">
                        <th style="text-align: left; padding: 0.75rem; color: var(--text-muted);">Month</th>
                        <th style="text-align: right; padding: 0.75rem; color: var(--text-muted);">Payment</th>
                        <th style="text-align: right; padding: 0.75rem; color: var(--text-muted);">Principal</th>
                        <th style="text-align: right; padding: 0.75rem; color: var(--text-muted);">Interest</th>
                        <th style="text-align: right; padding: 0.75rem; color: var(--text-muted);">Balance</th>
                    </tr>
                </thead>
                <tbody>
                    {schedule_html}
                </tbody>
            </table>
        </div>
        {show_note}
    </div>
    """
    
    return Response(content=html, media_type="text/html")

@router.get("/debts/simulate/{method}", response_class=HTMLResponse)
async def simulate_method_page(
    request: Request,
    method: str,
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    debt_svc = DebtEngineService(db)
    
    if method == "snowball":
        projections = await debt_svc.simulate_snowball(user.id, 0)
    else:
        projections = await debt_svc.simulate_avalanche(user.id, 0)
    
    projections_data = [
        {
            'name': p.name,
            'months_to_payoff': p.months_to_payoff,
            'total_interest_cents': p.total_interest_cents,
            'total_cost_cents': p.total_cost_cents
        }
        for p in projections
    ]
    
    return render_template("debts/simulate_method.html", {
        "user": user,
        "request": request,
        "method": method,
        "projections": projections_data
    })

@router.post("/debts/simulate/extra", response_class=HTMLResponse)
async def simulate_extra_payment(
    request: Request,
    extra_payment: float = Form(...),
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    htmx_request = request.headers.get("HX-Request", "false")
    
    debt_svc = DebtEngineService(db)
    avalanche_projections = await debt_svc.simulate_avalanche(user.id, int(extra_payment * 100))
    snowball_projections = await debt_svc.simulate_snowball(user.id, int(extra_payment * 100))
    
    def build_html_table(projections, method_name):
        html = f"""
        <div class="card" style="margin-top: 1.5rem;">
            <h3 style="font-size: 1rem; margin: 0 0 0.75rem;">{method_name}</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid var(--border);">
                        <th style="text-align: left; padding: 0.5rem;">#</th>
                        <th style="text-align: left; padding: 0.5rem;">Debt</th>
                        <th style="text-align: right; padding: 0.5rem;">Months</th>
                        <th style="text-align: right; padding: 0.5rem;">Interest</th>
                    </tr>
                </thead>
                <tbody>
        """
        for i, proj in enumerate(projections, 1):
            html += f"""
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 0.5rem;">{i}</td>
                        <td style="padding: 0.5rem;">{proj.name}</td>
                        <td style="text-align: right; padding: 0.5rem;">{proj.months_to_payoff}</td>
                        <td style="text-align: right; padding: 0.5rem;">${proj.total_interest_cents / 100:,.2f}</td>
                    </tr>
            """
        total_interest = sum(p.total_interest_cents for p in projections)
        total_months = max(p.months_to_payoff for p in projections) if projections else 0
        html += f"""
                </tbody>
                <tfoot>
                    <tr style="font-weight: 600;">
                        <td colspan="2" style="padding: 0.5rem;">Total</td>
                        <td style="text-align: right; padding: 0.5rem;">~{total_months}</td>
                        <td style="text-align: right; padding: 0.5rem;">${total_interest / 100:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """
        return html
    
    html = build_html_table(avalanche_projections, "Avalanche Method")
    html += build_html_table(snowball_projections, "Snowball Method")
    
    return Response(content=html, media_type="text/html")

@router.get("/forecast", response_class=HTMLResponse)
async def forecast(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    forecast_svc = ForecastingService(db)
    
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    cash_buffer = profile.cash_buffer_cents if profile else 0
    low_threshold = profile.low_balance_threshold_cents if profile else 0
    
    safe_to_spend = await forecast_svc.calculate_safe_to_spend(user.id, cash_buffer, low_threshold)
    
    today = date.today()
    end_date = today + timedelta(days=30)
    projections = await forecast_svc.project_cash_flow(user.id, today, end_date, safe_to_spend.current_balance_cents)
    
    upcoming = await forecast_svc.get_upcoming_bills(user.id, 30)
    
    return render_template("forecasting/index.html", {
        "user": user,
        "request": request,
        "safe_to_spend": {
            'current_balance_cents': safe_to_spend.current_balance_cents,
            'safe_to_spend_cents': safe_to_spend.safe_to_spend_cents,
            'upcoming_bills_cents': safe_to_spend.upcoming_bills_cents,
            'days_until_low_balance': safe_to_spend.days_until_low_balance
        },
        "projections": [
            {
                'date': p.date,
                'inflows_cents': p.inflows_cents,
                'outflows_cents': p.outflows_cents,
                'net_cents': p.net_cents,
                'projected_balance_cents': p.projected_balance_cents
            }
            for p in projections
        ],
        "upcoming_bills": upcoming
    })

@router.get("/recurring/new", response_class=HTMLResponse)
async def new_recurring(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    ledger = FinancialLedgerService(db)
    accounts = await ledger.list_accounts(user.id)
    categories = await ledger.list_categories(user.id)
    
    return render_template("recurring/form.html", {
        "user": user,
        "request": request,
        "recurring": None,
        "accounts": [{'id': a.id, 'name': a.name} for a in accounts],
        "categories": [{'id': c.id, 'name': c.name} for c in categories],
        "today": date.today().isoformat()
    })

@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding(request: Request):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    return render_template("onboarding/index.html", {"user": user})

@router.post("/onboarding/profile")
async def setup_profile(
    request: Request,
    profile_mode: str = Form(...),
    cash_buffer: Optional[float] = Form(None),
    low_balance_threshold: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    existing = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = existing.scalar_one_or_none()
    
    if profile:
        profile.profile_mode = profile_mode
        profile.cash_buffer_cents = int(cash_buffer * 100) if cash_buffer else 0
        profile.low_balance_threshold_cents = int(low_balance_threshold * 100) if low_balance_threshold else 0
    else:
        profile = UserProfile(
            user_id=user.id,
            profile_mode=profile_mode,
            cash_buffer_cents=int(cash_buffer * 100) if cash_buffer else 0,
            low_balance_threshold_cents=int(low_balance_threshold * 100) if low_balance_threshold else 0
        )
        db.add(profile)
    
    await db.commit()
    
    return RedirectResponse("/dashboard", status_code=303)