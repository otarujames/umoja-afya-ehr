#!/usr/bin/env python3
"""Fail fast when the Alembic revision graph is unsafe for deployment."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "migrations" / "versions"


def literal_assignment(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                value = node.value
                return ast.literal_eval(value)
    raise ValueError(f"missing {name}")


def main() -> int:
    revisions: dict[str, tuple[str, ...]] = {}
    sources: dict[str, Path] = {}
    errors: list[str] = []

    for path in sorted(VERSIONS.glob("*.py")):
        if path.name.startswith("__"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            revision = str(literal_assignment(tree, "revision"))
            raw_down = literal_assignment(tree, "down_revision")
            if raw_down is None:
                parents: tuple[str, ...] = ()
            elif isinstance(raw_down, str):
                parents = (raw_down,)
            else:
                parents = tuple(str(item) for item in raw_down)
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        if revision in revisions:
            errors.append(f"duplicate revision {revision}: {sources[revision].name} and {path.name}")
        revisions[revision] = parents
        sources[revision] = path

    for revision, parents in revisions.items():
        for parent in parents:
            if parent not in revisions:
                errors.append(f"{sources[revision].name}: missing parent revision {parent}")

    referenced = {parent for parents in revisions.values() for parent in parents}
    heads = sorted(set(revisions) - referenced)
    bases = sorted(rev for rev, parents in revisions.items() if not parents)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(rev: str) -> None:
        if rev in visiting:
            errors.append(f"cycle detected at revision {rev}")
            return
        if rev in visited:
            return
        visiting.add(rev)
        for parent in revisions.get(rev, ()):
            visit(parent)
        visiting.remove(rev)
        visited.add(rev)

    for revision in revisions:
        visit(revision)

    if len(heads) != 1:
        errors.append(f"expected exactly one Alembic head; found {len(heads)}: {', '.join(heads) or 'none'}")
    if len(bases) != 1:
        errors.append(f"expected exactly one Alembic base; found {len(bases)}: {', '.join(bases) or 'none'}")

    if errors:
        print("Alembic migration validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 2

    print(f"Alembic migration graph OK: {len(revisions)} revisions, base={bases[0]}, head={heads[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
