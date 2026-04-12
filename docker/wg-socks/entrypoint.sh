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
if wg-quick up wg0 2>&1; then
    echo "[wg-socks] Tunnel active."
else
    echo "[wg-socks] ERROR: wg-quick failed (exit $?). Dumping kernel info for debug..."
    uname -r || true
    ls /sys/module/wireguard 2>/dev/null && echo "wireguard module: present" || echo "wireguard module: NOT FOUND"
    cat /proc/modules 2>/dev/null | grep wire || echo "wireguard not in /proc/modules"
    ip link 2>/dev/null | head -20 || true
    echo "[wg-socks] Will sleep 30s then retry, or kill to inspect."
    sleep 30
    wg-quick up wg0 || true
fi

echo "[wg-socks] Starting SOCKS5 proxy on :1080..."
exec python3 /socks5proxy.py
