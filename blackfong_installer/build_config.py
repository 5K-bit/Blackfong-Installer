from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class BuildConfig:
    raw: Dict[str, Any]

    @property
    def targets(self) -> List[str]:
        return list(self.raw.get("targets") or [])

    @property
    def work_dir(self) -> str:
        return str(((self.raw.get("paths") or {}).get("work_dir")) or "build/work")

    @property
    def logs_dir(self) -> str:
        return str(((self.raw.get("paths") or {}).get("logs_dir")) or "logs")

    @property
    def offline_repo_path(self) -> str:
        return str(((self.raw.get("offline_repo") or {}).get("path")) or "assets/apt-repo")

    @property
    def offline_repo_live_path(self) -> str:
        return str(((self.raw.get("offline_repo") or {}).get("live_path")) or "/opt/blackfong/apt-repo")

    @property
    def offline_repo_suite(self) -> str:
        return str(((self.raw.get("offline_repo") or {}).get("suite")) or self.debian_suite)

    @property
    def offline_repo_component(self) -> str:
        return str(((self.raw.get("offline_repo") or {}).get("component")) or "main")

    @property
    def debian_suite(self) -> str:
        return str(((self.raw.get("debian") or {}).get("suite")) or "stable")

    @property
    def debian_mirror(self) -> str:
        return str(((self.raw.get("debian") or {}).get("mirror")) or "http://deb.debian.org/debian")


def load_build_config(path: str) -> BuildConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)

    if p.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError("build config must be YAML")

    try:
        import yaml  # type: ignore
    except Exception as e:
        raise RuntimeError("PyYAML is required to read build_config.yaml") from e

    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("build_config.yaml must contain a mapping/object")

    return BuildConfig(raw=raw)
