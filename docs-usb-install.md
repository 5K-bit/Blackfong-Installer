# Build and test the Blackfong USB installer (x86_64 UEFI, XFCE, hybrid)

Hybrid = the ISO carries the installer plus a snapshot of the O.B.E.O.S. repos. The machine being
installed needs **internet during install** (Debian packages via debootstrap, then pip for O.B.E.O.S.).
The wizard checks the connection *before* it touches any disk and lets you join Wi-Fi.

## 1. Build the ISO (WSL2 Debian/Ubuntu, or any Debian-based Linux)
```bash
cd ~ && git clone https://github.com/5K-bit/Blackfong-Installer && cd Blackfong-Installer
scripts/build_wsl.sh            # installs deps, builds, verifies, copies the ISO to Windows Downloads
scripts/build_wsl.sh --clean    # wipe build/ first (also unmounts leftovers from a crashed build)
```
Run it from the Linux filesystem (not `/mnt/c`). It takes 30-60 minutes. To keep it running if the
window closes: `nohup scripts/build_wsl.sh > ~/build.out 2>&1 &` then `tail -f ~/build.out`.
If the PC dies mid-build, just run `scripts/build_wsl.sh --clean` again.

## 2. Test in a VM first (re-runnable)
**Windows + VirtualBox** (PowerShell):
```powershell
.\scripts\vm_virtualbox.ps1 -Iso "$env:USERPROFILE\Downloads\blackfong-installer-amd64.iso"
# ...run the wizard in the VM; when it says it finished:
.\scripts\vm_virtualbox.ps1 -EjectIso     # boot the installed system from the virtual disk
.\scripts\vm_virtualbox.ps1 -Recreate -Iso ...   # start over with a blank disk
.\scripts\vm_virtualbox.ps1 -Destroy      # remove the VM
```
**Linux / WSL2 + QEMU** (slow without `/dev/kvm`):
```bash
scripts/vm_qemu.sh install            # boots output/*.iso as a virtual USB stick onto a fresh disk
scripts/vm_qemu.sh boot               # boot the installed disk
scripts/vm_qemu.sh reset              # delete the VM disk
```

## 3. Write the USB (double-check the device: this erases it)
Linux: `sudo dd if=output/blackfong-installer-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync`
Windows: Rufus or balenaEtcher in **DD image mode**.

## 4. Install
Boot the target from the USB (UEFI, Secure Boot off). The wizard (tty1):
1. checks the package mirror is reachable (retry / join Wi-Fi / quit),
2. lists disks (the USB itself is hidden) and makes you retype the device name,
3. asks hostname / user / password, then installs Debian 12 + XFCE + the O.B.E.O.S. bundle and reboots.

Installed system: your user (sudo, single-user policy), O.B.E.O.S. tools in `/opt/obeos/venv`
(linked into `/usr/local/bin`), `daise.service` running the Thoughtglass HUD on `127.0.0.1:8080`.
Night-watch-OS lives in its own venv (`/opt/obeos/venvs/Night-watch-OS`) because its `pydantic>=2.10`
conflicts with the core's `pydantic==2.6.4` (`config.obeos_isolated_components`). The shared venv pins
`numpy<2` and `opencv-python<4.12` (`config.obeos_pip_constraints`). Component install failures are
listed in `/var/lib/blackfong-installer/state.json` (`execution.warnings`) and never abort the OS install.

## Debugging
Build: `logs/blackfong-build.log`. Install: `/var/log/blackfong-installer.log` and
`/var/lib/blackfong-installer/state.json` in the live system. The live kernel also logs to the serial port.

## Known limits
- Verified end to end only on an Ubuntu base (Debian mirrors were blocked where it was tested);
  Debian package names and the XFCE desktop install are the least-tested parts.
- Secure Boot unsupported; arm64/armhf image builds are still placeholders.
