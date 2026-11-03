"""Target distribution for the installed system: Kubuntu 24.04 LTS (KDE Plasma).

This is the single place that names the installed OS. The O.B.E.O.S. v1 session doctrine is
Kubuntu 24.04 LTS + KDE Plasma; XFCE/Xubuntu is not part of the shipping install path.

The live *installer* environment (build_config.yaml `debian:`) is separate tooling and may stay
Debian; it only has to be able to debootstrap the Ubuntu target.
"""

from __future__ import annotations

from pathlib import Path

TARGET_DISTRO = "ubuntu"
TARGET_SUITE = "noble"  # Ubuntu 24.04 LTS
UBUNTU_MIRROR = "http://archive.ubuntu.com/ubuntu"
UBUNTU_PORTS_MIRROR = "http://ports.ubuntu.com/ubuntu-ports"
UBUNTU_SECURITY_MIRROR = "http://security.ubuntu.com/ubuntu"
UBUNTU_COMPONENTS = ("main", "restricted", "universe")

# desktop_base values accepted by the installer.
KUBUNTU_ALIASES = frozenset({"kubuntu", "kde", "plasma", "kde-plasma"})
LEGACY_XFCE_ALIASES = frozenset({"xubuntu", "xfce", "xfce4"})

# Kernel metapackage per architecture on Ubuntu (not Debian's linux-image-amd64).
KERNEL_BY_ARCH = {
    "amd64": "linux-image-generic",
    "arm64": "linux-image-generic",
}

KUBUNTU_PACKAGES = ("kubuntu-desktop", "sddm", "plasma-nm")
DISPLAY_MANAGER = "sddm"
DEBCONF_DISPLAY_MANAGER = "sddm shared/default-x-display-manager select sddm\n"


class UnsupportedDesktop(ValueError):
    pass


def normalize_desktop_base(value: object) -> str:
    """Return the canonical desktop base, or raise. Never silently install a different desktop."""
    name = str(value or "kubuntu").strip().lower()
    if name in KUBUNTU_ALIASES:
        return "kubuntu"
    if name in LEGACY_XFCE_ALIASES:
        raise UnsupportedDesktop(
            f"desktop_base={name!r}: XFCE/Xubuntu is not part of the O.B.E.O.S. v1 shipping path. "
            "Use desktop_base: kubuntu (Kubuntu 24.04 LTS + KDE Plasma)."
        )
    raise UnsupportedDesktop(
        f"desktop_base={name!r} is not supported. Supported: kubuntu (aliases: kde, plasma)."
    )


def default_mirror(arch: str) -> str:
    return UBUNTU_MIRROR if arch == "amd64" else UBUNTU_PORTS_MIRROR


def kernel_package(arch: str) -> str:
    try:
        return KERNEL_BY_ARCH[arch]
    except KeyError:
        raise RuntimeError(
            f"Unsupported arch for the Kubuntu target: {arch!r} (supported: {', '.join(sorted(KERNEL_BY_ARCH))})"
        ) from None


def debootstrap_script(suite: str, scripts_dir: str = "/usr/share/debootstrap/scripts") -> str | None:
    """Explicit debootstrap script for `suite`, or None to let debootstrap find its own.

    A Debian debootstrap older than the Ubuntu release lacks a `noble` script; the generic
    Ubuntu script (`gutsy`) works for it. Returns None when the suite's own script exists.
    """
    base = Path(scripts_dir)
    if (base / suite).exists():
        return None
    generic = base / "gutsy"
    return str(generic) if generic.exists() else None


def sources_list(suite: str, mirror: str, security_mirror: str, *, ports: bool) -> str:
    comps = " ".join(UBUNTU_COMPONENTS)
    security = mirror if ports else security_mirror
    return (
        f"deb {mirror} {suite} {comps}\n"
        f"deb {mirror} {suite}-updates {comps}\n"
        f"deb {security} {suite}-security {comps}\n"
    )
