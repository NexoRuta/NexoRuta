"""Create a sanitized, run-bound verification record for an isolated NFR-14 session."""

import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

import demo_session
import delivery
import integration
import reproduce
import host_versions
import deployment_health

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ("api", "admin", "backoffice", "commerce", "tracking", "mail", "monitor")
APPS = ("api", "admin", "backoffice", "commerce", "tracking")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def validate_endpoints(endpoints, frontend_ip):
    if not isinstance(endpoints, dict) or set(endpoints) != set(SERVICES):
        raise ValueError("Terraform endpoint output must contain the exact NexoRuta service set")
    try:
        address = ipaddress.IPv4Address(frontend_ip)
    except (ValueError, TypeError) as error:
        raise ValueError("The isolated global load balancer has no valid IPv4 address") from error
    if not address.is_global:
        raise ValueError("The isolated load balancer IPv4 address must be globally routable")
    normalized_ip = str(address)
    suffix = normalized_ip.replace(".", "-") + ".sslip.io"
    result = {}
    for name, value in endpoints.items():
        if not isinstance(value, str):
            raise ValueError("Terraform returned an invalid public endpoint")
        parsed = urllib.parse.urlsplit(value)
        try:
            port = parsed.port
        except ValueError as error:
            raise ValueError("Terraform returned an invalid public endpoint") from error
        expected_host = name + "." + suffix
        if (parsed.scheme != "https" or parsed.hostname != expected_host or port not in (None, 443)
                or parsed.username or parsed.password or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment):
            raise ValueError("Public endpoint does not match the isolated HTTPS load-balancer identity")
        result[name] = "https://" + expected_host
    return result


def check_tls(host, *, now=None, connector=socket.create_connection, context_factory=ssl.create_default_context):
    now = now or datetime.now(timezone.utc)
    context = context_factory()
    with connector((host, 443), timeout=10) as raw:
        with context.wrap_socket(raw, server_hostname=host) as connection:
            certificate = connection.getpeercert()
    try:
        not_before = datetime.fromtimestamp(ssl.cert_time_to_seconds(certificate["notBefore"]), timezone.utc)
        not_after = datetime.fromtimestamp(ssl.cert_time_to_seconds(certificate["notAfter"]), timezone.utc)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ValueError("The public TLS certificate has invalid validity dates") from error
    if not_before > now or not_after <= now:
        raise ValueError("The public TLS certificate is not currently valid")
    return {"hostname": host, "chain_and_hostname_verified": True,
            "not_before": not_before.isoformat(), "not_after": not_after.isoformat()}


def check_http_upgrade(origin, *, opener_factory=urllib.request.build_opener):
    parsed = urllib.parse.urlsplit(origin)
    request = urllib.request.Request(
        urllib.parse.urlunsplit(("http", parsed.netloc, "/", "", "")),
        method="GET", headers={"User-Agent": "NexoRuta-NFR14-verifier/1"},
    )
    opener = opener_factory(_NoRedirect())
    status, location = None, None
    try:
        with opener.open(request, timeout=10) as response:
            status = response.status
            location = response.headers.get("Location")
    except urllib.error.HTTPError as error:
        status, location = error.code, error.headers.get("Location")
    if status not in (301, 302, 303, 307, 308) or not location:
        raise ValueError("HTTP did not redirect to HTTPS")
    target = urllib.parse.urlsplit(urllib.parse.urljoin(request.full_url, location))
    if (target.scheme != "https" or target.hostname != parsed.hostname
            or target.port not in (None, 443) or target.username or target.password):
        raise ValueError("HTTP redirected outside the matching validated HTTPS hostname")
    return {"status": status, "https_hostname": target.hostname}


