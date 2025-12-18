#!/usr/bin/env bash
set -euo pipefail

# Build an ARM64 installer disk image for U-Boot devices.
# Requires platform-specific boot assets (DTBs/firmware) for target families.

echo "Not yet wired to a full ARM image pipeline."
echo "Next steps for completion:"
echo "- Create partitioned IMG with boot/root"
echo "- Populate boot assets (U-Boot/extlinux + DTBs)"
echo "- Populate live rootfs with this repo + offline repo"
exit 1
