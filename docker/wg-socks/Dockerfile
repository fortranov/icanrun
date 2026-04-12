FROM alpine:3.19

# wireguard-tools for tunnel, python3 for our tiny SOCKS5 proxy
RUN apk add --no-cache \
    wireguard-tools \
    iptables \
    iproute2 \
    python3

COPY socks5proxy.py /socks5proxy.py
COPY entrypoint.sh  /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 1080

ENTRYPOINT ["/entrypoint.sh"]
