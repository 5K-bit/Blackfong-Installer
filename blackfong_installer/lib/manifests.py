from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def _repo_root() -> Path:
    # blackfong_installer/lib/manifests.py -> blackfong_installer -> repo root
    return Path(__file__).resolve().parents[2]


def load_yaml_rel(rel_path: str) -> Dict[str, Any]:
    """Load a YAML file relative to repo root (manifests/...)."""
    try:
        import yaml  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("PyYAML required to load manifests") from e

    p = _repo_root() / rel_path.lstrip("/")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Manifest must be a mapping/dict: {p}")
    return data


def load_profile(profile_id: str) -> Dict[str, Any]:
    return load_yaml_rel(f"manifests/profiles/{profile_id}.yaml")


def load_features_manifest() -> Dict[str, Any]:
    return load_yaml_rel("manifests/features.yaml")

