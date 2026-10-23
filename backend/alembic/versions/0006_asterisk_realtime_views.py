"""Asterisk Realtime: PJSIP-Endpoints und Mailboxen als Views auf sip_accounts

sip_accounts bleibt die einzige Quelle. Asterisk liest per res_config_pgsql:
  ps_endpoints / ps_auths / ps_aors  (res_pjsip, siehe sorcery.conf)
  voicemail_users                    (app_voicemail, siehe extconfig.conf)
Ein Account mit is_active = false verschwindet sofort aus Asterisk.

Realtime-Objekte kennen keine Templates — die Werte aus dem früheren
[webrtc_endpoint](!) stehen deshalb direkt in der View.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-21

"""
import hashlib
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from cryptography.fernet import Fernet

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Muss zu telephony/service.py SIP_REALM passen
SIP_REALM = "asterisk"


def _q(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    op.add_column("sip_accounts", sa.Column("display_name", sa.String(255), nullable=True))
    op.add_column("sip_accounts", sa.Column("email", sa.String(255), nullable=True))
    # MD5(username:realm:password) — Asterisk sieht nie das Klartext-Passwort
    op.add_column("sip_accounts", sa.Column("sip_md5_cred", sa.String(32), nullable=True))

    # Bestehende Accounts nachrüsten
    fernet = Fernet(os.environ["SIP_ENCRYPTION_KEY"].encode())
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, username, password_encrypted FROM sip_accounts")).all()
    for row in rows:
        password = fernet.decrypt(row.password_encrypted.encode()).decode()
        cred = hashlib.md5(f"{row.username}:{SIP_REALM}:{password}".encode()).hexdigest()
        conn.execute(
            sa.text("UPDATE sip_accounts SET sip_md5_cred = :cred WHERE id = :id"),
            {"cred": cred, "id": row.id},
        )

    from_domain = os.environ.get("SIP_FROM_DOMAIN", "kitmunicator.intern.phudevelopement.xyz")

    op.execute(f"""
        CREATE VIEW ps_endpoints AS
        SELECT
            username                    AS id,
            'transport-ws'              AS transport,
            username                    AS aors,
            username                    AS auth,
            'internal'                  AS context,
            'de'                        AS language,
            'all'                       AS disallow,
            -- Kein Opus: codec_opus fehlt im Image
            'g722,ulaw,alaw'            AS allow,
            '"' || replace(coalesce(display_name, username), '"', '') || '" <' || extension || '>' AS callerid,
            'yes'                       AS webrtc,
            'yes'                       AS dtls_auto_generate_cert,
            'yes'                       AS use_avpf,
            'dtls'                      AS media_encryption,
            'fingerprint'               AS dtls_verify,
            'actpass'                   AS dtls_setup,
            'yes'                       AS ice_support,
            'yes'                       AS force_rport,
            'yes'                       AS rewrite_contact,
            'yes'                       AS media_use_received_transport,
            'yes'                       AS rtp_symmetric,
            'rfc4733'                   AS dtmf_mode,
            '15'                        AS rtp_timeout,
            '300'                       AS rtp_timeout_hold,
            {_q(from_domain)}           AS from_domain,
            '1'                         AS device_state_busy_at,
            'yes'                       AS allow_subscribe,
            '30'                        AS sub_min_expiry,
            -- Asterisk fragt die Spalte beim Start ab (MWI); leer = keine NOTIFYs an die Browser
            NULL::text                  AS mailboxes
        FROM sip_accounts
        WHERE is_active AND sip_md5_cred IS NOT NULL
    """)

    op.execute(f"""
        CREATE VIEW ps_auths AS
        SELECT
            username        AS id,
            'md5'           AS auth_type,
            username        AS username,
            {_q(SIP_REALM)} AS realm,
            sip_md5_cred    AS md5_cred
        FROM sip_accounts
        WHERE is_active AND sip_md5_cred IS NOT NULL
    """)

    op.execute("""
        CREATE VIEW ps_aors AS
        SELECT
            username    AS id,
            '3'         AS max_contacts,
            'yes'       AS remove_existing,
            '300'       AS default_expiration,
            '60'        AS minimum_expiration,
            '600'       AS maximum_expiration,
            -- OPTIONS-Ping aus: WebSocket-Clients antworten nicht, sonst Unavail
            '0'         AS qualify_frequency
        FROM sip_accounts
        WHERE is_active AND sip_md5_cred IS NOT NULL
    """)

    # PIN = Durchwahl wie bisher in voicemail.conf (Abhören per *98 vom eigenen Telefon)
    op.execute("""
        CREATE VIEW voicemail_users AS
        SELECT
            id                                  AS uniqueid,
            'internal_vm'                       AS context,
            extension                           AS mailbox,
            extension                           AS password,
            coalesce(display_name, username)    AS fullname,
            email                               AS email,
            'de'                                AS language
        FROM sip_accounts
        WHERE is_active
    """)


def downgrade() -> None:
    for view in ("voicemail_users", "ps_aors", "ps_auths", "ps_endpoints"):
        op.execute(f"DROP VIEW IF EXISTS {view}")
    op.drop_column("sip_accounts", "sip_md5_cred")
    op.drop_column("sip_accounts", "email")
    op.drop_column("sip_accounts", "display_name")
