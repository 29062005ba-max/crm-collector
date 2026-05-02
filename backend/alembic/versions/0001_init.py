"""init

Revision ID: 0001
Revises: 
Create Date: 2026-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create enum types safely
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE userrole AS ENUM ('ADMIN', 'HEAD', 'MANAGER'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE contractstatus AS ENUM ('active', 'closed', 'litigation', 'written_off'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE callresult AS ENUM ('reached', 'not_reached', 'busy', 'wrong_number', 'refused'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE promisestatus AS ENUM ('active', 'done', 'overdue', 'cancelled'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE paymentsource AS ENUM ('bank', 'cash', 'card', 'court'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE csistatus AS ENUM ('pending', 'filed', 'in_progress', 'closed'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))

    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.Text(), nullable=False, server_default='MANAGER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table('debtors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('iin', sa.String(12), nullable=False),
        sa.Column('full_name', sa.String(500), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('phone_primary', sa.String(50), nullable=True),
        sa.Column('phone_secondary', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('employer', sa.String(500), nullable=True),
        sa.Column('employer_phone', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iin'),
    )
    op.create_index('ix_debtors_iin', 'debtors', ['iin'])

    op.create_table('contracts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('debtor_id', sa.Integer(), nullable=False),
        sa.Column('contract_number', sa.String(100), nullable=False),
        sa.Column('original_creditor', sa.String(500), nullable=False),
        sa.Column('product_type', sa.String(100), nullable=True),
        sa.Column('principal_debt', sa.Numeric(18, 2), nullable=False),
        sa.Column('interest_debt', sa.Numeric(18, 2), server_default='0'),
        sa.Column('penalty_debt', sa.Numeric(18, 2), server_default='0'),
        sa.Column('total_debt', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.String(3), server_default='KZT'),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('overdue_date', sa.Date(), nullable=True),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Text(), server_default='active'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['debtor_id'], ['debtors.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contract_number'),
    )

    op.create_table('assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('manager_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['manager_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('call_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('manager_id', sa.Integer(), nullable=False),
        sa.Column('called_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('phone_number', sa.String(50)),
        sa.Column('result', sa.Text(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['manager_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('promises',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('promise_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('status', sa.Text(), server_default='active'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('source', sa.Text(), server_default='bank'),
        sa.Column('reference', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('registered_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['registered_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('csi_cases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('debtor_id', sa.Integer(), nullable=False),
        sa.Column('case_number', sa.String(100), nullable=True),
        sa.Column('filed_date', sa.Date(), nullable=True),
        sa.Column('court_name', sa.String(500), nullable=True),
        sa.Column('bailiff_name', sa.String(500), nullable=True),
        sa.Column('status', sa.Text(), server_default='pending'),
        sa.Column('amount_claimed', sa.Numeric(18, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['debtor_id'], ['debtors.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('import_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_rows', sa.Integer(), server_default='0'),
        sa.Column('success_rows', sa.Integer(), server_default='0'),
        sa.Column('error_rows', sa.Integer(), server_default='0'),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(50), server_default='processing'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('old_status', sa.String(100), nullable=True),
        sa.Column('new_status', sa.String(100), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    for t in ['audit_logs','status_history','import_logs','csi_cases','payments','promises','call_logs','assignments','contracts','debtors','users']:
        op.drop_table(t)
