"""Multi-tenancy + soft delete

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-25

Adds:
- companies table (tenants)
- company_id FK to all main tables
- deleted_at (soft delete) on critical tables
- Migrates existing data to "Default Company"
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    # ============== Companies (tenants) ==============
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('tariff', sa.String(50), nullable=False, server_default='basic'),
        sa.Column('max_users', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_debtors', sa.Integer(), nullable=False, server_default='5000'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('settings', sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_companies_slug', 'companies', ['slug'])
    op.create_index('ix_companies_active', 'companies', ['is_active'])

    # Insert default company for existing data migration
    op.execute(text("""
        INSERT INTO companies (id, name, slug, tariff, max_users, max_debtors, is_active, contact_email)
        VALUES (1, 'Default Company', 'default', 'enterprise', 100, 100000, true, 'admin@crm.local')
    """))
    op.execute(text("SELECT setval('companies_id_seq', 1, true)"))

    # ============== Add company_id to all main tables ==============
    tables_with_company = [
        'users', 'debtors', 'contracts', 'promises', 'payments',
        'call_logs', 'tasks', 'notifications', 'activity_logs',
        'payment_schedules', 'assignments', 'csi_cases',
    ]
    for table in tables_with_company:
        op.add_column(table, sa.Column('company_id', sa.Integer(), nullable=True))
        op.execute(text(f"UPDATE {table} SET company_id = 1"))
        op.alter_column(table, 'company_id', nullable=False)
        op.create_foreign_key(
            f'fk_{table}_company', table, 'companies',
            ['company_id'], ['id'], ondelete='RESTRICT'
        )
        op.create_index(f'ix_{table}_company', table, ['company_id'])

    # ============== Soft delete (deleted_at) on critical tables ==============
    soft_delete_tables = ['debtors', 'contracts', 'promises', 'payments', 'tasks']
    for table in soft_delete_tables:
        op.add_column(table, sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        op.create_index(f'ix_{table}_deleted', table, ['deleted_at'])

    # ============== Audit Log v2: old/new values ==============
    # activity_logs already exists; add fields for stronger audit
    op.add_column('activity_logs', sa.Column('old_value', sa.dialects.postgresql.JSONB, nullable=True))
    op.add_column('activity_logs', sa.Column('new_value', sa.dialects.postgresql.JSONB, nullable=True))
    op.add_column('activity_logs', sa.Column('user_agent', sa.String(500), nullable=True))


def downgrade():
    # Remove audit v2 fields
    op.drop_column('activity_logs', 'user_agent')
    op.drop_column('activity_logs', 'new_value')
    op.drop_column('activity_logs', 'old_value')

    # Remove soft delete
    soft_delete_tables = ['debtors', 'contracts', 'promises', 'payments', 'tasks']
    for table in soft_delete_tables:
        op.drop_index(f'ix_{table}_deleted', table_name=table)
        op.drop_column(table, 'deleted_at')

    # Remove company_id
    tables_with_company = [
        'users', 'debtors', 'contracts', 'promises', 'payments',
        'call_logs', 'tasks', 'notifications', 'activity_logs',
        'payment_schedules', 'assignments', 'csi_cases',
    ]
    for table in tables_with_company:
        op.drop_index(f'ix_{table}_company', table_name=table)
        op.drop_constraint(f'fk_{table}_company', table, type_='foreignkey')
        op.drop_column(table, 'company_id')

    # Drop companies
    op.drop_index('ix_companies_active', table_name='companies')
    op.drop_index('ix_companies_slug', table_name='companies')
    op.drop_table('companies')
