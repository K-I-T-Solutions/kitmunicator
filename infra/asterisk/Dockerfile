FROM andrius/asterisk:20

# Deutsche Asterisk Core Sounds herunterladen (enthält vm-theperson, vm-isunavail etc.)
RUN SOUNDS_DIR=/var/lib/asterisk/sounds/de && \
    mkdir -p "${SOUNDS_DIR}" && \
    wget -qO /tmp/de-sounds.tar.gz \
      "https://downloads.asterisk.org/pub/telephony/sounds/asterisk-core-sounds-de-wav-current.tar.gz" && \
    tar xzf /tmp/de-sounds.tar.gz -C "${SOUNDS_DIR}" --strip-components=1 && \
    rm /tmp/de-sounds.tar.gz

COPY entrypoint.sh /docker-entrypoint-rtp.sh
RUN chmod +x /docker-entrypoint-rtp.sh

ENTRYPOINT ["/docker-entrypoint-rtp.sh"]
CMD ["/usr/sbin/asterisk", "-vvvdddf", "-T", "-W", "-U", "asterisk", "-p"]
