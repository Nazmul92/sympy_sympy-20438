"""Tests for deciding subset and equality relations of finite sets.

A set that is finite and iterable is determined by its elements.  The
``ProductSet`` of two finite sets and the ``FiniteSet`` of the same tuples
are therefore equal as sets, but they are not structurally identical which
means that the intersection based fallback in ``Set.is_subset`` cannot
decide that the ``ProductSet`` is a subset of the ``FiniteSet`` even though
the reverse direction (handled by ``FiniteSet._eval_is_subset``) works.
"""

from sympy import (Eq, FiniteSet, Interval, Ne, ProductSet, Range, S,
                   SymmetricDifference, Union, oo, symbols)
from sympy.core.containers import Tuple

x, y = symbols('x y')
n = symbols('n', integer=True)


def _product_and_finiteset():
    """The example from the report: the same set in two representations."""
    a = FiniteSet(1, 2)
    b = ProductSet(a, a)
    c = FiniteSet((1, 1), (1, 2), (2, 1), (2, 2))
    return b, c


def check_pair(a, b):
    """Check the rules that must hold for every pair of sets.

    ``is_subset`` and ``is_superset`` are two views of the same relation and
    they must agree with each other and with ``Eq``.
    """
    ab = a.is_subset(b)
    ba = b.is_subset(a)

    assert ab in (True, False, None)
    assert ba in (True, False, None)

    # is_superset is the mirror image of is_subset
    assert b.is_superset(a) is ab
    assert a.is_superset(b) is ba
    assert b.issuperset(a) is ab
    assert a.issubset(b) is ab

    # Eq may only claim equality if both subset directions are True and it
    # may only claim inequality if the sets are not mutually contained
    eq = Eq(a, b)
    if eq is S.true:
        assert ab is True
        assert ba is True
    elif eq is S.false:
        assert not (ab is True and ba is True)

    # Ne is the negation of Eq
    ne = Ne(a, b)
    if eq is S.true:
        assert ne is S.false
    elif eq is S.false:
        assert ne is S.true
    else:
        assert ne not in (S.true, S.false)

    # a proper subset is a subset which is not the whole set
    if a.is_proper_subset(b) is True:
        assert ab is True
    return ab, ba


def brute_force_subset(a, b):
    """Decide a subset query by enumerating a: only valid for concrete sets."""
    return all(e in b for e in a)


def check_concrete_pair(a, b):
    """A concrete pair must be decided and agree with enumeration."""
    ab, ba = check_pair(a, b)
    truth = brute_force_subset(a, b)
    assert ab is truth, (a, b, ab, truth)
    assert ba is brute_force_subset(b, a), (a, b)
    eq = Eq(a, b)
    if truth and ba is True:
        assert eq is S.true, (a, b, eq)
    else:
        # the sets are provably different: each of them is finite and
        # iterable so an element that is missing from the other one is found
        assert eq is S.false, (a, b, eq)


def test_issue_example():
    b, c = _product_and_finiteset()
    assert b.intersection(c) == c.intersection(b)
    assert b.is_subset(c) is True
    assert c.is_subset(b) is True
    assert b.is_superset(c) is True
    assert Eq(b, c) is S.true
    assert Eq(b, c).simplify() is S.true
    assert Eq(c, b).simplify() is S.true
    assert check_pair(b, c) == (True, True)

    # everything that follows from the two sets being equal
    assert b - c is S.EmptySet
    assert c - b is S.EmptySet
    assert b ^ c is S.EmptySet
    assert b.is_disjoint(c) is False
    assert Union(b, c) == b
    assert Union(c, b) == b


