import socketserver
from contextlib import contextmanager
from threading import Thread

SMTP_LINE_LIMIT_BYTES = 65536


class LocalSMTPHandler(socketserver.StreamRequestHandler):
    def reply(self, response):
        self.wfile.write(response + b"\r\n")
        self.wfile.flush()

    def read_message(self):
        parts = []
        for line in iter(lambda: self.rfile.readline(SMTP_LINE_LIMIT_BYTES), b""):
            if line == b".\r\n":
                return b"".join(parts)
            parts.append(line[1:] if line.startswith(b"..") else line)
        raise AssertionError("SMTP data ended before its terminator.")

    def process_data(self):
        self.reply(b"354 Send data")
        self.server.messages.append(self.read_message())
        if self.server.outcome == "disconnect":
            return False
        self.reply(
            b"451 Rejected" if self.server.outcome == "reject" else b"250 Accepted"
        )
        return True

    def handle(self):
        self.request.settimeout(5)
        self.reply(b"220 Local verification SMTP")
        for line in iter(lambda: self.rfile.readline(SMTP_LINE_LIMIT_BYTES), b""):
            command = line.split(b" ", 1)[0].strip().upper()
            if not self.handle_command(command):
                return

    def handle_command(self, command):
        if command in {b"EHLO", b"HELO"}:
            self.reply(b"250-loopback.test\r\n250 SIZE 1048576")
        elif command == b"DATA":
            return self.process_data()
        elif command == b"QUIT":
            self.reply(b"221 Bye")
            return False
        else:
            self.reply(b"250 OK")
        return True


@contextmanager
def local_smtp(outcome):
    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), LocalSMTPHandler) as server:
        server.messages = []
        server.outcome = outcome
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join(timeout=5)
