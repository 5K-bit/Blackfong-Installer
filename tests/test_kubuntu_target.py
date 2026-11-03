"""The installed system must be Kubuntu 24.04 LTS + KDE Plasma, never XFCE.

Steps run in dry-run mode; every command the installer would execute is logged by
lib/command.run_cmd as 'CMD ...', which these tests read back.
"""
import logging
from pathlib import Path

import pytest

from blackfong_installer.lib import distro
from blackfong_installer.state_store import ensure_defaults
from blackfong_installer.steps.step_30_install_kernel import InstallKernelStep
from blackfong_installer.steps.step_40_install_rootfs import InstallRootFSStep
from blackfong_installer.steps.step_60_install_desktop import InstallDesktopStep
from blackfong_installer.steps.step_80_post_install_checks import PostInstallChecksStep

ROOT = Path(__file__).resolve().parents[1]


def _state(tmp_path, **cfg):
    state = ensure_defaults({})
    state["config"].update(dry_run=True, **cfg)
    state["hardware"] = {"arch": "amd64", "firmware": "efi"}
    state["execution"]["mounts"] = {"target_root": str(tmp_path / "target"), "root_part": "/dev/null"}
    return state


def _cmds(caplog):
    return [r.getMessage()[4:] for r in caplog.records if r.getMessage().startswith("CMD ")]


def test_defaults_are_kubuntu_on_ubuntu_noble():
    cfg = ensure_defaults({})["config"]
    assert cfg["desktop_base"] == "kubuntu"
    assert cfg["target_suite"] == "noble"
    assert "archive.ubuntu.com" in cfg["target_mirror"]
    assert "debian_suite" not in cfg and "debian_mirror" not in cfg


def test_desktop_step_installs_kubuntu_with_sddm_and_no_xfce(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    InstallDesktopStep().run(_state(tmp_path, code_warden_enabled=True))
    text = "\n".join(_cmds(caplog))
    for pkg in ("kubuntu-desktop", "sddm", "plasma-nm", "pipewire"):
        assert pkg in text
    assert "debconf-set-selections" in text
    assert "DEBIAN_FRONTEND=noninteractive" in text
    assert "set-default graphical.target" in text
    for forbidden in ("xfce", "lightdm", "network-manager-gnome", "xubuntu"):
        assert forbidden not in text


@pytest.mark.parametrize("legacy", ["xubuntu", "xfce", "xfce4"])
def test_xfce_is_refused_not_silently_replaced(tmp_path, legacy):
    with pytest.raises(distro.UnsupportedDesktop, match="not part of the O.B.E.O.S. v1"):
        InstallDesktopStep().run(_state(tmp_path, desktop_base=legacy))


def test_unknown_desktop_is_refused(tmp_path):
    with pytest.raises(distro.UnsupportedDesktop, match="not supported"):
        InstallDesktopStep().run(_state(tmp_path, desktop_base="gnome"))


@pytest.mark.parametrize("alias", ["kubuntu", "KDE", "plasma"])
def test_kde_aliases_accepted(alias):
    assert distro.normalize_desktop_base(alias) == "kubuntu"


def test_rootfs_bootstraps_ubuntu_noble_with_universe(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    InstallRootFSStep().run(_state(tmp_path))
    boot = next(c for c in _cmds(caplog) if c.startswith("debootstrap"))
    assert "noble" in boot
    assert "archive.ubuntu.com/ubuntu" in boot
    assert "--components=main,restricted,universe" in boot
    assert "deb.debian.org" not in boot and "bookworm" not in boot


def test_kernel_is_ubuntu_generic(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    InstallKernelStep().run(_state(tmp_path))
    text = "\n".join(_cmds(caplog))
    assert "linux-image-generic" in text and "linux-image-amd64" not in text


def test_armhf_is_unsupported_on_the_kubuntu_path(tmp_path):
    state = _state(tmp_path)
    state["hardware"]["arch"] = "armhf"
    with pytest.raises(RuntimeError, match="Unsupported arch"):
        InstallKernelStep().run(state)


def test_sources_include_updates_and_security_pockets():
    text = distro.sources_list("noble", distro.UBUNTU_MIRROR, distro.UBUNTU_SECURITY_MIRROR, ports=False)
    assert "noble-updates" in text and "noble-security" in text and "universe" in text
    assert "security.ubuntu.com" in text


def test_debootstrap_falls_back_to_generic_ubuntu_script(tmp_path):
    (tmp_path / "gutsy").write_text("")
    assert distro.debootstrap_script("noble", str(tmp_path)) == str(tmp_path / "gutsy")
    (tmp_path / "noble").write_text("")
    assert distro.debootstrap_script("noble", str(tmp_path)) is None


def test_post_install_check_rejects_xfce_and_accepts_plasma(tmp_path):
    for rel in ("etc", "boot", "usr/bin", "usr/sbin"):
        (tmp_path / rel).mkdir(parents=True)
    state = _state(tmp_path)
    state["config"]["dry_run"] = False
    state["execution"]["mounts"]["target_root"] = str(tmp_path)
    with pytest.raises(RuntimeError, match="KDE Plasma"):
        PostInstallChecksStep().run(state)
    (tmp_path / "usr/bin/startplasma-wayland").write_text("")
    (tmp_path / "usr/bin/sddm").write_text("")
    PostInstallChecksStep().run(state)
    (tmp_path / "usr/sbin/lightdm").write_text("")
    with pytest.raises(RuntimeError, match="XFCE is not part"):
        PostInstallChecksStep().run(state)


def test_no_xfce_in_the_install_path():
    """Guard against XFCE creeping back into the code that actually installs the target."""
    for rel in ("blackfong_installer/steps", "blackfong_installer/lib", "manifests"):
        for path in (ROOT / rel).rglob("*"):
            if path.suffix in {".py", ".yaml"} and path.name not in {"distro.py", "step_80_post_install_checks.py"}:
                text = path.read_text(encoding="utf-8").lower()
                assert "task-xfce" not in text and "lightdm" not in text, path
