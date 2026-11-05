#!/usr/bin/env python3
"""Valida el workflow o genera datos NUEVOS; no hace HTTP, SQL ni operaciones Android."""
import argparse
import csv
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "docs/demo/workflow.json"
HEADER = ["referenciaExterna", "nombreDestinatario", "emailDestinatario", "direccion",
          "codigoBulto", "pesoGramos", "largoCentimetros", "anchoCentimetros",
          "altoCentimetros", "zonaId", "latitud", "longitud", "modalidad"]
RESERVED = {"01a19e23-d3a5-7a48-92f4-97fe178c87ad", "01a19e71-822f-7434-9acc-2a02b89b2487"}


def read_workflow():
    return json.loads(WORKFLOW.read_text(encoding="utf-8"))


def validate(data):
    steps = {s["id"]: s for s in data["steps"]}
    requirements = {r["id"]: r for r in data["requirements"]}
    assert len(steps) == len(data["steps"]), "IDs de paso repetidos"
    assert len(requirements) == len(data["requirements"]), "IDs de requisito repetidos"
    expected = {f"{prefix}-{i:02}" for prefix, count in [("CU", 30), ("AP", 9), ("NFR", 15), ("OPT", 15)]
                for i in range(1, count + 1)}
    assert set(requirements) == expected, "Inventario de alcance incompleto"
    for source in data["sources"]:
        assert (ROOT / source).is_file(), f"Fuente ausente: {source}"
    visited, active = set(), set()

    def visit(step_id):
        assert step_id in steps, f"Dependencia inexistente: {step_id}"
        assert step_id not in active, f"Dependencia circular: {step_id}"
        if step_id in visited:
            return
        active.add(step_id)
        for dependency in steps[step_id]["depends_on"]:
            visit(dependency)
        active.remove(step_id)
        visited.add(step_id)

    for step in steps.values():
        visit(step["id"])
        assert step["track"] in data["tracks"]
        assert step["actions"] and step["assertions"] and step["evidence"]
        assert step["timeout_seconds"] > 0
        assert set(step["requirements"]) <= set(requirements)
    for requirement in requirements.values():
        actual = [s["id"] for s in steps.values() if requirement["id"] in s["requirements"]]
        assert requirement["steps"] == actual, f"Mapeo divergente: {requirement['id']}"
        assert actual or requirement["availability"] == "no_seleccionado"
    selected = {r["id"] for r in requirements.values() if r.get("selected")}
    assert selected == {"OPT-03", "OPT-05", "OPT-06", "OPT-07", "OPT-08", "OPT-09"}
    return f"OK: {len(steps)} pasos; 30 CU, 9 AP, 15 NFR y 15 opcionales inventariados. No acredita ejecucion E2E."


