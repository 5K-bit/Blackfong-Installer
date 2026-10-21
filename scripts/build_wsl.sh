#!/usr/bin/env bash
# One-shot, re-runnable ISO build for WSL2 / Debian / Ubuntu.
#
#   scripts/build_wsl.sh            build (or resume) the amd64 ISO
#   scripts/build_wsl.sh --clean    wipe build/ and output/ first (safe: unmounts leftovers)
#   scripts/build_wsl.sh --no-copy  do not copy the ISO to the Windows Downloads folder
#
# Run it from a clone that lives on the Linux filesystem (e.g. ~/Blackfong-Installer),
# NOT under /mnt/c: debootstrap needs real Linux permissions and device nodes.
set -euo pipefail
cd "$(dirname "$0")/.."

clean=0; copy=1
for a in "$@"; do
  case "$a" in
    --clean) clean=1 ;;
    --no-copy) copy=0 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo"
ROOT="$PWD"

case "$ROOT" in
  /mnt/*) echo "ERROR: $ROOT is on the Windows drive. Clone into your Linux home (cd ~) and retry." >&2; exit 1 ;;
esac

# --- host tools -------------------------------------------------------------
pkgs=(debootstrap debian-archive-keyring squashfs-tools xorriso grub-efi-amd64-bin grub-pc-bin
      mtools dpkg-dev apt-utils qemu-system-x86 git python3-yaml)
missing=0
for c in debootstrap mksquashfs xorriso grub-mkrescue mformat dpkg-scanpackages apt-ftparchive git; do
  command -v "$c" >/dev/null 2>&1 || missing=1
done
python3 -c 'import yaml' 2>/dev/null || missing=1
if [ "$missing" -eq 1 ]; then
  echo ">> installing build dependencies"
  $SUDO apt-get update
  $SUDO apt-get install -y "${pkgs[@]}"
fi
[ -e /usr/share/debootstrap/scripts/bookworm ] || {
  echo "ERROR: this debootstrap has no 'bookworm' script; update your distro's debootstrap." >&2; exit 1; }

# --- leftover bind mounts from a crashed/interrupted build ---------------------
# Never delete a tree while /dev, /proc or /sys are still bind-mounted into it.
if mount | grep -q " $ROOT/build/work"; then
  echo ">> unmounting leftovers from an earlier build"
  mount | awk -v p="$ROOT/build/work" 'index($3, p) == 1 {print $3}' | sort -r |
    while read -r m; do $SUDO umount -lf "$m" || true; done
fi
if mount | grep -q " $ROOT/build/work"; then
  echo "ERROR: build/work still has active mounts; refusing to continue. Run 'wsl --shutdown' and retry." >&2
  exit 1
fi

if [ "$clean" -eq 1 ]; then
  echo ">> cleaning build/ and output/"
  $SUDO rm -rf build output
fi

# --- build ---------------------------------------------------------------------
bash scripts/preflight.sh
mkdir -p logs
echo ">> building (30-60 min; log: logs/blackfong-build.log)"
$SUDO python3 -m blackfong_installer.build --target amd64

# --- verify ----------------------------------------------------------------------
iso=output/blackfong-installer-amd64.iso
[ -f "$iso" ] || { echo "ERROR: $iso was not produced" >&2; exit 1; }
(cd output && sha256sum -c SHA256SUMS)
xorriso -indev "$iso" -report_el_torito plain 2>/dev/null | grep -q UEFI \
  || { echo "ERROR: ISO has no UEFI boot entry" >&2; exit 1; }
echo ">> OK: $ROOT/$iso ($(du -h "$iso" | cut -f1)), UEFI boot entry present"

# --- hand the ISO to Windows ----------------------------------------------------------
if [ "$copy" -eq 1 ] && command -v cmd.exe >/dev/null 2>&1; then
  win=$(cmd.exe /c "echo %USERPROFILE%" 2>/dev/null | tr -d '\r' || true)
  if [ -n "$win" ] && dl="$(wslpath "$win" 2>/dev/null)/Downloads" && [ -d "$dl" ]; then
    cp -v "$iso" "$dl"/
    echo ">> copied to ${win}\\Downloads\\$(basename "$iso")"
  fi
fi
