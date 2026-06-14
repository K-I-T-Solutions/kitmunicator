"""encrypt sip passwords with fernet

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Joshuas bekanntes Klartext-Passwort (f56374624bca48ce9eecffd6),
# vorab mit dem SIP_ENCRYPTION_KEY aus .env verschlüsselt.
JOSHUA_ENCRYPTED = (
    "gAAAAABqLppNQ481akMJqCi5b_RxlmLUEtHzY99FPSQ_6xd5aP4L5sUtHi3Bdge"
    "A0ewC9izEnStFWRtaYHhGSAOGljXcgo7LSHSR6_NEaOmHDWdUdtbwJGs="
)


def upgrade() -> None:
    # Spalte umbenennen: password_hash → password_encrypted
    op.alter_column(
        "sip_accounts",
        "password_hash",
        new_column_name="password_encrypted",
        existing_type=sa.String(255),
        type_=sa.String(500),
        nullable=False,
    )

    # Joshuas SHA256-Eintrag durch Fernet-Token ersetzen
    op.execute(
        f"UPDATE sip_accounts SET password_encrypted = '{JOSHUA_ENCRYPTED}' "
        f"WHERE username = 'joshua'"
    )


def downgrade() -> None:
    op.alter_column(
        "sip_accounts",
        "password_encrypted",
        new_column_name="password_hash",
        existing_type=sa.String(500),
        type_=sa.String(255),
        nullable=False,
    )
