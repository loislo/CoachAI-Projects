#!/usr/bin/env python3
"""
Utility script to generate YouTube URLs for all matches listed in
CoachAI-Challenge-IJCAI2023/ShuttleSet22/set/match.csv.

The CSV contains a column named `video` that holds the YouTube video ID
for each match.  If the column is empty or missing, the script will
attempt to find the correct video on YouTube by searching with the
match metadata (tournament, round, year, etc.).  The first search
result is used as the video ID.

The script uses absl.flags for command‑line argument parsing and the
Google YouTube Data API v3 for searching.  An API key must be
provided via the environment variable `YOUTUBE_API_KEY`.

Usage:
    python match_urls.py --input_csv=path/to/match.csv \
                         --output_csv=path/to/match_with_urls.csv
"""

import csv
import os
from pathlib import Path

from absl import app
from absl import flags

# Import the YouTube Data API client
try:
    from googleapiclient.discovery import build
except ImportError:
    raise ImportError(
        "google-api-python-client is required. Install with:\n"
        "    pip install google-api-python-client"
    )

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
flags.DEFINE_integer(
    "max_results",
    1,
    "Maximum number of search results to consider when looking up a video.",
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


def get_youtube_service():
    """
    Build and return a YouTube Data API service object.

    Returns
    -------
    googleapiclient.discovery.Resource
        The YouTube service object.

    Raises
    ------
    RuntimeError
        If the YOUTUBE_API_KEY environment variable is not set.
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "YOUTUBE_API_KEY environment variable is not set. "
            "Please set it to a valid YouTube Data API v3 key."
        )
    return build("youtube", "v3", developerKey=api_key)


def search_video_id(query: str, max_results: int = 1) -> str:
    """
    Search YouTube for a video matching the query and return the first
    video's ID.

    Parameters
    ----------
    query : str
        The search query string.
    max_results : int, optional
        Number of results to return (default is 1).

    Returns
    -------
    str
        The video ID of the first search result, or an empty string if
        no results are found.
    """
    youtube = get_youtube_service()
    request = youtube.search().list(
        q=query,
        part="id",
        type="video",
        maxResults=max_results,
    )
    response = request.execute()
    items = response.get("items", [])
    if not items:
        return ""
    return items[0]["id"]["videoId"]


def build_search_query(row: dict) -> str:
    """
    Construct a YouTube search query from a CSV row.

    Parameters
    ----------
    row : dict
        A dictionary representing a CSV row.

    Returns
    -------
    str
        A search query string that includes tournament name, round,
        year, and any other relevant fields.
    """
    parts = [
        row.get("tournament", ""),
        row.get("round", ""),
        row.get("year", ""),
        row.get("month", ""),
        row.get("day", ""),
    ]
    # Filter out empty strings and join with spaces
    return " ".join(part for part in parts if part)


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
        # Ensure the output has the same columns plus youtube_url
        fieldnames = reader.fieldnames + ["youtube_url"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)

        writer.writeheader()

        for row in reader:
            # Prefer an existing video ID if present
            video_id = row.get("video", "").strip()
            if not video_id:
                # Build a search query from the row data
                query = build_search_query(row)
                if query:
                    try:
                        video_id = search_video_id(query, FLAGS.max_results)
                    except Exception as e:
                        # Log the error and continue with an empty URL
                        print(f"⚠️  Failed to search YouTube for '{query}': {e}")
                        video_id = ""
                else:
                    video_id = ""

            youtube_url = generate_youtube_url(video_id) if video_id else ""
            row["youtube_url"] = youtube_url
            writer.writerow(row)

    print(f"✅ URLs written to {output_csv}")


if __name__ == "__main__":
    app.run(main)
