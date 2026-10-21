<#
.SYNOPSIS
  Create/boot a throw-away UEFI VirtualBox VM to test the Blackfong installer ISO. Re-runnable.

.EXAMPLE
  .\vm_virtualbox.ps1 -Iso "$env:USERPROFILE\Downloads\blackfong-installer-amd64.iso"   # create + boot the installer
  .\vm_virtualbox.ps1 -EjectIso                                                        # after the install: boot from the disk
  .\vm_virtualbox.ps1 -Recreate -Iso ...                                               # start over with a blank disk
  .\vm_virtualbox.ps1 -Destroy                                                         # delete the VM and its disk

  If PowerShell blocks the script:  powershell -ExecutionPolicy Bypass -File .\vm_virtualbox.ps1 ...
#>
[CmdletBinding()]
param(
  [string]$Iso,
  [string]$Name = "BlackfongTest",
  [int]$DiskGB = 40,
  [int]$MemoryMB = 4096,
  [int]$Cpus = 4,
  [switch]$Recreate,
  [switch]$EjectIso,
  [switch]$Destroy
)
$ErrorActionPreference = "Stop"

$vbm = (Get-Command VBoxManage -ErrorAction SilentlyContinue).Source
if (-not $vbm) { $vbm = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" }
if (-not (Test-Path $vbm)) { throw "VirtualBox not found. Install it from virtualbox.org, then re-run." }

function Vbm { & $vbm @args; if ($LASTEXITCODE -ne 0) { throw "VBoxManage $($args -join ' ') failed ($LASTEXITCODE)" } }
function VmExists { (& $vbm list vms) -match "`"$Name`"" }
function VmRunning { (& $vbm list runningvms) -match "`"$Name`"" }
function Stop-IfRunning { if (VmRunning) { Vbm controlvm $Name poweroff; Start-Sleep 3 } }

if ($Destroy) {
  if (VmExists) { Stop-IfRunning; Vbm unregistervm $Name --delete; Write-Host "Deleted VM '$Name'." }
  else { Write-Host "VM '$Name' does not exist." }
  return
}

if ($EjectIso) {
  if (-not (VmExists)) { throw "VM '$Name' does not exist." }
  Stop-IfRunning
  Vbm storageattach $Name --storagectl SATA --port 1 --device 0 --type dvddrive --medium emptydrive
  Vbm modifyvm $Name --boot1 disk --boot2 none --boot3 none --boot4 none
  Vbm startvm $Name
  Write-Host "Booting the installed system from the virtual disk."
  return
}

if ($Recreate -and (VmExists)) { Stop-IfRunning; Vbm unregistervm $Name --delete }

if (-not (VmExists)) {
  if (-not $Iso -or -not (Test-Path $Iso)) { throw "Give the ISO: -Iso C:\path\blackfong-installer-amd64.iso" }
  $Iso = (Resolve-Path $Iso).Path
  Vbm createvm --name $Name --ostype Debian_64 --register
  $cfg = (& $vbm showvminfo $Name --machinereadable | Select-String '^CfgFile="(.*)"$').Matches[0].Groups[1].Value
  $dir = Split-Path ($cfg -replace '\\\\', '\')   # machine-readable output doubles backslashes
  $disk = Join-Path $dir "disk.vdi"
  # efi64 = UEFI boot, like the real target machine. Secure Boot is not enabled by default.
  Vbm modifyvm $Name --memory $MemoryMB --cpus $Cpus --firmware efi64 --nic1 nat `
      --graphicscontroller vmsvga --vram 16 --boot1 dvd --boot2 disk --boot3 none --boot4 none
  Vbm createmedium disk --filename $disk --size ($DiskGB * 1024)
  Vbm storagectl $Name --name SATA --add sata --controller IntelAhci
  Vbm storageattach $Name --storagectl SATA --port 0 --device 0 --type hdd --medium $disk
  Vbm storageattach $Name --storagectl SATA --port 1 --device 0 --type dvddrive --medium $Iso
  Write-Host "Created VM '$Name' ($DiskGB GB disk, $MemoryMB MB RAM, UEFI)."
} else {
  Write-Host "VM '$Name' exists; booting it (use -Recreate for a blank disk, -EjectIso after installing)."
}

if (-not (VmRunning)) { Vbm startvm $Name }
