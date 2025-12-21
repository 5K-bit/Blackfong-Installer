from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence

from .build_config import BuildConfig
from .build_state import is_completed, mark_completed
from .lib.assets import copy_tree
from .lib.apt_repo import build_file_repo_from_debs
from .lib.command import run_cmd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BuildCtx:
    cfg: BuildConfig
    target: str
    state_path: str
    dry_run: bool

    @property
    def work_target_dir(self) -> Path:
        return Path(self.cfg.work_dir) / self.target

    @property
    def rootfs_dir(self) -> Path:
        return self.work_target_dir / "rootfs"

    @property
    def iso_dir(self) -> Path:
        return self.work_target_dir / "iso"

    @property
    def img_path(self) -> Path:
        return self.work_target_dir / f"blackfong-installer-{self.target}.img"


def step_00_initialize(*, ctx: BuildCtx, state: Dict[str, Any], force: bool) -> None:
    step_id = "00_initialize"
    if (not force) and is_completed(state, target=ctx.target, step_id=step_id):
        logger.info("[%s] skip %s", ctx.target, step_id)
        return

    offline_repo = Path(ctx.cfg.offline_repo_path)
    if not offline_repo.exists():
        raise RuntimeError(f"Offline repo path missing: {offline_repo}")

    # Clean per-target work dirs
    ctx.work_target_dir.mkdir(parents=True, exist_ok=True)
    if force and not ctx.dry_run:
        # remove rootfs/iso artifacts
        for p in [ctx.rootfs_dir, ctx.iso_dir]:
            if p.exists():
                run_cmd(["rm", "-rf", str(p)], dry_run=ctx.dry_run)

    mark_completed(state, target=ctx.target, step_id=step_id)


def step_01_prepare_live_rootfs(*, ctx: BuildCtx, state: Dict[str, Any], force: bool) -> None:
    step_id = "01_prepare_live_rootfs"
    if (not force) and is_completed(state, target=ctx.target, step_id=step_id):
        logger.info("[%s] skip %s", ctx.target, step_id)
        return

    rootfs = ctx.rootfs_dir
    rootfs.mkdir(parents=True, exist_ok=True)

    # debootstrap (native or foreign)
    # NOTE: cross-arch builds require qemu-user-static/binfmt and a 2nd stage.
    run_cmd(
        [
            "debootstrap",
            "--arch",
            ctx.target,
            ctx.cfg.debian_suite,
            str(rootfs),
            ctx.cfg.debian_mirror,
        ],
        dry_run=ctx.dry_run,
    )

    # minimal base packages (inside chroot)
    run_cmd(["mount", "--bind", "/dev", str(rootfs / "dev")], dry_run=ctx.dry_run)
    run_cmd(["mount", "--bind", "/proc", str(rootfs / "proc")], dry_run=ctx.dry_run)
    run_cmd(["mount", "--bind", "/sys", str(rootfs / "sys")], dry_run=ctx.dry_run)

    try:
        run_cmd(["chroot", str(rootfs), "apt-get", "update"], dry_run=ctx.dry_run)
        run_cmd(
            [
                "chroot",
                str(rootfs),
                "apt-get",
                "install",
                "-y",
                "--no-install-recommends",
                "bash",
                "coreutils",
                "systemd",
                "iproute2",
                "iputils-ping",
                "ca-certificates",
            ],
            dry_run=ctx.dry_run,
        )
    finally:
        run_cmd(["umount", "-lf", str(rootfs / "sys")], check=False, dry_run=ctx.dry_run)
        run_cmd(["umount", "-lf", str(rootfs / "proc")], check=False, dry_run=ctx.dry_run)
        run_cmd(["umount", "-lf", str(rootfs / "dev")], check=False, dry_run=ctx.dry_run)

    mark_completed(state, target=ctx.target, step_id=step_id)


