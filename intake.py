import argparse
import os
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def ensure_valid_utf8(text: str) -> str:
    """
    Ensures that the returned string can be safely encoded as UTF-8.

    Any characters that cannot be encoded are replaced with the
    Unicode replacement character (), preventing write errors.
    """
    return text.encode("utf-8", "replace").decode("utf-8")


def chapter_to_text(chapter):
    """Extracts text from an ebooklib chapter object."""
    soup = BeautifulSoup(chapter.get_body_content(), "html.parser")

    # Remove footnote references, which are often in <sup> tags.
    for sup in soup.find_all("sup"):
        sup.decompose()

    text = soup.get_text()
    # Clean up whitespace and newlines
    text = re.sub(r"\s*\n\s*", "\n", text).strip()
    # Guarantee the string is UTF-8–safe before writing to disk
    text = ensure_valid_utf8(text)
    return text


def process_epub(input_file, output_dir):
    """
    Processes an ePub file, extracting each chapter into a separate text file.
    """
    if not os.path.isfile(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"Input ePub file: {os.path.abspath(input_file)}")
    print(f"Output directory for chapters: {os.path.abspath(output_dir)}")
    print("-" * 30)

    try:
        book = epub.read_epub(input_file)
    except Exception as e:
        print(f"  Error reading ePub file '{input_file}': {e}")
        return

    # Get chapters from the book (items of type ITEM_DOCUMENT)
    chapters = [item for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]

    if not chapters:
        print("No chapters found in the ePub file.")
        return

    print(f"Found {len(chapters)} chapter/document sections to process.")

    for i, chapter_item in enumerate(chapters):
        chapter_text = chapter_to_text(chapter_item)

        if not chapter_text.strip():
            print(f"  Skipping empty chapter section {i + 1} ({chapter_item.get_name()}).")
            continue

        basename = os.path.basename(chapter_item.get_name())
        base_filename, _ = os.path.splitext(basename)
        # Sanitize filename to remove invalid characters for most OSes
        sanitized_base_filename = re.sub(r'[<>:"/\\|?*]', '_', base_filename)
        filename = f"{i + 1:02d}_{sanitized_base_filename}.txt"
        output_filepath = os.path.join(output_dir, filename)

        try:
            with open(output_filepath, "w", encoding="utf-8") as outfile:
                outfile.write(chapter_text)
            print(f"  Successfully saved '{output_filepath}'")
        except Exception as e:
            print(f"  Error writing file '{output_filepath}': {e}")

    print("\n" + "-" * 30)
    print("ePub processing complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Extracts chapters from an ePub file into individual text files.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("input_file", help="Path to the .epub file to process.")
    parser.add_argument(
        "-o",
        "--output_dir",
        default="epub_chapters",
        help="Directory where the chapter text files will be saved (default: epub_chapters).",
    )

    args = parser.parse_args()

    process_epub(args.input_file, args.output_dir)


if __name__ == "__main__":
    main()