def test_productset_subset_finiteset():
    a = FiniteSet(1, 2)
    b = ProductSet(a, a)

    assert b.is_subset(FiniteSet((1, 1), (1, 2), (2, 1), (2, 2))) is True
    assert b.is_subset(FiniteSet((1, 1), (1, 2), (2, 1), (2, 2), (3, 3))) is True
    assert b.is_subset(FiniteSet((1, 1), (1, 2), (2, 1))) is False
    assert b.is_subset(FiniteSet((1, 1))) is False
    assert b.is_subset(FiniteSet((1, 1), (1, 2), (3, 1))) is False
    assert b.is_subset(FiniteSet(1, 2)) is False
    assert b.is_subset(S.EmptySet) is False
    assert b.is_subset(b) is True

    # three factors
    p = ProductSet(FiniteSet(1), FiniteSet(2), FiniteSet(3))
    assert p.is_subset(FiniteSet((1, 2, 3), (1, 2, 4))) is True
    assert p.is_subset(FiniteSet((1, 2, 4))) is False

    # a ProductSet with a factor that is finite but not a FiniteSet
    assert ProductSet(Range(2), FiniteSet(1)).is_subset(
        FiniteSet((0, 1), (1, 1))) is True
    assert ProductSet(Range(2), FiniteSet(1)).is_subset(
        FiniteSet((0, 1))) is False


def test_productset_subset_other_sets():
    a = FiniteSet(1, 2)
    b = ProductSet(a, a)

    assert b.is_subset(S.UniversalSet) is True
    assert b.is_subset(Union(b, FiniteSet((3, 3)))) is True
    assert b.is_subset(Union(ProductSet(FiniteSet(1), FiniteSet(1)),
                             ProductSet(FiniteSet(1, 2), FiniteSet(1, 2)))) is True
    assert b.is_subset(Union(ProductSet(FiniteSet(1), FiniteSet(1)),
                             FiniteSet((1, 2), (2, 1)))) is False
    assert b.is_subset(Interval(0, 3) * Interval(0, 3)) is True
    assert b.is_subset(Interval(0, 2) * Interval(0, 1)) is False

    # the reverse directions
    assert FiniteSet((1, 1), (1, 2), (2, 1), (2, 2)).is_subset(b) is True
    assert S.UniversalSet.is_subset(b) is False
    assert FiniteSet((1, 1), (3, 3)).is_subset(b) is False


def test_union_of_product_sets():
    # a ProductSet of finite sets inside a union which is equal to it
    u = Union(ProductSet(FiniteSet(1), FiniteSet(2)),
              ProductSet(FiniteSet(1, 2), FiniteSet(3)))
    assert u.is_subset(FiniteSet((1, 2), (1, 3), (2, 3))) is True
    assert u.is_subset(FiniteSet((1, 2), (1, 3))) is False
    assert FiniteSet((1, 2), (1, 3), (2, 3)).is_subset(u) is True
    assert Eq(u, FiniteSet((1, 2), (1, 3), (2, 3))) is S.true
    check_concrete_pair(u, FiniteSet((1, 2), (1, 3), (2, 3)))


def test_symbolic_elements():
    # the elements are not known so the relation cannot be decided
    p = ProductSet(FiniteSet(x), FiniteSet(1))
    assert p.is_subset(FiniteSet((x, 1), (y, 1))) is True
    assert p.is_subset(FiniteSet((x, 1))) is True
    assert p.is_subset(FiniteSet((y, 1))) is None
    assert p.is_subset(FiniteSet((1, 1))) is None
    assert FiniteSet((y, 1)).is_subset(p) is None
    assert Eq(p, FiniteSet((y, 1))) is not S.true
    assert Eq(p, FiniteSet((x, 1), (y, 1))) is not S.false

    # a symbol is not known to be an element of a product set
    assert ProductSet(FiniteSet(1, 2), FiniteSet(1, 2)).is_subset(
        FiniteSet((x, 1))) is False
    check_pair(p, FiniteSet((x, 1), (y, 1)))
    check_pair(p, FiniteSet((y, 1)))
    check_pair(p, FiniteSet((1, 1)))


