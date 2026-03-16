"""Add LinUCB: linucb_state table + job fields

Revision ID: 001_add_linucb
Revises:
Create Date: 2025-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_add_linucb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Новая таблица linucb_state ───────────────────────────────────────
    op.create_table(
        'linucb_state',
        sa.Column('arm_id',      sa.Integer(),     primary_key=True),
        sa.Column('arm_name',    sa.String(40),    nullable=False),
        sa.Column('A_flat',      postgresql.JSONB(), nullable=False),
        sa.Column('b_vec',       postgresql.JSONB(), nullable=False),
        sa.Column('n_pulls',     sa.Integer(),     nullable=False,
                  server_default=sa.text('0')),
        sa.Column('last_reward', sa.Float(),       nullable=False,
                  server_default=sa.text('0.0')),
        sa.Column('updated_at',  sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
        sa.UniqueConstraint('arm_name', name='uq_linucb_arm_name'),
    )

    # ── Новые поля в таблице jobs ────────────────────────────────────────
    op.add_column('jobs',
        sa.Column('use_linucb', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')))
    op.add_column('jobs',
        sa.Column('linucb_arm', sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'linucb_arm')
    op.drop_column('jobs', 'use_linucb')
    op.drop_table('linucb_state')