def get_status(url, *, opener=urllib.request.urlopen):
    expected = urllib.parse.urlsplit(url)

    def status_for(response):
        final = urllib.parse.urlsplit(response.geturl())
        if (final.scheme != "https" or final.hostname != expected.hostname
                or final.port not in (None, 443) or final.username or final.password):
            raise ValueError("HTTPS health endpoint redirected outside its validated hostname")
        return response.status

    try:
        with opener(url, timeout=15) as response:
            return status_for(response)
    except urllib.error.HTTPError as error:
        return status_for(error)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RuntimeError("HTTPS endpoint could not be reached") from error


def _gcloud_json(*arguments, allow_not_found=False):
    value = reproduce._gcloud_json(*arguments, allow_not_found=allow_not_found)
    return value


def _tofu_output(name):
    value = demo_session.command("tofu", f"-chdir={demo_session.INFRA}",
                                 "output", "-json", name, capture=True)
    return json.loads(value)


def _private_ci_evidence(integration_tag):
    path = os.environ.get("NEXORUTA_CI_EVIDENCE_FILE", "")
    if not path:
        raise ValueError("The exact protected CI evidence file is not available to the verification job")
    try:
        evidence = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("The protected CI evidence file is unreadable") from error
    if not isinstance(evidence, dict):
        raise ValueError("The protected CI evidence identity is missing")
    resolved_evidence = evidence.get("evidence")
    artifact = evidence.get("artifact")
    run = evidence.get("run")
    if not isinstance(resolved_evidence, dict) or not isinstance(artifact, dict) or not isinstance(run, dict):
        raise ValueError("The resolved protected CI artifact identity is incomplete")
    snapshot, manifest, expected_ci = reproduce._release_manifest(
        integration_tag, os.environ.get("GITHUB_REPOSITORY_ID"),
    )
    ci = expected_ci
    if (artifact != ci["artifact"] or run.get("id") != ci["run_id"]
            or run.get("attempt") != ci["run_attempt"]
            or run.get("workflow_path") != ci["workflow_path"]
            or resolved_evidence.get("root_sha") != ci["root_sha"]
            or resolved_evidence.get("root_tree") != snapshot["root_tree"]
            or resolved_evidence.get("sources") != snapshot["sources"]
            or resolved_evidence.get("repository_id") != ci["repository_id"]):
        raise ValueError("The workflow CI evidence differs from the exact release evidence")
    return snapshot, manifest, ci


