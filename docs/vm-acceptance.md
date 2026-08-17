# Kubuntu/Plasma VM Acceptance

Installer PR #7 is not merge-ready until a fresh UEFI VM installation proves the shipping path.

Required evidence:

1. Build the amd64 installer artifact successfully.
2. Boot it in a UEFI VM.
3. Complete install to a blank virtual disk.
4. Reboot from the installed disk with installer media detached.
5. Confirm Ubuntu 24.04 LTS / noble userspace.
6. Confirm KDE Plasma and SDDM are installed and usable.
7. Confirm XFCE/Xubuntu packages are not the shipping desktop/session.
8. Confirm networking, systemd, sudo and SSH baseline services.
9. Start the OBEOS/Blackfong workspace path and record health evidence.
10. Record artifact hash, VM configuration, result, and failing logs if any.

The GitHub static workflow validates source doctrine but does not substitute for this VM gate.
