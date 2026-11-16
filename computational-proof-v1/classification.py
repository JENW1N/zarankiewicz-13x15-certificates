"""Generate the fifteen residual SAT instances for Lemma 4.1."""

import argparse
from collections import defaultdict
import hashlib
from itertools import combinations, permutations, product
import json
from pathlib import Path

from pysat.card import CardEnc, EncType
from pysat.formula import CNF, IDPool
from pysat.solvers import Solver


def degrees():
    def visit(left, remaining, maximum):
        if left == 0:
            if remaining == 0:
                yield ()
            return
        for x in range(min(maximum, remaining), -1, -1):
            for tail in visit(left - 1, remaining - x, x):
                yield (7 + x,) + tail
    return sorted(visit(8, 7, 7), reverse=False)


def ordered_forms(rows):
    row_degrees = [row.count("1") for row in rows]
    groups = [[i for i, d in enumerate(row_degrees) if d == value]
              for value in sorted(set(row_degrees), reverse=True)]
    forms = set()
    for group_order in product(*(permutations(group) for group in groups)):
        perm = sum((tuple(g) for g in group_order), ())
        columns = sorted((tuple(int(rows[i][c]) for i in perm) for c in range(14)), reverse=True)
        candidate = tuple("".join(str(col[i]) for col in columns) for i in range(8))
        if all(row_degrees[perm[i]] != row_degrees[perm[i+1]]
               or candidate[i] >= candidate[i+1] for i in range(7)):
            forms.add(candidate)
    return forms


class Encoding:
    def __init__(self):
        self.pool = IDPool()
        self.cnf = CNF()
        self.cells = [[self.pool.id(("x", i, c)) for c in range(14)] for i in range(8)]

    def conjunction(self, inputs):
        z = self.pool.id()
        for x in inputs:
            self.cnf.append([-z, x])
        self.cnf.append([z] + [-x for x in inputs])
        return z

    def ge_lex(self, left, right):
        prefix = None
        for a, b in zip(left, right):
            self.cnf.append(([-prefix] if prefix else []) + [a, -b])
            next_prefix = self.pool.id()
            if prefix:
                self.cnf.append([-next_prefix, prefix])
            self.cnf.extend([[-next_prefix, -a, b], [-next_prefix, a, -b]])
            self.cnf.append(([-prefix] if prefix else []) + [a, b, next_prefix])
            self.cnf.append(([-prefix] if prefix else []) + [-a, -b, next_prefix])
            prefix = next_prefix

    def build(self, profile, excluded):
        x = self.cells
        for row, degree in zip(x, profile):
            for subset in combinations(row, degree + 1):
                self.cnf.append([-v for v in subset])
            for subset in combinations(row, 15 - degree):
                self.cnf.append(list(subset))
        for rows in combinations(range(8), 3):
            for columns in combinations(range(14), 3):
                self.cnf.append([-x[i][c] for i in rows for c in columns])
        for c in range(13):
            self.ge_lex([x[i][c] for i in range(8)], [x[i][c+1] for i in range(8)])
        for i in range(7):
            if profile[i] == profile[i+1]:
                self.ge_lex(x[i], x[i+1])
        if profile == (8, 8, 8, 8, 8, 8, 8, 7):
            choices = defaultdict(list)
            for i, j in combinations(range(7), 2):
                triples = [self.conjunction([x[7][c], x[i][c], x[j][c]]) for c in range(14)]
                active = self.pool.id()
                at_least_two = CardEnc.atleast(triples, bound=2, vpool=self.pool, encoding=EncType.seqcounter)
                self.cnf.extend([[-active] + clause for clause in at_least_two.clauses])
                for c in range(14):
                    choices[c].append(self.conjunction([active, x[i][c], x[j][c]]))
            for c in range(14):
                self.cnf.append([x[7][c]] + choices[c])
        for rows in sorted(excluded):
            self.cnf.append([-x[i][c] if rows[i][c] == "1" else x[i][c]
                             for i in range(8) for c in range(14)])
        return self.cnf


def generate(output):
    reps = json.loads((Path(__file__).with_name("representatives.json")).read_text())
    by_profile = defaultdict(set)
    classes = defaultdict(int)
    for rows in reps.values():
        profile = tuple(sorted((row.count("1") for row in rows), reverse=True))
        forms = ordered_forms(rows)
        assert not (by_profile[profile] & forms), "Representatives share an orbit"
        by_profile[profile].update(forms)
        classes[profile] += 1
    report = []
    output.mkdir(parents=True, exist_ok=True)
    for index, profile in enumerate(degrees()):
        excluded = by_profile[profile]
        cnf = Encoding().build(profile, excluded)
        stem = f"profile-{index:02d}"
        path = output / (stem + ".cnf")
        cnf.to_file(str(path))
        report.append({"id": stem, "degrees": profile, "equivalence_classes": classes[profile],
                       "ordered_forms": len(excluded), "variables": cnf.nv,
                       "clauses": len(cnf.clauses), "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        print(stem, profile, "classes", classes[profile], "forms", len(excluded), flush=True)
    assert sum(row["ordered_forms"] for row in report) == 1585
    (output / "instances.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("sat"))
    args = parser.parse_args()
    generate(args.output)
