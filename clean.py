import argparse
import os
from os import getenv

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=getenv("API_KEY"),
)

DEFAULT_MODEL = getenv("DEFAULT_MODEL")
CHAPTER_SEPARATOR = "[CHAPTER_BREAK]"


def get_system_prompt():
    """
    Defines the instructions for the LLM.
    """
    return f"""You are a text processing and book formatting assistant. Your task is to process the provided text, which is an entire book manuscript.
This text may have been extracted from a PDF or other source and might contain:
- Lines broken in awkward places.
- Inconsistent spacing between paragraphs or sentences.
- Words hyphenated at the end of lines that should be joined.
- Other OCR or extraction artifacts.

Your goal is to:
1.  Preserve ALL original content and meaning. Do NOT add, remove, or summarize any information.
2.  Reconstruct proper paragraphs. Ensure paragraphs are separated by a single blank line.
3.  Fix broken lines and join hyphenated words that were split across lines.
4.  Normalize spacing to be consistent and clean.
5.  Identify the boundaries between chapters. This includes any prologue, introduction, or other front matter.
6.  Output the ENTIRE book, with each chapter separated by a specific, unique marker on its own line: `{CHAPTER_SEPARATOR}`.
7.  The text before the first official chapter (like a title page, dedication, or prologue) should be treated as the first block of text.
8.  Do NOT add any introductory or concluding remarks, titles, or any text that wasn't in the original. Just output the cleaned book text with the chapter separators.
9.  Maintain the original language and style of the text.

Example output format:
[Title Page and Dedication text...]
{CHAPTER_SEPARATOR}
[Chapter 1 text...]
{CHAPTER_SEPARATOR}
[Chapter 2 text...]
...and so on.

Output ONLY the cleaned-up text with the `{CHAPTER_SEPARATOR}` separators.
"""


def process_book_with_llm(book_text, model_name=DEFAULT_MODEL):
    """
    Sends the entire book text to the LLM for cleaning and chapter splitting.
    """
    if not book_text.strip():
        return ""  # Handle empty input

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": book_text},
            ],
        )
        processed_text = completion.choices[0].message.content
        return (
            processed_text.strip() if processed_text else book_text
        )  # Fallback if empty response
    except Exception as e:
        print(f"  Error interacting with API: {e}")
        print("  Returning original text due to error.")
        return book_text  # Fallback to original text on error


def process_book(input_file, output_dir, model_name):
    """
    Loads a book from a single file, sends it to the LLM for processing,
    and saves the resulting chapters into separate files.
    """
    if not os.path.isfile(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"Input file: {os.path.abspath(input_file)}")
    print(f"Output directory for cleaned chapters: {os.path.abspath(output_dir)}")
    print(f"Using model: {model_name}")
    print("-" * 30)

    print(f"Reading book from '{input_file}'...")
    try:
        with open(input_file, encoding="utf-8") as f:
            original_content = f.read()
    except Exception as e:
        print(f"  Error reading file '{input_file}': {e}")
        return

    if not original_content.strip():
        print("Input file is empty. Nothing to do.")
        return

    print("Sending entire book to LLM for cleaning and chapter splitting...")
    print(
        "(This may take a significant amount of time depending on book length and model speed)"
    )
    processed_content = process_book_with_llm(original_content, model_name)

    if CHAPTER_SEPARATOR not in processed_content:
        print("\nWarning: Chapter separator not found in the LLM's response.")
        print("The entire cleaned text will be saved to a single file.")
        output_filepath = os.path.join(output_dir, "cleaned_book.txt")
        try:
            with open(output_filepath, "w", encoding="utf-8") as outfile:
                outfile.write(processed_content)
            print(f"  Successfully saved entire content to '{output_filepath}'")
        except Exception as e:
            print(f"  Error writing file '{output_filepath}': {e}")
    else:
        chapters = processed_content.split(CHAPTER_SEPARATOR)
        print(f"\nLLM processing complete. Found {len(chapters)} sections to write.")

        for i, chapter_text in enumerate(chapters):
            chapter_text = chapter_text.strip()
            if not chapter_text:
                print(f"  Skipping empty chapter section {i + 1}.")
                continue

            filename = f"{i + 1:02d}_chapter.txt"
            output_filepath = os.path.join(output_dir, filename)

            try:
                with open(output_filepath, "w", encoding="utf-8") as outfile:
                    outfile.write(chapter_text)
                print(f"  Successfully saved '{output_filepath}'")
            except Exception as e:
                print(f"  Error writing file '{output_filepath}': {e}")

    print("\n" + "-" * 30)
    print("Book processing complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Cleans and splits a book manuscript into chapter files using an LLM.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "input_file", help="Path to the single .txt file containing the entire book."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="cleaned_chapters",
        help="Directory where the cleaned chapter files will be saved (default: cleaned_chapters).",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenRouter model to use for processing (default: {DEFAULT_MODEL}).",
    )

    args = parser.parse_args()

    process_book(args.input_file, args.output_dir, args.model)


if __name__ == "__main__":
    main()
