"""Billing tables: subscriptions, invoices, payment methods

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    # Subscriptions
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('stripe_customer_id', sa.String(64), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(64), nullable=True, unique=True),
        sa.Column('tariff', sa.String(32), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='trial'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('amount_per_month', sa.Numeric(10, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='KZT'),
        sa.Column('metadata_json', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])

    # Invoices
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscription_id', sa.Integer(), sa.ForeignKey('subscriptions.id'), nullable=True),
        sa.Column('stripe_invoice_id', sa.String(64), nullable=True, unique=True),
        sa.Column('invoice_number', sa.String(64), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='KZT'),
        sa.Column('status', sa.String(32), nullable=False, server_default='draft'),  # draft|open|paid|void|uncollectible
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pdf_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_invoices_company', 'invoices', ['company_id'])

    # Stripe webhook events log (for replay protection)
    op.create_table(
        'stripe_webhook_events',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('stripe_event_id', sa.String(64), unique=True, nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table('stripe_webhook_events')
    op.drop_index('ix_invoices_company', table_name='invoices')
    op.drop_table('invoices')
    op.drop_index('ix_subscriptions_status', table_name='subscriptions')
    op.drop_table('subscriptions')
