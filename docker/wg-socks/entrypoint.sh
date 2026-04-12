#!/bin/sh
set -e

echo "[wg-socks] Writing WireGuard config..."
mkdir -p /etc/wireguard

# Write peer config (no [Interface] section — we set it manually below)
cat > /tmp/wg0-peer.conf << WGEOF
[Peer]
PublicKey = ${WG_PEER_PUBLIC_KEY}
PresharedKey = ${WG_PRESHARED_KEY}
Endpoint = ${WG_ENDPOINT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
WGEOF

echo "[wg-socks] Setting up WireGuard interface manually (bypassing wg-quick sysctl)..."

# Save default route before adding WireGuard routes
GATEWAY=$(ip route show default 2>/dev/null | awk 'NR==1{print $3}')
IFACE=$(ip route show default 2>/dev/null | awk 'NR==1{print $5}')
ENDPOINT_HOST=$(echo "${WG_ENDPOINT}" | cut -d: -f1)
echo "[wg-socks] Default gateway: ${GATEWAY} via ${IFACE}, endpoint: ${ENDPOINT_HOST}"

# Create wg interface
ip link add wg0 type wireguard
ip address add "${WG_ADDRESS}" dev wg0

# Load private key + peer config
printf '[Interface]\nPrivateKey = %s\n' "${WG_PRIVATE_KEY}" > /etc/wireguard/wg0-iface.conf
cat /etc/wireguard/wg0-iface.conf /tmp/wg0-peer.conf > /etc/wireguard/wg0.conf
chmod 600 /etc/wireguard/wg0.conf
wg setconf wg0 /etc/wireguard/wg0.conf

ip link set mtu 1420 up dev wg0

# Route WireGuard endpoint itself via original gateway (prevents routing loop)
if [ -n "${GATEWAY}" ] && [ -n "${ENDPOINT_HOST}" ]; then
    ip route add "${ENDPOINT_HOST}/32" via "${GATEWAY}" dev "${IFACE}" 2>/dev/null || true
fi

# Route all IPv4 traffic through the tunnel
ip route add 0.0.0.0/0 dev wg0 table 51820 2>/dev/null || true
ip rule add not fwmark 51820 table 51820 2>/dev/null || true
ip rule add table main suppress_prefixlength 0 2>/dev/null || true

# Confirm tunnel is up
echo "[wg-socks] WireGuard status:"
wg show wg0

echo "[wg-socks] Tunnel active. Starting SOCKS5 proxy on :1080..."
exec python3 /socks5proxy.py
