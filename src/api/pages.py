from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, date
from typing import Any, Optional
from uuid import UUID
import structlog

from src.infrastructure.database import get_db
from src.domain.models import User, UserProfile, Category, TransactionType
from src.services.financial_ledger import FinancialLedgerService
from src.services.debt_engine import DebtEngineService
from src.services.forecasting import ForecastingService
from src.services.insights import InsightsService
from src.api.templates import render_template

router = APIRouter()
logger = structlog.get_logger()

class LoginForm(BaseModel):
    email: str
    password: str

class RegisterForm(BaseModel):
    name: str
    email: str
    password: str

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    return render_template("index.html", {"user": user, "request": request})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    ledger = FinancialLedgerService(db)
    debt_svc = DebtEngineService(db)
    forecast_svc = ForecastingService(db)
    insights_svc = InsightsService(db)
    
    accounts = await ledger.list_accounts(user.id)
    
    balances = {}
    for acc in accounts:
        balances[acc.id] = await ledger.get_account_balance(acc.id)
    
    accounts_with_balance = [
        {**acc.__dict__, 'balance': balances.get(acc.id, 0)}
        for acc in accounts
    ]
    
    total_assets = sum(b['balance'] for b in accounts_with_balance if b['balance'] > 0)
    total_liabilities = sum(b['balance'] for b in accounts_with_balance if b['balance'] < 0)
    net_worth = total_assets + total_liabilities
    
    safe_to_spend_data = await forecast_svc.calculate_safe_to_spend(user.id)
    
    today = date.today()
    month_start = today.replace(day=1)
    transactions = await ledger.get_transactions(user.id, start_date=month_start, limit=100)
    
    monthly_inflow = sum(t.amount_cents for t in transactions if t.transaction_type == TransactionType.INFLOW.value)
    monthly_outflow = sum(t.amount_cents for t in transactions if t.transaction_type == TransactionType.OUTFLOW.value)
    
    recent = await ledger.get_transactions(user.id, limit=5)
    recent_with_category = []
    for t in recent:
        cat_name = None
        if t.category_id:
            result = await db.execute(select(Category).where(Category.id == t.category_id))
            cat = result.scalar_one_or_none()
            if cat:
                cat_name = cat.name
        recent_with_category.append({
            **t.__dict__,
            'category': cat_name
        })
    
    upcoming = await forecast_svc.get_upcoming_bills(user.id, 14)
    
    debt_summary = await debt_svc.get_debt_summary(user.id)
    insights = await insights_svc.generate_recommendations(user.id)
    insights_formatted = [{"type": "info", "message": i} for i in insights]
    
    return render_template("dashboard.html", {
        "user": user,
        "request": request,
        "accounts": accounts_with_balance,
        "net_worth": net_worth,
        "safe_to_spend": safe_to_spend_data.safe_to_spend_cents,
        "monthly_inflow": monthly_inflow,
        "monthly_outflow": monthly_outflow,
        "recent_transactions": recent_with_category,
        "upcoming_bills": upcoming[:5],
        "insights": insights_formatted
    })

