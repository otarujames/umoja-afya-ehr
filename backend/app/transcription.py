from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from .config import get_settings


class TranscriptionUnavailable(RuntimeError):
    """Raised when the configured speech-to-text service cannot be reached."""


class TranscriptionRejected(RuntimeError):
    """Raised when the speech-to-text service rejects an audio payload."""


@dataclass(frozen=True)
class TranscriptionResult:
    transcript: str
    language: str
    confidence: float | None
    duration_seconds: float | None
    engine: str
    model: str | None = None
    segments: list[dict[str, Any]] = field(default_factory=list)


def transcription_service_status() -> dict[str, Any]:
    settings = get_settings()
    endpoint = (settings.transcription_endpoint or "").strip()
    if not endpoint:
        return {"configured": False, "available": False, "detail": "not configured"}
    parsed = urlsplit(endpoint)
    health_url = urlunsplit((parsed.scheme, parsed.netloc, "/health/ready", "", ""))
    try:
        with httpx.Client(timeout=min(5, settings.transcription_timeout_seconds)) as client:
            response = client.get(health_url, headers={"X-Umoja-Request": "transcription-readiness"})
        if response.status_code >= 400:
            return {"configured": True, "available": False, "detail": f"HTTP {response.status_code}"}
        payload = response.json() if "json" in response.headers.get("content-type", "") else {}
        return {"configured": True, "available": True, "detail": "ready", "model": payload.get("model")}
    except Exception as exc:  # readiness reporting must not crash the core EHR
        return {"configured": True, "available": False, "detail": type(exc).__name__}


def transcribe_audio(
    *,
    audio: bytes,
    filename: str,
    content_type: str,
    language: str,
) -> TranscriptionResult:
    settings = get_settings()
    endpoint = (settings.transcription_endpoint or "").strip()
    if not endpoint:
        raise TranscriptionUnavailable(
            "No server-side transcription engine is configured. Start the bundled transcription "
            "service or use browser dictation/manual transcript entry."
        )

    try:
        with httpx.Client(timeout=settings.transcription_timeout_seconds) as client:
            response = client.post(
                endpoint,
                data={"language": language, "task": "transcribe"},
                files={"file": (filename, audio, content_type)},
                headers={"X-Umoja-Request": "clinical-audio-transcription"},
            )
    except httpx.HTTPError as exc:
        raise TranscriptionUnavailable("The configured transcription service is unavailable.") from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail") or response.json().get("message")
        except Exception:
            detail = response.text.strip()
        raise TranscriptionRejected(detail or f"Transcription service returned HTTP {response.status_code}.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise TranscriptionRejected("Transcription service returned a non-JSON response.") from exc

    transcript = " ".join(str(payload.get("transcript") or payload.get("text") or "").split())
    if not transcript:
        raise TranscriptionRejected("No speech could be transcribed from the submitted audio.")

    confidence_raw = payload.get("confidence")
    confidence = float(confidence_raw) if confidence_raw is not None else None
    duration_raw = payload.get("duration_seconds")
    duration_seconds = float(duration_raw) if duration_raw is not None else None
    return TranscriptionResult(
        transcript=transcript,
        language=str(payload.get("language") or language),
        confidence=confidence,
        duration_seconds=duration_seconds,
        engine=str(payload.get("engine") or "configured-transcription-service"),
        model=str(payload.get("model")) if payload.get("model") else None,
        segments=list(payload.get("segments") or []),
    )
