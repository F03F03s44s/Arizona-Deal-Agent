"""A throwaway SMTP server, so the SMTP transport can be tested for real.

Python 3.12 dropped ``smtpd``, and pulling in a mail server for one test is
overkill, so this implements just enough of RFC 5321 to accept a message and
hand back what was received.
"""

from __future__ import annotations

import socketserver
import threading


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.wfile.write(b"220 stub.localhost ESMTP\r\n")
        body: list[bytes] = []
        in_data = False

        while True:
            raw = self.rfile.readline()
            if not raw:
                return

            if in_data:
                if raw.strip() == b".":
                    in_data = False
                    self.server.messages.append(b"".join(body).decode("utf-8", "replace"))
                    body = []
                    self.wfile.write(b"250 2.0.0 Ok: queued\r\n")
                else:
                    body.append(raw)
                continue

            command = raw.decode("utf-8", "replace").strip().upper()
            if command.startswith("DATA"):
                in_data = True
                self.wfile.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
            elif command.startswith("QUIT"):
                self.wfile.write(b"221 2.0.0 Bye\r\n")
                return
            else:
                # HELO/EHLO/MAIL/RCPT/RSET/NOOP all get a bare 250, which also
                # advertises no extensions and therefore no STARTTLS.
                self.wfile.write(b"250 2.0.0 Ok\r\n")


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class StubSmtpServer:
    """Runs on a random local port and records every message delivered."""

    def __init__(self) -> None:
        self.messages: list[str] = []
        self._server = _Server(("127.0.0.1", 0), _Handler)
        self._server.messages = self.messages
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    def __enter__(self) -> StubSmtpServer:
        self._thread.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
