import logging

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.conversation import stt
from backend.tts import speech

router = APIRouter(prefix="/api/voice")
logger = logging.getLogger(__name__)


class SpeechText(BaseModel):
    text: str = Field(min_length=1, max_length=1500)


@router.post("/transcribe")
async def transcribe(request: Request):
    audio = bytearray()
    async for chunk in request.stream():
        if len(audio) + len(chunk) > 4_000_000:
            raise HTTPException(413, "Nagranie jest za duże.")
        audio.extend(chunk)
    if not audio:
        raise HTTPException(422, "Nagranie jest puste.")
    try:
        text = await run_in_threadpool(stt.transcribe, bytes(audio))
    except Exception as error:
        logger.exception("Transcription failed")
        raise HTTPException(503, "Nie udało się przetworzyć nagrania.") from error
    if not text:
        raise HTTPException(422, "Nie rozpoznano mowy. Nagraj pytanie ponownie.")
    return {"text": text}


@router.post("/speak")
def speak(message: SpeechText):
    if not message.text.strip():
        raise HTTPException(422, "Brak tekstu do odczytania.")
    try:
        audio = speech.synthesize(message.text.strip())
    except Exception as error:
        logger.exception("Speech synthesis failed")
        raise HTTPException(503, "Nie udało się odtworzyć głosu pacjenta.") from error
    return Response(audio, media_type="audio/wav")

