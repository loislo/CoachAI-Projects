#!/usr/bin/env python3
"""
get_urls.py

This script reads the `ShuttleSet/set/match.csv` file and extracts all non-empty URLs.
It can optionally download the videos using yt-dlp.

Usage:
    python3 get_urls.py                # just print URLs
    python3 get_urls.py --download     # download all videos
    python3 get_urls.py --download --output-dir ./videos
"""

import csv
import pathlib
import sys
import argparse
import subprocess
from typing import Optional, List


def read_urls(csv_path: pathlib.Path) -> List[str]:
    """
    Read the CSV file at `csv_path` and return a list of non-empty URLs.
    """
    if not csv_path.is_file():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    urls: List[str] = []

    with csv_path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if 'url' not in reader.fieldnames:
            print("Error: 'url' column not found in CSV", file=sys.stderr)
            sys.exit(1)

        for row in reader:
            url = row.get('url', '').strip()
            if url:
                urls.append(url)

    return urls


def download_videos(urls: List[str], output_dir: pathlib.Path) -> None:
    """
    Download videos using yt-dlp.

    Parameters
    ----------
    urls : List[str]
        List of URLs to download.
    output_dir : pathlib.Path
        Directory where videos will be saved.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for url in urls:
        # Build yt-dlp command to download the best video + best audio
        # and merge them into a single file (mp4 by default).
        cmd = [
            "yt-dlp",
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", str(output_dir / "%(title)s.%(ext)s"),
            url,
        ]

        try:
            print(f"Downloading: {url}")
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error downloading {url}: {e}", file=sys.stderr)


def main(csv_path: pathlib.Path, download: bool, output_dir: Optional[pathlib.Path]) -> None:
    """
    Main entry point.

    Parameters
    ----------
    csv_path : pathlib.Path
        Path to the CSV file containing match data.
    download : bool
        If True, download videos using yt-dlp.
    output_dir : pathlib.Path | None
        Directory to save downloaded videos. Ignored if download is False.
    """
    urls = read_urls(csv_path)

    if download:
        if output_dir is None:
            output_dir = pathlib.Path.cwd() / "videos"
        download_videos(urls, output_dir)
    else:
        for url in urls:
            print(url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract URLs from match.csv and optionally download videos with yt-dlp."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download videos using yt-dlp instead of printing URLs.",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=None,
        help="Directory to save downloaded videos (default: ./videos).",
    )
    parser.add_argument(
        "--csv",
        type=pathlib.Path,
        default=None,
        help="Path to the CSV file (default: match.csv in script directory).",
    )

    args = parser.parse_args()

    script_dir = pathlib.Path(__file__).parent
    csv_file = args.csv if args.csv else script_dir / "match.csv"

    main(csv_file, args.download, args.output_dir)
