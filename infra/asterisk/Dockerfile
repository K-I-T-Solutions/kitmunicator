FROM andrius/asterisk:20

COPY entrypoint.sh /docker-entrypoint-rtp.sh
RUN chmod +x /docker-entrypoint-rtp.sh

ENTRYPOINT ["/docker-entrypoint-rtp.sh"]
CMD ["/usr/sbin/asterisk", "-vvvdddf", "-T", "-W", "-U", "asterisk", "-p"]
