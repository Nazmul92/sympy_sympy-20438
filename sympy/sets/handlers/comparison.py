from sympy.core.relational import Eq, is_eq
from sympy.core.basic import Basic
from sympy.core.logic import fuzzy_and, fuzzy_bool
from sympy.logic.boolalg import And
from sympy.multipledispatch import dispatch
from sympy.sets.sets import tfn, ProductSet, Interval, FiniteSet, Set


@dispatch(Interval, FiniteSet) # type:ignore
def _eval_is_eq(lhs, rhs): # noqa: F811
    return False


@dispatch(FiniteSet, Interval) # type:ignore
def _eval_is_eq(lhs, rhs): # noqa: F811
    return False


@dispatch(Interval, Interval) # type:ignore
def _eval_is_eq(lhs, rhs): # noqa: F811
    return And(Eq(lhs.left, rhs.left),
               Eq(lhs.right, rhs.right),
               lhs.left_open == rhs.left_open,
               lhs.right_open == rhs.right_open)


@dispatch(FiniteSet, Interval) # type:ignore
def _eval_is_eq(lhs, rhs): # noqa: F811
    return False


@dispatch(FiniteSet, FiniteSet) # type:ignore
def _eval_is_eq(lhs, rhs): # noqa: F811
    def all_in_both():
        s_set = set(lhs.args)
        o_set = set(rhs.args)
        yield fuzzy_and(lhs._contains(e) for e in o_set - s_set)
        yield fuzzy_and(rhs._contains(e) for e in s_set - o_set)

    return tfn[fuzzy_and(all_in_both())]


def _eval_is_eq_from_subsets(lhs, rhs):
    """Decide the equality of two sets from their subset relations.

    A set is determined by its elements, so two sets are equal exactly when
    each of them is a subset of the other. A subset relation that provably
    does not hold therefore proves that the sets are not equal, and mutual
    containment proves that they are. This decides e.g.

        Eq(ProductSet(FiniteSet(1, 2), FiniteSet(1, 2)),
           FiniteSet((1, 1), (1, 2), (2, 1), (2, 2)))            -> True
        Eq(ProductSet(FiniteSet(1), FiniteSet(2)), Interval(1, 2)) -> False

    in the first case because the elements of the ProductSet are all in the
    FiniteSet and vice versa, in the second because (1, 2) is not a point of
    the interval.
    """
    try:
        lhs_subset = lhs.is_subset(rhs)
        rhs_subset = rhs.is_subset(lhs)
    except Exception:
        # Asking whether one of the sets is a subset of the other can fail
        # rather than answer for exotic pairs, e.g. Range(n) with a symbolic
        # number of elements raises ValueError and testing a ConditionSet for
        # a Partition raises AttributeError deep inside ConditionSet._contains.
        # The subset relation is only a means to decide the equality here, so
        # a failed query leaves the question undecided instead of aborting the
        # comparison.
        return None
    if lhs_subset is False or rhs_subset is False:
        return False
    if lhs_subset is True and rhs_subset is True:
        return True
    return None


@dispatch(ProductSet, ProductSet) # type:ignore
def _eval_is_eq(lhs, rhs): # noqa: F811
    if len(lhs.sets) != len(rhs.sets):
        return False

    # The empty set is a ProductSet in many different ways so the factors can
    # only decide the question if the product sets are not empty.
    empty = fuzzy_and([lhs.is_empty, rhs.is_empty])
    if empty is True:
        return True

    eqs = tuple(fuzzy_bool(is_eq(x, y)) for x, y in zip(lhs.sets, rhs.sets))
    if all(eqs):
        return True
    if empty is False and any(e is False for e in eqs):
        # the product sets are non-empty and one pair of factors differs
        return False
    # the factors cannot decide the question (e.g. because the emptiness of
    # the product sets is not known) so fall back on the subset relations
    return _eval_is_eq_from_subsets(lhs, rhs)


@dispatch(Set, Basic) # type:ignore
def _eval_is_eq(lhs, rhs): # noqa: F811
    return False


@dispatch(Set, Set) # type:ignore
def _eval_is_eq(lhs, rhs): # noqa: F811
    return _eval_is_eq_from_subsets(lhs, rhs)
