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

        hostname = str(cfg.get("hostname", "blackfong-node")).strip() or "blackfong-node"
        _write_file(target_root, "/etc/hostname", hostname + "\n", dry_run=dry_run)
        _write_file(
            target_root,
            "/etc/hosts",
            "\n".join(
                [
                    "127.0.0.1\tlocalhost",
                    f"127.0.1.1\t{hostname}",
                    "",
                    "# IPv6",
                    "::1\tlocalhost ip6-localhost ip6-loopback",
                    "ff02::1\tip6-allnodes",
                    "ff02::2\tip6-allrouters",
                    "",
                ]
            ),
            dry_run=dry_run,
        )

        firewall = bool(cfg.get("firewall_enabled", True))
        daise_perms = bool(cfg.get("daise_device_access_enabled", True))

        # Single-user policy: create fixed UID user (default 1000)
        username = cfg.get("username", "blackfong")
        uid = int(cfg.get("fixed_uid", 1000))

        # SSH access: enabled by default; keys may be injected via state['config']['ssh_authorized_keys'].
        ssh_enabled = bool(cfg.get("ssh_enabled", True))
        ssh_keys = cfg.get("ssh_authorized_keys") or []

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            try:
                # Ensure group exists; idempotent.
                chroot_cmd(target_root, ["groupadd", "-g", str(uid), username], dry_run=dry_run)
            except Exception:
                # group may exist
                pass

            try:
                # Ensure user exists; idempotent.
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

            if ssh_enabled and ssh_keys:
                if not isinstance(ssh_keys, list):
                    raise RuntimeError("config.ssh_authorized_keys must be a list of strings")
                keys_txt = "\n".join([str(k).strip() for k in ssh_keys if str(k).strip()]) + "\n"
                _write_file(
                    target_root,
                    f"/home/{username}/.ssh/authorized_keys",
                    keys_txt,
                    dry_run=dry_run,
                )
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        # Enable core "node" services. This is safe (systemctl enable only writes symlinks).
        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            chroot_cmd(target_root, ["systemctl", "enable", "NetworkManager.service"], dry_run=dry_run)
            if ssh_enabled:
                chroot_cmd(target_root, ["systemctl", "enable", "ssh.service"], dry_run=dry_run)

            # Ensure ssh key perms/ownership if we wrote them.
            if ssh_enabled and ssh_keys:
                chroot_cmd(
                    target_root,
                    ["bash", "-lc", f"chmod 700 /home/{username}/.ssh && chmod 600 /home/{username}/.ssh/authorized_keys"],
                    dry_run=dry_run,
                )
                chroot_cmd(
                    target_root,
                    ["chown", "-R", f"{username}:{username}", f"/home/{username}/.ssh"],
                    dry_run=dry_run,
                )
        except Exception:
            # Keep going; services may vary by distro/rootfs.
            logger.info("Non-fatal: service enablement step failed (will rely on defaults)")
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        state.setdefault("execution", {}).setdefault("decisions", {})["firewall_enabled"] = firewall
        state.setdefault("execution", {}).setdefault("decisions", {})["daise_device_access_enabled"] = daise_perms
        state.setdefault("execution", {}).setdefault("decisions", {})["single_user"] = {"username": username, "uid": uid}
        state.setdefault("execution", {}).setdefault("decisions", {})["ssh_enabled"] = ssh_enabled
        state.setdefault("execution", {}).setdefault("decisions", {})["hostname"] = hostname

        logger.info("Configured hostname=%s user=%s(uid=%s)", hostname, username, uid)
        logger.info("Firewall=%s DAISE device access=%s", firewall, daise_perms)
        return state