def test_relations_between_exotic_sets_do_not_raise():
    # Eq/Ne consult the subset relation, which cannot answer for every pair
    # (Range(n) has no fixed size, a SymmetricDifference has no _contains, a
    # ConditionSet tested for a Partition fails deep inside its own
    # machinery, ...). Such a pair must stay undecided instead of aborting.
    from sympy import (ConditionSet, DisjointUnion, ImageSet, Lambda,
                       SymmetricDifference)
    from sympy.combinatorics.partitions import Partition
    exotic = [
        ConditionSet(x, Eq(x**2, 1), S.Reals),
        SymmetricDifference(FiniteSet(1), FiniteSet(2), evaluate=False),
        Partition(FiniteSet(1), FiniteSet(2, 3)),
        Range(n),
        Range(0, oo),
        ImageSet(Lambda(x, x + 1), S.Integers),
        DisjointUnion(FiniteSet(1), FiniteSet(2)),
        Interval(0, oo),
        S.UniversalSet,
    ]
    for a in exotic:
        for b in exotic + [FiniteSet(1, 2), Interval(0, 1), ProductSet(
                FiniteSet(1), FiniteSet(2))]:
            for rel in (Eq(a, b), Ne(a, b)):
                assert rel in (S.true, S.false) or rel.is_Relational
                rel.simplify()


def test_eq_of_single_element_products():
    assert Eq(ProductSet(FiniteSet(1), FiniteSet(2)),
              FiniteSet((1, 2))) is S.true
    assert ProductSet(FiniteSet(1, 2), FiniteSet(3)).is_subset(
        FiniteSet((1, 3), (2, 3))) is True
    assert ProductSet(FiniteSet(1, 2), FiniteSet(3)).is_subset(
        FiniteSet((1, 3), (2, 4))) is False


def test_product_sets_with_a_possibly_empty_factor():
    # an empty factor makes the whole product empty so the factors cannot be
    # used to show that the product sets are different
    p = ProductSet(Range(0, 0, 1), FiniteSet(1))
    q = ProductSet(Range(0, 0, 1), FiniteSet(2))
    assert Eq(p, q) is not S.false
    assert Eq(p, FiniteSet((1, 2))) is not S.true
    # a ProductSet which is known to be empty is the empty set
    assert Eq(ProductSet(S.EmptySet, FiniteSet(1)), S.EmptySet) is S.true
    assert Eq(ProductSet(S.EmptySet, FiniteSet(1)),
              ProductSet(S.EmptySet, FiniteSet(2))) is S.true

    # factors that are known not to be equal still give unequal products
    assert Eq(ProductSet(FiniteSet(1), FiniteSet(2)),
              ProductSet(FiniteSet(1), FiniteSet(3))) is S.false
    assert Eq(ProductSet(FiniteSet(1), Interval(0, 1)),
              ProductSet(FiniteSet(2), Interval(0, 1))) is S.false


def test_not_decidable_sets_do_not_raise():
    # a Range with a symbolic stop cannot be enumerated; the query must not
    # raise but return the unknown value
    assert Range(n).is_subset(FiniteSet(0, 1, 2)) is None
    assert Range(n).is_subset(FiniteSet(0, 1, n)) is None
    assert Range(n, n + 2).is_subset(FiniteSet(n, n + 1)) is True
    assert Range(0, oo).is_subset(FiniteSet(0, 1, 2)) is False
    assert Range(3).is_subset(FiniteSet(0, 1, n)) is None
    # an infinite set is never a subset of a finite one
    assert S.Integers.is_subset(FiniteSet(1, 2)) is False
    # ... and so the two sets are known to be different
    assert Eq(S.Integers, S.Naturals0) is S.false
    assert Eq(S.Naturals0, S.Integers) is S.false


