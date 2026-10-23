"""Read a dedicated PAT privately and install it in the three GitHub environments."""

import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

COMPONENTS = ("NexoRuta-Backend", "NexoRuta-Frontend", "NexoRuta-Mobile")
ENVIRONMENT = "nexoruta-demo"
SECRET = "NEXORUTA_INTEGRATION_TOKEN"


def verify_token(token):
    if not re.fullmatch(r"github_pat_[A-Za-z0-9_]{40,}", token):
        raise ValueError("Se necesita un token fine-grained dedicado (github_pat_...).")
    # This event is deliberately outside the delivery workflow's accepted types.
    # A 204 verifies Contents: write without publishing images or starting a VM.
    request = urllib.request.Request(
        "https://api.github.com/repos/NexoRuta/NexoRuta/dispatches",
        data=json.dumps({"event_type": "nexoruta-integration-auth-check"}).encode(),
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 204:
                raise ValueError("GitHub no acepto la prueba de permisos del token.")
    except urllib.error.HTTPError as error:
        raise ValueError(f"GitHub devolvio HTTP {error.code}. Revisar repo seleccionado, Contents: write y aprobacion del token.") from None


def configure(token):
    cli = shutil.which("gh")
    if not cli and os.environ.get("LOCALAPPDATA"):
        candidate = Path(os.environ["LOCALAPPDATA"]) / "Programs/GitHubCLI/gh.exe"
        if candidate.is_file():
            cli = str(candidate)
    if not cli:
        raise RuntimeError("Instalar GitHub CLI e iniciar sesion con gh auth login.")
    verify_token(token)
    for component in COMPONENTS:
        repo = f"NexoRuta/{component}"
        # The existing gh session administers environment secrets; the new PAT
        # itself only needs Contents: write on the parent repository.
        result = subprocess.run([cli, "secret", "set", SECRET, "--repo", repo, "--env", ENVIRONMENT],
                                input=token, text=True, capture_output=True, check=False)
        if result.returncode:
            raise RuntimeError(f"No se pudo guardar {SECRET} en {repo}. Revisar permisos de la sesion gh.")
        checked = subprocess.run([cli, "api", f"repos/{repo}/environments/{ENVIRONMENT}/secrets/{SECRET}"],
                                 text=True, capture_output=True, check=False)
        if checked.returncode or json.loads(checked.stdout).get("name") != SECRET:
            raise RuntimeError(f"No se pudo verificar el secret en {repo}.")
        print(f"Guardado y verificado: {repo} / {ENVIRONMENT} / {SECRET}")


def main():
    print("Crear el PAT con Resource owner: NexoRuta; Only select repositories: NexoRuta/NexoRuta.")
    print("Permiso: Contents -> Read and write. El formulario propone una duracion de 90 dias.")
    print("Copiar el token generado y pegarlo aqui; la entrada no se muestra.")
    if not sys.stdin.isatty():
        raise RuntimeError("Ejecutar este script en una terminal interactiva.")
    token = getpass.getpass("PAT dedicado: ").strip()
    try:
        configure(token)
    finally:
        token = ""
    print("Configuracion completa. El token no se guardo en archivos ni se mostro en logs.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, urllib.error.URLError) as error:
        print(f"Configuracion pendiente: {error}", file=sys.stderr)
        sys.exit(1)
