from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter

from ..config import PROJECT_ROOT

router = APIRouter(tags=["Module Catalogue"])


def _load_config(name: str) -> dict:
    path: Path = PROJECT_ROOT / "config" / name
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


@router.get("/modules")
def modules() -> list[dict]:
    return _load_config("module-catalog.yml").get("modules", [])


@router.get("/flowsheet-templates")
def flowsheet_templates() -> list[dict]:
    return _load_config("flowsheet-templates.yml").get("templates", [])


@router.get("/workflow-statuses")
def workflow_statuses() -> dict:
    return _load_config("workflow-statuses.yml")
