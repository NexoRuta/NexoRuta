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
config.update({'data-root': '/srv/nexoruta/docker', 'log-driver': 'local'})
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
touch /srv/nexoruta/bootstrap-ready
echo 'VM bootstrap complete. The delivery pipeline can now deploy the application.'