def test_eq_decided_by_subset_relations():
    # two sets are equal exactly when each is a subset of the other, so a
    # subset relation that provably does not hold proves that they differ
    assert ProductSet(FiniteSet(1), FiniteSet(2)).is_subset(
        Interval(1, 2)) is False
    assert Eq(ProductSet(FiniteSet(1), FiniteSet(2)), Interval(1, 2)) is S.false
    assert Ne(ProductSet(FiniteSet(1), FiniteSet(2)), Interval(1, 2)) is S.true

    # the union covers [0, 2] only partially although it contains its ends
    u = Union(Interval(0, 1), FiniteSet(2))
    assert u.is_subset(Interval(0, 2)) is True
    assert Interval(0, 2).is_subset(u) is False
    assert Eq(u, Interval(0, 2)) is S.false
    assert Ne(u, Interval(0, 2)) is S.true

    # mutual containment decides equality
    assert Eq(Range(3), FiniteSet(0, 1, 2)) is S.true
    assert Eq(FiniteSet(0, 1, 2), Range(3)) is S.true
    assert Eq(S.Naturals0, S.Naturals) is S.false

    # nothing can be said when neither direction is decided
    assert Eq(ProductSet(Interval(0, 1), Interval(0, 1)),
              ProductSet(Interval(0, x), Interval(0, y))) not in (S.true, S.false)


def test_simplify_of_set_relations():
    # simplifying a relation between sets must not try to treat the sets as
    # numbers: the difference of two sets is a set, not an expression, so
    # there is nothing to compare with zero (this used to raise
    # AttributeError: 'Complement' object has no attribute 'equals')
    assert Eq({1}, {x}).simplify() == Eq({1}, {x})
    assert Ne({1}, {x}).simplify() == Ne({1}, {x})
    assert Eq(Interval(0, x), Interval(0, y)).simplify() == \
        Eq(Interval(0, x), Interval(0, y))

    # undecidable relations are preserved (up to the canonical ordering of
    # the arguments) and simplifying twice changes nothing
    for rel in [Eq(FiniteSet(x, y), FiniteSet(x)),
                Ne(FiniteSet(x, y), FiniteSet(x)),
                Eq(ProductSet(FiniteSet(1), Interval(0, 1)),
                   ProductSet(FiniteSet(1), Interval(0, x)))]:
        simple = rel.simplify()
        assert simple.is_Relational
        assert simple not in (S.true, S.false)
        assert simple.canonical == rel.canonical
        assert simple.simplify() == simple

    # decidable relations are returned as they are
    assert Eq({1}, {2}).simplify() is S.false
    assert Eq({1}, {1}).simplify() is S.true
    assert Ne({1}, {2}).simplify() is S.true
    assert Ne({1}, {1}).simplify() is S.false
    assert Eq(ProductSet(FiniteSet(1, 2), FiniteSet(1, 2)),
              FiniteSet((1, 1), (1, 2), (2, 1), (2, 2))).simplify() is S.true
    assert Eq(ProductSet(FiniteSet(1), FiniteSet(2)),
              Interval(1, 2)).simplify() is S.false


def test_eq_between_sets_of_different_kinds():
    # a set of tuples is not an interval and not a set of numbers
    assert Eq(ProductSet(FiniteSet(1), FiniteSet(2)), Interval(1, 2)) is S.false
    assert FiniteSet((1, 2)).is_subset(Interval(1, 2)) is False
    assert Interval(1, 2).is_subset(FiniteSet((1, 2))) is False

    # only the subset relation decides the question; queries that do not
    # involve it keep their previous answers
    assert Interval(0, 1).is_subset(FiniteSet(0, 1)) is False
    assert FiniteSet(0, 1).is_subset(Interval(0, 1)) is True
    assert Interval(0, 1).is_subset(Interval(0, 2)) is True
    assert Interval(0, 2).is_subset(Interval(0, 1)) is False
    assert Eq(ProductSet(FiniteSet(1)), ProductSet(FiniteSet(1),
                                                   FiniteSet(2))) is S.false
    assert Eq(ProductSet(), FiniteSet(1)) is S.false
    assert not ProductSet(FiniteSet(1, 2), FiniteSet(1, 2)).is_subset(
        ProductSet(FiniteSet(1), FiniteSet(2)))


