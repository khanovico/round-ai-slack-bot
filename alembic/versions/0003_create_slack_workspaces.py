"""Create slack_workspaces table

Revision ID: 0003
Revises: 0002
Create Date: 2025-08-16 00:02:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'slack_workspaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.String(length=50), nullable=False),
        sa.Column('team_name', sa.String(length=255), nullable=False),
        sa.Column('bot_user_id', sa.String(length=50), nullable=False),
        sa.Column('bot_token', sa.Text(), nullable=False),
        sa.Column('installed_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id')
    )


def downgrade() -> None:
    op.drop_table('slack_workspaces')
