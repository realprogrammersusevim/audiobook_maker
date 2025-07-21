import hashlib
from os import getenv

from chatterbox.models.tokenizers import EnTokenizer
from dotenv import load_dotenv

from splitter import TextSplitter

load_dotenv()
tokenizer = EnTokenizer(getenv("TOKENIZER"))

with open("chapter_08.txt") as f:
    text = f.read()


def tokenize(text):
    tokens = tokenizer.text_to_tokens(text)
    return tokens.size()[1]


def token_length_func(text):
    return tokenize(text)

token_splitter = TextSplitter(max_chunk_size=200, length_function=token_length_func)

fpaths = []

for chunk in token_splitter.split(text):
    chunk_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
    fpath = f"./audio/temp_chapter_08/{chunk_hash}.wav"
    fpaths.append(fpath)
