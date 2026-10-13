# Build the Blackfong USB installer (x86_64 UEFI, XFCE, hybrid)

Hybrid = the ISO carries the installer plus a snapshot of the O.B.E.O.S. repos;
the target machine needs **internet during install** (Debian packages via debootstrap, pip for O.B.E.O.S.).

## 1. Build the ISO (needs a real Linux host with root — Debian/Ubuntu, or WSL2 Debian)
```bash
sudo apt install debootstrap squashfs-tools xorriso grub-efi-amd64-bin grub-pc-bin mtools \
                 dpkg-dev apt-utils qemu-system-x86 git python3-yaml
git clone https://github.com/5K-bit/Blackfong-Installer && cd Blackfong-Installer
git checkout claude/affectionate-darwin-n1w36m
sudo python3 -m blackfong_installer.build --target amd64      # long: debootstrap + clones the bundle
sha256sum -c output/SHA256SUMS
```
Output: `output/blackfong-installer-amd64.iso` (hybrid, so it can be written raw to a USB).

## 2. Test in a VM first (strongly recommended)
```bash
qemu-system-x86_64 -m 4G -bios /usr/share/ovmf/OVMF.fd -cdrom output/blackfong-installer-amd64.iso \
                   -drive file=test.img,format=raw,if=virtio   # truncate -s 30G test.img
```

## 3. Write the USB (double-check the device — this erases it)
Linux: `sudo dd if=output/blackfong-installer-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync`
Windows: Rufus or balenaEtcher, choose **DD image mode**.

## 4. Install
Boot the target machine from the USB (UEFI, disable Secure Boot). On tty1 the wizard lists disks
(the USB itself is excluded), asks you to retype the device name before erasing anything, then asks
hostname / user / password. It installs Debian + XFCE + the O.B.E.O.S. bundle and reboots.

Installed system: user from the wizard (sudo), O.B.E.O.S. CLI tools in `/opt/obeos/venv` (symlinked
into `/usr/local/bin`), `daise.service` runs the Thoughtglass HUD on `127.0.0.1`.
Night-watch-OS is installed in its own venv (`/opt/obeos/venvs/Night-watch-OS`) because its `pydantic>=2.10` conflicts with the O.B.E.O.S. core's `pydantic==2.6.4`; override with `config.obeos_isolated_components`. The shared venv pins `numpy<2` and `opencv-python<4.12` (`config.obeos_pip_constraints`).
Failed component installs are listed in the state file (`execution.warnings`) and don't abort the OS install.

## Known limits
- Not yet run end-to-end on real hardware or in a VM — treat first run as a test.
- `daise` currently = `blackfong hud` (assumption); change `DAISE_LAUNCHER` in `step_52_install_obeos.py`.
- Secure Boot unsupported; arm64/armhf image builds are still placeholders.
