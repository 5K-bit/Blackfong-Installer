from __future__ import annotations

import logging
import shlex
from pathlib import Path
from typing import Any, Dict

from ..lib.assets import copy_tree
from ..lib.chroot import chroot_cmd, mount_chroot_binds, umount_chroot_binds
from ..lib.command import run_cmd
from ..lib.pkg import apt_install, apt_update

logger = logging.getLogger(__name__)

LIVE_BUNDLE = "/opt/blackfong/bundle"
TARGET_SRC = "/opt/obeos/src"
TARGET_VENV = "/opt/obeos/venv"

DAISE_LAUNCHER = """#!/bin/sh
# Blackfong system-wide DAISE entrypoint (installed by blackfong-installer).
# Runs the Thoughtglass HUD (O.B.E.O.S. secondary cockpit) bound to localhost.
exec /opt/obeos/venv/bin/blackfong hud --host 127.0.0.1 --no-open-browser
"""


class InstallObeosStep:
    """Install the bundled O.B.E.O.S. components onto the target (hybrid: pip needs network).

    Component failures are recorded as warnings and never abort the OS install.
    """

    step_id = "52_install_obeos"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        exe = state.setdefault("execution", {})
        target_root = (exe.get("mounts") or {}).get("target_root")
        if not target_root:
            raise RuntimeError("execution.mounts.target_root missing")
        dry_run = bool(cfg.get("dry_run", False))

        if not bool(cfg.get("install_obeos", True)):
            logger.info("install_obeos=false; skipping bundle install")
            return state

        bundle = Path(cfg.get("bundle_path", LIVE_BUNDLE))
        if not dry_run and not bundle.is_dir():
            exe.setdefault("warnings", []).append({"step": self.step_id, "reason": f"bundle missing: {bundle}"})
            logger.warning("Bundle not found at %s; skipping O.B.E.O.S. install", bundle)
            return state

        if dry_run:
            logger.info("Would copy %s -> %s%s", bundle, target_root, TARGET_SRC)
        else:
            copy_tree(str(bundle), f"{target_root}{TARGET_SRC}")

        # Chroot DNS for pip (debootstrap does not copy resolv.conf).
        run_cmd(["cp", "-L", "/etc/resolv.conf", f"{target_root}/etc/resolv.conf"], check=False, dry_run=dry_run)

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            apt_install(target_root, ["python3", "python3-venv", "python3-pip", "git", "build-essential"], dry_run=dry_run)
            chroot_cmd(target_root, ["python3", "-m", "venv", TARGET_VENV], dry_run=dry_run)

            # Prefer the build config's repo list when present; else install every bundled dir that is a package.
            names = sorted(p.name for p in bundle.iterdir()) if (bundle.is_dir() and not dry_run) else []
            skip = set(cfg.get("obeos_pip_skip") or ["The-Assistant", "Blackrelay", "PYBUS"])
            failed: list[str] = []
            for name in names:
                if name in skip:
                    continue
                src = f"{TARGET_SRC}/{name}"
                if not (bundle / name / "pyproject.toml").exists():
                    continue
                try:
                    chroot_cmd(
                        target_root,
                        ["bash", "-lc", f"{TARGET_VENV}/bin/pip install {shlex.quote(src)}"],
                        dry_run=dry_run,
                    )
                except Exception as e:  # keep going; the OS install must not fail on one component
                    failed.append(name)
                    exe.setdefault("warnings", []).append({"step": self.step_id, "component": name, "error": str(e)[:300]})
                    logger.warning("pip install failed for %s", name)

            launcher = Path(target_root) / "usr/local/bin/daise"
            if dry_run:
                logger.info("Would write %s", launcher)
            else:
                launcher.parent.mkdir(parents=True, exist_ok=True)
                launcher.write_text(DAISE_LAUNCHER, encoding="utf-8")
                launcher.chmod(0o755)
            for tool in ("blackfong", "3000", "blackforge", "earthglass", "maxpayne", "nightwatch", "quietdrop"):
                chroot_cmd(
                    target_root,
                    ["bash", "-lc", f"[ -x {TARGET_VENV}/bin/{tool} ] && ln -sf {TARGET_VENV}/bin/{tool} /usr/local/bin/{tool} || true"],
                    dry_run=dry_run,
                )
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        exe.setdefault("decisions", {})["obeos_failed_components"] = failed if not dry_run else []
        logger.info("O.B.E.O.S. bundle installed (failed=%s)", exe["decisions"]["obeos_failed_components"])
        return state
