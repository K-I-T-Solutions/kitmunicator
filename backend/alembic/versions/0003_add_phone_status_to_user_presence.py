"""add phone_status to user_presence

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    phone_status_enum = sa.Enum(
        "idle", "ringing", "in_call", "offline",
        name="phonestatus",
    )
    phone_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "user_presence",
        sa.Column(
            "phone_status",
            phone_status_enum,
            nullable=False,
            server_default="offline",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_presence", "phone_status")
    sa.Enum(name="phonestatus").drop(op.get_bind(), checkfirst=True)
