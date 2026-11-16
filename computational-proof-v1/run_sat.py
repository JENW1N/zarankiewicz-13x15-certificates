"""Run and independently check every residual classification instance."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time


def run_one(item, folder, solver, checker):
    name = item["id"]
    cnf = folder / (name + ".cnf")
    proof = folder / (name + ".drat")
    started = time.monotonic()
    with (folder / (name + ".solver.log")).open("w") as log:
        result = subprocess.run([str(solver), "--no-binary", str(cnf), str(proof)],
                                stdout=log, stderr=subprocess.STDOUT, timeout=7200)
    report = {"id": name, "solver_exit_code": result.returncode,
              "solver_seconds": round(time.monotonic() - started, 3)}
    if result.returncode == 20:
        check_log = folder / (name + ".check.log")
        with check_log.open("w") as log:
            check = subprocess.run([str(checker), str(cnf), str(proof)],
                                   stdout=log, stderr=subprocess.STDOUT, timeout=7200)
        report["checker_exit_code"] = check.returncode
        report["verified"] = check.returncode == 0 and "s VERIFIED" in check_log.read_text()
        report["proof_bytes"] = proof.stat().st_size
        report["proof_sha256"] = hashlib.sha256(proof.read_bytes()).hexdigest()
    else:
        report["verified"] = False
    (folder / (name + ".result.json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    folder = Path(__file__).with_name("sat")
    instances = json.loads((folder / "instances.json").read_text())
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda item: run_one(item, folder, args.solver, args.checker), instances))
    (folder / "verification.json").write_text(json.dumps(results, indent=2) + "\n")
    if not all(r["verified"] for r in results):
        raise SystemExit("At least one residual instance is unverified")
