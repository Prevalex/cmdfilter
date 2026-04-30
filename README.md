# cmdfilter

`cmdfilter` helps you turn a user query like `title:Core pb:6.5 stock:yes` into a reusable filter for Python objects.

It is built for the common backend task where you need to:

- accept compact text filters from CLI, admin panels, bots, or simple search boxes
- parse them once
- match the parsed command against one object or thousands of objects without reparsing

If you need a small Python library for declarative query parsing and repeatable filtering over dict-like data, this is exactly what `cmdfilter` is for.

`cmdfilter` is a small filtering library built around declarative layers.

The core idea is:

1. Define reusable filter grades.
2. Build selector layers on top of those grades.
3. Parse a user query into an immutable `ParsedCommand`.
4. Reuse that parsed command against one object or many objects.

The current API is reentrant by design:

- `Layer` is immutable configuration.
- `ParsedLayer` stores parsed runtime arguments.
- `Selector.parse(...)` does not mutate the selector.
- `Selector.match(...)` and `Selector.match_many(...)` can safely reuse the same parsed command.
- Runtime matching context is attached during `parse(...)` and reused by `match(...)`.

## Installation

```bash
pip install cmdfilter
```

From a local checkout:

```bash
pip install .
```

For development:

```bash
pip install -e .[dev]
```

## Quick Start

```python
from cmdfilter import IS_ANY_FLOAT_LE, IS_ANY_STR_EQ, Selector, layer

items = [
    {"title": "Core", "price": 6.0},
    {"title": "Rift", "price": 7.0},
]

selector = Selector(
    [
        layer("title", IS_ANY_STR_EQ, ("title", "t"), keys="title"),
        layer("price_below", IS_ANY_FLOAT_LE, ("price_below", "pb"), keys="price"),
    ]
)

parsed = selector.parse("t:Core pb:6.5")

print(parsed.as_dict())
# {(0, "title"): ("t", "Core"), (1, "price_below"): ("pb", "6.5")}

print(selector.match(parsed, items[0]))
# (True, None)

print(selector.match_many(parsed, items))
# [(0, None)]
```

This example shows the core workflow:

- declare filterable fields once
- parse a compact user command once
- reuse the parsed command for single-item and bulk matching

## Lifecycle: parse -> match

The intended flow is:

```python
parsed = selector.parse("pb:6.5")
result = selector.match(parsed, one_item)
results = selector.match_many(parsed, many_items)
```

This split is useful when:

- parsing is more expensive than matching
- the same query must be reused many times
- you want a stable parsed snapshot for tests or debugging

## Building Custom Grades

You can define your own matching logic with `grade(...)`.

The library also ships with built-in grades such as `IS_ANY_STR_EQ`, `IS_ANY_FLOAT_LE`, and `IS_ALL_INT_GE`.
These presets live in an internal module and are re-exported from the public `cmdfilter` package.

```python
from functools import reduce
from operator import mul

from cmdfilter import Selector, grade, layer, to_float

volume_at_least = grade(
    type_method=to_float,
    eval_method=lambda values, arg: reduce(mul, values) / 1000,
    match_method=lambda volume, arg: volume >= arg,
    group_keys=True,
    cost=10,
)

selector = Selector(
    [
        layer(
            "volume_above",
            volume_at_least,
            ("vol_above", "va"),
            keys=("width", "depth", "height"),
        )
    ]
)
```

Rules of thumb:

- `type_method(raw)` converts raw query values to the target type
- `arg_method(arg)` is optional post-processing for parsed arguments
- `eval_method(value, arg)` is used when `group_keys=False`
- `eval_method(values_tuple, arg)` is used when `group_keys=True`
- `match_method(eval_result)` is used when `group_keys=False`
- `match_method(eval_result, arg)` is used when `group_keys=True`
- If needed, `arg_method(...)`, `eval_method(...)`, and `match_method(...)` may additionally accept `*, context=None`
- `grade(..., context="name")` or `grade(..., context=("name1", "name2"))` declares which context fields a grade uses

Example with runtime context:

```python
from cmdfilter import Selector, grade, layer, to_str

case_aware_title = grade(
    type_method=to_str,
    eval_method=lambda value, arg, *, context=None: value if context and context.case else value.lower(),
    match_method=lambda values, *, context=None: any(
        item == ("RIFT" if context and context.case else "rift") for item in values
    ),
    context="case",
)

selector = Selector([layer("title", case_aware_title, ("title", "t"), keys="title")])
parsed = selector.parse("t:RIFT", context={"case": False})

print(selector.match(parsed, {"title": "Rift"}))
# (True, ('rift',))
```

To change runtime behavior, parse again with a different context:

```python
parsed_case_sensitive = selector.parse("t:RIFT", context={"case": True})

print(selector.match(parsed_case_sensitive, {"title": "Rift"}))
# (False, ('Rift',))
```

## Layer Metadata

`layer(...)` accepts `about=` as a public convenience argument.

That value is stored on `Layer.help_text` and rendered by `Selector.about()`.

```python
from cmdfilter import IS_ANY_STR_EQ, Selector, layer

selector = Selector(
    [
        layer("title", IS_ANY_STR_EQ, ("title", "t"), keys="title", about="Exact title match"),
    ]
)

print(selector.layers[0].help_text)
# Exact title match

print(selector.about())
# [title|t]:<str> - Exact title match
```

## Parsing Sources

`Selector.parse(...)` accepts either a string command or a dictionary.

String example:

```python
parsed = selector.parse("Rift yellow pb:7.5")
```

Dictionary example:

```python
parsed = selector.parse({"t": "Core", "pb": 6.5})
```

You can also attach runtime context during parsing:

```python
parsed = selector.parse("t:RIFT", context={"case": False})
print(parsed.context.case)
# False
```

Unknown options are preserved in `ParsedCommand.unparsed`.

```python
parsed = selector.parse("t:Core unknown:value")
print(parsed.unparsed)
# {"unknown": "value"}
```

## Injecting Extra Filters

`inject=` lets you merge external filters into the query at parse time.

```python
parsed = selector.parse("t:Core", inject={"pb": 6.5})
```

This is useful for system-imposed constraints such as tenant, visibility, or stock filters.

## Runtime Context

`context=` is an optional runtime channel for custom grades.

- `grade(..., context=...)` declares which named fields a grade wants
- `Selector.parse(..., context=...)` stores those fields inside `ParsedCommand.context` and also makes them available to `arg_method(...)` during parsing
- `Selector.match(...)` and `Selector.match_many(...)` use the context already stored in `ParsedCommand`
- Missing declared context fields are filled with `None`

This is useful when the query text stays the same, but matching behavior must vary between calls, for example:

- case-sensitive vs case-insensitive string comparison
- locale-specific normalization
- sort or comparison mode switches
- feature-flagged matching logic

When matching behavior must change, create another parsed snapshot with `Selector.parse(..., context=...)`.

## Main Public Objects

- `Grade`: immutable filter behavior definition
- `Layer`: immutable selector configuration
- `ParsedLayer`: parsed layer with runtime argument
- `ParsedCommand`: immutable parsed query snapshot with optional runtime context
- `Selector`: parser and matcher

Import note:

- Public import path: `cmdfilter`

## When It Fits Best

`cmdfilter` is a good fit when:

- you have a list of dicts, records, or row-like objects
- users need short `option:value` style filters
- the same parsed filter must be reused many times
- you want filtering rules to stay explicit and testable in Python code

It is probably not the right tool if you need:

- full text indexing
- SQL generation
- dataframe-style analytics
- spreadsheet file reading or writing