def _validate_live_identity(target, manifest, expected_tag, *, now=None):
    now = now or datetime.now(timezone.utc)
    project = _gcloud_json("projects", "describe", target["project_id"], "--format=json")
    labels = project.get("labels") or {}
    if (project.get("projectId") != target["project_id"]
            or str(project.get("projectNumber", "")) != target["project_number"]
            or project.get("lifecycleState") != "ACTIVE"
            or labels.get("nfr14_owner") != "nfr-14"
            or labels.get("nfr14_run") != target["run_id"][:16]):
        raise ValueError("Live Google Cloud project identity does not match this reproduction run")
    billing = _gcloud_json("billing", "projects", "describe", target["project_id"], "--format=json")
    if billing.get("billingEnabled") is not True:
        raise ValueError("The isolated project no longer has active billing")
    endpoints = validate_endpoints(_tofu_output("endpoints"), _tofu_output("load_balancer_ip"))
    expected_release = os.environ.get("NEXORUTA_EXPECTED_RELEASE", "")
    published = delivery.latest_manifest(demo_session.configuration())
    if (published.get("channel") != "main" or published.get("integration_tag") != expected_tag
            or not re.fullmatch(reproduce.RELEASE_ID, published.get("release", ""))
            or set(published.get("images", {})) != set(reproduce.SERVICES)
            or any(not re.search(r"@sha256:[a-f0-9]{64}$", published["images"][name])
                   for name in reproduce.SERVICES)):
        raise ValueError("The isolated main channel does not identify all immutable images for this tag")
    if expected_release and published["release"] != expected_release:
        raise ValueError("The isolated channel release differs from the build step output")
    if published.get("root_sha") != manifest.get("root_sha") or published.get("sources") != manifest.get("sources"):
        raise ValueError("The isolated deployment release differs from the validated main integration")
    if (set(published.get("built_images", [])) != set(reproduce.SERVICES)
            or published.get("reused_images") != {}
            or published.get("bundle_rebuilt") is not True):
        raise ValueError("The isolated release did not freshly build all six images and the bundle")

    database = _gcloud_json("sql", "instances", "describe", "nexoruta-demo-db",
                            f"--project={target['project_id']}", "--format=json")
    if (database.get("name") != "nexoruta-demo-db" or database.get("region") != reproduce.REGION
            or database.get("state") != "RUNNABLE"):
        raise ValueError("The isolated PostgreSQL instance is not RUNNABLE in the expected region")
    nodes = []
    for name, zone in (("nexoruta-demo", reproduce.ZONE), ("nexoruta-demo-b", reproduce.SECONDARY_ZONE)):
        vm = _gcloud_json("compute", "instances", "describe", name, f"--zone={zone}",
                          f"--project={target['project_id']}", "--format=json")
        if vm.get("name") != name or vm.get("status") != "RUNNING":
            raise ValueError("Both isolated application VMs must be running during online verification")
        deadline = demo_session.check_deadline(vm, now=now)
        nodes.append({"name": name, "zone": zone, "deadline": deadline})
    deadlines = [datetime.fromisoformat(item["deadline"].replace("Z", "+00:00")) for item in nodes]
    if abs((deadlines[0] - deadlines[1]).total_seconds()) > 60:
        raise ValueError("Isolated VM automatic stop deadlines do not match")
    if min(deadlines) > now.replace(microsecond=0) + timedelta(hours=4, minutes=1):
        raise ValueError("Isolated VM session exceeds the four-hour limit")
    token = reproduce._access_token()
    state_objects = reproduce.GCSJsonObjects(target["state_bucket"], token)
    _, lease = state_objects.read("leases/demo.json")
    if (not isinstance(lease, dict) or type(lease.get("expires_at")) not in (int, float)
            or not lease["expires_at"] > now.timestamp()
            or lease["expires_at"] > min(deadlines).timestamp() + 60):
        raise ValueError("The isolated session lease is missing, expired, or exceeds the VM stop deadline")
    if reproduce._read_active_marker(state_objects, "locks/demo-control.json", now=now.timestamp()):
        raise ValueError("An isolated application control lock remains active after deployment")
    return endpoints, published, database, nodes


def _online_checks(endpoints, *, tls_checker=check_tls, upgrade_checker=check_http_upgrade,
                   status_reader=get_status):
    certificates, redirects, statuses = {}, {}, {}
    for name, origin in endpoints.items():
        host = urllib.parse.urlsplit(origin).hostname
        certificates[name] = tls_checker(host)
        redirects[name] = upgrade_checker(origin)
    required = {
        "api": ("/live", "/ready", "/health"),
        "admin": ("/ingresar",), "backoffice": ("/ingresar",),
        "commerce": ("/ingresar",), "tracking": ("/ready",),
        "monitor": ("/api/health",),
    }
    for name, paths in required.items():
        for path in paths:
            code = status_reader(endpoints[name] + path)
            if code != 200:
                raise RuntimeError(f"HTTPS health check failed for {name}{path} (HTTP {code})")
            statuses[name + path] = code
    for name, path in (("monitor", "/api/search?query=nexoruta"), ("mail", "/")):
        code = status_reader(endpoints[name] + path)
        if code != 401:
            raise RuntimeError(f"Anonymous access policy failed for {name} (HTTP {code})")
        statuses[name + path] = code
    return {"tls": certificates, "http_upgrade": redirects, "https_status": statuses}


