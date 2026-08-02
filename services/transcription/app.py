from __future__ import annotations

import math
import os
import tempfile
import threading
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from faster_whisper import WhisperModel

app = FastAPI(title="Umoja Afya Clinical Audio Transcription", version="1.0.0", docs_url=None, redoc_url=None)
_model_lock = threading.Lock()


@lru_cache(maxsize=1)
def get_model() -> WhisperModel:
    model_name = os.getenv("WHISPER_MODEL", "small")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8" if device == "cpu" else "float16")
    with _model_lock:
        return WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            download_root=os.getenv("WHISPER_MODEL_CACHE", "/models"),
            cpu_threads=int(os.getenv("WHISPER_CPU_THREADS", "4")),
            num_workers=int(os.getenv("WHISPER_NUM_WORKERS", "1")),
        )


@app.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict:
    if os.getenv("WHISPER_EAGER_LOAD", "false").lower() in {"1", "true", "yes"}:
        get_model()
    return {"status": "ready", "model": os.getenv("WHISPER_MODEL", "small")}


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(default="en"),
    task: str = Form(default="transcribe"),
) -> dict:
    max_bytes = int(os.getenv("WHISPER_MAX_AUDIO_BYTES", str(50 * 1024 * 1024)))
    payload = await file.read(max_bytes + 1)
    await file.close()
    if not payload:
        raise HTTPException(status_code=422, detail="Audio file is empty")
    if len(payload) > max_bytes:
        raise HTTPException(status_code=413, detail="Audio file exceeds the configured size limit")

    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(prefix="umoja-audio-", suffix=suffix, delete=False) as temp:
            temp.write(payload)
            temp_name = temp.name

        model = get_model()
        initial_prompts = {
            'en': os.getenv('WHISPER_INITIAL_PROMPT_EN', 'Tanzania clinical documentation. Preserve medication names, dosages, routes, frequencies, anatomical terms, measurements and SI units exactly as spoken.'),
            'sw': os.getenv('WHISPER_INITIAL_PROMPT_SW', 'Nyaraka za kitabibu Tanzania. Hifadhi majina ya dawa, dozi, njia, vipimo, viungo vya mwili na vitengo kama vilivyotamkwa.'),
        }
        segments_iter, info = model.transcribe(
            temp_name,
            language=None if language in {"auto", ""} else language,
            task=task,
            beam_size=int(os.getenv("WHISPER_BEAM_SIZE", "5")),
            best_of=int(os.getenv("WHISPER_BEST_OF", "5")),
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=True,
            word_timestamps=True,
            temperature=0.0,
            initial_prompt=initial_prompts.get(language),
            compression_ratio_threshold=float(os.getenv('WHISPER_COMPRESSION_RATIO_THRESHOLD', '2.4')),
            log_prob_threshold=float(os.getenv('WHISPER_LOG_PROB_THRESHOLD', '-1.0')),
            no_speech_threshold=float(os.getenv('WHISPER_NO_SPEECH_THRESHOLD', '0.6')),
        )
        segments = []
        weighted_probability = 0.0
        weighted_duration = 0.0
        text_parts = []
        for segment in segments_iter:
            text = segment.text.strip()
            if text:
                text_parts.append(text)
            duration = max(0.01, float(segment.end - segment.start))
            words = []
            word_weight = 0.0
            word_probability = 0.0
            for word in segment.words or []:
                probability = max(0.0, min(1.0, float(word.probability or 0.0)))
                span = max(0.01, float((word.end or segment.end) - (word.start or segment.start)))
                word_probability += probability * span
                word_weight += span
                words.append({
                    "start": round(float(word.start or segment.start), 2),
                    "end": round(float(word.end or segment.end), 2),
                    "word": str(word.word).strip(),
                    "probability": round(probability, 4),
                })
            probability = (word_probability / word_weight) if word_weight else math.exp(min(0.0, float(segment.avg_logprob)))
            weighted_probability += probability * duration
            weighted_duration += duration
            segments.append(
                {
                    "start": round(float(segment.start), 2),
                    "end": round(float(segment.end), 2),
                    "text": text,
                    "confidence": round(probability, 4),
                    "no_speech_probability": round(float(segment.no_speech_prob), 4),
                    "words": words,
                }
            )
        transcript = " ".join(text_parts).strip()
        if not transcript:
            raise HTTPException(status_code=422, detail="No intelligible speech was detected")
        confidence = weighted_probability / weighted_duration if weighted_duration else float(info.language_probability or 0.0)
        return {
            "transcript": transcript,
            "language": info.language or language,
            "language_probability": round(float(info.language_probability or 0.0), 4),
            "confidence": round(max(0.0, min(1.0, confidence)), 4),
            "duration_seconds": round(float(info.duration or 0.0), 2),
            "engine": "faster-whisper",
            "model": os.getenv("WHISPER_MODEL", "small"),
            "segments": segments,
        }
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
