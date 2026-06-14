#!/bin/sh
set -e

# Container-IP automatisch ermitteln wenn nicht explizit gesetzt
ASTERISK_LOCAL_IP="${ASTERISK_LOCAL_IP:-$(hostname -I | awk '{print $1}')}"
export ASTERISK_LOCAL_IP

# rtp.conf aus Template generieren
sed "s|\${ASTERISK_LOCAL_IP}|${ASTERISK_LOCAL_IP}|g; \
     s|\${ASTERISK_PUBLIC_IP}|${ASTERISK_PUBLIC_IP}|g" \
  /etc/asterisk-tpl/rtp.conf.tmpl > /etc/asterisk/rtp.conf

# Alle anderen Config-Dateien aus dem Template-Verzeichnis übernehmen
cp /etc/asterisk-tpl/*.conf /etc/asterisk/ 2>/dev/null || true
# rtp.conf wurde bereits aus Template generiert – Template-Kopie entfernen falls vorhanden
rm -f /etc/asterisk/rtp.conf.tmpl

echo "[entrypoint] rtp.conf generiert: ice_host_candidate=${ASTERISK_LOCAL_IP}:${ASTERISK_PUBLIC_IP}"

# Original-Entrypoint des Basis-Images aufrufen
exec /usr/local/bin/entrypoint.sh "$@"
