from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.block import get_uuid
from ..lib.bootloader import install_grub_efi, write_extlinux_config
from ..lib.chroot import mount_chroot_binds, umount_chroot_binds
from ..lib.pkg import apt_has_package, apt_install, apt_update

logger = logging.getLogger(__name__)

GRUB_EFI_BY_ARCH = {
    "amd64": ["grub-efi-amd64"],
    "arm64": ["grub-efi-arm64"],
    # Rare, but keep a best-effort mapping.
    "armhf": ["grub-efi-arm", "grub-efi-armhf"],
}


class InstallBootloaderStep:
    step_id = "35_install_bootloader"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        hw = state.get("hardware") or {}
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}

        target_root = mounts.get("target_root")
        root_part = mounts.get("root_part")
        if not target_root or not root_part:
            raise RuntimeError("Missing target_root/root_part; run partition step first")

        firmware = hw.get("firmware")
        if firmware not in {"efi", "uboot"}:
            raise RuntimeError(f"hardware.firmware must be efi|uboot, got {firmware}")

        arch = hw.get("arch")
        if not arch:
            raise RuntimeError("hardware.arch is missing")

        dry_run = bool(cfg.get("dry_run", False))

        # Ensure bootloader tooling exists inside target
        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            if firmware == "efi":
                grub_candidates = GRUB_EFI_BY_ARCH.get(arch)
                if not grub_candidates:
                    raise RuntimeError(f"Unsupported arch for EFI grub selection: {arch}")
                grub_pkg = next((p for p in grub_candidates if apt_has_package(target_root, p, dry_run=dry_run)), None)
                if not grub_pkg:
                    raise RuntimeError(
                        f"No supported grub-efi package found for arch={arch}. "
                        f"Tried: {', '.join(grub_candidates)}"
                    )
                apt_install(target_root, [grub_pkg, "efibootmgr"], with_recommends=True, dry_run=dry_run)
            else:
                # extlinux is typically provided via syslinux-common/extlinux
                apt_install(target_root, ["extlinux", "syslinux-common"], with_recommends=True, dry_run=dry_run)
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        root_uuid = get_uuid(root_part, dry_run=dry_run)
        state.setdefault("execution", {}).setdefault("decisions", {})["root_uuid"] = root_uuid

        if firmware == "efi":
            install_grub_efi(target_root=target_root, disk=cfg.get("target_disk", ""), dry_run=dry_run)
        else:
            write_extlinux_config(target_root=target_root, root_uuid=root_uuid, dry_run=dry_run)

        logger.info("Bootloader configured (firmware=%s)", firmware)
        return state
