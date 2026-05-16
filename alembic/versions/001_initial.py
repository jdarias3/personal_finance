"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-05-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
    )
    
    op.create_table('user_profiles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('profile_mode', sa.String(50), nullable=False, default='financial-os'),
        sa.Column('cash_buffer_cents', sa.BigInteger(), nullable=False, default=0),
        sa.Column('low_balance_threshold_cents', sa.BigInteger(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    op.create_table('accounts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('account_type', sa.String(20), nullable=False),
        sa.Column('institution', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_accounts_user_id', 'accounts', ['user_id'])
    
    op.create_table('categories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('categories.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_categories_user_id', 'categories', ['user_id'])
    
    op.create_table('transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('categories.id'), nullable=True),
        sa.Column('amount_cents', sa.BigInteger(), nullable=False),
        sa.Column('balance_after_cents', sa.BigInteger(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('transaction_type', sa.String(20), nullable=False),
        sa.Column('payee', sa.String(255), nullable=True),
        sa.Column('notes', sa.String(1000), nullable=True),
        sa.Column('is_reconciled', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('compensating_transaction_id', UUID(as_uuid=True), sa.ForeignKey('transactions.id'), nullable=True),
    )
    op.create_index('ix_transactions_user_date', 'transactions', ['user_id', 'date'])
    op.create_index('ix_transactions_account_date', 'transactions', ['account_id', 'date'])
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'])
    op.create_check_constraint('non_zero_amount', 'transactions', 'amount_cents != 0')
    
    op.create_table('recurring_transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('categories.id'), nullable=True),
        sa.Column('amount_cents', sa.BigInteger(), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('payee', sa.String(255), nullable=True),
        sa.Column('recurrence_pattern', sa.String(20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('next_occurrence', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_recurring_user_id', 'recurring_transactions', ['user_id'])
    
    op.create_table('debts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('initial_amount_cents', sa.BigInteger(), nullable=False),
        sa.Column('current_balance_cents', sa.BigInteger(), nullable=False),
        sa.Column('interest_rate', sa.Integer(), nullable=False),
        sa.Column('minimum_payment_cents', sa.BigInteger(), nullable=False),
        sa.Column('due_day', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_debts_user_id', 'debts', ['user_id'])

def downgrade() -> None:
    for table in ['debts', 'recurring_transactions', 'transactions', 'categories', 'accounts', 'user_profiles', 'users']:
        op.drop_table(table)