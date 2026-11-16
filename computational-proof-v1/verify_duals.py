"""Check every integer certificate against the manuscript's finite type sets."""

import argparse
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
import time

W = (0, 14, 28, 30, 36, 44, 50, 56, 62, 70, 77, 84, 91, 98)


def choose3(n):
    return n * (n - 1) * (n - 2) // 6


@lru_cache(maxsize=None)
def profiles(length, total, minimum, maximum, budget, cost_kind):
    if length == 0:
        return ((),) if total == 0 and budget >= 0 else ()
    if total < length * minimum or total > length * maximum or budget < 0:
        return ()
    answer = []
    for value in range(minimum, min(maximum, total // length) + 1):
        cost = choose3(value) if cost_kind == 3 else value * (value - 1)
        for tail in profiles(length - 1, total - value, value, maximum,
                             budget - cost, cost_kind):
            answer.append((value,) + tail)
    return tuple(answer)


def distributions(capacities, total):
    if not capacities:
        if total == 0:
            yield ()
        return
    low = max(0, total - sum(capacities[1:]))
    for value in range(low, min(capacities[0], total) + 1):
        for tail in distributions(capacities[1:], total - value):
            yield (value,) + tail


@lru_cache(maxsize=None)
def row_types(column_counts, degree):
    degrees, counts = zip(*column_counts)
    costs = tuple((d - 1) * (d - 2) // 2 for d in degrees)
    return tuple(t for t in distributions(counts, degree)
                 if sum(a * b for a, b in zip(t, costs)) <= 198)


@lru_cache(maxsize=None)
def column_types(row_counts, degree):
    degrees, counts = zip(*row_counts)
    answer = []
    for t in distributions(counts, degree):
        weights = sorted((d - 1 for d, count in zip(degrees, t)
                          for _ in range(count)), reverse=True)
        total = 0
        for k, weight in enumerate(weights, 1):
            total += weight
            if total > W[k]:
                break
        else:
            answer.append(t)
    return tuple(answer)


def check(path):
    started = time.monotonic()
    cases = json.loads(path.read_text(encoding="utf-8"))
    columns = [p for p in profiles(15, 115, 0, 13, 858, 3)
               if sum(W[d] for d in p) >= 904]
    expected = {(r, c) for c in columns
                for r in profiles(13, 115, 0, 15, sum(W[d] for d in c), 2)}
    actual = [(tuple(c["rows"]), tuple(c["columns"])) for c in cases]
    assert len(columns) == 750
    assert len(cases) == 6019
    assert len(set(actual)) == len(actual)
    assert set(actual) == expected, "Degree-pair coverage mismatch"
    support_sizes = Counter()
    largest_multiplier = 0
    row_checks = 0
    column_checks = 0
    for number, case in enumerate(cases, 1):
        rc = tuple(sorted(Counter(case["rows"]).items()))
        cc = tuple(sorted(Counter(case["columns"]).items()))
        alpha, beta, gamma = case["alpha"], case["beta"], case["gamma"]
        assert len(alpha) == len(rc) and len(beta) == len(cc)
        assert len(gamma) == len(rc) and all(len(row) == len(cc) for row in gamma)
        values = alpha + beta + [x for row in gamma for x in row]
        assert all(type(x) is int for x in values)
        largest_multiplier = max(largest_multiplier, max(map(abs, values)))
        support_sizes[sum(x != 0 for x in values)] += 1
        rhs = sum(a * n for a, (_, n) in zip(alpha, rc))
        rhs += sum(b * n for b, (_, n) in zip(beta, cc))
        assert rhs < 0, f"Nonnegative right side in case {number}"
        for i, (degree, _) in enumerate(rc):
            for t in row_types(cc, degree):
                assert alpha[i] + sum(g * v for g, v in zip(gamma[i], t)) >= 0, number
                row_checks += 1
        for j, (degree, _) in enumerate(cc):
            for u in column_types(rc, degree):
                assert beta[j] - sum(gamma[i][j] * v for i, v in enumerate(u)) >= 0, number
                column_checks += 1
    return {"verified": True, "column_profiles": len(columns), "degree_pairs": len(cases),
            "row_type_inequalities": row_checks, "column_type_inequalities": column_checks,
            "largest_absolute_multiplier": largest_multiplier,
            "support_sizes": dict(sorted(support_sizes.items())),
            "elapsed_seconds": round(time.monotonic() - started, 3)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("dual_certificates.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check(args.data)
    text = json.dumps(report, indent=2) + "\n"
    print(text, end="", flush=True)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
