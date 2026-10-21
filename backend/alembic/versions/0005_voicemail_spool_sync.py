"""add asterisk_msg_id and caller_name to voicemails

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("voicemails", sa.Column("asterisk_msg_id", sa.String(64), nullable=True))
    op.add_column("voicemails", sa.Column("caller_name", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_voicemails_asterisk_msg_id", "voicemails", ["asterisk_msg_id"])


def downgrade() -> None:
    op.drop_constraint("uq_voicemails_asterisk_msg_id", "voicemails", type_="unique")
    op.drop_column("voicemails", "caller_name")
    op.drop_column("voicemails", "asterisk_msg_id")
