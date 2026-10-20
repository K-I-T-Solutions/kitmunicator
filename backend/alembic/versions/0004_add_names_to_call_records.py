"""add caller_name and callee_name to call_records

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("call_records", sa.Column("caller_name", sa.String(255), nullable=True))
    op.add_column("call_records", sa.Column("callee_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("call_records", "callee_name")
    op.drop_column("call_records", "caller_name")
