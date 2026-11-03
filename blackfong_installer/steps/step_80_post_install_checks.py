from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PostInstallChecksStep:
    step_id = "80_post_install_checks"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        if not target_root:
            raise RuntimeError("execution.mounts.target_root missing")

        # Basic filesystem sanity checks
        must_exist = [
            "etc",
            "boot",
        ]
        for rel in must_exist:
            p = Path(target_root) / rel
            if not p.exists():
                raise RuntimeError(f"Post-install check failed: missing {p}")

        if not bool((state.get("config") or {}).get("dry_run", False)):
            self._check_desktop(Path(target_root))

        logger.info("Post-install checks passed")
        return state

    @staticmethod
    def _check_desktop(root: Path) -> None:
        """The installed system must be the Kubuntu/Plasma session, not another desktop."""
        plasma = [root / "usr/bin/startplasma-x11", root / "usr/bin/startplasma-wayland"]
        if not any(p.exists() for p in plasma):
            raise RuntimeError("Post-install check failed: KDE Plasma session (startplasma-*) not installed")
        if not (root / "usr/bin/sddm").exists():
            raise RuntimeError("Post-install check failed: SDDM display manager not installed")
        dm = root / "etc/X11/default-display-manager"
        if dm.exists() and dm.read_text(encoding="utf-8").strip() != "/usr/bin/sddm":
            raise RuntimeError(f"Post-install check failed: default display manager is {dm.read_text().strip()}, not sddm")
        for forbidden in ("usr/bin/xfce4-session", "usr/sbin/lightdm"):
            if (root / forbidden).exists():
                raise RuntimeError(f"Post-install check failed: {forbidden} present; XFCE is not part of the O.B.E.O.S. v1 path")
