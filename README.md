## Blackfong OS Installer Documentation

**Version**: vNext 1.0

### Purpose
Provide a unified, hardware-adaptive installer for Blackfong OS targeting **ARM64**, **ARM32 (legacy)**, and **x86_64** systems including Raspberry Pi, uConsole, laptops/PCs, and Steam Deck.

### Scope
Supports a terminal-first desktop, system-wide DAISE, AI/ML tooling, media playback, accessories, and hardware detection.

---

## 1. Installer Goals
- **Multi-architecture**: Deploy Blackfong OS on ARM64/ARM32/x86_64.
- **Hardware adaptive**: Detect hardware and install compatible kernel, drivers, and feature sets.
- **System configuration**: Configure system-wide DAISE, device access, networking, and optional firewall.
- **Single-user system**: No additional users can be created.
- **Offline + online**: Supports offline (USB/SD/ISO) and online installation.
- **Flexible UI**: Text-based (CLI) and optional graphical (GUI).
- **Modular & future-proof**: Hardware features auto-enable only when present.

---

## 2. Supported Architectures & Devices

| Target device | Architecture | Boot method | Notes |
|---|---:|---|---|
| Raspberry Pi 3/4/5 | ARM64 | U-Boot | Full feature support |
| uConsole CM4/CM5 | ARM64 | U-Boot | Same as Pi |
| Legacy Pi (optional) | ARM32 | U-Boot | Experimental |
| Laptops / PCs | x86_64 | EFI | Full feature support |
| Steam Deck | x86_64 | EFI | Default profile compatible |
| SBCs (general) | ARM64 / ARM32 | U-Boot | Experimental |

---

## 3. Installer Modes
- **Text/CLI mode**: Always available; universal fallback.
- **Graphical mode**: Used if graphics drivers are available; network optional.

### Installation sources
- **Offline installation**: All packages included in media.
- **Online installation**: Additional packages fetched via `wget` or the package manager.

---

## 4. Installation Workflow

### Step 0 — Boot
1. Boot from installation media (USB, SD, ISO).
2. Load a temporary live environment (initramfs).
3. Detect firmware type: **U-Boot** or **EFI**.

### Step 1 — Hardware Detection
Automatically detect and log:

| Component | Detection method | Installer action |
|---|---|---|
| CPU | `/proc/cpuinfo` | Select kernel & architecture-specific packages |
| RAM / Storage | system inspection | Partition sizing & swap setup |
| GPU / Graphics | `lspci`, DRM | Configure Wayland, enable acceleration if supported |
| Displays | EDID / DRM | Confirm detection; layout deferred post-install |
| WiFi | `lspci` / `lsusb` / `iw` | NetworkManager configuration |
| Bluetooth | `hcitool` / `lsusb` | Enable BLE accessories support |
| LoRa | SPI / USB probe | Enable only if detected |
| Haptics | BLE / USB HID | Enable only if detected |
| Audio / Mic | ALSA / PipeWire | Enable system audio & DAISE audio input |
| Camera | V4L2 / libcamera | Enable DAISE optional input |

### Step 2 — Partition & Filesystem
- **Auto-partition**: root (`/`) + optional swap.
- **Filesystem**: `ext4` (default).
- **Partition table**: **GPT required**.
- **Advanced option**: custom layout (manual).

### Step 3 — Kernel & Base System
- Select architecture-appropriate kernel:
  - **ARM64** → `linux-image-arm64`
  - **ARM32** → `linux-image-armhf`
  - **x86_64** → `linux-image-amd64`
- Install minimal root filesystem (Debian-based).
- Include core packages: `systemd`, `coreutils`, Blackfong services.

### Step 4 — Core Service Configuration
- **Network**: WiFi/Ethernet auto-configurable; offline installation supported.
- **Firewall**: Optional toggle (default: enabled).
- **Device permissions**: Auto-configured for system-wide DAISE (toggleable).
- **DAISE**: Enabled system-wide; no multi-user support.
- **Single-user**: Created with fixed UID; no other users can be created.

### Step 5 — Desktop Environment (BDE)
- Install Wayland compositor + Blackfong shell.
- Terminal-first environment.
- Multi-monitor layouts deferred to post-installation.
- Audio/video drivers installed and configured (PipeWire / PulseAudio).

### Step 6 — Feature Installation
- AI/ML packages (Python, PyTorch, ONNX, etc.).
- Media playback (MP3/MP4 via GStreamer).
- Hardware-specific drivers (enabled only if detected):
  - LoRa
  - Haptics / BLE accessories
  - Camera / mic
- Optional packages fetched online if network is present.

### Step 7 — Post-Install Setup
- Default keyboard shortcuts and hotkeys.
- System checks:
  - Network connectivity
  - Device detection confirmation
  - AI/ML environment verification
- Reboot into installed system.

---

## 5. Installer Options
- **Firewall configuration**: enable / disable.
- **DAISE device access auto-config**: enable / disable.
- **Custom root partition size / layout**: advanced.
- **Extra packages**: optional online fetch.

---

## 6. Installer Outputs
- **Architecture-specific binaries**:
  - `blackfong-installer-amd64.iso`
  - `blackfong-installer-arm64.img`
  - `blackfong-installer-armhf.img` (experimental legacy)
- **Log file**: `/var/log/blackfong-installer.log`
- **Reproducibility**: All detection, decisions, and actions recorded.

---

## 7. Feature Matrix per Hardware

| Feature | ARM64 | ARM32 (legacy) | x86_64 | Notes |
|---|:---:|:---:|:---:|---|
| Terminal | ✔ | ✔ | ✔ | Always |
| DAISE | ✔ | ✔ | ✔ | System-wide |
| Multi-monitor | ✔ | ✔ | ✔ | Layout post-install |
| WiFi | ✔ | ✔ | ✔ | Configured automatically |
| Bluetooth | ✔ | ✔ | ✔ | Haptic & accessory support |
| LoRa | ✔ | ✔ | ✔ | Only if hardware detected |
| Haptics | ✔ | ✔ | ✔ | Optional if hardware detected |
| Audio/Video | ✔ | ✔ | ✔ | PipeWire / GStreamer |
| AI/ML | ✔ | ✔ | ✔ | Installed offline or online |

---

## 8. Installer Logic (for Automation / Cursor AI)

### Core functions
- **`detect_hardware()`** → returns architecture, RAM, storage, GPU, devices
- **`partition_disk()`** → auto or manual layout
- **`install_kernel(arch)`** → selects correct kernel
- **`install_rootfs()`** → minimal system + Blackfong services
- **`configure_services()`** → networking, firewall, DAISE, device permissions
- **`install_desktop()`** → Wayland compositor + BDE shell
- **`install_features()`** → AI/ML, media, accessories
- **`post_install_checks()`** → system verification
- **`log_actions()`** → all steps recorded

### High-level flow
`boot_media → detect_hardware → partition_disk → install_kernel → install_rootfs → configure_services → install_desktop → install_features → post_install_checks → reboot`

### Conditional branching
- **Architecture**
- **Hardware presence**
- **User installer choices**
- **Network availability**

---

## 9. Notes for Automation & Maintainability
- Use modular scripts per step.
- Keep architecture-specific binaries separate, but share installer logic.
- Include clear logging for hardware detection and package-install decisions.
- Offline media must fully support installation.
- GUI installer is optional; fall back to text-only when graphics are unavailable.
- System-wide DAISE is always installed; no multi-user support.
- Hardware features auto-enable only when detected; firewall and device-permission toggles are user-selectable.
