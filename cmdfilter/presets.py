from operator import eq, ge, le, ne

from .helpers import to_bool, to_float, to_int, to_str
from .selector import grade

IS_ANY_BOOL_EQ = grade(type_method=to_bool, eval_method=eq, match_method=any, cost=1)
IS_ANY_BOOL_NE = grade(type_method=to_bool, eval_method=ne, match_method=any, cost=2)
IS_ALL_BOOL_EQ = grade(type_method=to_bool, eval_method=eq, match_method=all, cost=3)
IS_ALL_BOOL_NE = grade(type_method=to_bool, eval_method=ne, match_method=all, cost=4)

IS_ANY_INT_EQ = grade(type_method=to_int, eval_method=eq, match_method=any, cost=5)
IS_ANY_INT_NE = grade(type_method=to_int, eval_method=ne, match_method=any, cost=6)
IS_ANY_INT_GE = grade(type_method=to_int, eval_method=ge, match_method=any, cost=7)
IS_ANY_INT_LE = grade(type_method=to_int, eval_method=le, match_method=any, cost=8)
IS_ALL_INT_EQ = grade(type_method=to_int, eval_method=eq, match_method=all, cost=9)
IS_ALL_INT_NE = grade(type_method=to_int, eval_method=ne, match_method=all, cost=10)
IS_ALL_INT_GE = grade(type_method=to_int, eval_method=ge, match_method=all, cost=11)
IS_ALL_INT_LE = grade(type_method=to_int, eval_method=le, match_method=all, cost=12)

IS_ANY_FLOAT_EQ = grade(type_method=to_float, eval_method=eq, match_method=any, cost=13)
IS_ANY_FLOAT_NE = grade(type_method=to_float, eval_method=ne, match_method=any, cost=14)
IS_ANY_FLOAT_GE = grade(type_method=to_float, eval_method=ge, match_method=any, cost=15)
IS_ANY_FLOAT_LE = grade(type_method=to_float, eval_method=le, match_method=any, cost=16)
IS_ALL_FLOAT_EQ = grade(type_method=to_float, eval_method=eq, match_method=all, cost=17)
IS_ALL_FLOAT_NE = grade(type_method=to_float, eval_method=ne, match_method=all, cost=18)
IS_ALL_FLOAT_GE = grade(type_method=to_float, eval_method=ge, match_method=all, cost=19)
IS_ALL_FLOAT_LE = grade(type_method=to_float, eval_method=le, match_method=all, cost=20)

IS_ANY_STR_EQ = grade(type_method=to_str, eval_method=eq, match_method=any, cost=21)
IS_ANY_STR_NE = grade(type_method=to_str, eval_method=ne, match_method=any, cost=22)
IS_ALL_STR_EQ = grade(type_method=to_str, eval_method=eq, match_method=all, cost=23)
IS_ALL_STR_NE = grade(type_method=to_str, eval_method=ne, match_method=all, cost=24)


__all__ = [
    "IS_ANY_BOOL_EQ",
    "IS_ANY_BOOL_NE",
    "IS_ALL_BOOL_EQ",
    "IS_ALL_BOOL_NE",
    "IS_ANY_INT_EQ",
    "IS_ANY_INT_NE",
    "IS_ANY_INT_GE",
    "IS_ANY_INT_LE",
    "IS_ALL_INT_EQ",
    "IS_ALL_INT_NE",
    "IS_ALL_INT_GE",
    "IS_ALL_INT_LE",
    "IS_ANY_FLOAT_EQ",
    "IS_ANY_FLOAT_NE",
    "IS_ANY_FLOAT_GE",
    "IS_ANY_FLOAT_LE",
    "IS_ALL_FLOAT_EQ",
    "IS_ALL_FLOAT_NE",
    "IS_ALL_FLOAT_GE",
    "IS_ALL_FLOAT_LE",
    "IS_ANY_STR_EQ",
    "IS_ANY_STR_NE",
    "IS_ALL_STR_EQ",
    "IS_ALL_STR_NE",
]
