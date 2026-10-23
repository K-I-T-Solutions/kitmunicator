"""Mailbox-PIN nicht mehr = Durchwahl, ps_aors.contact nachrüsten

- voicemail_users.password war die Durchwahl. *98 prüft jetzt den angemeldeten
  Endpoint und überspringt die PIN — die PIN ist damit nur noch ein Platzhalter,
  der nicht erratbar sein darf.
- ps_aors bekommt eine leere Spalte contact: Asterisk fragt sie z. B. bei
  „pjsip show contacts“ ab und loggt sonst einen Fehler (Issue #4).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_AORS = """
    CREATE OR REPLACE VIEW ps_aors AS
    SELECT
        username    AS id,
        '3'         AS max_contacts,
        'yes'       AS remove_existing,
        '300'       AS default_expiration,
        '60'        AS minimum_expiration,
        '600'       AS maximum_expiration,
        -- OPTIONS-Ping aus: WebSocket-Clients antworten nicht, sonst Unavail
        '0'         AS qualify_frequency{contact}
    FROM sip_accounts
    WHERE is_active AND sip_md5_cred IS NOT NULL
"""

_VOICEMAIL_USERS = """
    CREATE VIEW voicemail_users AS
    SELECT
        id                                  AS uniqueid,
        'internal_vm'                       AS context,
        extension                           AS mailbox,
        {password}                          AS password,
        coalesce(display_name, username)    AS fullname,
        email                               AS email,
        'de'                                AS language
    FROM sip_accounts
    WHERE is_active
"""


def upgrade() -> None:
    op.execute(_AORS.format(contact=",\n        NULL::text  AS contact"))
    # Typ der Spalte ändert sich → neu anlegen statt CREATE OR REPLACE
    op.execute("DROP VIEW voicemail_users")
    # Bei jeder Abfrage neu gewürfelt — wird nie geprüft (VoiceMailMain mit s)
    op.execute(_VOICEMAIL_USERS.format(password="md5(random()::text)"))


def downgrade() -> None:
    op.execute("DROP VIEW voicemail_users")
    op.execute(_VOICEMAIL_USERS.format(password="extension"))
    # Spalten lassen sich per CREATE OR REPLACE nicht entfernen
    op.execute("DROP VIEW ps_aors")
    op.execute(_AORS.format(contact="").replace("CREATE OR REPLACE VIEW", "CREATE VIEW"))
