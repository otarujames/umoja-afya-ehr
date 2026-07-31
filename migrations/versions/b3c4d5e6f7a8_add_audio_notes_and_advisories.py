"""add audio-assisted note and practice advisory events

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audio_note_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("note_type", sa.String(length=80), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("draft_note", sa.Text(), nullable=False),
        sa.Column("engine", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_by", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounter.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(op.f("ix_audio_note_session_encounter_id"), "audio_note_session", ["encounter_id"], unique=False)
    op.create_index(op.f("ix_audio_note_session_patient_id"), "audio_note_session", ["patient_id"], unique=False)
    op.create_index(op.f("ix_audio_note_session_session_id"), "audio_note_session", ["session_id"], unique=True)
    op.create_table(
        "practice_advisory_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=80), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("advisory_key", sa.String(length=160), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=160), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounter.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_practice_advisory_event_advisory_key"), "practice_advisory_event", ["advisory_key"], unique=False)
    op.create_index(op.f("ix_practice_advisory_event_encounter_id"), "practice_advisory_event", ["encounter_id"], unique=False)
    op.create_index(op.f("ix_practice_advisory_event_event_id"), "practice_advisory_event", ["event_id"], unique=True)
    op.create_index(op.f("ix_practice_advisory_event_patient_id"), "practice_advisory_event", ["patient_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_practice_advisory_event_patient_id"), table_name="practice_advisory_event")
    op.drop_index(op.f("ix_practice_advisory_event_event_id"), table_name="practice_advisory_event")
    op.drop_index(op.f("ix_practice_advisory_event_encounter_id"), table_name="practice_advisory_event")
    op.drop_index(op.f("ix_practice_advisory_event_advisory_key"), table_name="practice_advisory_event")
    op.drop_table("practice_advisory_event")
    op.drop_index(op.f("ix_audio_note_session_session_id"), table_name="audio_note_session")
    op.drop_index(op.f("ix_audio_note_session_patient_id"), table_name="audio_note_session")
    op.drop_index(op.f("ix_audio_note_session_encounter_id"), table_name="audio_note_session")
    op.drop_table("audio_note_session")
