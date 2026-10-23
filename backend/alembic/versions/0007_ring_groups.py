"""ring groups (Sammelrufnummern) mit Mitgliedern und Sipgate-Nummer

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ring_groups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("extension", sa.String(20), nullable=False, unique=True),
        sa.Column("ring_timeout", sa.Integer, nullable=False, server_default="25"),
        sa.Column("fallback_extension", sa.String(20), nullable=True),
        sa.Column("inbound_number", sa.String(30), nullable=True, unique=True),
        sa.Column("inbound_catch_all", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "ring_group_members",
        sa.Column("group_id", sa.Integer, sa.ForeignKey("ring_groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("sip_account_id", sa.Integer, sa.ForeignKey("sip_accounts.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("ring_group_members")
    op.drop_table("ring_groups")