def step_02_copy_blackfong_assets(*, ctx: BuildCtx, state: Dict[str, Any], force: bool) -> None:
    step_id = "02_copy_blackfong_assets"
    if (not force) and is_completed(state, target=ctx.target, step_id=step_id):
        logger.info("[%s] skip %s", ctx.target, step_id)
        return

    rootfs = ctx.rootfs_dir
    repo_root = Path(__file__).resolve().parents[1]

    # Copy this repo into the live rootfs so the installer can run.
    dst = rootfs / "opt/blackfong/installer"
    if dst.exists() and force and not ctx.dry_run:
        run_cmd(["rm", "-rf", str(dst)], dry_run=ctx.dry_run)

    copy_tree(str(repo_root), str(dst), dry_run=ctx.dry_run)

    # Apply system assets (systemd/udev/sudoers)
    copy_tree(str(repo_root / "assets/systemd"), str(rootfs / "etc/systemd/system"), dry_run=ctx.dry_run)
    copy_tree(str(repo_root / "assets/udev"), str(rootfs / "etc/udev/rules.d"), dry_run=ctx.dry_run)

    # Mark as live environment and enable the live installer service
    if not ctx.dry_run:
        (rootfs / "etc/blackfong-live").parent.mkdir(parents=True, exist_ok=True)
        (rootfs / "etc/blackfong-live").write_text("1\n", encoding="utf-8")

    run_cmd(["mount", "--bind", "/dev", str(rootfs / "dev")], dry_run=ctx.dry_run)
    run_cmd(["mount", "--bind", "/proc", str(rootfs / "proc")], dry_run=ctx.dry_run)
    run_cmd(["mount", "--bind", "/sys", str(rootfs / "sys")], dry_run=ctx.dry_run)
    try:
        run_cmd(
            [
                "chroot",
                str(rootfs),
                "systemctl",
                "enable",
                "blackfong-installer-live.service",
            ],
            dry_run=ctx.dry_run,
        )
    finally:
        run_cmd(["umount", "-lf", str(rootfs / "sys")], check=False, dry_run=ctx.dry_run)
        run_cmd(["umount", "-lf", str(rootfs / "proc")], check=False, dry_run=ctx.dry_run)
        run_cmd(["umount", "-lf", str(rootfs / "dev")], check=False, dry_run=ctx.dry_run)

    mark_completed(state, target=ctx.target, step_id=step_id)


def step_03_configure_boot(*, ctx: BuildCtx, state: Dict[str, Any], force: bool) -> None:
    step_id = "03_configure_boot"
    if (not force) and is_completed(state, target=ctx.target, step_id=step_id):
        logger.info("[%s] skip %s", ctx.target, step_id)
        return

    rootfs = ctx.rootfs_dir

    # Install kernel/initramfs inside live rootfs so we can copy them into ISO/IMG.
    run_cmd(["mount", "--bind", "/dev", str(rootfs / "dev")], dry_run=ctx.dry_run)
    run_cmd(["mount", "--bind", "/proc", str(rootfs / "proc")], dry_run=ctx.dry_run)
    run_cmd(["mount", "--bind", "/sys", str(rootfs / "sys")], dry_run=ctx.dry_run)

    try:
        run_cmd(["chroot", str(rootfs), "apt-get", "update"], dry_run=ctx.dry_run)

        # kernel package from config
        kernel_pkg = (((ctx.cfg.raw.get("arch") or {}).get(ctx.target)) or {}).get("kernel_package")
        if not kernel_pkg:
            raise RuntimeError(f"No kernel_package configured for {ctx.target}")

        extra = (((ctx.cfg.raw.get("arch") or {}).get(ctx.target)) or {}).get("extra_packages") or []

        run_cmd(
            [
                "chroot",
                str(rootfs),
                "apt-get",
                "install",
                "-y",
                "--no-install-recommends",
                kernel_pkg,
                "initramfs-tools",
                *list(extra),
            ],
            dry_run=ctx.dry_run,
        )
    finally:
        run_cmd(["umount", "-lf", str(rootfs / "sys")], check=False, dry_run=ctx.dry_run)
        run_cmd(["umount", "-lf", str(rootfs / "proc")], check=False, dry_run=ctx.dry_run)
        run_cmd(["umount", "-lf", str(rootfs / "dev")], check=False, dry_run=ctx.dry_run)

    mark_completed(state, target=ctx.target, step_id=step_id)


