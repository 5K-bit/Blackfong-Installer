#!/usr/bin/env bash
set -euo pipefail

# Build an amd64 EFI-bootable installer ISO.
# This is a project automation script; it requires build deps:
#   debootstrap xorriso grub-efi-amd64-bin mtools squashfs-tools
# and a prepared live root containing this repo's installer.

echo "Not yet wired to a full live-build pipeline."
echo "Next steps for completion:"
echo "- Create a live rootfs (debootstrap + packages + this repo)"
echo "- Produce kernel+initrd for the live environment"
echo "- Assemble EFI boot image and ISO filesystem with xorriso"
exit 1