def test_contains_of_productset_with_plain_tuple():
    # iterating a ProductSet yields plain tuples which can be fed back into
    # a containment query of another ProductSet
    a = ProductSet(FiniteSet(1, 2), FiniteSet(1, 2))
    b = ProductSet(FiniteSet(1), FiniteSet(2))
    assert a._contains((1, 1)) is True
    assert b._contains((1, 2)) is True
    assert b._contains((1, 1)) is False
    assert b._contains((1, 2, 3)) is False
    assert b._contains(x) is None
    assert Tuple(1, 2) in b
    assert (1, 2) in b
    assert all(b._contains(e) is True for e in b)


def test_same_elements_different_sets():
    # the same number of elements in a different arrangement must not be
    # confused: these are two different sets
    p = ProductSet(FiniteSet(1, 2), FiniteSet(3))
    q = ProductSet(FiniteSet(1), FiniteSet(2, 3))
    r = ProductSet(FiniteSet(1, 2), FiniteSet(4))
    assert p.is_subset(q) is False
    assert q.is_subset(p) is False
    assert Eq(p, q) is S.false
    assert p.is_subset(r) is False
    assert p.is_subset(FiniteSet((1, 3), (2, 3))) is True
    assert FiniteSet((1, 3), (2, 3)).is_subset(q) is False
    check_concrete_pair(p, FiniteSet((1, 3), (2, 3)))
    check_concrete_pair(p, q)
    check_concrete_pair(p, r)


def test_empty_and_duplicate_elements():
    empty = ProductSet(S.EmptySet, FiniteSet(1))
    assert empty.is_empty is True
    assert empty.is_subset(S.EmptySet) is True
    assert empty.is_subset(FiniteSet((1, 1))) is True
    assert FiniteSet((1, 1)).is_subset(empty) is False
    assert Eq(empty, S.EmptySet) is S.true

    # duplicate factors are the same element of the set
    assert ProductSet(FiniteSet(1, 1, 2), FiniteSet(3)).is_subset(
        FiniteSet((1, 3), (2, 3))) is True
    assert ProductSet(FiniteSet(1, 1, 2), FiniteSet(3)) == ProductSet(
        FiniteSet(1, 2), FiniteSet(3))


def test_subset_agrees_with_enumeration():
    # every pair of small concrete sets must be decided by is_subset and the
    # answer must agree with enumerating the elements of the first set
    bases = [FiniteSet(1, 2), FiniteSet(2, 3), Range(0, 2), Range(1, 3)]
    sets = [ProductSet(a, b) for a in bases for b in bases]
    sets += [
        FiniteSet((1, 1), (1, 2), (2, 1), (2, 2)),
        FiniteSet((1, 1), (2, 2)),
        FiniteSet((1, 1), (1, 2), (2, 1), (2, 2), (3, 3)),
        ProductSet(FiniteSet(1, 2, 3), FiniteSet(1, 2)),
        Union(FiniteSet((3, 3)), ProductSet(FiniteSet(1, 2),
                                           FiniteSet(1, 2))),
        Union(ProductSet(FiniteSet(1), FiniteSet(2)),
              ProductSet(FiniteSet(3), FiniteSet(3))),
    ]
    for a in sets:
        for b in sets:
            check_concrete_pair(a, b)  # uses brute_force_subset and check_pair


def test_repeated_queries_are_stable():
    a = ProductSet(FiniteSet(1, 2), FiniteSet(1, 2))
    b = FiniteSet((1, 1), (1, 2), (2, 1), (2, 2))
    results = [(a.is_subset(b), b.is_subset(a), Eq(a, b)) for _ in range(5)]
    assert results == [(True, True, S.true)] * 5
    # asking about a and b does not change either of them
    assert a == ProductSet(FiniteSet(1, 2), FiniteSet(1, 2))
    assert b == FiniteSet((1, 1), (1, 2), (2, 1), (2, 2))
