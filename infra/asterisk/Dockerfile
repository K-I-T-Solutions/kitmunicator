FROM andrius/asterisk:20

# Deutsche Ansagen (vm-theperson, vm-isunavail …) aus Debian — Asterisk selbst
# veröffentlicht keine deutschen Core-Sounds. Landen unter
# /usr/share/asterisk/sounds/de, der Entrypoint verlinkt sie ins Sounds-Volume.
# Englische Core-Sounds als Fallback — u. a. für "beep" vor der Voicemail-Aufnahme.
RUN apt-get update && \
    apt-get install -y --no-install-recommends asterisk-prompt-de asterisk-core-sounds-en-gsm && \
    rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /docker-entrypoint-rtp.sh
RUN chmod +x /docker-entrypoint-rtp.sh

ENTRYPOINT ["/docker-entrypoint-rtp.sh"]
CMD ["/usr/sbin/asterisk", "-vvvdddf", "-T", "-W", "-U", "asterisk", "-p"]
