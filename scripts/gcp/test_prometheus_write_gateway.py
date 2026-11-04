"""Verify that the load-test gateway exposes write/readiness only."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


GATEWAY_PATH = Path(__file__).parents[2] / "deploy/gcp/monitoring/prometheus-write-gateway.py"
SPEC = importlib.util.spec_from_file_location("prometheus_write_gateway", GATEWAY_PATH)
gateway = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gateway)


class UpstreamHandler(BaseHTTPRequestHandler):
    calls = []

    def do_GET(self):
        self.calls.append(("GET", self.path, b"", dict(self.headers)))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ready")

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.calls.append(("POST", self.path, body, dict(self.headers)))
        self.send_response(204)
        self.end_headers()

    def log_message(self, _format, *_args):
        return


class PrometheusWriteGatewayTests(unittest.TestCase):
    def setUp(self):
        UpstreamHandler.calls = []
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), gateway.Handler)
        gateway.UPSTREAM = f"http://127.0.0.1:{self.upstream.server_port}"
        self.threads = [threading.Thread(target=server.serve_forever, daemon=True)
                        for server in (self.upstream, self.server)]
        for thread in self.threads:
            thread.start()
        self.addCleanup(self.close_servers)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def close_servers(self):
        for server in (self.server, self.upstream):
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=2)

    def test_remote_write_and_readiness_are_forwarded(self):
        request = Request(self.origin + "/api/v1/write", data=b"snappy-payload", method="POST",
                          headers={"Content-Type": "application/x-protobuf", "Content-Encoding": "snappy",
                                   "X-Prometheus-Remote-Write-Version": "0.1.0"})
        with urlopen(request, timeout=3) as response:
            self.assertEqual(response.status, 204)
        with urlopen(self.origin + "/-/ready", timeout=3) as response:
            self.assertEqual(response.read(), b"ready")
        self.assertEqual([call[:3] for call in UpstreamHandler.calls], [
            ("POST", "/api/v1/write", b"snappy-payload"),
            ("GET", "/-/ready", b""),
        ])
        headers = UpstreamHandler.calls[0][3]
        self.assertEqual(headers["Content-Encoding"], "snappy")
        self.assertEqual(headers["X-Prometheus-Remote-Write-Version"], "0.1.0")

    def test_query_and_other_paths_never_reach_prometheus(self):
        for path, method in (("/api/v1/query?query=up", "GET"), ("/metrics", "GET"),
                             ("/api/v1/write?query=up", "POST")):
            request = Request(self.origin + path, data=b"x" if method == "POST" else None, method=method)
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=3)
            self.assertEqual(error.exception.code, 404)
        self.assertEqual(UpstreamHandler.calls, [])


if __name__ == "__main__":
    unittest.main()
