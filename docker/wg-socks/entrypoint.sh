#!/bin/sh
set -e

echo "[wg-socks] Writing WireGuard config..."

mkdir -p /etc/wireguard

# All WG credentials come from environment variables — never stored in the image.
cat > /etc/wireguard/wg0.conf << WGEOF
[Interface]
PrivateKey = ${WG_PRIVATE_KEY}
Address = ${WG_ADDRESS}

[Peer]
PublicKey = ${WG_PEER_PUBLIC_KEY}
PresharedKey = ${WG_PRESHARED_KEY}
Endpoint = ${WG_ENDPOINT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
WGEOF

chmod 600 /etc/wireguard/wg0.conf

echo "[wg-socks] Bringing up WireGuard tunnel (wg0)..."
wg-quick up wg0

echo "[wg-socks] Tunnel up. Public IP via VPN:"
wget -qO- https://api.ipify.org 2>/dev/null || echo "(ipify unreachable)"

echo "[wg-socks] Starting SOCKS5 proxy on 0.0.0.0:1080..."

# 3proxy config: anonymous SOCKS5, bind all interfaces
cat > /tmp/3proxy.cfg << PROXYEOF
nserver 1.1.1.1
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
log /dev/stdout D
auth none
socks -p1080 -i0.0.0.0 -e0.0.0.0
PROXYEOF

exec 3proxy /tmp/3proxy.cfg
