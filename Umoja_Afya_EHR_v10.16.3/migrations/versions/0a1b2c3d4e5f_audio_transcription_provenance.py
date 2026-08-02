"""add production audio transcription provenance

Revision ID: 0a1b2c3d4e5f
Revises: f7a8b9c0d1e2
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clinical_note", sa.Column("source_audio_session_id", sa.String(length=80), nullable=True))
    op.create_index(op.f("ix_clinical_note_source_audio_session_id"), "clinical_note", ["source_audio_session_id"], unique=False)

    op.add_column("audio_note_session", sa.Column("engine_model", sa.String(length=160), nullable=True))
    op.add_column("audio_note_session", sa.Column("source_type", sa.String(length=40), nullable=False, server_default="MANUAL_TRANSCRIPT"))
    op.add_column("audio_note_session", sa.Column("original_filename", sa.String(length=255), nullable=True))
    op.add_column("audio_note_session", sa.Column("mime_type", sa.String(length=120), nullable=True))
    op.add_column("audio_note_session", sa.Column("audio_sha256", sa.String(length=64), nullable=True))
    op.add_column("audio_note_session", sa.Column("audio_size_bytes", sa.Integer(), nullable=True))
    op.add_column("audio_note_session", sa.Column("duration_seconds", sa.Integer(), nullable=True))
    op.add_column("audio_note_session", sa.Column("confidence_percent", sa.Integer(), nullable=True))
    op.add_column("audio_note_session", sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"))
    op.add_column("audio_note_session", sa.Column("raw_audio_retained", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_audio_note_session_audio_sha256"), "audio_note_session", ["audio_sha256"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audio_note_session_audio_sha256"), table_name="audio_note_session")
    op.drop_column("audio_note_session", "raw_audio_retained")
    op.drop_column("audio_note_session", "metadata_json")
    op.drop_column("audio_note_session", "confidence_percent")
    op.drop_column("audio_note_session", "duration_seconds")
    op.drop_column("audio_note_session", "audio_size_bytes")
    op.drop_column("audio_note_session", "audio_sha256")
    op.drop_column("audio_note_session", "mime_type")
    op.drop_column("audio_note_session", "original_filename")
    op.drop_column("audio_note_session", "source_type")
    op.drop_column("audio_note_session", "engine_model")

    op.drop_index(op.f("ix_clinical_note_source_audio_session_id"), table_name="clinical_note")
    op.drop_column("clinical_note", "source_audio_session_id")
