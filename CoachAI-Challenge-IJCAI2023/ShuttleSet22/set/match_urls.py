#!/usr/bin/env python3
"""
Utility script to generate YouTube URLs for all matches listed in
CoachAI-Challenge-IJCAI2023/ShuttleSet22/set/match.csv.

The CSV contains a column named `video` that holds the YouTube video ID
for each match.  This script reads the CSV, constructs the full YouTube
URL for each match, and writes the results to a new CSV file
`match_with_urls.csv` in the same directory.

The script uses absl.flags for command‑line argument parsing.

Usage:
    python match_urls.py --input_csv=path/to/match.csv \
                         --output_csv=path/to/match_with_urls.csv
"""

import csv
import os
from pathlib import Path

from absl import app
from absl import flags

FLAGS = flags.FLAGS

flags.DEFINE_string(
    "input_csv",
    "CoachAI-Challenge-IJCAI2023/ShuttleSet22/set/match.csv",
    "Path to the input CSV file containing match data.",
)
flags.DEFINE_string(
    "output_csv",
    "CoachAI-Challenge-IJCAI2023/ShuttleSet22/set/match_with_urls.csv",
    "Path to the output CSV file that will contain the enriched data.",
)
flags.DEFINE_string(
    "youtube_base",
    "https://www.youtube.com/watch?v=",
    "Base URL for YouTube videos.",
)


def generate_youtube_url(video_id: str) -> str:
    """
    Construct a full YouTube URL from a video ID.

    Parameters
    ----------
    video_id : str
        The YouTube video ID (e.g., 'dQw4w9WgXcQ').

    Returns
    -------
    str
        The full YouTube URL.
    """
    return f"{FLAGS.youtube_base}{video_id}"


def main(argv):
    # Allow absl to consume any flags; ignore the rest.
    del argv

    input_csv = Path(FLAGS.input_csv)
    output_csv = Path(FLAGS.output_csv)

    if not input_csv.exists():
        raise FileNotFoundError(f"Input file not found: {input_csv}")

    with input_csv.open(newline="", encoding="utf-8") as infile, \
         output_csv.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["youtube_url"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)

        writer.writeheader()

        for row in reader:
            video_id = row.get("video", "").strip()
            youtube_url = generate_youtube_url(video_id) if video_id else ""
            row["youtube_url"] = youtube_url
            writer.writerow(row)

    print(f"✅ URLs written to {output_csv}")


if __name__ == "__main__":
    app.run(main)
