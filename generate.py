import argparse
import hashlib
import os
import shutil
import wave
from os import getenv

import torch
import torchaudio as ta
from chatterbox.models.tokenizers import EnTokenizer
from chatterbox.tts import ChatterboxTTS
from dotenv import load_dotenv

from splitter import TextSplitter

load_dotenv()


def generate_book(input_directory, output, voice, verbose):
    os.makedirs(output, exist_ok=True)

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    map_location = torch.device(device)

    torch_load_original = torch.load

    def patched_torch_load(*args, **kwargs):
        if "map_location" not in kwargs:
            kwargs["map_location"] = map_location
        return torch_load_original(*args, **kwargs)

    torch.load = patched_torch_load

    model = ChatterboxTTS.from_pretrained(device="mps")

    tokenizer = EnTokenizer(getenv("TOKENIZER"))

    def tokenize(text):
        tokens = tokenizer.text_to_tokens(text)
        return tokens.size()[1]

    def token_length_func(text):
        return tokenize(text)

    token_splitter = TextSplitter(max_chunk_size=200, length_function=token_length_func)

    for file in sorted(os.listdir(input_directory)):
        name, ext = os.path.splitext(file)

        final_audio_path = os.path.join(output, name + ".wav")

        # skip if the output already exists
        if os.path.exists(final_audio_path):
            print(f"Skipping {name}.wav as it already exists.")
            continue

        with open(os.path.join(input_directory, file)) as f:
            text = f.read()

        # Create a temporary directory for this chapter's chunks
        temp_dir = os.path.join(output, f"temp_{name}")
        os.makedirs(temp_dir, exist_ok=True)
        temp_files = []

        print(f"Processing chapter: {name}")
        for i, text_chunk in enumerate(token_splitter.split(text)):
            chunk_hash = hashlib.sha256(text_chunk.encode("utf-8")).hexdigest()
            temp_file_path = os.path.join(temp_dir, f"{i:04d}-{chunk_hash}.wav")

            if os.path.exists(temp_file_path):
                if verbose:
                    print(
                        f"  - Chunk {i} ({chunk_hash[:7]}...) already exists, skipping generation."
                    )
                temp_files.append(temp_file_path)
                continue

            if verbose:
                print(f"  - Generating chunk {i} ({chunk_hash[:7]}...)...")
            print(text_chunk)
            wav = model.generate(text_chunk, audio_prompt_path=voice)

            ta.save(temp_file_path, wav, model.sr, encoding="PCM_S", bits_per_sample=16)
            temp_files.append(temp_file_path)

        if not temp_files:
            if verbose:
                print(f"No audio generated for {name}, skipping.")
            os.rmdir(temp_dir)
            continue

        # Combine temporary audio files into one
        if verbose:
            print(f"Combining {len(temp_files)} chunks for {name}.wav...")

        with wave.open(final_audio_path, "wb") as wav_out:
            # Use first file to set parameters
            with wave.open(temp_files[0], "rb") as wav_in:
                wav_out.setparams(wav_in.getparams())
                wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))

            # Append data from subsequent files
            for temp_file in temp_files[1:]:
                with wave.open(temp_file, "rb") as wav_in:
                    wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))

        print(f"Finished writing {final_audio_path}")

        # Clean up temporary files and directory
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate audio from text files of a book."
    )
    parser.add_argument(
        "input_directory",
        nargs="?",
        default="cleaned_chapters",
        help="Directory with text files for input. Not used with --combine-only.",
    )
    parser.add_argument(
        "-o", "--output", default="audio", help="Directory to output the audio files."
    )
    parser.add_argument(
        "-v", "--voice", default="af_heart", help="Voice for TTS model."
    )
    parser.add_argument("-V", "--verbose", action="store_true", help="Verbose output.")

    args = parser.parse_args()

    generate_book(args.input_directory, args.output, args.voice, args.verbose)
