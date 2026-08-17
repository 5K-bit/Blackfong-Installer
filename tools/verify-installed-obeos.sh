#!/usr/bin/env bash
set -euo pipefail

failures=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; failures=$((failures + 1)); }
check() { if "$@" >/dev/null 2>&1; then pass "$*"; else fail "$*"; fi; }
package_installed() { dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q 'install ok installed'; }

printf 'OBEOS installed-guest acceptance\n'
printf 'timestamp=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'kernel=%s\n' "$(uname -r)"
printf 'arch=%s\n' "$(dpkg --print-architecture 2>/dev/null || uname -m)"

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  [[ "${ID:-}" == "ubuntu" ]] && pass 'Ubuntu base' || fail "Ubuntu base (ID=${ID:-unknown})"
  [[ "${VERSION_ID:-}" == "24.04" ]] && pass 'Ubuntu 24.04 LTS' || fail "Ubuntu 24.04 LTS (VERSION_ID=${VERSION_ID:-unknown})"
  [[ "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}" == "noble" ]] && pass 'Noble suite' || fail "Noble suite (codename=${UBUNTU_CODENAME:-${VERSION_CODENAME:-unknown}})"
else
  fail '/etc/os-release readable'
fi

for pkg in kubuntu-desktop plasma-workspace sddm network-manager openssh-server sudo; do
  if package_installed "$pkg"; then pass "package:$pkg"; else fail "package:$pkg"; fi
done

for forbidden in xubuntu-desktop task-xfce-desktop lightdm; do
  if package_installed "$forbidden"; then fail "forbidden-package:$forbidden absent"; else pass "forbidden-package:$forbidden absent"; fi
done

if command -v systemctl >/dev/null 2>&1; then
  check systemctl is-enabled NetworkManager
  check systemctl is-enabled ssh
  check systemctl is-enabled sddm
else
  fail 'systemctl available'
fi

if [[ -d /sys/firmware/efi ]]; then pass 'booted in UEFI mode'; else fail 'booted in UEFI mode'; fi

printf 'failures=%d\n' "$failures"
if (( failures > 0 )); then
  exit 1
fi
printf 'RESULT=PASS\n'