def _base_report(target, integration_tag):
    return {
        "schema_version": 1, "status": "failed", "run_id": target["run_id"],
        "integration_tag": integration_tag, "project_id": target["project_id"],
        "project_number": target["project_number"],
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "checks": {}, "session_stop": "pending",
    }


def validate_deployment_smoke(raw, target, published, *, cache_enabled):
    if not isinstance(raw, str) or not raw:
        raise ValueError("The existing deployment stage did not emit its sanitized authenticated smoke result")
    try:
        proof = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("The deployment smoke output is not valid JSON") from error
    if (not isinstance(proof, dict) or type(proof.get("schema_version")) is not int
            or proof.get("schema_version") != 3
            or proof.get("project_id") != target["project_id"]
            or proof.get("release") != published.get("release")
            or type(proof.get("cache_enabled")) is not bool
            or proof.get("cache_enabled") is not cache_enabled
            or proof.get("redis_node") != "b"):
        raise ValueError("The deployment smoke output belongs to another release or project")
    reads = proof.get("authenticated_reads")
    expected = {"admin", "operator", "commerce"}
    if (not isinstance(reads, list) or len(reads) != len(expected)
            or any(not isinstance(item, dict) or item.get("role") not in expected for item in reads)
            or {item["role"] for item in reads} != expected
            or any(not isinstance(item, dict) or item.get("login") != "passed"
                   or item.get("actor_read") != "passed" for item in reads)):
        raise ValueError("The existing deployment stage did not prove login and authenticated reads for all synthetic roles")
    clients = proof.get("redis_smoke_clients")
    expected_clients = ["a", "b"] if cache_enabled else []
    if clients != expected_clients:
        raise ValueError("Redis TLS/AUTH smoke results do not match the isolated cache configuration")
    host_version_evidence = host_versions.sanitize_node_map(proof.get("host_versions"))
    compose_health_evidence = deployment_health.sanitize_node_map(
        proof.get("compose_health"), cache_enabled,
    )
    return {"authenticated_reads": sorted(reads, key=lambda item: item["role"]),
            "redis_smoke_clients": clients, "cache_enabled": cache_enabled,
            "host_versions": host_version_evidence, "compose_health": compose_health_evidence}


def _write_report(path, report):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".tmp")
    temp.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(destination)
    return destination


def verify_live(*, run_id, integration_tag, output_path, environment=None,
                identity_check=_validate_live_identity, online_check=_online_checks):
    environment = os.environ if environment is None else environment
    report = None
    try:
        target = reproduce.validate_runtime_environment(environment, input_run_id=run_id,
                                                        input_tag=integration_tag)
        report = _base_report(target, integration_tag)
        snapshot, main_manifest, ci = _private_ci_evidence(integration_tag)
        report["tested_integration"] = {
            "tag": integration_tag, "main_release_id": main_manifest["release"],
            "root_sha": snapshot["root_sha"], "sources": snapshot["sources"],
            "ci_run_id": ci["run_id"], "ci_run_attempt": ci["run_attempt"],
            "ci_artifact": ci["artifact"],
        }
        endpoints, published, database, nodes = identity_check(target, main_manifest, integration_tag)
        cache_value = environment.get("NEXORUTA_CACHE_ENABLED", "true").strip().lower()
        if cache_value not in ("true", "false"):
            raise ValueError("NEXORUTA_CACHE_ENABLED must be true or false")
        smoke = validate_deployment_smoke(
            environment.get("NEXORUTA_DEPLOY_SMOKE", ""), target, published,
            cache_enabled=(cache_value == "true"),
        )
        report["checks"]["project_identity"] = "passed"
        report["checks"]["release_identity"] = "passed"
        report["checks"]["postgresql"] = {"state": database["state"], "region": database["region"]}
        report["checks"]["vms"] = nodes
        report["checks"]["deployment_smoke"] = smoke
        report["deployed_release"] = {
            "id": published["release"], "root_sha": published["root_sha"],
            "sources": published["sources"], "images": published["images"],
            "bundle_sha256": published["bundle_sha256"],
            "publication_order": published["publication_order"],
        }
        report["checks"]["online"] = online_check(endpoints)
        report["scope"] = {
            "verified": ["protected CI identity", "six immutable app image digests", "TLS and HTTPS health",
                         "synthetic role login and authenticated actor reads", "Redis TLS/AUTH smoke",
                         "effective Debian/Docker/Compose host versions on both nodes",
                         "exact running Compose service inventory and declared healthchecks on both nodes",
                         "VM stop and SQL retention"],
            "pending": ["applied PostgreSQL/PostGIS schema and runtime least-privilege/RLS verification",
                        "two-organization RLS isolation query", "functional health of all shared Compose dependencies",
                        "captured synthetic mail delivery",
                        "interactive browser navigation and visual review",
                        "independent second project recreation", "current billing consumption report"],
        }
        report["status"] = "passed"
    except Exception as error:
        if report is None:
            report = {"schema_version": 1, "status": "failed", "run_id": run_id,
                      "integration_tag": integration_tag, "checks": {}, "session_stop": "pending"}
        report["failure"] = {"type": type(error).__name__}
        _write_report(output_path, report)
        raise
    _write_report(output_path, report)
    return report


