from splitter import TextSplitter

import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
from chatterbox.models.tokenizers import EnTokenizer
import os
from os import getenv
import argparse
from dotenv import load_dotenv

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

    token_length_func = lambda text: tokenize(text)

    token_splitter = TextSplitter(max_chunk_size=200, length_function=token_length_func)

    for file in sorted(os.listdir(input_directory)):
        name, ext = os.path.splitext(file)

        # skip if the output already exists
        if os.path.exists(os.path.join(output, name + ".wav")):
            print(f"Skipping {name}.wav")
            continue

        with open(os.path.join(input_directory, file), "r") as f:
            text = f.read()

        wav_chunks = []

        for i, text_chunk in enumerate(token_splitter.split(text)):
            print(text_chunk)
            wav = model.generate(text_chunk, audio_prompt_path=voice)
            wav_chunks.append(wav)

        final_wav = torch.cat(wav_chunks, dim=1)
        ta.save(os.path.join(output, name + ".wav"), final_wav, model.sr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate audio from text files of a book."
    )
    parser.add_argument(
        "input_directory",
        default="cleaned_chapters",
        help="Directory with text files for input.",
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
