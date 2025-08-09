#!/usr/bin/env python3
"""
Utility script to generate YouTube URLs for all matches listed in
CoachAI-Challenge-IJCAI2023/ShuttleSet22/set/match.csv.

The CSV contains a column named `video` that holds the YouTube video ID
for each match.  This script reads the CSV, constructs the full YouTube
URL for each match, and writes the results to a new CSV file
`match_with_urls.csv` in the same directory.

Usage:
    python match_urls.py

The output CSV will have the same columns as the input, plus an
additional column `youtube_url`.
"""

import csv
import os
from pathlib import Path

# Path to the original match CSV
INPUT_CSV = Path("CoachAI-Challenge-IJCAI2023/ShuttleSet22/set/match.csv")
# Path to the output CSV
OUTPUT_CSV = Path("CoachAI-Challenge-IJCAI2023/ShuttleSet22/set/match_with_urls.csv")

YOUTUBE_BASE = "https://www.youtube.com/watch?v="


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
    return f"{YOUTUBE_BASE}{video_id}"


def main() -> None:
    """
    Read the input CSV, generate YouTube URLs, and write the enriched
    data to the output CSV.
    """
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    with INPUT_CSV.open(newline="", encoding="utf-8") as infile, \
         OUTPUT_CSV.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["youtube_url"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)

        writer.writeheader()

        for row in reader:
            video_id = row.get("video", "").strip()
            if not video_id:
                # If the video field is empty, leave the URL blank
                youtube_url = ""
            else:
                youtube_url = generate_youtube_url(video_id)

            row["youtube_url"] = youtube_url
            writer.writerow(row)

    print(f"✅ URLs written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
