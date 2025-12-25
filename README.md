## Blackfong OS Installer Documentation

**Version**: vNext 1.0

### Purpose
Provide a unified, hardware-adaptive installer for Blackfong OS targeting **ARM64**, **ARM32 (legacy)**, and **x86_64** systems including Raspberry Pi, uConsole, laptops/PCs, and Steam Deck.

### Scope
Supports a terminal-first desktop (**Blackfong’s Code Warden**), system-wide DAISE, AI/ML tooling, media playback, accessories, and hardware detection **that drives real install decisions**.

---

## 1. Installer Goals
- **Multi-architecture**: Deploy Blackfong OS on ARM64/ARM32/x86_64.
- **Hardware adaptive**: Detect hardware and install compatible kernel, drivers, and feature sets.
- **System configuration**: Configure system-wide DAISE, device access, networking, and optional firewall.
- **Single-user system**: No additional users can be created.
- **Offline + online**: Supports offline (USB/SD/ISO) and online installation.
- **Flexible UI**: Text-based (CLI) and optional graphical (GUI).
- **Modular & future-proof**: Hardware features auto-enable only when present.

### Non-negotiables (project integrity)
- **A rock-solid CLI that never lies**: compute and persist a **plan** (packages/services/features) from state + detection before taking action; dry-run must reflect the same plan.
- **A GUI stub that only wraps core logic**: GUI collects inputs and writes state, but does not change behavior.
- **Identical behavior regardless of interface**: same state + same detection → same actions.
- **If CLI and GUI ever disagree, the project is bToken**.

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
| LoRa | SPI / USB probe | **Opt-in via profile** (never install/enable by default) |
| Haptics | BLE / USB HID | **Opt-in via profile** (never install/enable by default) |
| Audio / Mic | ALSA / PipeWire | Enable system audio & DAISE audio input |
| Camera | V4L2 / libcamera | Enable DAISE optional input |

#### Profile auto-selection (rule engine)
The installer auto-picks a profile using **real identity signals**, and writes the evidence into state:
- **PC vs Steam Deck (amd64)**: DMI (`/sys/class/dmi/id/*`) with Valve/Jupiter/Galileo identifiers.
- **SBC model (arm64)**: device-tree model (`/sys/firmware/devicetree/base/model`).

The selected profile and its confidence are stored under:
- `state['hardware']['profile']`
- `state['hardware']['profile_selection']` (reason + evidence)

Override (hard requirement for edge cases):
- Set `state['config']['profile']` to force a specific profile id (e.g. `amd64-steamdeck`, `arm64-uconsole`).

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

### Step 5 — Desktop Environment (Xubuntu desktop)
- Default boot target is an **XFCE (“Xubuntu-style”) desktop**.
- **Code Warden** remains an optional alternate terminal-first identity (selectable via state config).
- Multi-monitor layouts deferred to post-installation.
- Audio/video drivers installed and configured (PipeWire / PulseAudio).

### Step 6 — Feature Installation
#### AI/ML feature bundles (explicit)
- **`ai_ml_core`**: Python foundation (always safe).
- **`ai_ml_cpu`**: CPU inference/runtime (safe default).
- **`ai_ml_gpu_*`**: GPU accelerators selected strictly from detected GPU vendor (only attempted when `install_source` permits and network is available).

#### Media feature bundles (explicit)
- **`media_core`**: baseline plugins/codecs.
- **`media_full`**: additional plugins/codecs.
- **`media_hwaccel_*`**: GPU-dependent acceleration path selected by vendor when GPU is present.

#### Hardware detection that actually means something (strict rules)
- **Camera detected → camera bundle enabled**
  - If V4L2 nodes exist (e.g. `/dev/video*`), camera bundle may be installed/enabled.
- **No camera → nothing installed, nothing listening**
  - No camera bundle packages installed; no camera services enabled.
- **LoRa / haptics / sensors → opt-in via profile**
  - These are never installed/enabled unless the selected `manifests/profiles/*.yaml` opts in.
- **GPU detected → different AI/media path**
  - GPU presence/vendor selects different AI/ML and media acceleration bundles.

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

## 8. Installer Logic (Concrete Implementation Plan)

This section defines an implementable structure for a modular installer where **CLI and GUI share the same core pipeline**.

