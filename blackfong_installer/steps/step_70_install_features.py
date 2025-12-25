from __future__ import annotations

import logging
from typing import Any, Dict

from ..lib.chroot import mount_chroot_binds, umount_chroot_binds
from ..lib.manifests import load_features_manifest
from ..lib.net import is_online
from ..lib.pkg import apt_has_package, apt_install, apt_update

logger = logging.getLogger(__name__)


class InstallFeaturesStep:
    step_id = "70_install_features"

    def _get_profile_flag(self, state: Dict[str, Any], key: str, default: Any) -> Any:
        profile = state.get("profile") or {}
        features = profile.get("features") or {}
        return features.get(key, default)

    def _select_groups(self, state: Dict[str, Any], *, allow_online: bool) -> list[str]:
        hw = state.get("hardware") or {}
        gpu = hw.get("gpu") or {}
        camera = hw.get("camera") or {}

        groups: list[str] = []

        # Media always gets a minimal baseline.
        groups.append("media_core")

        # AI/ML always gets python baseline; runtime varies by policy.
        groups.append("ai_ml_core")

        # Camera: STRICT auto-gate.
        camera_policy = self._get_profile_flag(state, "camera", "auto")
        if camera_policy == "auto" and bool(camera.get("present", False)):
            groups.append("camera")
        elif camera_policy is True:
            # Even if opted-in explicitly, we still refuse to install listeners without a camera.
            if bool(camera.get("present", False)):
                groups.append("camera")
            else:
                state.setdefault("execution", {}).setdefault("warnings", []).append(
                    {"feature": "camera", "reason": "profile_enabled_but_no_camera_detected"}
                )

        # LoRa / haptics / sensors: OPT-IN via profile.
        for name in ("lora", "haptics", "sensors"):
            if bool(self._get_profile_flag(state, name, False)):
                groups.append(name)

        # Media path: if GPU present, attempt hw accel packages.
        if bool(gpu.get("present", False)):
            vendor = str(gpu.get("vendor") or "unknown").lower()
            if vendor == "intel":
                groups.append("media_hwaccel_intel")
            elif vendor == "amd":
                groups.append("media_hwaccel_amd")
            elif vendor == "nvidia":
                groups.append("media_hwaccel_nvidia")

            # AI/ML GPU path only if online/hybrid allows it (these are heavy / repo-dependent).
            ai_policy = str(self._get_profile_flag(state, "ai_ml", "auto")).lower()
            if allow_online and ai_policy in {"auto", "gpu", "on"}:
                if vendor == "intel":
                    groups.append("ai_ml_gpu_intel")
                elif vendor == "amd":
                    groups.append("ai_ml_gpu_amd")
                elif vendor == "nvidia":
                    groups.append("ai_ml_gpu_nvidia")

        # CPU AI/ML runtime (safe default when online GPU path isn't selected).
        ai_policy = str(self._get_profile_flag(state, "ai_ml", "auto")).lower()
        if ai_policy in {"auto", "cpu", "on"}:
            groups.append("ai_ml_cpu")

        # Full media plugins can be profile-controlled.
        media_policy = str(self._get_profile_flag(state, "media", "auto")).lower()
        if media_policy in {"full", "on"}:
            groups.append("media_full")

        # De-dup while preserving order
        dedup: list[str] = []
        for g in groups:
            if g not in dedup:
                dedup.append(g)
        return dedup

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("config") or {}
        exe = state.get("execution") or {}
        mounts = exe.get("mounts") or {}
        target_root = mounts.get("target_root")
        if not target_root:
            raise RuntimeError("execution.mounts.target_root missing")

        dry_run = bool(cfg.get("dry_run", False))
        src = cfg.get("install_source", "offline")

        online = is_online(dry_run=dry_run)
        state.setdefault("execution", {}).setdefault("decisions", {})["online"] = online

        # Offline-first rule: only attempt online extras if install_source permits and we are online.
        allow_online = src in {"online", "hybrid"} and online

        manifest = load_features_manifest()
        groups_cfg = manifest.get("feature_groups") or {}
        if not isinstance(groups_cfg, dict):
            raise RuntimeError("manifests/features.yaml: feature_groups must be a mapping")

        selected_groups = self._select_groups(state, allow_online=allow_online)
        desired_packages: list[str] = []
        for group in selected_groups:
            group_obj = groups_cfg.get(group) or {}
            pkgs = group_obj.get("packages") or []
            if not isinstance(pkgs, list):
                raise RuntimeError(f"Feature group {group} packages must be a list")
            desired_packages.extend([str(p).strip() for p in pkgs if str(p).strip()])

        mount_chroot_binds(target_root, dry_run=dry_run)
        try:
            apt_update(target_root, dry_run=dry_run)
            # Never fail the installer on repo variance: skip packages not known to apt.
            packages: list[str] = []
            missing: list[str] = []
            for p in desired_packages:
                if apt_has_package(target_root, p, dry_run=dry_run):
                    packages.append(p)
                else:
                    missing.append(p)

            state.setdefault("execution", {}).setdefault("plan", {}).setdefault("features", {})[
                "selected_groups"
            ] = selected_groups
            state.setdefault("execution", {}).setdefault("plan", {}).setdefault("features", {})[
                "packages"
            ] = packages
            if missing:
                state.setdefault("execution", {}).setdefault("warnings", []).append(
                    {"feature_packages_missing": missing}
                )

            apt_install(target_root, packages, dry_run=dry_run)
        finally:
            umount_chroot_binds(target_root, dry_run=dry_run)

        logger.info("Features installed (allow_online=%s groups=%s)", allow_online, ",".join(selected_groups))
        return state