def finalize_stop(*, run_id, integration_tag, output_path, environment=None,
                  google_json=_gcloud_json, objects_factory=reproduce.GCSJsonObjects):
    environment = os.environ if environment is None else environment
    target = reproduce.validate_runtime_environment(environment, input_run_id=run_id,
                                                    input_tag=integration_tag)
    path = Path(output_path)
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("The online NFR-14 verification report is missing or unreadable") from error
    if (report.get("schema_version") != 1 or report.get("run_id") != run_id
            or report.get("integration_tag") != integration_tag
            or report.get("project_id") != target["project_id"]
            or report.get("project_number") != target["project_number"]):
        raise ValueError("The online NFR-14 verification report belongs to a different target")
    try:
        for name, zone in (("nexoruta-demo", reproduce.ZONE),
                           ("nexoruta-demo-b", reproduce.SECONDARY_ZONE)):
            vm = google_json("compute", "instances", "describe", name, f"--zone={zone}",
                             f"--project={target['project_id']}", "--format=json", allow_not_found=True)
            if vm is not None and (vm.get("name") != name or vm.get("status") != "TERMINATED"):
                raise RuntimeError("The reproduction VMs are not both stopped after the cleanup step")
        token = reproduce._access_token()
        storage = objects_factory(target["state_bucket"], token)
        if reproduce._read_active_marker(storage, "leases/demo.json"):
            raise RuntimeError("The reproduction session lease remains active after cleanup")
        database = google_json("sql", "instances", "describe", "nexoruta-demo-db",
                               f"--project={target['project_id']}", "--format=json")
        if database.get("state") != "RUNNABLE":
            raise RuntimeError("Cloud SQL did not remain running after VM stop")
        report["session_stop"] = "passed"
        report.setdefault("checks", {})["post_stop_sql"] = "RUNNABLE"
    except Exception as error:
        report["session_stop"] = "failed"
        report["failure"] = {"type": type(error).__name__}
    report["status"] = "passed" if report.get("status") == "passed" and report["session_stop"] == "passed" else "failed"
    report["finalized_at"] = datetime.now(timezone.utc).isoformat()
    _write_report(path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--integration-tag", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--finalize-stop", action="store_true")
    args = parser.parse_args()
    if args.finalize_stop:
        report = finalize_stop(run_id=args.run_id, integration_tag=args.integration_tag,
                               output_path=args.output)
    else:
        report = verify_live(run_id=args.run_id, integration_tag=args.integration_tag,
                             output_path=args.output)
    print(json.dumps({"status": report["status"], "run_id": args.run_id,
                      "integration_tag": args.integration_tag}, sort_keys=True))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
