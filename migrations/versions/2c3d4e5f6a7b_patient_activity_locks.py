"""patient activity locks and idempotent workflows

Revision ID: 2c3d4e5f6a7b
Revises: 1b2c3d4e5f6a
"""
from alembic import op
import sqlalchemy as sa

revision = '2c3d4e5f6a7b'
down_revision = '1b2c3d4e5f6a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('patient_activity_lock',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('lock_id', sa.String(80), nullable=False),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patient.id', ondelete='CASCADE'), nullable=False),
        sa.Column('encounter_id', sa.Integer(), sa.ForeignKey('encounter.id', ondelete='SET NULL')),
        sa.Column('activity_code', sa.String(120), nullable=False), sa.Column('holder_user_id', sa.Integer(), sa.ForeignKey('user_account.id', ondelete='CASCADE'), nullable=False),
        sa.Column('holder_username', sa.String(120), nullable=False), sa.Column('holder_display_name', sa.String(180), nullable=False),
        sa.Column('acquired_at', sa.DateTime(timezone=True), nullable=False), sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False), sa.Column('released_at', sa.DateTime(timezone=True)), sa.Column('release_reason', sa.Text()),
        sa.UniqueConstraint('lock_id'), sa.UniqueConstraint('patient_id','activity_code',name='uq_patient_activity_lock'))
    op.create_index('ix_patient_activity_lock_expires_at','patient_activity_lock',['expires_at'])
    op.create_table('activity_access_request',
        sa.Column('id',sa.Integer(),primary_key=True), sa.Column('request_id',sa.String(80),nullable=False,unique=True),
        sa.Column('lock_id',sa.Integer(),sa.ForeignKey('patient_activity_lock.id',ondelete='CASCADE'),nullable=False),
        sa.Column('patient_id',sa.Integer(),sa.ForeignKey('patient.id',ondelete='CASCADE'),nullable=False), sa.Column('activity_code',sa.String(120),nullable=False),
        sa.Column('requester_user_id',sa.Integer(),sa.ForeignKey('user_account.id',ondelete='CASCADE'),nullable=False), sa.Column('requester_username',sa.String(120),nullable=False), sa.Column('requester_display_name',sa.String(180),nullable=False),
        sa.Column('status',sa.String(40),nullable=False),sa.Column('reason',sa.Text()),sa.Column('denial_reason',sa.Text()),sa.Column('retry_after',sa.DateTime(timezone=True)),
        sa.Column('requested_at',sa.DateTime(timezone=True),nullable=False),sa.Column('responded_at',sa.DateTime(timezone=True)),sa.Column('transferred_at',sa.DateTime(timezone=True)))
    op.create_index('ix_activity_access_request_status','activity_access_request',['status'])
    op.create_table('workflow_instance',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('workflow_id',sa.String(80),nullable=False,unique=True),
        sa.Column('patient_id',sa.Integer(),sa.ForeignKey('patient.id',ondelete='CASCADE'),nullable=False),sa.Column('encounter_id',sa.Integer(),sa.ForeignKey('encounter.id',ondelete='SET NULL')),
        sa.Column('workflow_code',sa.String(120),nullable=False),sa.Column('status',sa.String(40),nullable=False),sa.Column('initiated_by',sa.String(180),nullable=False),
        sa.Column('initiated_at',sa.DateTime(timezone=True),nullable=False),sa.Column('completed_at',sa.DateTime(timezone=True)),sa.Column('cancelled_at',sa.DateTime(timezone=True)),sa.Column('reversal_reason',sa.Text()),sa.Column('metadata_json',sa.Text()),
        sa.UniqueConstraint('patient_id','encounter_id','workflow_code',name='uq_patient_encounter_workflow'))


def downgrade():
    op.drop_table('workflow_instance'); op.drop_table('activity_access_request'); op.drop_table('patient_activity_lock')
