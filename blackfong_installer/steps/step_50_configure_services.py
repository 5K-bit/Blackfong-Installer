from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from ..lib.chroot import chroot_cmd, mount_chroot_binds, umount_chroot_binds

logger = logging.getLogger(__name__)


def _write_file(root: str, rel: str, contents: str, *, dry_run: bool) -> None:
    p = Path(root) / rel.lstrip("/")
    if dry_run:
        logger.info("Would write %s", str(p))
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(contents, encoding="utf-8")


class ConfigureServicesStep:
    step_id = "50_configure_services"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        if not target_root:
            raise RuntimeError("execution.mounts.target_root missing")

        dry_run = bool(cfg.get("dry_run", False))

        hostname = cfg.get("hostname", "blackfong")
        _write_file(target_root, "/etc/hostname", hostname + "\n", dry_run=dry_run)

        firewall = bool(cfg.get("firewall_enabled", True))
        daise_perms = bool(cfg.get("daise_device_access_enabled", True))

        # Single-user policy: create fixed UID user (default 1000)
        username = cfg.get("username", "blackfong")
        uid = int(cfg.get("fixed_uid", 1000))

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            # Ensure group/user exist; idempotent
            chroot_cmd(target_root, ["groupadd", "-g", str(uid), username], dry_run=dry_run)
        except Exception:
            # group may exist
            pass

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            chroot_cmd(
                target_root,
                [
                    "useradd",
                    "-m",
                    "-u",
                    str(uid),
                    "-g",
                    str(uid),
                    "-s",
                    "/bin/bash",
                    username,
                ],
                dry_run=dry_run,
            )
        except Exception:
            # user may exist
            pass
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        state.setdefault("execution", {}).setdefault("decisions", {})["firewall_enabled"] = firewall
        state.setdefault("execution", {}).setdefault("decisions", {})["daise_device_access_enabled"] = daise_perms
        state.setdefault("execution", {}).setdefault("decisions", {})["single_user"] = {"username": username, "uid": uid}

        logger.info("Configured hostname=%s user=%s(uid=%s)", hostname, username, uid)
        logger.info("Firewall=%s DAISE device access=%s", firewall, daise_perms)
        return state
