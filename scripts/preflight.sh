#!/usr/bin/env bash
set -euo pipefail

required=(
  debootstrap
  mksquashfs
  xorriso
  grub-mkrescue
  dpkg-scanpackages
  apt-ftparchive
  qemu-system-x86_64
)

missing=()
for cmd in "${required[@]}"; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    missing+=("${cmd}")
  fi
done

if ((${#missing[@]} > 0)); then
  echo "ERROR: build preflight failed. Missing required tools:" >&2
  for cmd in "${missing[@]}"; do
    echo "  - ${cmd}" >&2
  done
  exit 2
fi

echo "OK: build preflight passed (${#required[@]} tools present)."
