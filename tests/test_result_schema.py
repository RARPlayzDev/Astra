"""Phase 0 evidence-freeze test: the canonical result artifact is well-formed.

Validates ``results/suite_results.json`` against the canonical JSON Schema in
``results/result_schema.json`` using a small, self-contained structural
validator (no third-party dependency).  This locks the machine-readable result
contract so downstream phases cannot silently reshape the headline numbers.

If ``results/suite_results.json`` is absent (e.g. a fresh checkout that has not
run ``python -m ewsmart.experiments --suite full`` yet) the artifact-dependent
checks skip gracefully; the schema-self-consistency checks always run.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "results" / "result_schema.json"
RESULTS_PATH = ROOT / "results" / "suite_results.json"


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------
# Minimal, dependency-free JSON-Schema (subset) validator.
# Supports the keywords actually used by result_schema.json:
#   type, required, properties, additionalProperties, items, $ref, $defs,
#   minimum, maximum, enum.
# --------------------------------------------------------------------------
_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value, type_spec) -> bool:
    types = type_spec if isinstance(type_spec, list) else [type_spec]
    for t in types:
        if t == "number":
            # bool is a subclass of int; exclude it from "number"
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                return True
        elif t == "integer":
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return True
        else:
            py = _JSON_TYPES.get(t)
            if py is not None and isinstance(value, py):
                # object/array must not accidentally match bool etc.
                if t == "boolean" or not isinstance(value, bool):
                    return True
    return False


def _resolve_ref(ref, root):
    assert ref.startswith("#/"), f"only local refs supported, got {ref!r}"
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _validate(value, schema, root, path, errors):
    if "$ref" in schema:
        schema = _resolve_ref(schema["$ref"], root)

    if "type" in schema and not _type_ok(value, schema["type"]):
        errors.append(f"{path}: expected type {schema['type']!r}, "
                      f"got {type(value).__name__}")
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in enum {schema['enum']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required key {req!r}")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                _validate(v, props[k], root, f"{path}.{k}", errors)
            else:
                addl = schema.get("additionalProperties", True)
                if addl is False:
                    errors.append(f"{path}: unexpected key {k!r}")
                elif isinstance(addl, dict):
                    _validate(v, addl, root, f"{path}.{k}", errors)

    elif isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                _validate(item, item_schema, root, f"{path}[{i}]", errors)


def validate(instance, schema) -> list:
    """Return a list of human-readable validation errors (empty == valid)."""
    errors: list = []
    _validate(instance, schema, schema, "$", errors)
    return errors


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------
def test_schema_file_is_valid_json():
    assert SCHEMA_PATH.exists(), f"missing schema: {SCHEMA_PATH}"
    schema = _load(SCHEMA_PATH)
    assert schema.get("$schema", "").startswith("https://json-schema.org/")
    assert schema["type"] == "object"
    assert "monte_carlo" in schema["properties"]


def test_validator_rejects_bad_documents():
    schema = _load(SCHEMA_PATH)
    # Missing every required top-level key.
    bad = {"significance": []}
    errs = validate(bad, schema)
    assert any("monte_carlo" in e for e in errs), errs
    # Wrong type for a required section.
    bad2 = {"monte_carlo": [], "significance": [], "mission_effectiveness": {}}
    errs2 = validate(bad2, schema)
    assert errs2, "expected a type error for monte_carlo as a list"


def test_suite_results_matches_schema():
    if not RESULTS_PATH.exists():
        print(f"SKIP (no artifact: run "
              f"`python -m ewsmart.experiments --suite full` to generate "
              f"{RESULTS_PATH.name})")
        return
    schema = _load(SCHEMA_PATH)
    results = _load(RESULTS_PATH)
    errors = validate(results, schema)
    assert not errors, "suite_results.json violates schema:\n" + "\n".join(errors)
    # Provenance sanity: significance rows carry an episode count.
    for row in results.get("significance", []):
        assert row.get("n", 0) >= 1, f"significance row without n: {row}"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} result-schema tests passed")
