from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Sequence

from .chroot import chroot_cmd
from .command import run_cmd
from .distro import (
    TARGET_SUITE,
    UBUNTU_COMPONENTS,
    UBUNTU_MIRROR,
    UBUNTU_SECURITY_MIRROR,
    debootstrap_script,
    sources_list,
)

logger = logging.getLogger(__name__)


def debootstrap_rootfs(
    *,
    target_root: str,
    suite: str = TARGET_SUITE,
    mirror: str = UBUNTU_MIRROR,
    arch: str | None = None,
    components: Sequence[str] = UBUNTU_COMPONENTS,
    dry_run: bool = False,
) -> None:
    argv = ["debootstrap"]
    if arch:
        argv += ["--arch", arch]
    if components:
        argv.append(f"--components={','.join(components)}")
    argv += [suite, target_root, mirror]
    script = debootstrap_script(suite)
    if script:
        argv.append(script)
    run_cmd(argv, dry_run=dry_run)


def write_ubuntu_sources(
    target_root: str, *, suite: str, mirror: str, arch: str, dry_run: bool = False
) -> None:
    """Write apt sources with the -updates and -security pockets (debootstrap only writes the base)."""
    text = sources_list(suite, mirror, UBUNTU_SECURITY_MIRROR, ports=(arch != "amd64"))
    logger.info("Writing %s/etc/apt/sources.list for %s", target_root, suite)
    if dry_run:
        return
    path = Path(target_root) / "etc/apt/sources.list"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def apt_update(target_root: str, *, dry_run: bool = False) -> None:
    chroot_cmd(target_root, ["apt-get", "update"], dry_run=dry_run)


def apt_install(
    target_root: str,
    packages: Sequence[str],
    *,
    with_recommends: bool = False,
    dry_run: bool = False,
) -> None:
    if not packages:
        return
    argv = [
        "apt-get",
        "install",
        "-y",
    ]
    if not with_recommends:
        argv.append("--no-install-recommends")
    # noninteractive: a desktop install must never stop on a debconf prompt inside the chroot.
    chroot_cmd(
        target_root,
        ["env", "DEBIAN_FRONTEND=noninteractive", *argv, *packages],
        dry_run=dry_run,
    )


def apt_has_package(target_root: str, package: str, *, dry_run: bool = False) -> bool:
    """Return True if apt knows about a package name in the target root.

    This is useful for optional packages that may only exist in some repos.
    """
    if dry_run:
        # Be permissive in dry-run so planning doesn't fail.
        return True
    r = run_cmd(["chroot", target_root, "apt-cache", "show", package], check=False)
    return r.returncode == 0


def write_sources_list_offline(
    target_root: str,
    repo_path: str,
    *,
    suite: str = TARGET_SUITE,
    component: str = "main",
) -> None:
    """Configure apt to use an on-media repo (file://).

    repo_path must be a path accessible in the live environment and mounted or copied into target.
    """

    p = Path(target_root) / "etc/apt/sources.list.d/blackfong-offline.list"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"deb [trusted=yes] file:{repo_path} {suite} {component}\n", encoding="utf-8")
    logger.info("Configured offline apt repo: %s (%s %s)", repo_path, suite, component)
