FROM alpine:3.19

# wireguard-tools + iptables for tunnel setup
# microsocks = tiny SOCKS5 server (single binary, no config needed)
RUN apk add --no-cache \
        wireguard-tools \
        iptables \
        iproute2 && \
    apk add --no-cache \
        --repository=https://dl-cdn.alpinelinux.org/alpine/edge/community \
        microsocks

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 1080

# Health check: is the SOCKS5 port open?
HEALTHCHECK --interval=20s --timeout=5s --retries=3 \
    CMD /bin/sh -c "echo '' | nc -w1 127.0.0.1 1080" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
