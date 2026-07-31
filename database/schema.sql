-- Umoja Afya Enterprise EHR 10.1.0 schema snapshot (SQLite review profile)
-- PostgreSQL production schema is managed by Alembic migrations.

CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

CREATE TABLE appointment (
	id INTEGER NOT NULL, 
	appointment_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	facility_id INTEGER NOT NULL, 
	service VARCHAR(160) NOT NULL, 
	provider VARCHAR(160), 
	appointment_type VARCHAR(80) NOT NULL, 
	scheduled_start DATETIME NOT NULL, 
	scheduled_end DATETIME NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	arrival_method VARCHAR(80), 
	referral_id VARCHAR(80), 
	notes TEXT, 
	created_by VARCHAR(160) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(facility_id) REFERENCES facility (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE appointment_status_event (
	id INTEGER NOT NULL, 
	event_id VARCHAR(80) NOT NULL, 
	appointment_id INTEGER NOT NULL, 
	status_before VARCHAR(80) NOT NULL, 
	status_after VARCHAR(80) NOT NULL, 
	reason TEXT NOT NULL, 
	actor VARCHAR(160) NOT NULL, 
	occurred_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(appointment_id) REFERENCES appointment (id) ON DELETE CASCADE, 
	UNIQUE (event_id)
);

CREATE TABLE audio_note_session (
	id INTEGER NOT NULL, 
	session_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER, 
	language VARCHAR(10) NOT NULL, 
	note_type VARCHAR(80) NOT NULL, 
	transcript TEXT NOT NULL, 
	draft_note TEXT NOT NULL, 
	engine VARCHAR(120) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	created_by VARCHAR(160) NOT NULL, 
	created_at DATETIME NOT NULL, engine_model VARCHAR(160), source_type VARCHAR(40) DEFAULT 'MANUAL_TRANSCRIPT' NOT NULL, original_filename VARCHAR(255), mime_type VARCHAR(120), audio_sha256 VARCHAR(64), audio_size_bytes INTEGER, duration_seconds INTEGER, confidence_percent INTEGER, metadata_json TEXT DEFAULT '{}' NOT NULL, raw_audio_retained BOOLEAN DEFAULT 0 NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	UNIQUE (session_id)
);

CREATE TABLE audit_event (
	id INTEGER NOT NULL, 
	event_id VARCHAR(80) NOT NULL, 
	occurred_at DATETIME NOT NULL, 
	actor VARCHAR(160) NOT NULL, 
	role VARCHAR(120) NOT NULL, 
	action VARCHAR(160) NOT NULL, 
	resource_type VARCHAR(120) NOT NULL, 
	resource_id VARCHAR(120), 
	patient_mpi_id VARCHAR(80), 
	facility_code VARCHAR(80), 
	outcome VARCHAR(40) NOT NULL, 
	details TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (event_id)
);

CREATE TABLE bed (
	id INTEGER NOT NULL, 
	bed_id VARCHAR(80) NOT NULL, 
	facility_id INTEGER NOT NULL, 
	unit VARCHAR(120) NOT NULL, 
	room VARCHAR(80) NOT NULL, 
	bed_label VARCHAR(80) NOT NULL, 
	bed_type VARCHAR(80) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	encounter_id INTEGER, 
	isolation VARCHAR(120), 
	assigned_at DATETIME, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(facility_id) REFERENCES facility (id)
);

CREATE TABLE break_glass_access (
	id INTEGER NOT NULL, 
	access_id VARCHAR(80) NOT NULL, 
	user_account_id INTEGER NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER, 
	reason TEXT NOT NULL, 
	emergency_type VARCHAR(80) DEFAULT 'PATIENT_SAFETY' NOT NULL, 
	status VARCHAR(40) DEFAULT 'ACTIVE' NOT NULL, 
	started_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	reviewed_by VARCHAR(160), 
	reviewed_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (access_id), 
	FOREIGN KEY(user_account_id) REFERENCES user_account (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id)
);

CREATE TABLE charge (
	id INTEGER NOT NULL, 
	charge_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER NOT NULL, 
	service_code VARCHAR(80) NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	quantity INTEGER NOT NULL, 
	unit_price NUMERIC(14, 2) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	payer VARCHAR(120), 
	posted_by VARCHAR(160) NOT NULL, 
	posted_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE claim (
	id INTEGER NOT NULL, 
	claim_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER NOT NULL, 
	payer VARCHAR(120) NOT NULL, 
	member_number VARCHAR(120), 
	amount NUMERIC(14, 2) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	authorization_number VARCHAR(120), 
	denial_code VARCHAR(80), 
	denial_reason TEXT, 
	submitted_at DATETIME, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE clinical_note (
	id INTEGER NOT NULL, 
	note_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER NOT NULL, 
	note_type VARCHAR(120) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	author VARCHAR(160) NOT NULL, 
	service VARCHAR(160) NOT NULL, 
	body TEXT NOT NULL, 
	cosign_required BOOLEAN NOT NULL, 
	signed_by VARCHAR(160), 
	created_at DATETIME NOT NULL, 
	signed_at DATETIME, 
	amended_at DATETIME, source_audio_session_id VARCHAR(80), 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE clinical_order (
	id INTEGER NOT NULL, 
	order_id VARCHAR(80) NOT NULL, 
	encounter_id INTEGER NOT NULL, 
	order_type VARCHAR(80) NOT NULL, 
	order_name VARCHAR(255) NOT NULL, 
	priority VARCHAR(40) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	indication TEXT, 
	ordered_by VARCHAR(160) NOT NULL, 
	ordered_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id)
);

CREATE TABLE coverage_verification (
	id INTEGER NOT NULL, 
	verification_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER, 
	payer VARCHAR(160) NOT NULL, 
	member_number VARCHAR(160), 
	service VARCHAR(160), 
	status VARCHAR(40) NOT NULL, 
	response_code VARCHAR(80), 
	response_message TEXT, 
	copay_amount VARCHAR(80), 
	requested_by VARCHAR(160) NOT NULL, 
	requested_at DATETIME NOT NULL, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id)
);

CREATE TABLE device_endpoint (
	id INTEGER NOT NULL, 
	device_id VARCHAR(80) NOT NULL, 
	facility_code VARCHAR(80) NOT NULL, 
	unit VARCHAR(120) NOT NULL, 
	room VARCHAR(80), 
	bed_label VARCHAR(80), 
	name VARCHAR(180) NOT NULL, 
	device_type VARCHAR(100) NOT NULL, 
	manufacturer VARCHAR(120), 
	model VARCHAR(120), 
	protocol VARCHAR(80) DEFAULT 'FHIR_OBSERVATION' NOT NULL, 
	status VARCHAR(40) DEFAULT 'ONLINE' NOT NULL, 
	last_seen_at DATETIME, 
	active BOOLEAN DEFAULT 1 NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE device_reading (
	id INTEGER NOT NULL, 
	reading_id VARCHAR(80) NOT NULL, 
	device_endpoint_id INTEGER NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER NOT NULL, 
	flowsheet_id INTEGER, 
	parameter_code VARCHAR(100) NOT NULL, 
	parameter_name VARCHAR(180) NOT NULL, 
	numeric_value FLOAT, 
	text_value VARCHAR(255), 
	unit VARCHAR(80), 
	quality VARCHAR(40) DEFAULT 'VALID' NOT NULL, 
	source_message_id VARCHAR(160), 
	recorded_at DATETIME NOT NULL, 
	received_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(device_endpoint_id) REFERENCES device_endpoint (id) ON DELETE CASCADE, 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(flowsheet_id) REFERENCES flowsheet (id)
);

CREATE TABLE diagnostic_result (
	id INTEGER NOT NULL, 
	result_id VARCHAR(80) NOT NULL, 
	order_id INTEGER, 
	patient_id INTEGER NOT NULL, 
	test_name VARCHAR(255) NOT NULL, 
	value VARCHAR(180) NOT NULL, 
	unit VARCHAR(80), 
	flag VARCHAR(40) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	source VARCHAR(160) NOT NULL, 
	issued_at DATETIME NOT NULL, 
	acknowledged BOOLEAN NOT NULL, 
	acknowledged_by VARCHAR(160), 
	acknowledged_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES clinical_order (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE duty_roster (
	id INTEGER NOT NULL, 
	roster_id VARCHAR(80) NOT NULL, 
	service_point_id INTEGER NOT NULL, 
	roster_date DATE NOT NULL, 
	shift_start TIME NOT NULL, 
	shift_end TIME NOT NULL, 
	team_name VARCHAR(160) NOT NULL, 
	lead_provider VARCHAR(160), 
	staff_count INTEGER DEFAULT '1' NOT NULL, 
	status VARCHAR(40) DEFAULT 'ACTIVE' NOT NULL, 
	notes TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_duty_roster_shift UNIQUE (service_point_id, roster_date, shift_start), 
	UNIQUE (roster_id), 
	FOREIGN KEY(service_point_id) REFERENCES service_point (id) ON DELETE CASCADE
);

CREATE TABLE encounter (
	id INTEGER NOT NULL, 
	encounter_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	facility_id INTEGER NOT NULL, 
	encounter_type VARCHAR(80) NOT NULL, 
	service VARCHAR(160) NOT NULL, 
	status VARCHAR(23) NOT NULL, 
	acuity VARCHAR(40) NOT NULL, 
	location VARCHAR(160) NOT NULL, 
	room VARCHAR(80), 
	provider VARCHAR(160), 
	reason_for_visit TEXT, 
	arrival_at DATETIME NOT NULL, 
	triage_at DATETIME, 
	provider_start_at DATETIME, 
	discharge_at DATETIME, 
	discharge_disposition VARCHAR(160), 
	discharge_summary TEXT, 
	follow_up TEXT, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(facility_id) REFERENCES facility (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE facility (
	id INTEGER NOT NULL, 
	code VARCHAR(80) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	facility_type VARCHAR(120) NOT NULL, 
	relation VARCHAR(160) NOT NULL, 
	active BOOLEAN NOT NULL, hfr_code VARCHAR(80), region VARCHAR(120), council VARCHAR(120), ownership_category VARCHAR(80) DEFAULT 'Public' NOT NULL, ownership_authority VARCHAR(120), hierarchy_level VARCHAR(80), parent_code VARCHAR(80), source_system VARCHAR(80) DEFAULT 'Umoja Afya' NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE flowsheet (
	id INTEGER NOT NULL, 
	flowsheet_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER, 
	name VARCHAR(180) NOT NULL, 
	template_code VARCHAR(120) NOT NULL, 
	status VARCHAR(7) NOT NULL, 
	cadence_minutes INTEGER NOT NULL, 
	parameters_json TEXT NOT NULL, 
	elapsed_seconds INTEGER NOT NULL, 
	active_since DATETIME, 
	started_at DATETIME, 
	stopped_at DATETIME, 
	owner VARCHAR(160), 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE flowsheet_event (
	id INTEGER NOT NULL, 
	flowsheet_id INTEGER NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	actor VARCHAR(160) NOT NULL, 
	note TEXT, 
	occurred_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(flowsheet_id) REFERENCES flowsheet (id)
);

CREATE TABLE flowsheet_observation (
	id INTEGER NOT NULL, 
	flowsheet_id INTEGER NOT NULL, 
	parameter VARCHAR(160) NOT NULL, 
	value VARCHAR(160) NOT NULL, 
	unit VARCHAR(80), 
	source VARCHAR(80) NOT NULL, 
	recorded_by VARCHAR(160) NOT NULL, 
	recorded_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(flowsheet_id) REFERENCES flowsheet (id)
);

CREATE TABLE integration_event (
	id INTEGER NOT NULL, 
	integration_event_id VARCHAR(80) NOT NULL, 
	system VARCHAR(120) NOT NULL, 
	event_type VARCHAR(120) NOT NULL, 
	resource_type VARCHAR(120) NOT NULL, 
	resource_id VARCHAR(120) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	attempts INTEGER NOT NULL, 
	payload_json TEXT NOT NULL, 
	error TEXT, 
	created_at DATETIME NOT NULL, 
	processed_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE inventory_item (
	id INTEGER NOT NULL, 
	item_id VARCHAR(80) NOT NULL, 
	facility_id INTEGER NOT NULL, 
	item_code VARCHAR(80) NOT NULL, 
	item_name VARCHAR(255) NOT NULL, 
	category VARCHAR(120) NOT NULL, 
	unit VARCHAR(80) NOT NULL, 
	on_hand INTEGER NOT NULL, 
	reorder_level INTEGER NOT NULL, 
	batch_number VARCHAR(120), 
	expiry_at DATETIME, 
	location VARCHAR(160) NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(facility_id) REFERENCES facility (id)
);

CREATE TABLE inventory_transaction (
	id INTEGER NOT NULL, 
	transaction_id VARCHAR(80) NOT NULL, 
	inventory_item_id INTEGER NOT NULL, 
	transaction_type VARCHAR(80) NOT NULL, 
	quantity INTEGER NOT NULL, 
	reason VARCHAR(255) NOT NULL, 
	reference VARCHAR(160), 
	actor VARCHAR(160) NOT NULL, 
	occurred_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(inventory_item_id) REFERENCES inventory_item (id)
);

CREATE TABLE managed_event (
	id INTEGER NOT NULL, 
	event_id VARCHAR(80) NOT NULL, 
	entity_type VARCHAR(80) NOT NULL, 
	entity_id VARCHAR(120) NOT NULL, 
	patient_id INTEGER, 
	encounter_id INTEGER, 
	action VARCHAR(80) NOT NULL, 
	status_before VARCHAR(120), 
	status_after VARCHAR(120), 
	actor VARCHAR(160) NOT NULL, 
	reason TEXT, 
	reversible BOOLEAN DEFAULT 0 NOT NULL, 
	reversed_by_event_id VARCHAR(80), 
	occurred_at DATETIME NOT NULL, 
	metadata_json TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id)
);

CREATE TABLE medication_administration (
	id INTEGER NOT NULL, 
	administration_id VARCHAR(80) NOT NULL, 
	medication_order_id INTEGER NOT NULL, 
	scheduled_at DATETIME NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	dose_given VARCHAR(80), 
	administered_by VARCHAR(160) NOT NULL, 
	reason TEXT, 
	barcode_verified BOOLEAN NOT NULL, 
	administered_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(medication_order_id) REFERENCES medication_order (id)
);

CREATE TABLE medication_order (
	id INTEGER NOT NULL, 
	medication_order_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER NOT NULL, 
	medication_name VARCHAR(255) NOT NULL, 
	dose VARCHAR(80) NOT NULL, 
	route VARCHAR(80) NOT NULL, 
	frequency VARCHAR(80) NOT NULL, 
	start_at DATETIME NOT NULL, 
	end_at DATETIME, 
	status VARCHAR(80) NOT NULL, 
	indication TEXT, 
	ordered_by VARCHAR(160) NOT NULL, 
	verified_by VARCHAR(160), 
	verified_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE module_activity (
	id INTEGER NOT NULL, 
	activity_id VARCHAR(80) NOT NULL, 
	module_code VARCHAR(80) NOT NULL, 
	patient_id INTEGER, 
	encounter_id INTEGER, 
	activity_type VARCHAR(120) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	priority VARCHAR(40) NOT NULL, 
	assigned_to VARCHAR(160), 
	details TEXT, 
	payload_json TEXT NOT NULL, 
	created_by VARCHAR(160) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE order_catalog_item (
	id INTEGER NOT NULL, 
	orderable_code VARCHAR(100) NOT NULL, 
	display_name VARCHAR(255) NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	subcategory VARCHAR(120), 
	clinical BOOLEAN DEFAULT 1 NOT NULL, 
	department VARCHAR(120), 
	specimen VARCHAR(120), 
	default_priority VARCHAR(40) DEFAULT 'ROUTINE' NOT NULL, 
	default_instructions TEXT, 
	synonyms TEXT, 
	units VARCHAR(120), 
	route VARCHAR(80), 
	requires_reason BOOLEAN DEFAULT 0 NOT NULL, 
	requires_cosign BOOLEAN DEFAULT 0 NOT NULL, 
	active BOOLEAN DEFAULT 1 NOT NULL, 
	metadata_json TEXT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE order_status_event (
	id INTEGER NOT NULL, 
	event_id VARCHAR(80) NOT NULL, 
	order_id INTEGER NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	status_before VARCHAR(80) NOT NULL, 
	status_after VARCHAR(80) NOT NULL, 
	reason TEXT NOT NULL, 
	actor VARCHAR(160) NOT NULL, 
	occurred_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES clinical_order (id) ON DELETE CASCADE, 
	UNIQUE (event_id)
);

CREATE TABLE patient (
	id INTEGER NOT NULL, 
	mpi_id VARCHAR(80) NOT NULL, 
	mrn VARCHAR(80) NOT NULL, 
	first_name VARCHAR(120) NOT NULL, 
	middle_name VARCHAR(120), 
	last_name VARCHAR(120) NOT NULL, 
	date_of_birth DATE, 
	sex VARCHAR(40) NOT NULL, 
	phone VARCHAR(80), 
	nida_number VARCHAR(120), 
	address VARCHAR(255), 
	region VARCHAR(120), 
	district VARCHAR(120), 
	next_of_kin VARCHAR(255), 
	payer VARCHAR(120), 
	member_number VARCHAR(120), 
	allergies TEXT NOT NULL, 
	problems TEXT NOT NULL, 
	medications TEXT NOT NULL, 
	consent_status VARCHAR(80) NOT NULL, 
	identity_status VARCHAR(80) NOT NULL, 
	created_at DATETIME NOT NULL, record_status VARCHAR(40) DEFAULT 'ACTIVE' NOT NULL, deceased_at DATETIME, deceased_location VARCHAR(160), deceased_cause TEXT, death_certificate_number VARCHAR(120), expired_by VARCHAR(160), 
	PRIMARY KEY (id)
);

CREATE TABLE payment (
	id INTEGER NOT NULL, 
	payment_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER, 
	amount NUMERIC(14, 2) NOT NULL, 
	method VARCHAR(80) NOT NULL, 
	reference VARCHAR(160), 
	received_by VARCHAR(160) NOT NULL, 
	received_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE practice_advisory_event (
	id INTEGER NOT NULL, 
	event_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER, 
	advisory_key VARCHAR(160) NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	reason TEXT, 
	actor VARCHAR(160) NOT NULL, 
	occurred_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	UNIQUE (event_id)
);

CREATE TABLE print_job (
	id INTEGER NOT NULL, 
	job_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER, 
	facility_code VARCHAR(80) NOT NULL, 
	template_code VARCHAR(100) NOT NULL, 
	template_name VARCHAR(200) NOT NULL, 
	copies INTEGER NOT NULL, 
	language VARCHAR(10) NOT NULL, 
	printer_name VARCHAR(160), 
	status VARCHAR(40) NOT NULL, 
	payload_json TEXT, 
	requested_by VARCHAR(160) NOT NULL, 
	created_at DATETIME NOT NULL, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id)
);

CREATE TABLE public_health_event (
	id INTEGER NOT NULL, 
	event_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	condition_code VARCHAR(80) NOT NULL, 
	condition_name VARCHAR(255) NOT NULL, 
	event_type VARCHAR(80) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	district VARCHAR(120), 
	region VARCHAR(120), 
	reported_to VARCHAR(120) NOT NULL, 
	created_at DATETIME NOT NULL, 
	reported_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE quality_incident (
	id INTEGER NOT NULL, 
	incident_id VARCHAR(80) NOT NULL, 
	facility_id INTEGER NOT NULL, 
	patient_id INTEGER, 
	category VARCHAR(120) NOT NULL, 
	severity VARCHAR(40) NOT NULL, 
	description TEXT NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	owner VARCHAR(160), 
	reported_by VARCHAR(160) NOT NULL, 
	reported_at DATETIME NOT NULL, 
	closed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(facility_id) REFERENCES facility (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE referral (
	id INTEGER NOT NULL, 
	referral_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	source_facility_code VARCHAR(80) NOT NULL, 
	destination_facility_code VARCHAR(80) NOT NULL, 
	service VARCHAR(160) NOT NULL, 
	priority VARCHAR(40) NOT NULL, 
	reason TEXT NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	requested_by VARCHAR(160) NOT NULL, 
	accepted_by VARCHAR(160), 
	appointment_id VARCHAR(80), 
	closure_summary TEXT, 
	requested_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE service_point (
	id INTEGER NOT NULL, 
	service_point_id VARCHAR(80) NOT NULL, 
	facility_id INTEGER NOT NULL, 
	code VARCHAR(80) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	department VARCHAR(120) NOT NULL, 
	clinic VARCHAR(160) NOT NULL, 
	room VARCHAR(80), 
	scheduling_model VARCHAR(80) DEFAULT 'PUBLIC_DUTY_ROSTER' NOT NULL, 
	queue_capacity INTEGER DEFAULT '20' NOT NULL, 
	active BOOLEAN DEFAULT 1 NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_service_point_facility_code UNIQUE (facility_id, code), 
	UNIQUE (service_point_id), 
	FOREIGN KEY(facility_id) REFERENCES facility (id) ON DELETE CASCADE
);

CREATE TABLE telehealth_session (
	id INTEGER NOT NULL, 
	session_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	facility_id INTEGER NOT NULL, 
	appointment_id INTEGER, 
	encounter_id INTEGER, 
	service VARCHAR(160) NOT NULL, 
	provider VARCHAR(160) NOT NULL, 
	modality VARCHAR(40) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	reason TEXT, 
	scheduled_start DATETIME NOT NULL, 
	started_at DATETIME, 
	paused_at DATETIME, 
	ended_at DATETIME, 
	join_code VARCHAR(80) NOT NULL, 
	created_by VARCHAR(160) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(appointment_id) REFERENCES appointment (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(facility_id) REFERENCES facility (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	UNIQUE (join_code)
);

CREATE TABLE travel_screening (
	id INTEGER NOT NULL, 
	screening_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER NOT NULL, 
	encounter_id INTEGER, 
	screening_type VARCHAR(80) NOT NULL, 
	responses_json TEXT NOT NULL, 
	risk_level VARCHAR(40) NOT NULL, 
	disposition VARCHAR(200) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	completed_by VARCHAR(160) NOT NULL, 
	completed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id)
);

CREATE TABLE user_access_grant (
	id INTEGER NOT NULL, 
	grant_id VARCHAR(80) NOT NULL, 
	user_account_id INTEGER NOT NULL, 
	scope_type VARCHAR(40) NOT NULL, 
	scope_code VARCHAR(160) NOT NULL, 
	active BOOLEAN NOT NULL, 
	granted_by VARCHAR(180) NOT NULL, 
	reason TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_account_id) REFERENCES user_account (id) ON DELETE CASCADE, 
	UNIQUE (grant_id), 
	CONSTRAINT uq_user_access_grant UNIQUE (user_account_id, scope_type, scope_code)
);

CREATE TABLE "user_account" (
	id INTEGER NOT NULL, 
	user_id VARCHAR(80) NOT NULL, 
	username VARCHAR(120) NOT NULL, 
	display_name VARCHAR(180) NOT NULL, 
	role_code VARCHAR(80) NOT NULL, 
	facility_code VARCHAR(80) NOT NULL, 
	password_hash TEXT NOT NULL, 
	active BOOLEAN NOT NULL, 
	requires_mfa BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	last_login_at DATETIME, 
	failed_login_count INTEGER DEFAULT '0' NOT NULL, 
	locked_until DATETIME, 
	password_changed_at DATETIME, 
	must_change_password BOOLEAN DEFAULT 0 NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE user_message (
	id INTEGER NOT NULL, 
	message_id VARCHAR(80) NOT NULL, 
	thread_id VARCHAR(80) NOT NULL, 
	sender_user_id INTEGER NOT NULL, 
	recipient_user_id INTEGER NOT NULL, 
	patient_id INTEGER, 
	encounter_id INTEGER, 
	subject VARCHAR(240) NOT NULL, 
	body TEXT NOT NULL, 
	priority VARCHAR(40) DEFAULT 'ROUTINE' NOT NULL, 
	status VARCHAR(40) DEFAULT 'UNREAD' NOT NULL, 
	sent_at DATETIME NOT NULL, 
	read_at DATETIME, 
	archived_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sender_user_id) REFERENCES user_account (id) ON DELETE CASCADE, 
	FOREIGN KEY(recipient_user_id) REFERENCES user_account (id) ON DELETE CASCADE, 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id)
);

CREATE TABLE user_session (
	id INTEGER NOT NULL, 
	session_id VARCHAR(80) NOT NULL, 
	user_account_id INTEGER NOT NULL, 
	token_jti VARCHAR(96) NOT NULL, 
	issued_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	revoked_at DATETIME, 
	source_ip VARCHAR(80), 
	user_agent VARCHAR(500), 
	PRIMARY KEY (id), 
	UNIQUE (session_id), 
	UNIQUE (token_jti), 
	FOREIGN KEY(user_account_id) REFERENCES user_account (id) ON DELETE CASCADE
);

CREATE TABLE walk_in_episode (
	id INTEGER NOT NULL, 
	walkin_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER, 
	encounter_id INTEGER, 
	facility_id INTEGER NOT NULL, 
	service_point_id INTEGER, 
	reason TEXT, 
	notes TEXT, 
	status VARCHAR(80) DEFAULT 'SEARCH_OR_CREATE' NOT NULL, 
	coverage_route VARCHAR(80), 
	queue_name VARCHAR(160), 
	created_by VARCHAR(160) NOT NULL, 
	created_at DATETIME NOT NULL, 
	arrived_at DATETIME, 
	completed_at DATETIME, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (walkin_id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(facility_id) REFERENCES facility (id), 
	FOREIGN KEY(service_point_id) REFERENCES service_point (id)
);

CREATE TABLE work_item (
	id INTEGER NOT NULL, 
	work_item_id VARCHAR(80) NOT NULL, 
	patient_id INTEGER, 
	encounter_id INTEGER, 
	queue VARCHAR(120) NOT NULL, 
	task_type VARCHAR(120) NOT NULL, 
	subject VARCHAR(255) NOT NULL, 
	details TEXT, 
	priority VARCHAR(40) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	assigned_to VARCHAR(160), 
	due_at DATETIME, 
	created_by VARCHAR(160) NOT NULL, 
	created_at DATETIME NOT NULL, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id)
);

CREATE TABLE work_queue_definition (
	id INTEGER NOT NULL, 
	queue_id VARCHAR(80) NOT NULL, 
	code VARCHAR(120) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	service_area VARCHAR(120) NOT NULL, 
	owner_team VARCHAR(160) NOT NULL, 
	facility_code VARCHAR(80), 
	description TEXT, 
	routing_rule_json TEXT, 
	sla_hours INTEGER DEFAULT '24' NOT NULL, 
	active BOOLEAN DEFAULT 1 NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (queue_id), 
	UNIQUE (code)
);

CREATE TABLE work_queue_event (
	id INTEGER NOT NULL, 
	event_id VARCHAR(80) NOT NULL, 
	work_queue_item_id INTEGER NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	status_before VARCHAR(40), 
	status_after VARCHAR(40), 
	actor VARCHAR(160) NOT NULL, 
	note TEXT, 
	occurred_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (event_id), 
	FOREIGN KEY(work_queue_item_id) REFERENCES work_queue_item (id) ON DELETE CASCADE
);

CREATE TABLE work_queue_item (
	id INTEGER NOT NULL, 
	item_id VARCHAR(80) NOT NULL, 
	queue_definition_id INTEGER NOT NULL, 
	patient_id INTEGER, 
	encounter_id INTEGER, 
	appointment_id INTEGER, 
	title VARCHAR(240) NOT NULL, 
	reason TEXT NOT NULL, 
	priority VARCHAR(40) DEFAULT 'ROUTINE' NOT NULL, 
	status VARCHAR(40) DEFAULT 'ACTIVE' NOT NULL, 
	assigned_to VARCHAR(160), 
	due_at DATETIME, 
	deferred_until DATETIME, 
	created_by VARCHAR(160) DEFAULT 'Workflow Engine' NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	closed_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (item_id), 
	FOREIGN KEY(queue_definition_id) REFERENCES work_queue_definition (id) ON DELETE CASCADE, 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id), 
	FOREIGN KEY(appointment_id) REFERENCES appointment (id)
);

CREATE TABLE workflow_notification (
	id INTEGER NOT NULL, 
	notification_id VARCHAR(80) NOT NULL, 
	event_type VARCHAR(80) NOT NULL, 
	facility_code VARCHAR(80) NOT NULL, 
	patient_id INTEGER, 
	encounter_id INTEGER, 
	audience VARCHAR(160) DEFAULT 'CLINICAL_WORKFLOW' NOT NULL, 
	message_en VARCHAR(400) NOT NULL, 
	message_sw VARCHAR(400) NOT NULL, 
	payload_json TEXT, 
	created_at DATETIME NOT NULL, 
	expires_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (notification_id), 
	FOREIGN KEY(patient_id) REFERENCES patient (id), 
	FOREIGN KEY(encounter_id) REFERENCES encounter (id)
);

CREATE UNIQUE INDEX ix_appointment_appointment_id ON appointment (appointment_id);

CREATE INDEX ix_appointment_facility_id ON appointment (facility_id);

CREATE INDEX ix_appointment_patient_id ON appointment (patient_id);

CREATE INDEX ix_appointment_scheduled_start ON appointment (scheduled_start);

CREATE INDEX ix_appointment_service ON appointment (service);

CREATE INDEX ix_appointment_status ON appointment (status);

CREATE INDEX ix_appointment_status_event_appointment_id ON appointment_status_event (appointment_id);

CREATE UNIQUE INDEX ix_appointment_status_event_event_id ON appointment_status_event (event_id);

CREATE INDEX ix_audio_note_session_audio_sha256 ON audio_note_session (audio_sha256);

CREATE INDEX ix_audio_note_session_encounter_id ON audio_note_session (encounter_id);

CREATE INDEX ix_audio_note_session_patient_id ON audio_note_session (patient_id);

CREATE UNIQUE INDEX ix_audio_note_session_session_id ON audio_note_session (session_id);

CREATE INDEX ix_audit_event_occurred_at ON audit_event (occurred_at);

CREATE UNIQUE INDEX ix_bed_bed_id ON bed (bed_id);

CREATE INDEX ix_bed_encounter_id ON bed (encounter_id);

CREATE INDEX ix_bed_facility_id ON bed (facility_id);

CREATE INDEX ix_bed_status ON bed (status);

CREATE INDEX ix_bed_unit ON bed (unit);

CREATE INDEX ix_break_glass_access_access_id ON break_glass_access (access_id);

CREATE INDEX ix_break_glass_access_encounter_id ON break_glass_access (encounter_id);

CREATE INDEX ix_break_glass_access_expires_at ON break_glass_access (expires_at);

CREATE INDEX ix_break_glass_access_patient_id ON break_glass_access (patient_id);

CREATE INDEX ix_break_glass_access_status ON break_glass_access (status);

CREATE INDEX ix_break_glass_access_user_account_id ON break_glass_access (user_account_id);

CREATE UNIQUE INDEX ix_charge_charge_id ON charge (charge_id);

CREATE INDEX ix_charge_encounter_id ON charge (encounter_id);

CREATE INDEX ix_charge_patient_id ON charge (patient_id);

CREATE UNIQUE INDEX ix_claim_claim_id ON claim (claim_id);

CREATE INDEX ix_claim_encounter_id ON claim (encounter_id);

CREATE INDEX ix_claim_patient_id ON claim (patient_id);

CREATE INDEX ix_claim_payer ON claim (payer);

CREATE INDEX ix_claim_status ON claim (status);

CREATE INDEX ix_clinical_note_encounter_id ON clinical_note (encounter_id);

CREATE UNIQUE INDEX ix_clinical_note_note_id ON clinical_note (note_id);

CREATE INDEX ix_clinical_note_note_type ON clinical_note (note_type);

CREATE INDEX ix_clinical_note_patient_id ON clinical_note (patient_id);

CREATE INDEX ix_clinical_note_source_audio_session_id ON clinical_note (source_audio_session_id);

CREATE INDEX ix_clinical_note_status ON clinical_note (status);

CREATE INDEX ix_clinical_order_encounter_id ON clinical_order (encounter_id);

CREATE UNIQUE INDEX ix_clinical_order_order_id ON clinical_order (order_id);

CREATE INDEX ix_coverage_verification_encounter_id ON coverage_verification (encounter_id);

CREATE INDEX ix_coverage_verification_patient_id ON coverage_verification (patient_id);

CREATE INDEX ix_coverage_verification_payer ON coverage_verification (payer);

CREATE INDEX ix_coverage_verification_requested_at ON coverage_verification (requested_at);

CREATE INDEX ix_coverage_verification_status ON coverage_verification (status);

CREATE UNIQUE INDEX ix_coverage_verification_verification_id ON coverage_verification (verification_id);

CREATE INDEX ix_device_endpoint_active ON device_endpoint (active);

CREATE UNIQUE INDEX ix_device_endpoint_device_id ON device_endpoint (device_id);

CREATE INDEX ix_device_endpoint_device_type ON device_endpoint (device_type);

CREATE INDEX ix_device_endpoint_facility_code ON device_endpoint (facility_code);

CREATE INDEX ix_device_endpoint_status ON device_endpoint (status);

CREATE INDEX ix_device_endpoint_unit ON device_endpoint (unit);

CREATE INDEX ix_device_reading_device_endpoint_id ON device_reading (device_endpoint_id);

CREATE INDEX ix_device_reading_encounter_id ON device_reading (encounter_id);

CREATE INDEX ix_device_reading_flowsheet_id ON device_reading (flowsheet_id);

CREATE INDEX ix_device_reading_parameter_code ON device_reading (parameter_code);

CREATE INDEX ix_device_reading_patient_id ON device_reading (patient_id);

CREATE UNIQUE INDEX ix_device_reading_reading_id ON device_reading (reading_id);

CREATE INDEX ix_device_reading_recorded_at ON device_reading (recorded_at);

CREATE INDEX ix_device_reading_source_message_id ON device_reading (source_message_id);

CREATE INDEX ix_diagnostic_result_patient_id ON diagnostic_result (patient_id);

CREATE UNIQUE INDEX ix_diagnostic_result_result_id ON diagnostic_result (result_id);

CREATE INDEX ix_duty_roster_roster_date ON duty_roster (roster_date);

CREATE INDEX ix_duty_roster_roster_id ON duty_roster (roster_id);

CREATE INDEX ix_duty_roster_service_point_id ON duty_roster (service_point_id);

CREATE INDEX ix_duty_roster_status ON duty_roster (status);

CREATE UNIQUE INDEX ix_encounter_encounter_id ON encounter (encounter_id);

CREATE INDEX ix_encounter_facility_id ON encounter (facility_id);

CREATE INDEX ix_encounter_patient_id ON encounter (patient_id);

CREATE INDEX ix_encounter_status ON encounter (status);

CREATE UNIQUE INDEX ix_facility_code ON facility (code);

CREATE INDEX ix_facility_council ON facility (council);

CREATE UNIQUE INDEX ix_facility_hfr_code ON facility (hfr_code);

CREATE INDEX ix_facility_hierarchy_level ON facility (hierarchy_level);

CREATE INDEX ix_facility_ownership_authority ON facility (ownership_authority);

CREATE INDEX ix_facility_ownership_category ON facility (ownership_category);

CREATE INDEX ix_facility_parent_code ON facility (parent_code);

CREATE INDEX ix_facility_region ON facility (region);

CREATE INDEX ix_flowsheet_event_flowsheet_id ON flowsheet_event (flowsheet_id);

CREATE UNIQUE INDEX ix_flowsheet_flowsheet_id ON flowsheet (flowsheet_id);

CREATE INDEX ix_flowsheet_observation_flowsheet_id ON flowsheet_observation (flowsheet_id);

CREATE INDEX ix_flowsheet_patient_id ON flowsheet (patient_id);

CREATE UNIQUE INDEX ix_integration_event_integration_event_id ON integration_event (integration_event_id);

CREATE INDEX ix_integration_event_status ON integration_event (status);

CREATE INDEX ix_integration_event_system ON integration_event (system);

CREATE INDEX ix_inventory_item_category ON inventory_item (category);

CREATE INDEX ix_inventory_item_facility_id ON inventory_item (facility_id);

CREATE INDEX ix_inventory_item_item_code ON inventory_item (item_code);

CREATE UNIQUE INDEX ix_inventory_item_item_id ON inventory_item (item_id);

CREATE INDEX ix_inventory_transaction_inventory_item_id ON inventory_transaction (inventory_item_id);

CREATE UNIQUE INDEX ix_inventory_transaction_transaction_id ON inventory_transaction (transaction_id);

CREATE INDEX ix_managed_event_action ON managed_event (action);

CREATE INDEX ix_managed_event_encounter_id ON managed_event (encounter_id);

CREATE INDEX ix_managed_event_entity_id ON managed_event (entity_id);

CREATE INDEX ix_managed_event_entity_type ON managed_event (entity_type);

CREATE UNIQUE INDEX ix_managed_event_event_id ON managed_event (event_id);

CREATE INDEX ix_managed_event_occurred_at ON managed_event (occurred_at);

CREATE INDEX ix_managed_event_patient_id ON managed_event (patient_id);

CREATE INDEX ix_managed_event_reversed_by_event_id ON managed_event (reversed_by_event_id);

CREATE INDEX ix_managed_event_reversible ON managed_event (reversible);

CREATE UNIQUE INDEX ix_medication_administration_administration_id ON medication_administration (administration_id);

CREATE INDEX ix_medication_administration_medication_order_id ON medication_administration (medication_order_id);

CREATE INDEX ix_medication_order_encounter_id ON medication_order (encounter_id);

CREATE UNIQUE INDEX ix_medication_order_medication_order_id ON medication_order (medication_order_id);

CREATE INDEX ix_medication_order_patient_id ON medication_order (patient_id);

CREATE INDEX ix_medication_order_status ON medication_order (status);

CREATE UNIQUE INDEX ix_module_activity_activity_id ON module_activity (activity_id);

CREATE INDEX ix_module_activity_encounter_id ON module_activity (encounter_id);

CREATE INDEX ix_module_activity_module_code ON module_activity (module_code);

CREATE INDEX ix_module_activity_patient_id ON module_activity (patient_id);

CREATE INDEX ix_module_activity_status ON module_activity (status);

CREATE INDEX ix_order_catalog_item_active ON order_catalog_item (active);

CREATE INDEX ix_order_catalog_item_category ON order_catalog_item (category);

CREATE INDEX ix_order_catalog_item_clinical ON order_catalog_item (clinical);

CREATE INDEX ix_order_catalog_item_department ON order_catalog_item (department);

CREATE INDEX ix_order_catalog_item_display_name ON order_catalog_item (display_name);

CREATE UNIQUE INDEX ix_order_catalog_item_orderable_code ON order_catalog_item (orderable_code);

CREATE INDEX ix_order_catalog_item_subcategory ON order_catalog_item (subcategory);

CREATE UNIQUE INDEX ix_order_status_event_event_id ON order_status_event (event_id);

CREATE INDEX ix_order_status_event_order_id ON order_status_event (order_id);

CREATE UNIQUE INDEX ix_patient_mpi_id ON patient (mpi_id);

CREATE INDEX ix_patient_mrn ON patient (mrn);

CREATE INDEX ix_patient_nida_number ON patient (nida_number);

CREATE INDEX ix_patient_record_status ON patient (record_status);

CREATE INDEX ix_payment_patient_id ON payment (patient_id);

CREATE UNIQUE INDEX ix_payment_payment_id ON payment (payment_id);

CREATE INDEX ix_practice_advisory_event_advisory_key ON practice_advisory_event (advisory_key);

CREATE INDEX ix_practice_advisory_event_encounter_id ON practice_advisory_event (encounter_id);

CREATE UNIQUE INDEX ix_practice_advisory_event_event_id ON practice_advisory_event (event_id);

CREATE INDEX ix_practice_advisory_event_patient_id ON practice_advisory_event (patient_id);

CREATE INDEX ix_print_job_created_at ON print_job (created_at);

CREATE INDEX ix_print_job_encounter_id ON print_job (encounter_id);

CREATE INDEX ix_print_job_facility_code ON print_job (facility_code);

CREATE UNIQUE INDEX ix_print_job_job_id ON print_job (job_id);

CREATE INDEX ix_print_job_patient_id ON print_job (patient_id);

CREATE INDEX ix_print_job_status ON print_job (status);

CREATE INDEX ix_print_job_template_code ON print_job (template_code);

CREATE INDEX ix_public_health_event_condition_code ON public_health_event (condition_code);

CREATE UNIQUE INDEX ix_public_health_event_event_id ON public_health_event (event_id);

CREATE INDEX ix_public_health_event_patient_id ON public_health_event (patient_id);

CREATE INDEX ix_public_health_event_status ON public_health_event (status);

CREATE INDEX ix_quality_incident_facility_id ON quality_incident (facility_id);

CREATE UNIQUE INDEX ix_quality_incident_incident_id ON quality_incident (incident_id);

CREATE INDEX ix_quality_incident_status ON quality_incident (status);

CREATE INDEX ix_referral_patient_id ON referral (patient_id);

CREATE UNIQUE INDEX ix_referral_referral_id ON referral (referral_id);

CREATE INDEX ix_referral_status ON referral (status);

CREATE INDEX ix_service_point_clinic ON service_point (clinic);

CREATE INDEX ix_service_point_code ON service_point (code);

CREATE INDEX ix_service_point_department ON service_point (department);

CREATE INDEX ix_service_point_facility_id ON service_point (facility_id);

CREATE INDEX ix_service_point_service_point_id ON service_point (service_point_id);

CREATE INDEX ix_telehealth_session_appointment_id ON telehealth_session (appointment_id);

CREATE INDEX ix_telehealth_session_encounter_id ON telehealth_session (encounter_id);

CREATE INDEX ix_telehealth_session_facility_id ON telehealth_session (facility_id);

CREATE INDEX ix_telehealth_session_patient_id ON telehealth_session (patient_id);

CREATE INDEX ix_telehealth_session_scheduled_start ON telehealth_session (scheduled_start);

CREATE INDEX ix_telehealth_session_service ON telehealth_session (service);

CREATE UNIQUE INDEX ix_telehealth_session_session_id ON telehealth_session (session_id);

CREATE INDEX ix_telehealth_session_status ON telehealth_session (status);

CREATE INDEX ix_travel_screening_completed_at ON travel_screening (completed_at);

CREATE INDEX ix_travel_screening_encounter_id ON travel_screening (encounter_id);

CREATE INDEX ix_travel_screening_patient_id ON travel_screening (patient_id);

CREATE INDEX ix_travel_screening_risk_level ON travel_screening (risk_level);

CREATE UNIQUE INDEX ix_travel_screening_screening_id ON travel_screening (screening_id);

CREATE INDEX ix_travel_screening_status ON travel_screening (status);

CREATE UNIQUE INDEX ix_user_access_grant_grant_id ON user_access_grant (grant_id);

CREATE INDEX ix_user_access_grant_scope_code ON user_access_grant (scope_code);

CREATE INDEX ix_user_access_grant_scope_type ON user_access_grant (scope_type);

CREATE INDEX ix_user_access_grant_user_account_id ON user_access_grant (user_account_id);

CREATE INDEX ix_user_account_role_code ON user_account (role_code);

CREATE UNIQUE INDEX ix_user_account_user_id ON user_account (user_id);

CREATE UNIQUE INDEX ix_user_account_username ON user_account (username);

CREATE INDEX ix_user_message_encounter_id ON user_message (encounter_id);

CREATE UNIQUE INDEX ix_user_message_message_id ON user_message (message_id);

CREATE INDEX ix_user_message_patient_id ON user_message (patient_id);

CREATE INDEX ix_user_message_priority ON user_message (priority);

CREATE INDEX ix_user_message_recipient_user_id ON user_message (recipient_user_id);

CREATE INDEX ix_user_message_sender_user_id ON user_message (sender_user_id);

CREATE INDEX ix_user_message_sent_at ON user_message (sent_at);

CREATE INDEX ix_user_message_status ON user_message (status);

CREATE INDEX ix_user_message_thread_id ON user_message (thread_id);

CREATE INDEX ix_user_session_expires_at ON user_session (expires_at);

CREATE INDEX ix_user_session_session_id ON user_session (session_id);

CREATE INDEX ix_user_session_token_jti ON user_session (token_jti);

CREATE INDEX ix_user_session_user_account_id ON user_session (user_account_id);

CREATE INDEX ix_walk_in_episode_created_at ON walk_in_episode (created_at);

CREATE INDEX ix_walk_in_episode_encounter_id ON walk_in_episode (encounter_id);

CREATE INDEX ix_walk_in_episode_facility_id ON walk_in_episode (facility_id);

CREATE INDEX ix_walk_in_episode_patient_id ON walk_in_episode (patient_id);

CREATE INDEX ix_walk_in_episode_service_point_id ON walk_in_episode (service_point_id);

CREATE INDEX ix_walk_in_episode_status ON walk_in_episode (status);

CREATE INDEX ix_walk_in_episode_walkin_id ON walk_in_episode (walkin_id);

CREATE INDEX ix_work_item_encounter_id ON work_item (encounter_id);

CREATE INDEX ix_work_item_patient_id ON work_item (patient_id);

CREATE INDEX ix_work_item_queue ON work_item (queue);

CREATE INDEX ix_work_item_status ON work_item (status);

CREATE UNIQUE INDEX ix_work_item_work_item_id ON work_item (work_item_id);

CREATE INDEX ix_work_queue_definition_active ON work_queue_definition (active);

CREATE INDEX ix_work_queue_definition_category ON work_queue_definition (category);

CREATE INDEX ix_work_queue_definition_code ON work_queue_definition (code);

CREATE INDEX ix_work_queue_definition_facility_code ON work_queue_definition (facility_code);

CREATE INDEX ix_work_queue_definition_owner_team ON work_queue_definition (owner_team);

CREATE INDEX ix_work_queue_definition_queue_id ON work_queue_definition (queue_id);

CREATE INDEX ix_work_queue_definition_service_area ON work_queue_definition (service_area);

CREATE INDEX ix_work_queue_event_action ON work_queue_event (action);

CREATE INDEX ix_work_queue_event_event_id ON work_queue_event (event_id);

CREATE INDEX ix_work_queue_event_occurred_at ON work_queue_event (occurred_at);

CREATE INDEX ix_work_queue_event_work_queue_item_id ON work_queue_event (work_queue_item_id);

CREATE INDEX ix_work_queue_item_appointment_id ON work_queue_item (appointment_id);

CREATE INDEX ix_work_queue_item_assigned_to ON work_queue_item (assigned_to);

CREATE INDEX ix_work_queue_item_created_at ON work_queue_item (created_at);

CREATE INDEX ix_work_queue_item_due_at ON work_queue_item (due_at);

CREATE INDEX ix_work_queue_item_encounter_id ON work_queue_item (encounter_id);

CREATE INDEX ix_work_queue_item_item_id ON work_queue_item (item_id);

CREATE INDEX ix_work_queue_item_patient_id ON work_queue_item (patient_id);

CREATE INDEX ix_work_queue_item_priority ON work_queue_item (priority);

CREATE INDEX ix_work_queue_item_queue_definition_id ON work_queue_item (queue_definition_id);

CREATE INDEX ix_work_queue_item_status ON work_queue_item (status);

CREATE INDEX ix_workflow_notification_created_at ON workflow_notification (created_at);

CREATE INDEX ix_workflow_notification_encounter_id ON workflow_notification (encounter_id);

CREATE INDEX ix_workflow_notification_event_type ON workflow_notification (event_type);

CREATE INDEX ix_workflow_notification_facility_code ON workflow_notification (facility_code);

CREATE INDEX ix_workflow_notification_notification_id ON workflow_notification (notification_id);

CREATE INDEX ix_workflow_notification_patient_id ON workflow_notification (patient_id);
