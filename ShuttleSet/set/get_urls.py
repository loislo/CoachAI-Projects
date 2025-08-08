#!/usr/bin/env python3
"""
get_urls.py

This script reads the `ShuttleSet/set/match.csv` file and extracts all non-empty URLs.
The URLs are printed to stdout, one per line.  If you prefer to write them to a file,
you can redirect the output or modify the script to write to a file directly.

Usage:
    python3 get_urls.py
"""

import csv
import pathlib
import sys

def main(csv_path: pathlib.Path, output_path: pathlib.Path | None = None):
    """
    Read the CSV file at `csv_path`, extract the 'url' column, and output the URLs.

    Parameters
    ----------
    csv_path : pathlib.Path
        Path to the CSV file containing match data.
    output_path : pathlib.Path | None
        If provided, URLs will be written to this file.  Otherwise, they are printed
        to stdout.
    """
    if not csv_path.is_file():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    urls = []

    with csv_path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if 'url' not in reader.fieldnames:
            print("Error: 'url' column not found in CSV", file=sys.stderr)
            sys.exit(1)

        for row in reader:
            url = row.get('url', '').strip()
            if url:
                urls.append(url)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8') as out_f:
            for url in urls:
                out_f.write(url + '\n')
        print(f"Wrote {len(urls)} URLs to {output_path}")
    else:
        for url in urls:
            print(url)

if __name__ == "__main__":
    # Default to the CSV file in the same directory as this script
    script_dir = pathlib.Path(__file__).parent
    csv_file = script_dir / "match.csv"

    # Optional: write to a file named urls.txt in the same directory
    # output_file = script_dir / "urls.txt"
    # main(csv_file, output_file)

    # If you just want to print to stdout:
    main(csv_file)