@router.get("/accounts", response_class=HTMLResponse)
async def list_accounts(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    ledger = FinancialLedgerService(db)
    accounts = await ledger.list_accounts(user.id)
    
    accounts_with_balance = []
    for acc in accounts:
        balance = await ledger.get_account_balance(acc.id)
        accounts_with_balance.append({
            'id': acc.id,
            'name': acc.name,
            'account_type': acc.account_type,
            'institution': acc.institution,
            'balance': balance
        })
    
    total_assets = sum(b['balance'] for b in accounts_with_balance if b['balance'] > 0)
    total_liabilities = sum(b['balance'] for b in accounts_with_balance if b['balance'] < 0)
    net_worth = total_assets + total_liabilities
    
    return render_template("accounts/list.html", {
        "user": user,
        "request": request,
        "accounts": accounts_with_balance,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth
    })

@router.get("/accounts/new", response_class=HTMLResponse)
async def new_account(request: Request):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    return render_template("accounts/form.html", {
        "user": user,
        "request": request,
        "account": None,
        "today": date.today().isoformat()
    })

@router.post("/accounts/new")
async def create_account(
    request: Request,
    name: str = Form(...),
    account_type: str = Form(...),
    institution: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    ledger = FinancialLedgerService(db)
    from src.domain.models import AccountType
    account_type_enum = AccountType(account_type)
    await ledger.create_account(user.id, name, account_type_enum, institution)
    
    return RedirectResponse("/accounts", status_code=303)

@router.get("/accounts/{account_id}/edit", response_class=HTMLResponse)
async def edit_account(request: Request, account_id: UUID, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    ledger = FinancialLedgerService(db)
    account = await ledger.get_account(account_id, user.id)
    
    return render_template("accounts/form.html", {
        "user": user,
        "request": request,
        "account": account,
        "today": date.today().isoformat()
    })

@router.post("/accounts/{account_id}/edit")
async def update_account(
    request: Request,
    account_id: UUID,
    name: str = Form(...),
    account_type: str = Form(...),
    institution: Optional[str] = Form(None),
    initial_balance: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    ledger = FinancialLedgerService(db)
    from src.domain.models import AccountType, TransactionType
    account = await ledger.get_account(account_id, user.id)
    
    account.name = name
    account.account_type = AccountType(account_type)
    account.institution = institution
    await db.commit()
    
    if initial_balance:
        balance_cents = int(initial_balance * 100)
        await ledger.record_transaction(
            user_id=user.id,
            account_id=account_id,
            amount_cents=balance_cents,
            date=date.today(),
            description="Initial balance",
            transaction_type=TransactionType.ADJUSTMENT
        )
    
    return RedirectResponse("/accounts", status_code=303)

@router.post("/accounts/{account_id}/delete")
async def delete_account(request: Request, account_id: UUID, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    try:
        ledger = FinancialLedgerService(db)
        account = await ledger.get_account(account_id, user.id)
        
        await db.delete(account)
        await db.commit()
        
        return RedirectResponse("/accounts", status_code=303)
    except Exception as e:
        await db.rollback()
        logger.error("delete_account_error", error=str(e), account_id=str(account_id))
        raise HTTPException(status_code=500, detail=f"Could not delete account: {e}")

from src.domain.models import Category

@router.get("/transactions", response_class=HTMLResponse)
async def list_transactions(
    request: Request,
    account_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = 1,
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    ledger = FinancialLedgerService(db)
    accounts = await ledger.list_accounts(user.id)
    categories = await ledger.list_categories(user.id)
    
    transactions = await ledger.get_transactions(
        user.id,
        account_id=account_id,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        limit=50,
        offset=(page - 1) * 50
    )
    
    transactions_with_category: list[dict[str, Any]] = []
    for t in transactions:
        cat_name = None
        if t.category_id:
            result = await db.execute(select(Category).where(Category.id == t.category_id))
            cat = result.scalar_one_or_none()
            if cat:
                cat_name = cat.name
        transactions_with_category.append({
            **t.__dict__,
            'category': cat_name
        })
    
    from collections import defaultdict
    by_date = defaultdict(list)
    for t in transactions_with_category:  # type: ignore[assignment]
        date_key = t['date'].strftime("%Y-%m-%d")
        by_date[date_key].append(t)
    
    accounts_list = [{'id': a.id, 'name': a.name} for a in accounts]
    
    return render_template("transactions/list.html", {
        "user": user,
        "request": request,
        "transactions": transactions_with_category,
        "transactions_by_date": dict(by_date),
        "accounts": accounts_list,
        "categories": [{'id': c.id, 'name': c.name} for c in categories],
        "current_category": str(category_id) if category_id else "",
        "start_date": start_date.isoformat() if start_date else "",
        "end_date": end_date.isoformat() if end_date else "",
        "current_account": str(account_id) if account_id else "",
        "pagination": {"has_next": len(transactions) == 50, "next_page": page + 1}
    })

@router.get("/transactions/new", response_class=HTMLResponse)
async def new_transaction(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        return RedirectResponse("/", status_code=303)
    
    ledger = FinancialLedgerService(db)
    accounts = await ledger.list_accounts(user.id)
    categories = await ledger.list_categories(user.id)
    
    return render_template("transactions/form.html", {
        "user": user,
        "request": request,
        "transaction": None,
        "accounts": [{'id': a.id, 'name': a.name} for a in accounts],
        "categories": [{'id': c.id, 'name': c.name} for c in categories],
        "today": date.today().isoformat()
    })

@router.post("/transactions/new")
async def create_transaction(
    request: Request,
    account_id: UUID = Form(...),
    transaction_type: str = Form(...),
    amount: float = Form(...),
    date: date = Form(...),
    description: str = Form(...),
    payee: Optional[str] = Form(None),
    category_id: Optional[UUID] = Form(None),
    notes: Optional[str] = Form(None),
    new_category_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    ledger = FinancialLedgerService(db)
    from src.domain.models import TransactionType
    txn_type = TransactionType.INFLOW if transaction_type == 'inflow' else TransactionType.OUTFLOW
    
    if new_category_name:
        new_cat = await ledger.create_category(user.id, new_category_name)
        category_id = new_cat.id
    
    await ledger.record_transaction(
        user_id=user.id,
        account_id=account_id,
        amount_cents=int(amount * 100),
        date=date,
        description=description,
        transaction_type=txn_type,
        category_id=category_id,
        payee=payee,
        notes=notes
    )
    
    return RedirectResponse("/transactions", status_code=303)

@router.post("/transactions/{transaction_id}/reverse")
async def reverse_transaction(
    request: Request,
    transaction_id: UUID,
    reason: str = "Manual reversal",
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    ledger = FinancialLedgerService(db)
    await ledger.reverse_transaction(transaction_id, user.id, reason)
    
    return RedirectResponse("/transactions", status_code=303)

@router.post("/transactions/{transaction_id}/delete")
async def delete_transaction(request: Request, transaction_id: UUID, db: AsyncSession = Depends(get_db)):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    ledger = FinancialLedgerService(db)
    await ledger.reverse_transaction(transaction_id, user.id, "User deleted")
    
    return RedirectResponse("/transactions", status_code=303)

@router.post("/categories/new")
async def create_category(
    request: Request,
    name: str = Form(...),
    icon: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        raise HTTPException(status_code=401)
    
    ledger = FinancialLedgerService(db)
    await ledger.create_category(user.id, name, icon, color)
    
    return RedirectResponse(request.headers.get("referer", "/transactions"), status_code=303)