### 8.1 Repository / Media Layout (Python-first, proposed)
- **`blackfong_installer/`**: shared core logic (no UI)
  - `main.py`: entrypoint for the pipeline (used by CLI and GUI)
  - `lib/`
    - `log.*`: structured logging to `/var/log/blackfong-installer.log`
    - `env.*`: constants, paths, mount points, feature flags
    - `hwdetect.*`: probes and normalization into a single hardware profile
    - `net.*`: network bring-up, connectivity tests, online/offline decision
    - `storage.*`: disk enumeration, partitioning, formatting, mounting
    - `pkg.*`: offline repo setup + online mirrors + package install wrapper
    - `chroot.*`: helpers to run commands inside target rootfs
  - `steps/` (each step is idempotent; can be resumed)
    - `00_bootstrap_live.*`
    - `10_detect_hardware.*`
    - `20_partition_fs.*`
    - `30_install_kernel.*`
    - `40_install_rootfs.*`
    - `50_configure_services.*`
    - `60_install_desktop.*`
    - `70_install_features.*`
    - `80_post_install_checks.*`
    - `90_finalize_reboot.*`
- **`ui/`**: frontends (thin wrappers)
  - `cli.py`: universal fallback; calls `blackfong_installer.main.run(...)`
  - `gui_stub.py`: optional (Wayland/GTK/Qt); calls the same core pipeline APIs
- **`manifests/`**: package manifests + profiles
  - `base.yaml`: always-installed packages/services
  - `desktop.yaml`: Code Warden desktop identity (terminal-first)
  - `features.yaml`: AI/ML, media, accessories (split into feature groups)
  - `profiles/`
    - `arm64-pi.yaml`, `arm64-uconsole.yaml`, `amd64-pc.yaml`, `amd64-steamdeck.yaml`, `armhf-legacy.yaml`
- **`assets/`**: configs, systemd units, default hotkeys, udev rules, polkit rules

### 8.2 Data Model (single source of truth)
All steps read/write a single JSON (or YAML) state file that is also logged for reproducibility.

- **Installer config** (user choices):
  - `mode`: `cli|gui`
  - `install_source`: `offline|online|hybrid`
  - `firewall_enabled`: `true|false` (default `true`)
  - `daise_device_access_enabled`: `true|false` (default `true`)
  - `partitioning`: `auto|manual`
  - `target_disk`: `/dev/nvme0n1|/dev/sda|/dev/mmcblk0|...`
  - `swap`: `none|auto|size_mb`
  - `hostname`, `locale`, `timezone`, `keyboard_layout`
  - `ssh_enabled`: `true|false` (default `true`)
  - `ssh_authorized_keys`: list of SSH public keys to install for deterministic access

- **Hardware profile** (detected):
  - `arch`: `arm64|armhf|amd64`
  - `firmware`: `uboot|efi`
  - `cpu_model`, `ram_mb`
  - `disks[]`: size, type (nvme/sata/mmc), removable flag
  - `gpu`: vendor/device + driver class (modesetting/amdgpu/nouveau/vc4/…)
  - `net`: ethernet/wifi devices; wifi chipset hint
  - `bt`: present yes/no
  - `audio`, `camera`, `lora`, `haptics`: present yes/no (+ bus: usb/spi/ble)

- **Execution state** (for resume):
  - `current_step`, `completed_steps[]`
  - `mounts`: target root mountpoint, EFI/boot mountpoint
  - `errors[]`: structured error objects with step + command + exit code
  - `plan`: computed “truth” of what will be installed/enabled (must match for CLI and GUI)

### 8.3 Step Responsibilities (what each module must do)
- **`10_detect_hardware`**:
  - Produce `hardware_profile` and write it to the state file
  - Decide a **profile** (e.g. `amd64-steamdeck`) from rules
  - Log all probe outputs (redact secrets)
  - Detect camera/GPU signals that materially change what is installed/enabled
- **`20_partition_fs`**:
  - Enforce **GPT**; create EFI System Partition for EFI targets
  - Create root (`/`) ext4; optional swap
  - Mount target root at a predictable mount point (e.g. `/target`)
- **`30_install_kernel`**:
  - Map `arch → kernel package` (`linux-image-arm64|linux-image-armhf|linux-image-amd64`)
  - Install required firmware/boot tooling based on `firmware` and device profile
- **`40_install_rootfs`**:
  - Bootstrap Debian-based minimal rootfs to `/target`
  - Install Blackfong core services from `manifests/base.yaml`
- **`50_configure_services`**:
  - Configure NetworkManager (offline-safe)
  - Apply firewall toggle (default enabled)
  - Install/enable system-wide DAISE and (optionally) device-permission rules
  - Enforce **single-user policy** (fixed UID) and block other user creation
- **`60_install_desktop`**:
  - Install Code Warden desktop identity + terminal-first defaults
  - Configure PipeWire (or PulseAudio where required) and DRM acceleration if supported
