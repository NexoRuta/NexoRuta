#!/bin/bash
set -euo pipefail
exec > >(tee -a /var/log/nexoruta-bootstrap.log) 2>&1
export DEBIAN_FRONTEND=noninteractive

# Persistent disk: refuse unexpected formats rather than overwriting them.
device=/dev/disk/by-id/google-nexoruta-data
for attempt in {1..60}; do
  [[ -b "$device" ]] && break
  sleep 2
done
[[ -b "$device" ]]
if filesystem=$(blkid -p -s TYPE -o value "$device"); then
  [[ "$filesystem" == ext4 ]] || { echo "Unsupported data disk filesystem" >&2; exit 1; }
else
  probe_status=$?
  [[ "$probe_status" == 2 ]] || exit "$probe_status"
  # A partition table is also existing data, even without a filesystem TYPE.
  [[ -z "$(wipefs --noheadings --output TYPE "$device")" ]] || exit 1
  mkfs.ext4 -F "$device"
fi
install -d -m 0750 /srv/nexoruta
disk_uuid=$(blkid -s UUID -o value "$device")
if ! grep -qF "UUID=$disk_uuid " /etc/fstab; then
  printf 'UUID=%s /srv/nexoruta ext4 defaults 0 2\n' "$disk_uuid" >> /etc/fstab
fi
mountpoint -q /srv/nexoruta || mount /srv/nexoruta
rm -f /srv/nexoruta/bootstrap-ready

if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ca-certificates curl python3
  install -d -m 0755 /etc/apt/keyrings
  curl --fail --silent --show-error --retry 3 https://download.docker.com/linux/debian/gpg \
    -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  architecture=$(dpkg --print-architecture)
  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable\n' \
    "$architecture" > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# Both engine state and named volumes survive VM replacement on the data disk.
systemctl stop docker.service docker.socket containerd.service
install -d -m 0750 /srv/nexoruta/docker /srv/nexoruta/containerd /srv/nexoruta/deploy /etc/docker /etc/containerd
python3 - <<'PY'
import json
import re
from pathlib import Path
path = Path('/etc/docker/daemon.json')
config = json.loads(path.read_text()) if path.exists() else {}
config.update({'data-root': '/srv/nexoruta/docker', 'log-driver': 'json-file', 'log-opts': {'max-size': '10m', 'max-file': '3'}})
path.write_text(json.dumps(config) + '\n')
containerd_path = Path('/etc/containerd/config.toml')
containerd = containerd_path.read_text() if containerd_path.exists() else ''
setting = 'root = "/srv/nexoruta/containerd"'
if re.search(r'^root\s*=', containerd, re.MULTILINE):
    containerd = re.sub(r'^root\s*=.*$', setting, containerd, count=1, flags=re.MULTILINE)
else:
    containerd = setting + '\n' + containerd
containerd_path.write_text(containerd)
PY
systemctl enable docker.service containerd.service
systemctl start containerd.service docker.service
docker compose version
# Install the supported host agent; application-specific config arrives with the release.
if ! dpkg-query -W google-cloud-ops-agent >/dev/null 2>&1; then
  curl --fail --silent --show-error --retry 3 https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh -o /tmp/nexoruta-ops-repo.sh
  bash /tmp/nexoruta-ops-repo.sh --also-install
  rm -f /tmp/nexoruta-ops-repo.sh
fi
python3 - <<'PY'
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def command(*args):
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None

packages = {}
for package in (
    "docker-ce", "docker-ce-cli", "containerd.io", "docker-buildx-plugin",
    "docker-compose-plugin", "google-cloud-ops-agent", "python3",
):
    packages[package] = command("dpkg-query", "-W", "-f=${Version}", package)

os_release = {}
for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        os_release[key] = value.strip('"')

record = {
    "schema_version": 1,
    "recorded_at": datetime.now(timezone.utc).isoformat(),
    "os_id": os_release.get("ID"),
    "os_version_id": os_release.get("VERSION_ID"),
    "kernel": platform.release(),
    "architecture": platform.machine(),
    "docker_server": command("docker", "version", "--format", "{{.Server.Version}}"),
    "docker_compose": command("docker", "compose", "version", "--short"),
    "docker_buildx": command("docker", "buildx", "version"),
    "containerd": command("containerd", "--version"),
    "packages": packages,
}
destination = Path("/srv/nexoruta/host-versions.json")
temporary = destination.with_suffix(".json.tmp")
temporary.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
temporary.replace(destination)
print("Recorded effective Debian, kernel, Docker, Compose, containerd, and Ops Agent versions.")
PY
cat > /etc/systemd/system/nexoruta-monitor.service <<'UNIT'
[Unit]
Description=NexoRuta infrastructure and application signals
After=docker.service network-online.target
Requires=docker.service
ConditionPathExists=/srv/nexoruta/monitor.json
[Service]
Type=simple
ExecStart=/usr/bin/python3 /srv/nexoruta/deploy/monitor_agent.py
Restart=on-failure
RestartSec=15
UMask=0077
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable nexoruta-monitor.service
touch /srv/nexoruta/bootstrap-ready
echo 'VM bootstrap complete. The delivery pipeline can now deploy the application.'