def step_04_integrate_offline_repo(*, ctx: BuildCtx, state: Dict[str, Any], force: bool) -> None:
    step_id = "04_integrate_offline_repo"
    if (not force) and is_completed(state, target=ctx.target, step_id=step_id):
        logger.info("[%s] skip %s", ctx.target, step_id)
        return

    rootfs = ctx.rootfs_dir

    # Build a structured APT repo from a flat folder of .deb files.
    built_repo = ctx.work_target_dir / "apt-repo-built"
    if built_repo.exists() and force and not ctx.dry_run:
        run_cmd(["rm", "-rf", str(built_repo)], dry_run=ctx.dry_run)

    build_file_repo_from_debs(
        debs_dir=ctx.cfg.offline_repo_path,
        out_repo_dir=str(built_repo),
        suite=ctx.cfg.offline_repo_suite,
        component=ctx.cfg.offline_repo_component,
        arch=ctx.target,
        dry_run=ctx.dry_run,
    )

    if ctx.dry_run:
        logger.info(
            "[%s] would copy built repo -> %s and write blackfong.list",
            ctx.target,
            str(rootfs / ctx.cfg.offline_repo_live_path.lstrip("/")),
        )
        mark_completed(state, target=ctx.target, step_id=step_id)
        return

    # Copy built repo into the live rootfs
    offline_repo_dst = rootfs / ctx.cfg.offline_repo_live_path.lstrip("/")
    if offline_repo_dst.exists() and force and not ctx.dry_run:
        run_cmd(["rm", "-rf", str(offline_repo_dst)], dry_run=ctx.dry_run)
    copy_tree(str(built_repo), str(offline_repo_dst), dry_run=ctx.dry_run)

    # Configure apt in live rootfs
    list_dir = rootfs / "etc/apt/sources.list.d"
    list_dir.mkdir(parents=True, exist_ok=True)
    line = (
        f"deb [trusted=yes] file:{ctx.cfg.offline_repo_live_path} "
        f"{ctx.cfg.offline_repo_suite} {ctx.cfg.offline_repo_component}\n"
    )
    if not ctx.dry_run:
        (list_dir / "blackfong.list").write_text(line, encoding="utf-8")

    mark_completed(state, target=ctx.target, step_id=step_id)


def step_05_optional_network_config(*, ctx: BuildCtx, state: Dict[str, Any], force: bool) -> None:
    step_id = "05_optional_network_config"
    if (not force) and is_completed(state, target=ctx.target, step_id=step_id):
        logger.info("[%s] skip %s", ctx.target, step_id)
        return

    rootfs = ctx.rootfs_dir
    run_cmd(["mount", "--bind", "/dev", str(rootfs / "dev")], dry_run=ctx.dry_run)
    run_cmd(["mount", "--bind", "/proc", str(rootfs / "proc")], dry_run=ctx.dry_run)
    run_cmd(["mount", "--bind", "/sys", str(rootfs / "sys")], dry_run=ctx.dry_run)

    try:
        run_cmd(["chroot", str(rootfs), "apt-get", "update"], dry_run=ctx.dry_run)
        run_cmd(
            [
                "chroot",
                str(rootfs),
                "apt-get",
                "install",
                "-y",
                "--no-install-recommends",
                "network-manager",
                "wget",
            ],
            dry_run=ctx.dry_run,
        )
    finally:
        run_cmd(["umount", "-lf", str(rootfs / "sys")], check=False, dry_run=ctx.dry_run)
        run_cmd(["umount", "-lf", str(rootfs / "proc")], check=False, dry_run=ctx.dry_run)
        run_cmd(["umount", "-lf", str(rootfs / "dev")], check=False, dry_run=ctx.dry_run)

    mark_completed(state, target=ctx.target, step_id=step_id)


