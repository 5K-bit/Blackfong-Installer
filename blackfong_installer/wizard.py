from __future__ import annotations

import getpass
import json
import subprocess
import sys
from typing import Any, Dict, List

from .main import DEFAULT_STATE_PATH, run
from .state_store import ensure_defaults, load_state, save_state


def list_disks() -> List[Dict[str, Any]]:
    """Whole disks only, excluding the device the live system booted from."""
    out = subprocess.run(
        ["lsblk", "-J", "-b", "-d", "-o", "NAME,SIZE,MODEL,TRAN,RM,TYPE"],
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    disks = [d for d in json.loads(out)["blockdevices"] if d.get("type") == "disk"]
    live_dev = _live_media_disk()
    return [d for d in disks if d["name"] != live_dev and not d["name"].startswith(("loop", "sr", "zram"))]


def _live_media_disk() -> str | None:
    """Best-effort: find the disk holding the live media (/run/live/medium or /)."""
    for mp in ("/run/live/medium", "/lib/live/mount/medium", "/cdrom"):
        r = subprocess.run(["findmnt", "-no", "SOURCE", mp], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        src = r.stdout.strip()
        if src:
            p = subprocess.run(["lsblk", "-no", "PKNAME", src], text=True, stdout=subprocess.PIPE).stdout.strip()
            return p or src.rsplit("/", 1)[-1]
    return None


def _hash_password(pw: str) -> str:
    return subprocess.run(
        ["openssl", "passwd", "-6", "-stdin"], input=pw, text=True, stdout=subprocess.PIPE, check=True
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    dry = "--dry-run" in (argv or sys.argv[1:])
    print("=== Blackfong OS installer (x86_64 UEFI, hybrid: needs internet) ===")
    disks = list_disks()
    if not disks:
        print("No installable disks found.")
        return 1
    for i, d in enumerate(disks, 1):
        gb = int(d["size"]) / 1e9
        print(f"  [{i}] /dev/{d['name']}  {gb:7.1f} GB  {d.get('model') or ''}  {d.get('tran') or ''}")
    sel = int(input("Install onto which disk number? ")) - 1
    disk = f"/dev/{disks[sel]['name']}"
    print(f"\n*** ALL DATA ON {disk} WILL BE ERASED. ***")
    if input(f"Type the device name ({disk}) to confirm: ").strip() != disk:
        print("Confirmation mismatch; aborting. Nothing was changed.")
        return 1

    hostname = input("Hostname [blackfong-node]: ").strip() or "blackfong-node"
    username = input("Username [blackfong]: ").strip() or "blackfong"
    while True:
        pw = getpass.getpass("Password: ")
        if pw and pw == getpass.getpass("Repeat password: "):
            break
        print("Passwords empty or do not match.")

    state = ensure_defaults(load_state(DEFAULT_STATE_PATH))
    state["config"].update(
        {
            "target_disk": disk,
            "hostname": hostname,
            "username": username,
            "user_password_hash": _hash_password(pw),
            "install_source": "hybrid",
            "finalize_reboot": not dry,
            "dry_run": dry,
        }
    )
    save_state(DEFAULT_STATE_PATH, state)
    run(state_path=DEFAULT_STATE_PATH)
    print("\nInstall finished. Remove the USB drive when the machine reboots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
