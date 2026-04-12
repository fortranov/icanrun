FROM alpine:3.19

# wireguard-tools + iptables for tunnel setup
# 3proxy for SOCKS5 proxy on :1080
# netcat-openbsd for HEALTHCHECK
RUN apk add --no-cache \
    wireguard-tools \
    iptables \
    iproute2 \
    3proxy \
    netcat-openbsd

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 1080

# Quick health check: is the SOCKS5 port open?
HEALTHCHECK --interval=20s --timeout=5s --retries=3 \
    CMD nc -z 127.0.0.1 1080 || exit 1

ENTRYPOINT ["/entrypoint.sh"]
