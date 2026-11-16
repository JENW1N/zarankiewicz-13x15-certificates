"""Reproduce all 82 five-row extension tests from Section 5."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
import json
from pathlib import Path
import time


def base_inputs():
    columns = []
    for i in range(8):
        zeros = {i, (i + 1) % 8, (i + 3) % 8}
        columns.append([int(r not in zeros) for r in range(8)])
    for a, b in combinations(range(4), 2):
        ones = {a, a + 4, b, b + 4}
        columns.append([int(r in ones) for r in range(8)])
    g = tuple(sum(columns[c][r] << c for c in range(14)) for r in range(8))
    yield "G", g
    for r in range(8):
        for c in range(14):
            if (g[r] >> c) & 1:
                changed = list(g)
                changed[r] ^= 1 << c
                yield f"G-delete-{r+1:02d}-{c+1:02d}", tuple(changed)
    reps = json.loads(Path(__file__).with_name("representatives.json").read_text())
    for name, rows in reps.items():
        yield name, tuple(int(row, 2) for row in rows)


def check_one(item):
    name, base = item
    started = time.monotonic()
    assert all((a & b & c).bit_count() <= 2 for a, b, c in combinations(base, 3))
    old = tuple(row | (1 << 14) for row in base)
    target = 115 - sum(row.bit_count() for row in old)
    pairs = tuple(a & b for a, b in combinations(old, 2))
    allowed = [v for v in range(1 << 15) if all((v & p).bit_count() <= 3 for p in pairs)]
    maximum = max(map(int.bit_count, allowed))
    candidates = sorted((v for v in allowed if v.bit_count() >= target - 4 * maximum),
                        key=lambda v: (v.bit_count(), v), reverse=True)
    weights = [v.bit_count() for v in candidates]
    compatibility = {}
    nodes = 0

    def pair_ok(a, b):
        key = (a, b) if a <= b else (b, a)
        if key not in compatibility:
            both = candidates[a] & candidates[b]
            compatibility[key] = all((both & row).bit_count() <= 3 for row in old)
        return compatibility[key]

    def visit(chosen, first, weight):
        nonlocal nodes
        nodes += 1
        left = 5 - len(chosen)
        if left == 0:
            return chosen if weight >= target else None
        for j in range(first, len(candidates)):
            if weight + left * weights[j] < target:
                break
            if not all(pair_ok(i, j) for i in chosen):
                continue
            v = candidates[j]
            if not all((v & candidates[i] & candidates[k]).bit_count() <= 3
                       for i, k in combinations(chosen, 2)):
                continue
            answer = visit(chosen + (j,), j, weight + weights[j])
            if answer is not None:
                return answer
        return None

    answer = visit((), 0, 0)
    report = {"id": name, "base_rows": [format(v, "014b") for v in base],
              "adjoined_column_bit": 14, "base_weight": sum(v.bit_count() for v in base),
              "target_new_weight": target, "allowed_rows": len(allowed),
              "maximum_row_weight": maximum, "retained_rows": len(candidates),
              "search_nodes": nodes, "accepted": answer is not None,
              "elapsed_seconds": round(time.monotonic() - started, 3)}
    if answer is not None:
        report["extension"] = [format(candidates[j], "015b") for j in answer]
    print(json.dumps(report), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("extensions.json"))
    args = parser.parse_args()
    inputs = list(base_inputs())
    assert len(inputs) == 82
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(check_one, inputs))
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    assert not any(result["accepted"] for result in results), "An extension exists"
