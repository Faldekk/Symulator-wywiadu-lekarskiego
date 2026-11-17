from functools import lru_cache
from io import BytesIO
from pathlib import Path


@lru_cache(maxsize=1)
def model():
    from faster_whisper import WhisperModel

    return WhisperModel(
        "base", device="cpu", compute_type="int8",
        download_root=str(Path(__file__).with_name("models")),
        local_files_only=True,
    )


def transcribe(audio: bytes) -> str:
    segments, _ = model().transcribe(
        BytesIO(audio), language="pl", beam_size=1,
        vad_filter=True, condition_on_previous_text=False,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()

