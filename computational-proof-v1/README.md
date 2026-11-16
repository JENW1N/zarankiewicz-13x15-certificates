# Computational proof archive for z(13,15;3,4) = 114

Release v1, 16 November 2026. Prepared for the supporting-material revision of
Hexagon 2611.00319v1 by Will Howe, Grant Huffman, Jensen Kohlmeyer, and Liam Kruer.

## Contents and provenance

The computations here were regenerated on 16 November 2026 from the submitted
manuscript's displayed constraints and representatives and from the supplied
single-file Lean source. The regeneration independently reproduces the paper's
counts and conclusions. These files are the outputs of that regeneration.

* `sat/profile-00` through `sat/profile-14` contain all fifteen residual
  classification instances in DIMACS CNF format, complete text DRAT refutations,
  CaDiCaL logs, independent drat-trim logs, and per-instance verification records.
  CNF and DRAT files are compressed individually with gzip. `sat/instances.json`
  maps each instance to its degree sequence and excluded ordered-form count.
* `representatives.json` contains the seventeen matrices in Appendix A.
  `classification.py` constructs every residual instance, including both
  lexicographic orders and the maximality condition for (8,8,8,8,8,8,8,7).
  It reproduces all 1,585 excluded ordered forms. Its cardinality auxiliaries
  express the existence of a pair sharing at least two other occupied columns.
* `extensions.json` contains the inputs and exhaustive outputs for all 82 bases:
  G, each of its 64 one-entry deletions, and the seventeen maximal representatives.
  Each output includes the base rows, target weight, candidate counts, search-node
  count, and rejection result. `verify_extensions.py` implements the recursion in
  Section 5, including repeated rows and both values in the adjoined column.
* `dual_certificates.json` contains all 6,019 integer dual certificates and their
  row and column degree sequences. Alpha follows increasing distinct row degree,
  beta increasing distinct column degree, and gamma has that row/column order.
  The data were extracted exactly from the supplied Lean file. `verify_duals.py`
  independently enumerates every degree profile and all admissible types, checks
  coverage without duplicates, and evaluates all certificate inequalities using
  Python integers. `dual_check.json` gives the resulting counts.
* `Zarankiewicz1315.lean` is the supplied companion source, unchanged. Its header
  specifies Lean 4.33.1 and mathlib commit
  `0df444a360eaa60ab8c11dca51a86af692955474`. This archive's independent checks
  concern the SAT, extension, and dual-certificate components. They do not record
  a fresh full Lean compilation.
* `manifest.json` gives SHA-256 hashes of every other archived file.

## Check the complete archive

Use Python 3.12 and a C compiler. Install the exact Python dependency in a virtual
environment, then build the included independent checker.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cc -O2 -o drat-trim tools/drat-trim.c
python verify_archive.py --checker ./drat-trim
```

On Windows activate the environment using `.venv\Scripts\Activate.ps1` and use
the path to a Windows build of drat-trim. `verify_archive.py` first checks the
manifest. It checks avoidance, maximality, and distinct orbits of every displayed
representative, regenerates the fifteen CNFs byte for byte, checks all DRAT proofs,
reruns all 82 extensions, and verifies all 6,019 dual certificates. Success ends
with `All archived proof components verified.` Any mismatch raises an error.

## Regenerate solver outputs

The recorded solver is CaDiCaL 2.1.2. Obtain CaDiCaL from its upstream project and
build it according to its instructions. The independent checker is drat-trim by
Marijn Heule and Nathan Wetzler. Its original license remains in the included C
source. Upstream sources are https://github.com/arminbiere/cadical and
https://github.com/marijnheule/drat-trim .

```sh
python classification.py --output sat
python run_sat.py --solver /path/to/cadical --checker /path/to/drat-trim --jobs 4
python verify_extensions.py --jobs 4 --output extensions-new.json
python verify_duals.py --output dual-check-new.json
```

The SAT script requires solver exit code 20 and drat-trim's `s VERIFIED` result
for every instance. The proof itself is checked against the exact archived CNF,
so accepting the solver's result is not a premise of the verification.

## License

The authors' supporting material is distributed under CC BY 4.0,
https://creativecommons.org/licenses/by/4.0/ . The included third-party
drat-trim source retains its MIT license and copyright notice.
