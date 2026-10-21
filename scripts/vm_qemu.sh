#!/usr/bin/env bash
# Test the installer ISO in a throw-away UEFI VM with QEMU (Linux or WSL2). Re-runnable.
#
#   scripts/vm_qemu.sh install [ISO]   boot the ISO and install onto a fresh virtual disk
#   scripts/vm_qemu.sh boot            boot the installed virtual disk (no ISO)
#   scripts/vm_qemu.sh reset           delete the virtual disk + firmware settings
#
# Options (env or flags):  --dry-run   print the QEMU command only
#                          DISK_GB=40  MEM_MB=4096  CPUS=4  VMDIR=~/.cache/blackfong-vm
#
# Display: a window if a graphical session exists (WSLg / desktop), otherwise VNC on
# 127.0.0.1:5900. Without /dev/kvm QEMU is software-emulated: it works but is SLOW
# (a full install can take hours). For speed use VirtualBox on Windows: scripts/vm_virtualbox.ps1
set -euo pipefail

VMDIR="${VMDIR:-$HOME/.cache/blackfong-vm}"
DISK_GB="${DISK_GB:-40}"; MEM_MB="${MEM_MB:-4096}"; CPUS="${CPUS:-4}"
DISK="$VMDIR/disk.qcow2"; VARS="$VMDIR/OVMF_VARS.fd"

dry=0; args=()
for a in "$@"; do [ "$a" = "--dry-run" ] && dry=1 || args+=("$a"); done
cmd="${args[0]:-}"; iso="${args[1]:-}"

find_ovmf() {
  local code vars
  for pair in "/usr/share/OVMF/OVMF_CODE_4M.fd:/usr/share/OVMF/OVMF_VARS_4M.fd" \
              "/usr/share/OVMF/OVMF_CODE.fd:/usr/share/OVMF/OVMF_VARS.fd" \
              "/usr/share/edk2/x64/OVMF_CODE.4m.fd:/usr/share/edk2/x64/OVMF_VARS.4m.fd"; do
    code="${pair%%:*}"; vars="${pair##*:}"
    if [ -f "$code" ] && [ -f "$vars" ]; then OVMF_CODE="$code"; OVMF_VARS_TEMPLATE="$vars"; return 0; fi
  done
  echo "ERROR: OVMF firmware not found. Install it:  sudo apt install ovmf" >&2; return 1
}

usage() { sed -n '2,13p' "$0"; exit "${1:-0}"; }

case "$cmd" in
  install|boot|reset) ;;
  -h|--help|"") usage 0 ;;
  *) echo "unknown command: $cmd" >&2; usage 2 ;;
esac

if [ "$cmd" = reset ]; then rm -rf "$VMDIR"; echo "removed $VMDIR"; exit 0; fi

command -v qemu-system-x86_64 >/dev/null || { echo "ERROR: install QEMU:  sudo apt install qemu-system-x86 qemu-utils" >&2; exit 1; }
find_ovmf
mkdir -p "$VMDIR"
[ -f "$DISK" ] || { [ "$dry" -eq 1 ] || qemu-img create -q -f qcow2 "$DISK" "${DISK_GB}G"; }
# Fresh firmware settings every run: a new machine has no boot entry for the new disk, and a stale
# one (e.g. pointing at the USB/ISO) can drop you into the UEFI shell instead of the installed OS.
[ "$dry" -eq 1 ] || cp "$OVMF_VARS_TEMPLATE" "$VARS"

q=(qemu-system-x86_64 -machine q35 -smp "$CPUS" -m "$MEM_MB"
   -drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE"
   -drive "if=pflash,format=raw,file=$VARS"
   -drive "if=virtio,file=$DISK,format=qcow2"
   -netdev user,id=n0 -device virtio-net-pci,netdev=n0)

if [ -w /dev/kvm ] 2>/dev/null; then q+=(-enable-kvm -cpu host); else
  echo "NOTE: no /dev/kvm - using slow software emulation." >&2; q+=(-cpu max); fi

if [ "$cmd" = install ]; then
  if [ -z "$iso" ]; then iso="$(ls -t output/blackfong-installer-*.iso 2>/dev/null | head -1 || true)"; fi
  [ -n "$iso" ] && [ -f "$iso" ] || { echo "ERROR: give the ISO path: $0 install path/to.iso" >&2; exit 1; }
  # Attach as a USB stick: that is how it will be used on real hardware (and tests the
  # wizard's 'hide the installer media' logic).
  q+=(-drive "if=none,id=iso,file=$iso,format=raw,readonly=on" -device qemu-xhci
      -device usb-storage,drive=iso,bootindex=0)
fi

if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then q+=(-display gtk)
else q+=(-vnc 127.0.0.1:0); echo "No graphical session: connect a VNC viewer to 127.0.0.1:5900" >&2; fi

if [ "$dry" -eq 1 ]; then printf '%q ' "${q[@]}"; echo; exit 0; fi
exec "${q[@]}"
