from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.models import Account, Transaction, Category, AccountType, TransactionType, RecurringTransaction
from src.services.exceptions import NotFoundError, ValidationError

class FinancialLedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_account_balance(self, account_id: UUID, as_of_date: date | None = None) -> int:
        query = select(func.coalesce(func.max(Transaction.balance_after_cents), 0)).where(
            Transaction.account_id == account_id
        )
        if as_of_date:
            query = query.where(Transaction.date <= as_of_date)
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def create_account(self, user_id: UUID, name: str, account_type: AccountType, institution: str | None = None) -> Account:
        account = Account(
            user_id=user_id,
            name=name,
            account_type=account_type,
            institution=institution
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account
    
    async def get_account(self, account_id: UUID, user_id: UUID) -> Account:
        result = await self.db.execute(
            select(Account).where(Account.id == account_id, Account.user_id == user_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundError(f"Account {account_id} not found")
        return account
    
    async def list_accounts(self, user_id: UUID, include_closed: bool = False) -> list[Account]:
        query = select(Account).where(Account.user_id == user_id)
        if not include_closed:
            query = query.where(Account.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def record_transaction(
        self,
        user_id: UUID,
        account_id: UUID,
        amount_cents: int,
        date: date,
        description: str,
        transaction_type: TransactionType,
        category_id: UUID | None = None,
        payee: str | None = None,
        notes: str | None = None
    ) -> Transaction:
        if amount_cents == 0:
            raise ValidationError("Transaction amount cannot be zero")
        
        current_balance = await self.get_account_balance(account_id)
        
        if transaction_type == TransactionType.OUTFLOW:
            new_balance = current_balance - abs(amount_cents)
        else:
            new_balance = current_balance + abs(amount_cents)
        
        transaction = Transaction(
            user_id=user_id,
            account_id=account_id,
            amount_cents=abs(amount_cents),
            balance_after_cents=new_balance,
            date=date,
            description=description,
            transaction_type=transaction_type.value,
            category_id=category_id,
            payee=payee,
            notes=notes
        )
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction
    
    async def reverse_transaction(self, transaction_id: UUID, user_id: UUID, reason: str) -> Transaction:
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
        )
        original = result.scalar_one_or_none()
        if not original:
            raise NotFoundError(f"Transaction {transaction_id} not found")
        
        reverse_type = TransactionType.OUTFLOW if original.transaction_type == TransactionType.INFLOW.value else TransactionType.INFLOW
        
        compensating = Transaction(
            user_id=user_id,
            account_id=original.account_id,
            amount_cents=original.amount_cents,
            balance_after_cents=original.balance_after_cents,
            date=date.today(),
            description=f"Reversal: {original.description}",
            transaction_type=reverse_type.value,
            payee=original.payee,
            notes=f"Reversed: {reason}",
            compensating_transaction_id=original.id
        )
        self.db.add(compensating)
        original.compensating_transaction_id = compensating.id
        await self.db.commit()
        await self.db.refresh(compensating)
        return compensating
    
    async def get_transactions(
        self,
        user_id: UUID,
        account_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        category_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Transaction]:
        query = select(Transaction).where(Transaction.user_id == user_id)
        
        if account_id:
            query = query.where(Transaction.account_id == account_id)
        if start_date:
            query = query.where(Transaction.date >= start_date)
        if end_date:
            query = query.where(Transaction.date <= end_date)
        if category_id:
            query = query.where(Transaction.category_id == category_id)
        
        query = query.order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create_category(self, user_id: UUID, name: str, icon: str | None = None, color: str | None = None, parent_id: UUID | None = None) -> Category:
        category = Category(user_id=user_id, name=name, icon=icon, color=color, parent_id=parent_id)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category
    
    async def list_categories(self, user_id: UUID) -> list[Category]:
        result = await self.db.execute(
            select(Category).where(Category.user_id == user_id).order_by(Category.name)
        )
        return list(result.scalars().all())
    
    async def import_transactions(
        self,
        user_id: UUID,
        account_id: UUID,
        transactions_data: list[dict]
    ) -> list[Transaction]:
        imported = []
        current_balance = await self.get_account_balance(account_id)
        
        for txn_data in transactions_data:
            if txn_data.get("amount_cents", 0) == 0:
                continue
            
            amount = abs(txn_data["amount_cents"])
            is_inflow = txn_data.get("is_inflow", True)
            txn_type = TransactionType.INFLOW if is_inflow else TransactionType.OUTFLOW
            
            if txn_type == TransactionType.OUTFLOW:
                current_balance -= amount
            else:
                current_balance += amount
            
            transaction = Transaction(
                user_id=user_id,
                account_id=account_id,
                amount_cents=amount,
                balance_after_cents=current_balance,
                date=txn_data.get("date", date.today()),
                description=txn_data.get("description", "Imported"),
                transaction_type=txn_type.value,
                payee=txn_data.get("payee"),
                notes=f"Imported: {txn_data.get('original_description', '')}"
            )
            self.db.add(transaction)
            imported.append(transaction)
        
        await self.db.commit()
        for t in imported:
            await self.db.refresh(t)
        return imported