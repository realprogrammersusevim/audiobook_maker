# audiobook_maker

A command-line pipeline that converts books into audiobooks using LLM-based text cleaning and neural text-to-speech.

## How it works

The pipeline has four stages:

1. **intake** — Extract chapters from an EPUB file into plain text files
2. **clean** — Clean and normalize the raw text using an LLM, splitting it into chapters
3. **generate** — Synthesize audio from the cleaned chapters using ChatterboxTTS
4. **convert** — Compress the WAV output to Opus format using ffmpeg

Each stage reads from a directory and writes to another, so you can run them independently or skip stages that don't apply to your input.

## Requirements

- Python 3.12
- ffmpeg (required for `convert.py`)
- An [OpenRouter](https://openrouter.ai) API key (required for `clean.py`)
- A GPU or Apple Silicon is recommended for audio generation, but CPU works too

## Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
BASE_URL="https://openrouter.ai/api/v1"
API_KEY="your-openrouter-api-key"
DEFAULT_MODEL="google/gemini-2.5-flash-preview"
TOKENIZER="/path/to/chatterbox/tokenizer.json"
```

The `TOKENIZER` path points to the ChatterboxTTS tokenizer, which is downloaded automatically by HuggingFace when you first run `generate.py`. Check `~/.cache/huggingface/hub/` for the path after first run.

## Usage

### Full pipeline example

```bash
# Step 1: Extract chapters from an EPUB
python intake.py mybook.epub -o epub_chapters

# Step 2: Clean the text and split into chapters
# (Use this if you have a single raw text file instead of an EPUB)
python clean.py mybook.txt -o cleaned_chapters

# Step 3: Generate audio
python generate.py cleaned_chapters -o audio -v af_heart

# Step 4: Compress to Opus
python convert.py -i audio -o converted
```

---

### `intake.py` — EPUB to text

Extracts each chapter from an EPUB file into a numbered text file.

```
python intake.py <input.epub> [-o output_dir]
```

| Argument | Default | Description |
|---|---|---|
| `input.epub` | — | Path to the EPUB file |
| `-o`, `--output_dir` | `epub_chapters/` | Directory for output text files |

Output files are named `01_chapter_name.txt`, `02_chapter_name.txt`, etc.

---

### `clean.py` — LLM text cleaning

Sends a raw text file to an LLM via OpenRouter to clean OCR artifacts, fix broken line wrapping, join hyphenated words, and split the book into chapters.

```
python clean.py <input.txt> [-o output_dir] [-m model]
```

| Argument | Default | Description |
|---|---|---|
| `input.txt` | — | Path to raw book text |
| `-o`, `--output_dir` | `cleaned_chapters/` | Directory for output chapter files |
| `-m`, `--model` | `DEFAULT_MODEL` from `.env` | OpenRouter model ID |

Output files are named `01_chapter.txt`, `02_chapter.txt`, etc. If the LLM doesn't detect chapter boundaries, the cleaned text is saved as a single `cleaned_book.txt`.

---

### `generate.py` — Text to audio

Generates WAV audio for each chapter using [ChatterboxTTS](https://github.com/resemble-ai/chatterbox). Text is split into ~200-token chunks internally; chunks are cached by content hash so interrupted runs resume automatically.

```
python generate.py [input_dir] [-o output_dir] [-v voice] [-V]
```

| Argument | Default | Description |
|---|---|---|
| `input_dir` | `cleaned_chapters/` | Directory of input text files |
| `-o`, `--output` | `audio/` | Directory for output WAV files |
| `-v`, `--voice` | `af_heart` | Voice to use for synthesis |
| `-V`, `--verbose` | off | Print detailed progress |

Chapters already present in the output directory are skipped. The script detects Apple Silicon (MPS) automatically and falls back to CPU.

---

### `convert.py` — WAV to Opus

Converts WAV files to Opus using ffmpeg. Files already present in the output directory are skipped.

```
python convert.py [-i input_dir] [-o output_dir]
```

| Argument | Default | Description |
|---|---|---|
| `-i`, `--input` | `audio/` | Directory of input WAV files |
| `-o`, `--output` | `converted/` | Directory for output Opus files |

## Project structure

```
audiobook_maker/
├── intake.py           # EPUB → text chapters
├── clean.py            # Raw text → cleaned chapters (LLM)
├── generate.py         # Text → WAV audio (TTS)
├── convert.py          # WAV → Opus (ffmpeg)
├── splitter.py         # Text chunking utility used by generate.py
├── requirements.txt
└── .env                # API keys and model config (not committed)
```

## License

MIT — see [LICENSE](LICENSE).