def step_06_create_artifact(*, ctx: BuildCtx, state: Dict[str, Any], force: bool) -> None:
    step_id = "06_create_artifact"
    if (not force) and is_completed(state, target=ctx.target, step_id=step_id):
        logger.info("[%s] skip %s", ctx.target, step_id)
        return

    rootfs = ctx.rootfs_dir
    out_dir = Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)

    if ctx.target == "amd64":
        # Minimal ISO structure: squashfs + kernel/initrd copied from rootfs /boot
        iso_dir = ctx.iso_dir
        if iso_dir.exists() and force and not ctx.dry_run:
            run_cmd(["rm", "-rf", str(iso_dir)], dry_run=ctx.dry_run)
        (iso_dir / "live").mkdir(parents=True, exist_ok=True)
        (iso_dir / "boot").mkdir(parents=True, exist_ok=True)
        (iso_dir / "boot/grub").mkdir(parents=True, exist_ok=True)

        squash = iso_dir / "live/filesystem.squashfs"
        run_cmd(["mksquashfs", str(rootfs), str(squash), "-e", "boot"], dry_run=ctx.dry_run)

        # Copy kernel/initrd (best-effort: pick newest)
        boot_src = rootfs / "boot"
        vmlinuz = sorted(boot_src.glob("vmlinuz-*"))[-1]
        initrd = sorted(boot_src.glob("initrd.img-*"))[-1]
        if not ctx.dry_run:
            run_cmd(["cp", "-a", str(vmlinuz), str(iso_dir / "live/vmlinuz")], dry_run=ctx.dry_run)
            run_cmd(["cp", "-a", str(initrd), str(iso_dir / "live/initrd")], dry_run=ctx.dry_run)

        # GRUB config for ISO (boot=live uses live-boot inside the squashfs)
        grub_cfg = (
            "set default=0\n"
            "set timeout=5\n\n"
            "menuentry 'Blackfong Installer (Live)' {\n"
            "  search --set=root --file /live/filesystem.squashfs\n"
            "  linux /live/vmlinuz boot=live live-media-path=/live quiet\n"
            "  initrd /live/initrd\n"
            "}\n"
        )
        if not ctx.dry_run:
            (iso_dir / "boot/grub/grub.cfg").write_text(grub_cfg, encoding="utf-8")

        # Build ISO using grub-mkrescue (requires grub tooling + xorriso)
        iso_path = Path((ctx.cfg.raw.get("outputs") or {}).get("amd64_iso") or "output/blackfong-installer-amd64.iso")
        run_cmd(["grub-mkrescue", "-o", str(iso_path), str(iso_dir)], dry_run=ctx.dry_run)
    else:
        # IMG build is more involved; this step implements a generic extlinux/U-Boot layout.
        img_path = Path((ctx.cfg.raw.get("outputs") or {}).get(f"{ctx.target}_img") or f"output/blackfong-installer-{ctx.target}.img")
        # Placeholder: real implementation will partition a sparse file, loop-mount, copy rootfs.
        # We keep the pipeline modular; the IMG builder will be extended per-device (Pi/uConsole) with firmware/DTBs.
        if not ctx.dry_run:
            img_path.write_text(
                "IMG build pipeline not yet fully implemented for this arch in this repo snapshot.\n",
                encoding="utf-8",
            )

    mark_completed(state, target=ctx.target, step_id=step_id)


def step_07_verify(*, ctx: BuildCtx, state: Dict[str, Any], force: bool) -> None:
    step_id = "07_verify"
    if (not force) and is_completed(state, target=ctx.target, step_id=step_id):
        logger.info("[%s] skip %s", ctx.target, step_id)
        return

    outputs = ctx.cfg.raw.get("outputs") or {}
    if ctx.target == "amd64":
        iso_path = Path(outputs.get("amd64_iso") or "output/blackfong-installer-amd64.iso")
        if not iso_path.exists() and not ctx.dry_run:
            raise RuntimeError(f"Missing ISO output: {iso_path}")
    else:
        img_key = f"{ctx.target}_img"
        img_path = Path(outputs.get(img_key) or f"output/blackfong-installer-{ctx.target}.img")
        if not img_path.exists() and not ctx.dry_run:
            raise RuntimeError(f"Missing IMG output: {img_path}")

    mark_completed(state, target=ctx.target, step_id=step_id)


def step_08_package_outputs(*, ctx: BuildCtx, state: Dict[str, Any], force: bool) -> None:
    step_id = "08_package_outputs"
    if (not force) and is_completed(state, target=ctx.target, step_id=step_id):
        logger.info("[%s] skip %s", ctx.target, step_id)
        return

    out_dir = Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write SHA256SUMS for all outputs
    sums_path = out_dir / "SHA256SUMS"
    if not ctx.dry_run:
        lines = []
        for p in sorted(out_dir.glob("blackfong-installer-*")):
            if p.is_file():
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                lines.append(f"{h}  {p.name}")
        sums_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    mark_completed(state, target=ctx.target, step_id=step_id)


ALL_STEPS = [
    step_00_initialize,
    step_01_prepare_live_rootfs,
    step_02_copy_blackfong_assets,
    step_03_configure_boot,
    step_04_integrate_offline_repo,
    step_05_optional_network_config,
    step_06_create_artifact,
    step_07_verify,
    step_08_package_outputs,
]
