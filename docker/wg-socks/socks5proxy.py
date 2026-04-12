"""
Minimal async SOCKS5 proxy (RFC 1928).
No authentication — listens on 0.0.0.0:1080.
All outbound traffic goes through whatever routes the OS has set
(in our case, the WireGuard wg0 interface).
"""
import asyncio
import struct
import socket
import sys

PORT = 1080
VER = 0x05
NO_AUTH = 0x00
CMD_CONNECT = 0x01
ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03
ATYP_IPV6 = 0x04


async def relay(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass


async def handle(reader, writer):
    peer = writer.get_extra_info("peername", ("<?>", 0))
    try:
        # --- Greeting ---
        header = await reader.read(2)
        if len(header) < 2 or header[0] != VER:
            return
        n = header[1]
        await reader.read(n)  # skip method list
        writer.write(bytes([VER, NO_AUTH]))
        await writer.drain()

        # --- Request ---
        req = await reader.read(4)
        if len(req) < 4 or req[0] != VER or req[1] != CMD_CONNECT:
            return

        atyp = req[3]
        if atyp == ATYP_IPV4:
            raw = await reader.read(4)
            host = socket.inet_ntoa(raw)
        elif atyp == ATYP_DOMAIN:
            length = (await reader.read(1))[0]
            host = (await reader.read(length)).decode()
        elif atyp == ATYP_IPV6:
            raw = await reader.read(16)
            host = socket.inet_ntop(socket.AF_INET6, raw)
        else:
            return

        port_raw = await reader.read(2)
        port = struct.unpack("!H", port_raw)[0]

        # --- Connect to target ---
        try:
            tr, tw = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=10
            )
        except Exception as exc:
            print(f"[socks5] CONNECT {host}:{port} FAILED: {exc}", flush=True)
            writer.write(bytes([VER, 0x05, 0x00, ATYP_IPV4, 0, 0, 0, 0, 0, 0]))
            await writer.drain()
            return

        print(f"[socks5] CONNECT {host}:{port} OK", flush=True)
        # Success reply (bind addr 0.0.0.0:0)
        writer.write(bytes([VER, 0x00, 0x00, ATYP_IPV4, 0, 0, 0, 0, 0, 0]))
        await writer.drain()

        # Relay in both directions concurrently
        await asyncio.gather(relay(reader, tw), relay(tr, writer))

    except Exception as exc:
        print(f"[socks5] error from {peer}: {exc}", flush=True)
    finally:
        writer.close()


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", PORT)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    print(f"[socks5] SOCKS5 proxy listening on {addrs}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
