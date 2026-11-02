"""Expose the NexoRuta Compose container states as Prometheus metrics."""

from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import re
import socket


DOCKER_SOCKET = "/var/run/docker.sock"
PROJECT = os.environ.get("NEXORUTA_COMPOSE_PROJECT", "nexoruta")
NODE = os.environ.get("NEXORUTA_NODE_NAME", "local")


class UnixHTTPConnection(HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(DOCKER_SOCKET)


def containers():
    connection = UnixHTTPConnection("docker")
    try:
        connection.request("GET", "/version")
        response = connection.getresponse()
        body = response.read()
        if response.status != 200:
            raise RuntimeError(f"Docker API /version returned HTTP {response.status}")
        api_version = json.loads(body).get("ApiVersion", "")
        if not re.fullmatch(r"\d+\.\d+", api_version):
            raise RuntimeError("Docker API returned an invalid ApiVersion")

        connection.request("GET", f"/v{api_version}/containers/json?all=1")
        response = connection.getresponse()
        body = response.read()
        if response.status != 200:
            raise RuntimeError(f"Docker API containers endpoint returned HTTP {response.status}")
        return json.loads(body)
    finally:
        connection.close()


def label(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def metrics():
    lines = [
        "# HELP nexoruta_container_up Whether a NexoRuta Compose container is running and healthy.",
        "# TYPE nexoruta_container_up gauge",
        "# HELP nexoruta_container_status_exporter_up Whether Docker state collection succeeded.",
        "# TYPE nexoruta_container_status_exporter_up gauge",
    ]
    try:
        items = [item for item in containers()
                 if item.get("Labels", {}).get("com.docker.compose.project") == PROJECT
                 and item.get("Labels", {}).get("com.docker.compose.service")]
        for item in items:
            labels = item.get("Labels", {})
            service = labels["com.docker.compose.service"]
            container = item.get("Names", [item.get("Id", "unknown")])[0].lstrip("/")
            state = item.get("State", "unknown")
            status = item.get("Status", "")
            health_match = re.search(r"\((healthy|unhealthy|starting)\)", status)
            health = health_match.group(1) if health_match else "none"
            running = int(state == "running" and health != "unhealthy")
            values = (service, container, NODE, state, health)
            encoded = ",".join(f'{key}="{label(value)}"' for key, value in zip(
                ("service", "container", "node", "state", "health"), values
            ))
            lines.append(f"nexoruta_container_up{{{encoded}}} {running}")
        lines.append("nexoruta_container_status_exporter_up 1")
    except Exception as error:
        logging.error("Docker state collection failed: %s", error)
        lines.append("nexoruta_container_status_exporter_up 0")
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            body = b"ok\n"
            status = 200
            content_type = "text/plain; charset=utf-8"
        elif self.path == "/metrics":
            body = metrics().encode("utf-8")
            status = 200
            content_type = "text/plain; version=0.0.4; charset=utf-8"
        else:
            body = b"not found\n"
            status = 404
            content_type = "text/plain; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        logging.info(format, *args)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ThreadingHTTPServer(("0.0.0.0", 9927), Handler).serve_forever()
