import logging
import re
from typing import Callable, Generator, Optional

# Set up a logger for this module
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class TextSplitter:
    """
    Splits long text into smaller, manageable chunks suitable for TTS models.

    This class intelligently splits text by trying to fill each chunk up to
    the `max_chunk_size` while respecting grammatical boundaries.

    The splitting strategy is as follows:
    1.  **Forced Splitting:** The text is first split by a `force_split_pattern`
        (e.g., newlines) to respect hard boundaries like paragraphs.
    2.  **Sentence-based Aggregation:** Each resulting block is then broken into
        sentences. The splitter aggregates these sentences into a single chunk
        until adding the next sentence would exceed `max_chunk_size`.
    3.  **Boundary-respecting Splits:** The split occurs at the last sentence
        boundary before the chunk size limit is reached.
    4.  **Fallback Punctuation-aware Splitting:** If a single sentence is longer
        than `max_chunk_size`, it falls back to a more sophisticated splitting
        strategy for that sentence. It will attempt to split at the last
        minor punctuation mark (like a comma) before the size limit is reached.
        If no such punctuation exists, it splits by word.

    The size of a chunk can be measured either by character count (default)
    or by a custom `length_function` (e.g., token count).
    """

    def __init__(
        self,
        max_chunk_size: int = 450,
        length_function: Optional[Callable[[str], int]] = None,
        force_split_pattern: Optional[str] = r"\n",
    ):
        """
        Initializes the TextSplitter.

        Args:
            max_chunk_size: The target maximum size for each chunk. This size is
                measured by the `length_function`.
            length_function: An optional callable that takes a string and
                returns an integer representing its "length" (e.g., number
                of tokens, characters). If None, defaults to `len`, which
                counts characters.
            force_split_pattern: An optional regex pattern on which to always
                split. This is useful for respecting hard boundaries like
                paragraph breaks. Defaults to `\n`. Set to `None` to disable
                and revert to treating newlines as regular sentence terminators.
        """
        if max_chunk_size <= 0:
            raise ValueError("max_chunk_size must be a positive integer.")
        self.max_chunk_size = max_chunk_size
        self.length_fn = length_function or len
        self.force_split_pattern = force_split_pattern
        # Regex to find potential split points within a long sentence
        self._intra_sentence_split_regex = re.compile(r"[,;:]")

    def _split_long_chunk(self, chunk: str) -> Generator[str, None, None]:
        """
        Splits a chunk that is known to be too long.

        This method first tries to split at the last possible comma, semicolon,
        or colon before the `max_chunk_size` is exceeded. If no such
        punctuation is found, it falls back to splitting at the last word.
        """
        current_chunk = chunk
        while self.length_fn(current_chunk) > self.max_chunk_size:
            # Find the rough cut-off point by word
            words = current_chunk.split()
            estimated_cut_off = 0
            current_len = 0
            for word in words:
                # Add 1 for the space
                word_len = self.length_fn(word) + (1 if current_len > 0 else 0)
                if current_len + word_len > self.max_chunk_size:
                    break
                current_len += word_len
                estimated_cut_off += len(word) + 1

            # Trim to the estimated cut-off point
            cut_text = current_chunk[:estimated_cut_off].rstrip()

            # Search backwards from the cut-off for a punctuation mark
            last_punctuation_pos = -1
            for match in self._intra_sentence_split_regex.finditer(cut_text):
                last_punctuation_pos = match.start()

            if last_punctuation_pos != -1:
                # Split after the punctuation
                split_point = last_punctuation_pos + 1
                yield current_chunk[:split_point].strip()
                current_chunk = current_chunk[split_point:].strip()
            else:
                # Fallback: no punctuation found, split at the last word
                yield cut_text
                current_chunk = current_chunk[len(cut_text) :].strip()

        # Yield the final remaining part
        if current_chunk:
            yield current_chunk

    def split(self, text: str) -> Generator[str, None, None]:
        """
        Splits the input text into chunks based on the configured rules.

        This method is a generator, yielding each chunk of text one by one.
        It first splits the text by `force_split_pattern` (e.g., paragraphs),
        and then aggregates sentences within those blocks into chunks that are
        as large as possible without exceeding `max_chunk_size`.

        Args:
            text: The text to be split.

        Yields:
            A string representing the next chunk of text.
        """
        if not text or not text.strip():
            return

        if self.force_split_pattern:
            blocks = re.split(self.force_split_pattern, text)
            # When splitting by a pattern, we treat sentence ends within a block
            # as only . ! ?
            sentence_split_regex = r"(?<=[.!?])\s+"
        else:
            # Original behavior: process the whole text as one block, and
            # treat newlines as sentence terminators.
            blocks = [text]
            sentence_split_regex = r"(?<=[.!?\n])\s+"

        for block in blocks:
            if not block or not block.strip():
                continue

            sentences = re.split(sentence_split_regex, block.strip())

            current_chunk = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                # Case 1: The sentence itself is too long to ever fit in a chunk.
                # We must split it using the more advanced intra-sentence logic.
                if self.length_fn(sentence) > self.max_chunk_size:
                    # First, yield any accumulated text before this long sentence.
                    if current_chunk:
                        yield current_chunk
                        current_chunk = ""
                    # Then, split the long sentence and yield its parts.
                    yield from self._split_long_chunk(sentence)
                    continue

                # Case 2: The sentence fits, but adding it would make the chunk too long.
                separator = " " if current_chunk else ""
                if (
                    self.length_fn(current_chunk + separator + sentence)
                    > self.max_chunk_size
                ):
                    # Yield the current chunk...
                    yield current_chunk
                    # ...and start a new chunk with the current sentence.
                    current_chunk = sentence
                else:
                    # Case 3: The sentence fits and can be added to the current chunk.
                    current_chunk += separator + sentence

            # Yield any remaining text from the current block.
            if current_chunk:
                yield current_chunk
