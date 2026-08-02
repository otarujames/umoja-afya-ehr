# Umoja Afya EHR 10.13.0

## Included corrections

- Reflows sign-in, patient-station, workqueue, note and audio workspaces on phones instead of shrinking desktop columns.
- Restores visible borders and focus states for fields, cards and scrolling tables.
- Keeps toast notifications visible for at least 60 seconds and adds an explicit dismiss button and countdown.
- Selects workflow wording from encounter context: outpatient, walk-in, emergency, inpatient or telehealth.
- Improves browser dictation error handling and preserves finalized transcript text.
- Keeps secure recorded-audio transcription as the preferred clinical path with playback, provenance, confidence and clinician review.
- Makes the Whisper/Hugging Face model cache writable while retaining a read-only transcription container filesystem.

## VPS upgrade

From `/opt/umoja-afya-ehr`, after replacing or pulling the 10.13.0 source:

```bash
docker compose config --quiet
docker compose build --pull app transcription
docker compose up -d --force-recreate transcription app
docker compose ps
docker compose logs --tail=100 transcription app
```

The first transcription start downloads the configured Whisper model into the persistent `umoja_whisper_models` volume and can take several minutes. It is ready when `docker compose ps` reports `transcription` as healthy.

Do not delete the PostgreSQL or Whisper model volumes during this upgrade.

## Browser audio requirements

- Serve the application over HTTPS.
- Permit microphone access for `umojaehr.online` in the browser and operating system.
- Prefer **Record** followed by **Transcribe Recording** for clinical documentation.
- Browser live dictation is an optional browser service and may be blocked by Safari or device policy.
- Clinicians must review patient names, medicines, doses, routes, allergies, measurements and negation before signing.