def new_uuid(value):
    result = str(uuid.UUID(value))
    if result in RESERVED or uuid.UUID(result).int == 0:
        raise argparse.ArgumentTypeError("Se requiere un UUID nuevo de la organizacion de demo")
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(args, data):
    if not re.fullmatch(r"[A-Za-z0-9]{1,24}", args.run_id):
        raise SystemExit("run-id debe contener de 1 a 24 caracteres alfanumericos")
    out = ROOT / ".local/demo" / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    prefix = f"DEMO-{args.run_id}"

    def row(case):
        ref = f"{prefix}-{case}"
        return [ref, f"Demo {case}", f"{args.run_id.lower()}-{case.lower()}@example.test",
                "Direccion sintetica de demo, Montevideo", f"{ref}-B1", 500, 20, 10, 5,
                args.zona_id, -34.9, -56.2, "Estandar"]

    def write_csv(name, rows):
        with (out / name).open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(HEADER)
            writer.writerows(rows)

    core = [row("INTENTO"), row("RETORNO")]
    write_csv("01-alta-v2.csv", core)
    write_csv("02-reimportacion-parcial-v2.csv", core[:1])
    bad = row("INVALIDO")
    bad[5] = -1
    write_csv("03-lote-invalido-atomico-v2.csv", [row("ATOMICO"), bad])
    outside = row("FUERACOBERTURA")
    outside[10:12] = [-30.905, -55.55]
    write_csv("04-sin-cobertura-v2.csv", [outside])
    extra_cases = ["DISCREPANCIA", "CAPACIDAD", "CONFLICTO", "PRUEBA", "CANCELACION", "HISTORIA", "AISLAMIENTO"]
    write_csv("05-extensiones-v2.csv", [row(case) for case in extra_cases])

    def parcel(case, number):
        return {"codigo": f"{prefix}-{case}-B{number}", "pesoGramos": 500,
                "largoCentimetros": 20, "anchoCentimetros": 10, "altoCentimetros": 5}

    def shipment(case, count):
        return {"operadorId": args.operador_id, "destinatarioNombre": f"Demo {case}",
                "destinatarioEmail": f"{args.run_id.lower()}-{case.lower()}@example.test",
                "direccion": "Direccion sintetica de demo, Montevideo",
                "servicio": {"versionTarifarioEsperada": None, "zonaId": args.zona_id,
                             "latitud": -34.9, "longitud": -56.2, "modalidad": "Estandar"},
                "bultos": [parcel(case, i) for i in range(1, count + 1)]}

    write_json(out / "individual.json", shipment("MULTI", 2))
    write_json(out / "api-alta.json", shipment("API", 1))
    actors = ["adminA", "adminB", "commerceC1", "commerceC2", "dispatcherA1",
              "dispatcherA2", "driverR1", "driverR2", "readonly", "platformAdmin"]
    heads = {name: subprocess.check_output(["git", "-C", str(ROOT / path), "rev-parse", "HEAD"],
                                          text=True).strip()
             for name, path in [("root", "."), ("backend", "backend"), ("frontend", "frontend"), ("mobile", "mobile")]}
    manifest = {"run_id": args.run_id, "date": args.fecha, "timezone": "America/Montevideo",
                "environment": "gcp-remoto", "sources_local": heads,
                "deployed_release": None, "deployed_sources": {}, "session_deadline": None,
                "urls": {key: None for key in data["inputs"]["urls"]},
                "credentials_ref": {actor: None for actor in actors},
                "android": {"serial": None, "package": "uy.nexoruta.repartidor", "target": "GcpDemo", "apk_sha256": None},
                "ids": {"operator_a": args.operador_id, "zone_a": args.zona_id},
                "references": {case: f"{prefix}-{case}" for case in ["MULTI", "API", "INTENTO", "RETORNO", *extra_cases]},
                "tariff_oracle": {"multi_standard_v1_uyu": 115, "single_standard_v1_uyu": 109,
                                  "multi_urgent_v1_uyu": 165, "multi_standard_v2_uyu": 135},
                "route_oracle": {"stops": 3, "parcels": 4, "weight_grams": 2000, "volume_cm3": 4000},
                "pending": ["Resolver versionTarifarioEsperada antes del POST y registrar versiones de reglas.",
                            "Completar URLs/release/fecha/actores/recursos antes de ejecutar.",
                            "Correos example.test no reciben correo remoto: usar buzon de prueba propio autorizado para cancelacion.",
                            "Declaraciones sinteticas; no hay recepciones/cargas/entregas creadas por este generador.",
                            "05-extensiones se usa por escenario, no se mezcla con la ruta principal."]}
    write_json(out / "manifest.json", manifest)
    write_json(out / "resultados.json", {"run_id": args.run_id, "environment": "gcp-remoto", "steps": [
        {"id": s["id"], "status": "pendiente", "started_at": None, "finished_at": None,
         "mode": None, "observed": "", "evidence": [], "assertions": []} for s in data["steps"]]})
    print(f"Datos nuevos: {out}")
    print("No se ejecutaron HTTP, SQL, despliegues ni operaciones fisicas. Completar manifest.json.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validar")
    prep = commands.add_parser("preparar")
    prep.add_argument("--run-id", required=True)
    prep.add_argument("--operador-id", required=True, type=new_uuid)
    prep.add_argument("--zona-id", required=True, type=new_uuid)
    prep.add_argument("--fecha", default=dt.date.today().isoformat(), type=lambda v: dt.date.fromisoformat(v).isoformat())
    args = parser.parse_args()
    data = read_workflow()
    message = validate(data)
    if args.command == "validar":
        print(message)
    else:
        prepare(args, data)


if __name__ == "__main__":
    main()
