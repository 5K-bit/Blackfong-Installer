from .step_10_detect_hardware import DetectHardwareStep
from .step_20_partition_fs import PartitionFilesystemStep
from .step_30_install_kernel import InstallKernelStep
from .step_40_install_rootfs import InstallRootFSStep
from .step_50_configure_services import ConfigureServicesStep
from .step_60_install_desktop import InstallDesktopStep
from .step_70_install_features import InstallFeaturesStep
from .step_80_post_install_checks import PostInstallChecksStep
from .step_90_finalize_reboot import FinalizeRebootStep

__all__ = [
    "DetectHardwareStep",
    "PartitionFilesystemStep",
    "InstallKernelStep",
    "InstallRootFSStep",
    "ConfigureServicesStep",
    "InstallDesktopStep",
    "InstallFeaturesStep",
    "PostInstallChecksStep",
    "FinalizeRebootStep",
]
