"""
Converts all PNG/JPG images in a specified directory to WebP format.
Original files are moved to a '_source' subdirectory.

Usage:
    1. Command line: python tools/media/convert_to_webp.py src/backend_django/static/img
    2. Interactive: Run script, enter path when prompted.
"""

import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image


def get_project_root() -> Path:
    """
    Returns the project root directory.
    Assumes this script is located at <root>/tools/media/convert_to_webp.py
    """
    return Path(__file__).resolve().parent.parent.parent


def convert_to_webp(relative_path_str: str):
    """
    Finds all PNG/JPG images, converts to WebP, and moves originals to '_source'.
    """
    project_root = get_project_root()
    source_path = (project_root / relative_path_str).resolve()

    print(f"Project Root: {project_root}")
    print(f"Target Directory: {source_path}")

    if not source_path.exists() or not source_path.is_dir():
        print(f"Error: '{source_path}' is not a valid directory.")
        return

    # Create _source directory if it doesn't exist
    originals_dir = source_path / "_source"
    originals_dir.mkdir(exist_ok=True)
    print(f"Originals will be moved to: {originals_dir}")

    print("Scanning for images...")

    # Exclude _source directory from scanning to avoid re-processing moved files
    # We scan only the top level or recursively but skip _source
    all_files = list(source_path.rglob("*"))

    image_paths = []
    for f in all_files:
        if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            # Check if file is inside _source folder
            if "_source" in f.parts:
                continue
            image_paths.append(f)

    if not image_paths:
        print("No PNG or JPG images found (excluding _source).")
        return

    count = 0
    for img_path in image_paths:
        webp_path = img_path.with_suffix(".webp")

        # 1. Convert
        try:
            if webp_path.exists():
                print(f"WebP exists, skipping conversion: {img_path.name}")
            else:
                with Image.open(img_path) as img:
                    img.save(webp_path, "webp", quality=80)
                    print(f"Converted: {img_path.name} -> {webp_path.name}")

            # 2. Move original
            # Calculate relative path inside source_path to keep structure in _source if needed
            # But for simplicity, we just move flat or keep structure?
            # Let's keep structure relative to source_path.

            rel_path = img_path.relative_to(source_path)
            dest_path = originals_dir / rel_path

            # Ensure parent dirs exist in _source
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(img_path), str(dest_path))
            print(f"Moved original to: {dest_path.relative_to(source_path)}")

            count += 1

        except Exception as e:
            print(f"Error processing {img_path.name}: {e}")

    print(f"\nDone! Processed {count} images.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="Convert images to WebP.")
        parser.add_argument("directory", type=str, help="Relative path to directory.")
        args = parser.parse_args()
        target_dir_str = args.directory
    else:
        print("--- Image to WebP Converter ---")
        target_dir_str = input("Enter path relative to project root (e.g. src/backend_django/static/img): ").strip()

    if target_dir_str:
        convert_to_webp(target_dir_str)
    else:
        print("No path provided.")
