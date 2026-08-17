# OBEOS Installer

The Blackfong Installer is the installation pipeline for the OBEOS desktop target. The v0.9 release candidate is intentionally narrow: **amd64 PCs, Ubuntu 24.04 LTS (Noble), KDE Plasma/Kubuntu, SDDM, and OBEOS as session authority**.

This repository is the installer implementation. OBEOS core remains canonical in `5K-bit/O.B.E.O.S`.

## Shipping contract

| Layer | v0.9 target |
|---|---|
| Architecture | amd64 |
| Base | Ubuntu 24.04 LTS |
| Suite | `noble` |
| Desktop | KDE Plasma / Kubuntu |
| Display manager | SDDM |
| Networking | NetworkManager |
| Audio | PipeWire + WirePlumber |
| Boot | UEFI/GPT |
| Session authority | OBEOS |

XFCE/Xubuntu and Debian/Bookworm inputs are migration history only. The shipping installer rejects incompatible desktop/base selections instead of silently installing a fallback environment.

ARM64/ARM32 support is not part of the v0.9 shipping installer. Those targets can return later behind explicit architecture-specific acceptance gates.

## Design rules

- The installer must never silently substitute a different OS or desktop.
- Installation decisions come from persisted state and detected hardware.
- Dry-run uses the same pipeline and decision rules as execution.
- OBEOS owns the session; Plasma is the managed graphical workspace.
- Code Warden is an optional operator/developer capability inside the OBEOS environment, not a replacement desktop.
- Offline package content must match the target Ubuntu suite.
- Destructive installation requires explicit execution; development and CI should use dry-run/static validation unless a disposable VM is being used.

## Pipeline

The current installer executes these steps in order:

1. Detect hardware.
2. Partition/filesystem preparation.
3. Write fstab.
4. Bootstrap Ubuntu Noble rootfs.
5. Install kernel.
6. Install UEFI bootloader.
7. Configure baseline services.
8. Apply OBEOS assets.
9. Install Kubuntu/Plasma + SDDM.
10. Install selected feature bundles.
11. Run post-install checks.
12. Finalize/reboot.

The rootfs baseline includes `systemd`, `network-manager`, `openssh-server`, `sudo`, `linux-base`, and `initramfs-tools` before the desktop layer is installed.

## CLI

Run from a Linux live environment or disposable VM:

```bash
python -m blackfong_installer --dry-run
```

The installer persists state at:

```text
/var/lib/blackfong-installer/state.json
```

and logs to the configured installer log path.

Useful controls:

```bash
python -m blackfong_installer --dry-run
python -m blackfong_installer --start-at 40_install_rootfs
python -m blackfong_installer --stop-after 60_install_desktop
python -m blackfong_installer --force
```

Do not execute the destructive pipeline against a host that contains data you need. Release acceptance must use a blank virtual disk or dedicated test device.

## Media configuration

`build_config.yaml` is the shipping media contract. For v0.9 it must remain aligned to:

```yaml
ubuntu:
  suite: noble
  mirror: http://archive.ubuntu.com/ubuntu

offline_repo:
  suite: noble

outputs:
  amd64_iso: output/obeos-installer-amd64.iso
```

The amd64 media uses Ubuntu-compatible UEFI packages including GRUB EFI and shim components.

## CI gate

`.github/workflows/kubuntu-plasma-gate.yml` checks the source doctrine on every stabilization change:

- Python compilation succeeds.
- Noble is the configured suite.
- `kubuntu-desktop` is present in the desktop install path.
- SDDM is present.
- the shipping desktop step does not contain the old `task-xfce-desktop` fallback.
- installer unit tests run when present.

A green static workflow is necessary but **does not prove installability**.

## UEFI VM acceptance gate

PR #7 cannot become release-ready until a fresh amd64 UEFI VM proves the complete path.

Required evidence:

1. Build the amd64 installer artifact.
2. Record its SHA-256 hash.
3. Boot the media in a UEFI VM with a blank virtual disk.
4. Complete installation.
5. Detach installer media and boot the installed disk.
6. Confirm Ubuntu 24.04/Noble.
7. Confirm KDE Plasma and SDDM.
8. Confirm XFCE/Xubuntu/LightDM are not the shipping session.
9. Confirm NetworkManager, systemd, sudo, and SSH baseline readiness.
10. Start the OBEOS workspace/runtime path and capture health evidence.

The repository includes `docs/kubuntu-vm-acceptance.md` as the release checklist. The guest-side verifier should be run after first boot and its output retained with the release evidence.

## Relationship to OBEOS v0.9

The installer is one gate in the larger OBEOS Integration & Stabilization matrix. OBEOS itself must separately pass:

- Ubuntu and Windows core tests
- DAISE model-first reasoning regressions
- Thoughtglass regressions
- Telegram and Legion client regressions
- canonical child component tests
- full OBEOS verification
- cloud/Telegram live runtime smoke
- Legion private-path runtime smoke

Only after both the installer VM gate and OBEOS runtime gates pass should the installer and OBEOS stabilization pull requests be promoted for merge/release.
