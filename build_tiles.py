#!/usr/bin/env python3
"""Utility script to download Israel/Palestine OSM data and render compact vector tiles.

The script:
1. Downloads the Geofabrik extract (unless already cached).
2. Downloads the requested Planetiler release.
3. Runs Planetiler with a compact profile suitable for 100–200 MB targets.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import urlretrieve

PLANETILER_VERSION = "0.9.3"
PLANETILER_JAR_URL = (
    f"https://github.com/onthegomap/planetiler/releases/download/v{PLANETILER_VERSION}/"
    "planetiler.jar"
)
OSM_PBF_URL = "https://download.geofabrik.de/asia/israel-and-palestine-latest.osm.pbf"
DEFAULT_BOUNDS = "34.0,29.0,36.0,34.0"  # lon_min,lat_min,lon_max,lat_max


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"✔ {target.name} already exists, skipping download.")
        return
    print(f"⬇ Downloading {url} -> {target} ...")
    urlretrieve(url, target)
    print(f"✔ Downloaded {target.name} ({target.stat().st_size / (1024 * 1024):.1f} MB).")


def run_planetiler(jar: Path, args: argparse.Namespace) -> None:
    cmd = [
        "java",
        f"-Xmx{args.heap}",
        "-jar",
        str(jar),
        f"--osm-path={args.osm_pbf}",
        f"--mbtiles={args.output}",
        "--download=true",
        f"--min-zoom={args.min_zoom}",
        f"--max-zoom={args.max_zoom}",
        f"--bounds={args.bounds}",
        "--languages=he,ar,en",
        "--name=Israel/Palestine Compact",
        "--description=High-zoom compact tiles for Israel and Palestine",
        f"--tmp={args.tmp_dir}",
    ]

    env = os.environ.copy()
    env.setdefault("JAVA_TOOL_OPTIONS", "-XX:+UseG1GC")

    print("🚀 Running Planetiler:\n", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory to cache downloads (default: data/)",
    )
    parser.add_argument(
        "--osm-url",
        default=OSM_PBF_URL,
        help="URL of the OSM PBF extract to download",
    )
    parser.add_argument(
        "--planetiler-url",
        default=PLANETILER_JAR_URL,
        help="URL of the Planetiler JAR release",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/israel-palestine.mbtiles"),
        help="Path to the resulting MBTiles file",
    )
    parser.add_argument(
        "--min-zoom", type=int, default=0, help="Minimum zoom level"
    )
    parser.add_argument(
        "--max-zoom", type=int, default=15, help="Maximum zoom level"
    )
    parser.add_argument(
        "--bounds",
        default=DEFAULT_BOUNDS,
        help="Bounding box in lon_min,lat_min,lon_max,lat_max",
    )
    parser.add_argument(
        "--heap",
        default="12G",
        help="Java heap size passed to Planetiler (e.g. 12G)",
    )
    parser.add_argument(
        "--tmp-dir",
        type=Path,
        default=Path("tmp"),
        help="Temp directory for Planetiler scratch files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    jar_name = Path(args.planetiler_url).name
    planetiler_path = args.data_dir / jar_name
    osm_path = args.data_dir / "israel-palestine.osm.pbf"

    download(args.planetiler_url, planetiler_path)
    download(args.osm_url, osm_path)

    args.osm_pbf = osm_path
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.tmp_dir.mkdir(parents=True, exist_ok=True)

    run_planetiler(planetiler_path, args)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Planetiler failed with exit code {exc.returncode}", file=sys.stderr)
        sys.exit(exc.returncode)
