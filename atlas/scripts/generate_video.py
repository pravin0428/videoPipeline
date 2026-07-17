#!/usr/bin/env python3
"""CLI entry point for Video Short Generator V3.

Usage:
    python scripts/generate_video.py --title "जंगल का इंटरनेट" --script "..."
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.logging import get_logger

logger = get_logger()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate YouTube Shorts video from script")
    parser.add_argument("--title", type=str, required=True, help="Video title")
    parser.add_argument("--script", type=str, required=True, help="Hindi script text")
    parser.add_argument("--output", type=str, default="final_video.mp4", help="Output filename")
    parser.add_argument("--output-dir", type=str, default=None, help="Output root directory")
    args = parser.parse_args()

    from pipelines.video_short_v3 import VideoShortGeneratorV3
    generator = VideoShortGeneratorV3(output_root=args.output_dir)

    output_path = asyncio.run(generator.generate(args.title, args.script, args.output))
    print(f"\nVideo generated: {output_path}", flush=True)


if __name__ == "__main__":
    main()
