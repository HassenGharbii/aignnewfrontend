# TCP forwarder that gives the api/worker containers a route to the source
# events API. Runs as the `proxy` service in docker-compose.yml; see the
# "Source API proxy" section of the README for why the direct address doesn't
# work from inside a container.
import os
import socket
import threading

LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "8004"))
TARGET_HOST = os.getenv("TARGET_HOST", "172.19.0.37")
TARGET_PORT = int(os.getenv("TARGET_PORT", "8003"))
# Without this the target connect() blocks for the OS default (~2 minutes) when
# the source API is off-network, so callers hit their own timeout with nothing
# logged here and the handler threads pile up.
CONNECT_TIMEOUT = float(os.getenv("TARGET_CONNECT_TIMEOUT", "10"))

BUFFER_SIZE = 4096


def forward(src, dst):
    """Pump bytes one way until either side closes. A peer resetting mid-stream
    is normal here (clients hang up on timeouts), so it ends the pump quietly
    rather than raising out of the thread."""
    try:
        while True:
            data = src.recv(BUFFER_SIZE)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        # Half-close so the other direction's pump sees EOF and exits too,
        # instead of blocking in recv() until the process dies.
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle_client(client_socket):
    # Wait for the client's first bytes before dialing the target. The
    # container healthcheck connects and immediately hangs up; connecting
    # lazily keeps those probes from opening a target connection (and logging
    # a failure) every few seconds. Safe because the target speaks HTTP, where
    # the client always sends first.
    try:
        first_chunk = client_socket.recv(BUFFER_SIZE)
    except OSError:
        client_socket.close()
        return
    if not first_chunk:
        client_socket.close()
        return

    target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        target_socket.settimeout(CONNECT_TIMEOUT)
        target_socket.connect((TARGET_HOST, TARGET_PORT))
        # Back to blocking for the forwarding phase — a long-polling response
        # must not be cut off by the connect timeout.
        target_socket.settimeout(None)
        target_socket.sendall(first_chunk)
    except OSError as exc:
        print(f"Proxy: cannot reach target {TARGET_HOST}:{TARGET_PORT}: {exc}", flush=True)
        client_socket.close()
        target_socket.close()
        return

    t1 = threading.Thread(target=forward, args=(client_socket, target_socket), daemon=True)
    t2 = threading.Thread(target=forward, args=(target_socket, client_socket), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    client_socket.close()
    target_socket.close()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Without this, restarting the container while old connections sit in
    # TIME_WAIT fails the bind with "address already in use".
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen(128)
    print(
        f"Proxy listening on {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}",
        flush=True,
    )
    while True:
        client, _addr = server.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
