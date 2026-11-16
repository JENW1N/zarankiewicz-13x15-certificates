"""Check the archived inputs, representative matrices, and proof outputs."""

import argparse
import gzip
import hashlib
from itertools import combinations
import json
from pathlib import Path
import subprocess
import tempfile

from classification import Encoding, degrees, ordered_forms
from verify_duals import check
from verify_extensions import base_inputs, check_one


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checker", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "manifest.json").read_text())
    for name, expected in manifest["sha256"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
    representatives = json.loads((root / "representatives.json").read_text())
    forms = {}
    for label, rows in representatives.items():
        assert len(rows) == 8 and all(len(r) == 14 and set(r) <= {"0", "1"} for r in rows)
        assert sum(row.count("1") for row in rows) == 63
        words = [int(row, 2) for row in rows]
        assert all((a & b & c).bit_count() <= 2 for a, b, c in combinations(words, 3))
        for i, row in enumerate(words):
            for c in range(14):
                if (row >> c) & 1 == 0:
                    extended = words.copy()
                    extended[i] |= 1 << c
                    assert any((a & b & d).bit_count() >= 3
                               for a, b, d in combinations(extended, 3)), (label, i, c)
        profile = tuple(sorted((r.count("1") for r in rows), reverse=True))
        orbit = ordered_forms(rows)
        assert not (forms.get(profile, set()) & orbit), label
        forms.setdefault(profile, set()).update(orbit)
    with tempfile.TemporaryDirectory(prefix="zarankiewicz-check-") as tmp:
        temporary = Path(tmp)
        for number, profile in enumerate(degrees()):
            name = f"profile-{number:02d}"
            generated = temporary / (name + ".cnf")
            Encoding().build(profile, forms.get(profile, set())).to_file(str(generated))
            archived = gzip.decompress((root / "sat" / (name + ".cnf.gz")).read_bytes())
            assert generated.read_bytes() == archived, name
            proof = temporary / (name + ".drat")
            proof.write_bytes(gzip.decompress((root / "sat" / (name + ".drat.gz")).read_bytes()))
            result = subprocess.run([str(args.checker.resolve()), str(generated), str(proof)],
                                    text=True, capture_output=True)
            assert result.returncode == 0 and "s VERIFIED" in result.stdout, name
            print(name, "verified", flush=True)
    archived_extensions = json.loads((root / "extensions.json").read_text())
    for item, recorded in zip(base_inputs(), archived_extensions, strict=True):
        observed = check_one(item)
        for key in recorded.keys() - {"elapsed_seconds"}:
            assert observed[key] == recorded[key], (item[0], key)
        assert not observed["accepted"]
    print(json.dumps(check(root / "dual_certificates.json"), indent=2), flush=True)
    print("All archived proof components verified.", flush=True)


if __name__ == "__main__":
    main()
