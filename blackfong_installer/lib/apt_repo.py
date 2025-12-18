from __future__ import annotations

import gzip
import logging
from pathlib import Path

from .command import run_cmd

logger = logging.getLogger(__name__)


def build_file_repo_from_debs(
    *,
    debs_dir: str,
    out_repo_dir: str,
    suite: str,
    component: str,
    arch: str,
    dry_run: bool = False,
) -> None:
    """Build a minimal file:// APT repo from a flat directory of .deb files.

    Output structure:
      out_repo_dir/
        pool/<component>/... .deb
        dists/<suite>/<component>/binary-<arch>/Packages.gz
        dists/<suite>/Release (best-effort)

    This supports sources lines like:
      deb [trusted=yes] file:/opt/blackfong/apt-repo <suite> <component>

    Notes:
    - Requires dpkg-dev (dpkg-scanpackages). Release file generation is best-effort.
    """

    src = Path(debs_dir)
    out = Path(out_repo_dir)

    if not src.exists():
        raise FileNotFoundError(debs_dir)

    debs = sorted(src.glob("*.deb"))
    if not debs:
        logger.warning("No .deb files found under %s", str(src))

    pool_dir = out / "pool" / component
    packages_dir = out / "dists" / suite / component / f"binary-{arch}"

    if not dry_run:
        pool_dir.mkdir(parents=True, exist_ok=True)
        packages_dir.mkdir(parents=True, exist_ok=True)

    # Copy debs into pool
    for d in debs:
        dst = pool_dir / d.name
        if dry_run:
            logger.info("Would copy %s -> %s", str(d), str(dst))
        else:
            dst.write_bytes(d.read_bytes())

    # Generate Packages using dpkg-scanpackages
    # dpkg-scanpackages expects relative paths in the output; run from repo root.
    rel_pool = str(Path("pool") / component)
    packages_path = packages_dir / "Packages"
    r = run_cmd(
        [
            "dpkg-scanpackages",
            "-m",
            rel_pool,
            "/dev/null",
        ],
        cwd=str(out),
        dry_run=dry_run,
    )

    if not dry_run:
        packages_path.write_text(r.stdout, encoding="utf-8")
        with gzip.open(str(packages_dir / "Packages.gz"), "wb") as f:
            f.write(r.stdout.encode("utf-8"))

    # Best-effort Release file (apt is happier when it exists).
    try:
        rel = run_cmd(["apt-ftparchive", "release", str(Path("dists") / suite)], cwd=str(out), dry_run=dry_run)
        if not dry_run:
            (out / "dists" / suite / "Release").write_text(rel.stdout, encoding="utf-8")
    except Exception:
        logger.warning("apt-ftparchive not available; skipping Release generation")
