"""Expose only Prometheus remote write and readiness to the load-test subnet."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


UPSTREAM = "http://prometheus:9090"
MAX_REQUEST_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
FORWARDED_HEADERS = (
    "Content-Type", "Content-Encoding", "X-Prometheus-Remote-Write-Version", "User-Agent",
)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "NexoRutaMetricsGateway"
    sys_version = ""

    def do_GET(self):
        if self.path != "/-/ready":
            self.send_error(404)
            return
        self.proxy("GET", self.path)

    def do_POST(self):
        if self.path != "/api/v1/write":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.send_error(411)
            return
        if length < 0 or length > MAX_REQUEST_BYTES:
            self.send_error(413)
            return
        body = self.rfile.read(length)
        if len(body) != length:
            self.send_error(400)
            return
        self.proxy("POST", self.path, body)

    def proxy(self, method, path, body=None):
        headers = {name: self.headers[name] for name in FORWARDED_HEADERS if self.headers.get(name)}
        request = Request(UPSTREAM + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=15) as response:
                status = response.status
                response_headers = response.headers
                data = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            status = error.code
            response_headers = error.headers
            data = error.read(MAX_RESPONSE_BYTES + 1)
        except (OSError, URLError, TimeoutError):
            status, response_headers, data = 503, {}, b"Prometheus unavailable"
        if len(data) > MAX_RESPONSE_BYTES:
            status, data = 502, b"Prometheus response exceeded the gateway limit"
        self.send_response(status)
        content_type = response_headers.get("Content-Type") if response_headers else None
        if content_type:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

    def log_message(self, _format, *_args):
        # Keep request metadata and any remote-write diagnostics out of VM logs.
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "9091"))), Handler)
    server.daemon_threads = True
    server.serve_forever()
