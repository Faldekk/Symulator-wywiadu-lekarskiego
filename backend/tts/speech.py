import wave
from functools import lru_cache
from io import BytesIO
from pathlib import Path


@lru_cache(maxsize=1)
def voice():
    from piper import PiperVoice

    return PiperVoice.load(Path(__file__).with_name("pl_PL-darkman-medium.onnx"))


def synthesize(text: str) -> bytes:
    audio = BytesIO()
    with wave.open(audio, "wb") as output:
        voice().synthesize_wav(text, output)
    return audio.getvalue()