- **`70_install_features`**:
  - Install feature groups based on:
    - `install_source` (offline vs online availability)
    - strict camera gate (no camera → no camera bundle)
    - profile opt-ins (LoRa/haptics/sensors)
    - GPU vendor (AI/media bundle selection)
- **`80_post_install_checks`**:
  - Verify bootloader installed (EFI or U-Boot path)
  - Verify DAISE enabled, audio input available if present
  - Verify basic network connectivity (if hardware present)
  - Verify AI/ML environment (lightweight sanity checks)
- **`90_finalize_reboot`**:
  - Write final summary to log (profile, packages, checks)
  - Unmount, sync, reboot

### 8.4 Package Installation Strategy (offline-first)
- **Offline**: media includes a local package repository; `pkg.*` configures sources to prefer it.
- **Online**: if connectivity is detected, enable online mirrors and fetch optional packages.
- **Hybrid**: install base+desktop from offline media, fetch extras online when available.

### 8.5 Logging & Reproducibility Requirements
- Write to **`/var/log/blackfong-installer.log`** (live env + copied into target).
- Log **every decision** (selected profile, kernel, packages, toggles, detected devices).
- Log **every command** with start/end timestamps and exit code.
- Persist the final **state file** (config + hardware profile + completed steps) for support.

### 8.6 Conditional Branching Rules (minimum set)
- **Architecture**: selects kernel, ABI-specific packages, and output image type.
- **Firmware**: selects EFI vs U-Boot bootloader path and partition layout.
- **Hardware presence**: camera is strictly gated by detection (no camera → no camera bundle/services).
- **Profile opt-ins**: LoRa/haptics/sensors are installed/enabled only when opted-in by profile.
- **Network availability**: controls offline/online package sources and optional extras.
- **User choices**: firewall and DAISE device-permission toggles, partitioning mode.

---

## 9. Notes for Automation & Maintainability
- Use modular scripts per step.
- Keep architecture-specific binaries separate, but share installer logic.
- Include clear logging for hardware detection and package-install decisions.
- Offline media must fully support installation.
- GUI installer is optional; fall back to text-only when graphics are unavailable.
- System-wide DAISE is always installed; no multi-user support.
- Hardware features auto-enable only when detected; firewall and device-permission toggles are user-selectable.

---

## 10. Project Automation (Build + Run)

### Run the installer pipeline (in a live environment)
This project is designed to run from a privileged live environment (installer media) and install onto a target disk.

- **CLI entrypoint**:
  - `python3 -m blackfong_installer --state /var/lib/blackfong-installer/state.json`
- **Key config fields** (in `state['config']`):
  - `target_disk`: required (e.g. `/dev/nvme0n1`, `/dev/sda`, `/dev/mmcblk0`)
  - `install_source`: `offline|online|hybrid`
  - `firewall_enabled`: default `true`
  - `daise_device_access_enabled`: default `true`
  - `dry_run`: `true` logs and plans without destructive commands

---

## 11. Node-first OS defaults (“one node in a larger system”)
Blackfong OS should be controllable by default:
- **Clean networking defaults**: NetworkManager enabled; no “desktop-only” assumptions.
- **Predictable hostname/identity**: default hostname is `blackfong-node` unless overridden in state.
- **Easy SSH access**: SSH enabled by default; recommend injecting `ssh_authorized_keys` via state for deterministic access.
- **Ready to be controlled, not pampered**: automation-friendly defaults and predictable behavior.

### Build installer media artifacts (project automation)
Build scripts live under `scripts/`:
- `scripts/build_installer_media_amd64_efi.sh`
- `scripts/build_installer_media_arm64_img.sh`
- `scripts/build_installer_media_armhf_img.sh`

These scripts document required build dependencies and the remaining assembly steps for generating:
- `blackfong-installer-amd64.iso`
- `blackfong-installer-arm64.img`
- `blackfong-installer-armhf.img` (experimental)

### Build pipeline (state-driven, resumable)
The media builder is implemented as a Python pipeline driven by `build_config.yaml` and tracked in `build/build_state.json`.

- **Config**: `build_config.yaml`
- **State**: `build/build_state.json`
- **Build command**:
  - `python3 -m blackfong_installer.build --config build_config.yaml`
  - Or, for a single target: `python3 -m blackfong_installer.build --target amd64`
- **Dry-run**:
  - `python3 -m blackfong_installer.build --dry-run`

The pipeline mirrors these steps:
`00_initialize → 01_prepare_live_rootfs → 02_copy_blackfong_assets → 03_configure_boot → 04_integrate_offline_repo → 05_optional_network_config → 06_create_artifact → 07_verify → 08_package_outputs`
