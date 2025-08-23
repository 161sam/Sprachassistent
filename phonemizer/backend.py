import re


class EspeakBackend:
    """Very small stub for tests.

    The real phonemizer library provides an ``EspeakBackend`` that converts
    text to phonemes.  For unit testing we only need a predictable placeholder
    that removes characters outside the basic alphabet to mimic phonemization.
    """

    def __init__(self, language: str = "de"):
        self.language = language

    def phonemize(self, text: str, strip: bool = True) -> str:
        # Remove punctuation such as question marks to avoid false positives.
        return re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ\s]", "", text)
