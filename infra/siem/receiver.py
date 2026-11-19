"""Demo syslog receiver (X30, compose profile `siem`): prints every line it receives, so the
events arriving can be shown live with `docker compose logs -f syslog-receiver`. UDP and TCP, port 514."""

import socketserver
import threading


class Udp(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        data = self.request[0].decode("utf-8", "replace").strip()
        print(f"[udp] {data}", flush=True)


class Tcp(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        for line in self.rfile:
            print(f"[tcp] {line.decode('utf-8', 'replace').strip()}", flush=True)


if __name__ == "__main__":
    socketserver.ThreadingUDPServer.allow_reuse_address = True
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    udp = socketserver.ThreadingUDPServer(("0.0.0.0", 514), Udp)
    tcp = socketserver.ThreadingTCPServer(("0.0.0.0", 514), Tcp)
    threading.Thread(target=udp.serve_forever, daemon=True).start()
    print("Sentry demo syslog receiver listening on 514 (udp and tcp)", flush=True)
    tcp.serve_forever()
