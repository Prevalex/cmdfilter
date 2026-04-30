from __future__ import annotations

import argparse
import random
import time
from functools import reduce
from operator import mul

from cmdfilter import (
    IS_ANY_BOOL_EQ,
    IS_ANY_FLOAT_GE,
    IS_ANY_FLOAT_LE,
    IS_ANY_STR_EQ,
    DataItem,
    Selector,
    grade,
    layer,
    to_float,
    to_str,
)


def build_selector() -> Selector:
    volume_at_least = grade(
        type_method=to_float,
        eval_method=lambda value_tuple, arg: reduce(mul, value_tuple) / 1000,
        match_method=lambda volume, arg: volume >= arg,
        group_keys=True,
        cost=10,
    )
    similar_text = grade(
        type_method=to_str,
        eval_method=lambda values, arg: (
            arg.lower() in " ".join(part.lower() for part in values)
        ),
        match_method=lambda result, arg: result,
        group_keys=True,
        cost=50,
    )
    return Selector(
        [
            layer("by_text", similar_text, ("find", "f"), keys=("title", "color")),
            layer("by_title", IS_ANY_STR_EQ, "t", keys="title"),
            layer(
                "volume_above",
                volume_at_least,
                ("vol_above", "va"),
                keys=("width", "depth", "height"),
            ),
            layer("price_below", IS_ANY_FLOAT_LE, ("price_below", "pb"), keys="price"),
            layer("price_above", IS_ANY_FLOAT_GE, ("price_above", "pa"), keys="price"),
            layer(
                "availability",
                IS_ANY_BOOL_EQ,
                ("stock", "s"),
                keys=("stock", "transit"),
            ),
        ]
    )


def build_catalog(size: int, *, seed: int) -> list[DataItem]:
    rng = random.Random(seed)
    colors = ("white", "yellow", "grey", "gray", "black", "red", "green")
    prefixes = ("Core", "Rift", "Mobi", "Cube", "Bulk", "Peer", "Fore")
    catalog: list[DataItem] = []
    for index in range(size):
        width = rng.randint(20, 60)
        depth = rng.randint(20, 60)
        height = rng.randint(20, 60)
        catalog.append(
            {
                "title": f"{prefixes[index % len(prefixes)]}-{index}",
                "color": colors[index % len(colors)],
                "price": round(rng.uniform(1.0, 99.0), 2),
                "width": width,
                "depth": depth,
                "height": height,
                "stock": bool(index % 3),
                "transit": index % 2,
            }
        )
    return catalog


def run_benchmark(size: int, repeats: int, seed: int) -> None:
    selector = build_selector()
    catalog = build_catalog(size, seed=seed)
    parsed = selector.parse("Rift pb:60 pa:10 va:20 s:yes", context={"case": False})

    durations: list[float] = []
    matches = 0
    for _ in range(repeats):
        started = time.perf_counter()
        result = selector.match_many(parsed, catalog)
        durations.append(time.perf_counter() - started)
        matches = len(result)

    best = min(durations)
    average = sum(durations) / len(durations)
    print(f"items={size:,}")
    print(f"repeats={repeats}")
    print(f"matches={matches:,}")
    print(f"best_seconds={best:.6f}")
    print(f"avg_seconds={average:.6f}")
    print(f"items_per_second_best={size / best:,.0f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Micro-benchmark for Selector.match_many()."
    )
    parser.add_argument(
        "--items", type=int, default=50_000, help="Number of catalog items to generate."
    )
    parser.add_argument(
        "--repeats", type=int, default=5, help="How many times to run match_many()."
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for generated catalog data."
    )
    args = parser.parse_args()
    run_benchmark(args.items, args.repeats, args.seed)


if __name__ == "__main__":
    main()
