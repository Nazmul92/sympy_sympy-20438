# sympy\_\_sympy-20438

A focused fix for the SymPy bug reported as
[sympy/sympy#20438](https://github.com/sympy/sympy/issues/20438): set subset and equality
queries stayed undecided when they were decidable, and `simplify()` raised on any relation
whose two sides are sets.

This repository is the SymPy source tree at the SWE-bench Verified base commit with the fix
applied on top; no other upstream file is changed. If you only want the change, read
[`sympy-20438-fix.patch`](sympy-20438-fix.patch) or, equivalently, `git show HEAD~1`.

| | |
| --- | --- |
| Instance | `sympy__sympy-20438` — SWE-bench Verified, `test` split |
| Base commit | `33b47e4bd60e2302e42616141e76285038b724d6` |
| Fix | `HEAD~1` — 4 files changed, +499 −3 |
| Patch SHA-256 | `ffd6dc32b3011198477d32f3806341fd740e3008730b472fc9436b453d4a73a9` |
| Official evaluation | SWE-bench 5.0.2 — `resolved: true`, FAIL_TO_PASS 2/2, PASS_TO_PASS 93/93 |

## The bug

```python
>>> from sympy import *

>>> a = FiniteSet(1, 2)
>>> ProductSet(a, a).is_subset(FiniteSet((1, 1), (1, 2), (2, 1), (2, 2)))
None                                       # after the fix: True

>>> Eq(ProductSet(FiniteSet(1), FiniteSet(2)), Interval(1, 2))
Eq(ProductSet(FiniteSet(1), FiniteSet(2)), Interval(1, 2))
                                           # after the fix: False

>>> x = Symbol('x')
>>> Eq({1}, {x}).simplify()
AttributeError: 'Complement' object has no attribute 'equals'
                                           # after the fix: Eq(FiniteSet(1), FiniteSet(x))
```

The same `AttributeError` hit every relation between sets, because `simplify()` treated
`lhs - rhs` as a number. The first two cases are the other half of the issue: the information
needed to answer was present, but the code never used it.

## Root cause

Four independent gaps, which is why the visible symptom looked inconsistent.

1. **`is_subset` did not try the elements.** `Set.is_subset` decided `self ⊆ other` by testing
   `self.intersect(other) == self`, which only works when that intersection is *structurally*
   equal to `self`. Intersecting `ProductSet(FiniteSet(1, 2), FiniteSet(1, 2))` with the
   `FiniteSet` of its four tuples gives that `FiniteSet`, so the test never fired and the
   question fell through to `(Range, Range)`-style handlers that return `None`. A set that is
   finite is determined by its elements, but nothing ever asked its elements.

2. **`ProductSet` could not be iterated and queried consistently.** `ProductSet.__iter__`
   yields plain `tuple`s, while `ProductSet._contains` only understood `Tuple`. Even a
   correct elementwise test would therefore have failed on product sets.

3. **`Eq`/`Ne` between sets had no general rule.** `_eval_is_eq(Set, Set)` was a stub returning
   `None`, and the `(ProductSet, ProductSet)` handler decided only from the factors, so
   `Eq(ProductSet({1}, {2}), Interval(1, 2))` was left unevaluated even though `(1, 2)` is
   plainly not a point of `[1, 2]`. The general principle was missing: **two sets are equal
   exactly when each is a subset of the other**, so a subset relation that provably fails
   proves inequality.

4. **`simplify()` ran numeric machinery on sets.** `Relational._eval_simplify` computes
   `dif = lhs - rhs` and then calls `dif.equals(0)`, `linear_coeffs(dif, x)`,
   `rewrite(Add, evaluate=False)` and finally compares a `count_ops`-based measure with the
   original. For sets, `lhs - rhs` *is a set* (a `Complement`, `EmptySet` or `UniversalSet`),
   so the first attribute lookup raised `AttributeError`; and `count_ops` walked an infinite
   set such as `ImageSet(Lambda(x, x + 1), S.Integers)`, which does not terminate.

## The fix

### `sympy/sets/sets.py` — decide subsets from the elements

`Set.is_subset` now falls back on elementwise containment for a set that is both finite and
iterable, and `ProductSet._contains` accepts the plain tuples its own iterator produces:

```python
if self.is_finite_set and self.is_iterable:
    try:
        ret = fuzzy_and(other.contains(e) for e in self)
    except (NotImplementedError, TypeError, ValueError):
        ret = None            # not enumerable in practice: undecided
    if ret is not None:
        return ret
```

A set whose finiteness is unknown is never iterated, and a set that cannot actually be
enumerated (for example a `Range` with a symbolic stop) leaves the question undecided instead
of raising.

### `sympy/sets/handlers/comparison.py` — equality from the subset relations

```python
def _eval_is_eq_from_subsets(lhs, rhs):
    try:
        lhs_subset = lhs.is_subset(rhs)
        rhs_subset = rhs.is_subset(lhs)
    except Exception:
        return None           # e.g. Range(n) or ConditionSet vs Partition
    if lhs_subset is False or rhs_subset is False:
        return False
    if lhs_subset is True and rhs_subset is True:
        return True
    return None
```

`(Set, Set)` uses this rule directly. `(ProductSet, ProductSet)` keeps the cheap factor
reasoning, guarded by emptiness — the empty set is a `ProductSet` in many ways, so
`ProductSet({1})` and `ProductSet({1}, {2})` are equal while differing in one factor — and
falls back on the subset relations when the factors cannot decide. Since `Ne` is defined as
the negation of `Eq`, it is decided by the same rule.

### `sympy/core/relational.py` — `simplify()` that understands sets

`Relational._eval_simplify` and `Equality._eval_simplify` return early when either side of the
relation is a `Set`: the arguments are simplified, the relation is re-canonicalised, and the
numeric `equals`/`linear_coeffs`/`count_ops` path is skipped entirely.

## Verification

**Official result.** SWE-bench 5.0.2, dataset `SWE-bench/SWE-bench_Verified`, split `test`,
run id `adakode-sympy-20438-v2-official`, the unmodified CLI:

```bash
swebench eval verified -p predictions_v2.json \
  --run-id adakode-sympy-20438-v2-official -i sympy__sympy-20438 -j 1 -t 1800
```

```text
patch_successfully_applied : true
FAIL_TO_PASS               : 2/2   (test_Eq, test_issue_19378)
PASS_TO_PASS               : 93/93
infra_failure              : false
resolved                   : true
```

**Local suites.** `sympy/sets`, `sympy/core`, `sympy/logic` and
`sympy/testing/tests/test_code_quality.py`: 369 passed, 1 failed. The whole `sympy` suite:
9288 passed, 9 failed, 388 skipped. Eight of those nine fail identically on the untouched base
commit (`test_numbers.py::test_Float`, two `test_holonomic.py` tests, five
`testing/tests/test_pytest.py` warning tests); the ninth is the stale expectation described
under *Known limitations*.

**Differential testing.** A brute-force check that enumerates ~16 900 concrete set pairs and
compares `is_subset`/`Eq`/`Ne` against exact element enumeration: no exceptions, no wrong
answers, 284 pre-existing problems fixed and 14 left undecided that the base commit also
cannot answer. A 4 608-operation matrix over 47 `Set` subclasses (including geometry sets,
`MatrixSet`, `Partition` and the complex regions) raises nothing. A base-versus-fix exception
diff over 4 093 (pair, operation) combinations shows **no new exceptions** and 1 236
pre-existing crashes — including several hangs in `simplify()` — removed.

## Reproduce

```bash
python -m pytest sympy/sets/tests/test_finite_subset_eq.py -q
python -m pytest sympy/sets sympy/core -q
```

```bash
python -c "from sympy import *; \
a = FiniteSet(1, 2); b = ProductSet(a, a); c = FiniteSet((1,1),(1,2),(2,1),(2,2)); \
print(b.is_subset(c), c.is_subset(b), Eq(b, c).simplify(), \
      Eq(ProductSet({1}, {2}), Interval(1, 2)) is S.false, \
      Eq({1}, FiniteSet(Symbol('x'))).simplify() == Eq({1}, FiniteSet(Symbol('x'))))"
# True True True True True
```

## Repository layout

```text
README.md                                   this file
sympy-20438-fix.patch                       the graded change, as a patch against the base commit
sympy/core/relational.py                    simplify() for relations between sets
sympy/sets/handlers/comparison.py           equality decided from the subset relations
sympy/sets/sets.py                          elementwise subsets; tuples in ProductSet._contains
sympy/sets/tests/test_finite_subset_eq.py   new: 17 tests for the fixed behaviour
```

History: `HEAD~2` is a single root commit holding the base tree (this clone is a filtered
clone, so SymPy's own 45 000-commit history is not part of this repository), `HEAD~1` is the
fix and `HEAD` adds this README and the patch file. Upstream's own `README.md` from the base
commit is still available as `git show HEAD~2:README.md`.

## Known limitations

These are unchanged by the fix and are present on the base commit as well:

* `Range(0, 0, 1).is_subset(Range(1, 3, 1))` is `False`, although an empty range is a subset
  of every set. This is an independent bug in the `(Range, Range)` handler.
* Relations that need to compare *elements* of a set whose finiteness is not known stay
  undecided: `Eq(FiniteSet(1, 2), ImageSet(Lambda(x, x + 1), FiniteSet(0, 1)))` and
  `ProductSet(FiniteSet(1, 2), FiniteSet(1, 2)).is_subset(Range(0, 5))`. The fix never
  iterates such a set, because doing so could not terminate.
* `sympy/sets/tests/test_sets.py::test_Eq` in this snapshot still asserts the *old* behaviour
  on one line — `assert Eq(ProductSet({1}, {2}), Interval(1, 2)) not in (S.true, S.false)` —
  and therefore fails. The benchmark's own test patch replaces that assertion with
  `is S.false`; with that line updated the rest of the test passes unchanged, which is exactly
  what the official run above measured. The checked-in test is deliberately left untouched.

## License

SymPy is distributed under the BSD 3-clause license; see [`LICENSE`](LICENSE). This repository
is a snapshot of the upstream project at the commit named above and keeps that license
unchanged.
