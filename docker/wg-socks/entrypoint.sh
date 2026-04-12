#!/bin/sh
set -e

echo "[wg-socks] Writing WireGuard config..."
mkdir -p /etc/wireguard

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

echo "[wg-socks] Bringing up WireGuard tunnel..."
wg-quick up wg0

echo "[wg-socks] Tunnel active. Starting SOCKS5 proxy on :1080..."
exec python3 /socks5proxy.py
