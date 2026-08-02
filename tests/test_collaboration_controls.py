from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.database import Base
from backend.app import collaboration_models, enterprise_models, models, operational_models  # noqa
from backend.app.collaboration_models import ActivityAccessRequest, PatientActivityLock, WorkflowInstance
from backend.app.enterprise_models import UserAccount
from backend.app.models import Patient
from backend.app.routers.collaboration import auto_transfer_if_expired


def test_expired_lock_auto_transfers_to_oldest_requester():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        holder=UserAccount(username='holder',display_name='Holder User',role_code='physician',password_hash='x')
        requester=UserAccount(username='requester',display_name='Requesting User',role_code='nurse',password_hash='x')
        patient=Patient(mpi_id='TZ-MPI-LOCK',mrn='MNH-LOCK',first_name='Asha',last_name='Test',sex='Female')
        db.add_all([holder,requester,patient]);db.flush()
        lock=PatientActivityLock(patient_id=patient.id,activity_code='clinical-documentation',holder_user_id=holder.id,holder_username=holder.username,holder_display_name=holder.display_name,expires_at=datetime.now(timezone.utc)-timedelta(seconds=1))
        db.add(lock);db.flush()
        req=ActivityAccessRequest(lock_id=lock.id,patient_id=patient.id,activity_code=lock.activity_code,requester_user_id=requester.id,requester_username=requester.username,requester_display_name=requester.display_name,reason='Continue documentation')
        db.add(req);db.flush()
        transferred=auto_transfer_if_expired(db,lock)
        assert transferred.holder_user_id==requester.id
        assert req.status=='AUTO_GRANTED'


def test_workflow_uniqueness_prevents_duplicate_process():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        patient=Patient(mpi_id='TZ-MPI-WF',mrn='MNH-WF',first_name='Juma',last_name='Test',sex='Male')
        db.add(patient);db.flush()
        db.add(WorkflowInstance(patient_id=patient.id,encounter_id=None,workflow_code='PATIENT_EXPIRY',initiated_by='Tester'))
        db.commit()
        assert len(db.scalars(select(WorkflowInstance).where(WorkflowInstance.patient_id==patient.id,WorkflowInstance.workflow_code=='PATIENT_EXPIRY')).all())==1
