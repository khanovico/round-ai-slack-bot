"""Initial app_metrics table

Revision ID: 0001
Revises: 
Create Date: 2025-08-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create app_metrics table
    op.create_table('app_metrics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('app_name', sa.String(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('installs', sa.Integer(), nullable=False),
        sa.Column('in_app_revenue', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('ads_revenue', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.Column('ua_cost', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
        sa.CheckConstraint("platform IN ('iOS', 'Android')", name='check_platform'),
        sa.CheckConstraint('installs >= 0', name='check_installs_positive'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_metrics_date', 'app_metrics', ['date'])
    op.create_index('idx_metrics_app_date', 'app_metrics', ['app_name', 'date'])
    op.create_index('idx_metrics_country_date', 'app_metrics', ['country', 'date'])
    op.create_index('idx_metrics_platform_date', 'app_metrics', ['platform', 'date'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_metrics_platform_date', table_name='app_metrics')
    op.drop_index('idx_metrics_country_date', table_name='app_metrics')
    op.drop_index('idx_metrics_app_date', table_name='app_metrics')
    op.drop_index('idx_metrics_date', table_name='app_metrics')
    
    # Drop table
    op.drop_table('app_metrics')