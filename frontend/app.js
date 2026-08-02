(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const esc = (value = '') => String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[ch]));
  const API = '/api/v1';
  const APP_REFRESH_INTERVAL_MS = 5 * 60 * 1000;

  const roles = [
    { id:'physician', username:'doctor', name:'Physician', icon:'⚕', detail:'Patient tracker, chart review, documentation, orders, results and discharge', user:'Dr. Neema M.', initials:'DR' },
    { id:'nurse', username:'nurse', name:'Nurse', icon:'✚', detail:'Triage, patient flow, flowsheets, eMAR, care plans and handoff', user:'Neema Kweka, RN', initials:'NK' },
    { id:'registration', username:'registration', name:'Patient Access & Registration', icon:'◎', detail:'MPI search, registration, consent, coverage, arrival and pre-registration', user:'Amina Salum', initials:'AS' },
    { id:'pharmacy', username:'pharmacy', name:'Pharmacy', icon:'Rx', detail:'Verification, dispensing, formulary, stock and medication safety', user:'Pharm. Juma K.', initials:'JK' },
    { id:'laboratory', username:'laboratory', name:'Laboratory', icon:'⚗', detail:'Specimens, worklists, validation, release and critical results', user:'Grace Mushi', initials:'GM' },
    { id:'operations', username:'operations', name:'Hospital Operations', icon:'▦', detail:'ADT, bed board, transport, EVS, capacity and command center', user:'Dr. Rahma L.', initials:'RL' },
    { id:'finance', username:'finance', name:'Revenue Cycle', icon:'₮', detail:'Eligibility, authorization, claims, denials and reconciliation', user:'Hassan Bakari', initials:'HB' },
    { id:'admin', username:'admin', name:'System Administration', icon:'⚙', detail:'Users, roles, configuration, interfaces, audit and support', user:'ICT Administrator', initials:'IA' }
  ];

  const navGroups = [
    { title:'Workspace', items:[
      ['dashboard','Command Center','▦'], ['today-patients',"Today's Patients",'☷'], ['workqueues','Workqueues','☑'], ['patient-flow','Provider Patient Tracker','↔'], ['patient-search','Patient Search & MPI','⌕'], ['chart','Longitudinal Chart','▤'], ['recent-discharges','Recent Discharges','✓']
    ]},
    { title:'Patient Access', items:[
      ['registration','Patient Registration','◎'], ['scheduling','Scheduling & Referrals','◷'], ['bed-board','ADT & Bed Board','▥'], ['emergency','Emergency & Triage','⚠']
    ]},
    { title:'Clinical Care', items:[
      ['clinical-documentation','Clinical Documentation','▤'], ['flowsheets','Flowsheets & eMAR','⌁'], ['orders','CPOE Orders','⇄'], ['results','Results Review','◉'], ['nursing','Nursing Workspace','✚']
    ]},
    { title:'Ancillary & Procedural', items:[
      ['pharmacy','Pharmacy','Rx'], ['laboratory','Laboratory','⚗'], ['blood-bank','Blood Bank','◒'], ['radiology','Radiology / PACS','◉'], ['theatre','Theatre & Procedures','✣'], ['anesthesia','Anesthesia','≈']
    ]},
    { title:'Specialty', items:[
      ['maternity','Maternity & Newborn','◌'], ['cardiology','Cardiology / JKCI','♥'], ['orthopaedics','Orthopaedics / MOI','骨'], ['oncology','Oncology / ORCI','✦'], ['critical-care','Critical Care','⌁'], ['rehab','Rehab, Mental & Dental','◈']
    ]},
    { title:'Enterprise & National', items:[
      ['revenue','Revenue Cycle & Claims','₮'], ['supply','Supply Chain & Assets','▣'], ['telehealth','Telehealth & Remote Care','◫'], ['public-health','Public Health & Registries','⌖'], ['quality','Quality, Safety & IPC','✓'], ['analytics','Analytics, M&E & Research','▥'], ['workforce','Workforce & Learning','♟'], ['admin','System Admin & Security','⚙']
    ]}
  ];

  const roleDefaults = { physician:'patient-flow', nurse:'patient-flow', registration:'registration', pharmacy:'pharmacy', laboratory:'laboratory', operations:'dashboard', finance:'revenue', admin:'admin' };

  const routeFunctionMap = {
    dashboard:'dashboard.view', 'today-patients':'patient_flow.view', workqueues:'workqueues.view', 'patient-flow':'patient_flow.view', 'patient-search':'patient.search', chart:'patient.chart', 'recent-discharges':'patient_flow.view',
    registration:'registration.manage', scheduling:'scheduling.manage', 'bed-board':'adt.manage', emergency:'emergency.manage',
    'clinical-documentation':'notes.manage', flowsheets:'flowsheets.manage', orders:'orders.create', results:'results.review', nursing:'nursing.manage',
    pharmacy:'medications.verify', laboratory:'laboratory.manage', 'blood-bank':'blood_bank.manage', radiology:'radiology.manage', theatre:'theatre.manage', anesthesia:'anesthesia.manage',
    maternity:'maternity.manage', cardiology:'cardiology.manage', orthopaedics:'orthopaedics.manage', oncology:'oncology.manage', 'critical-care':'critical_care.manage', rehab:'rehab.manage',
    revenue:'revenue.manage', supply:'supply.manage', telehealth:'telehealth.manage', 'public-health':'public_health.manage', quality:'quality.manage', analytics:'analytics.view', workforce:'workforce.manage', admin:'system.users.manage'
  };

  function canOpenRoute(route){
    if(!state.account) return true;
    const required=routeFunctionMap[route];
    return !required || (state.account.functions||[]).includes(required);
  }


  const genericModules = {
    scheduling:{ title:'Scheduling & Closed-Loop Referrals', subtitle:'Appointments, waitlists, referral intake, procedure slots, reminders and returned-summary tracking.', metrics:[['Appointments today','1,284','Network'],['Waiting > 60 min','38','Escalate'],['Open referrals','164','26 overdue'],['No-show rate','11.8%','Down 1.7 pts']] },
    'bed-board':{ title:'Enterprise Bed Board', subtitle:'Admission, transfer, discharge, capacity, EVS, transport and isolation visibility.', metrics:[['Staffed beds','1,164','Pilot network'],['Occupancy','82.7%','High'],['Pending admissions','31','9 urgent'],['Expected discharges','47','23 confirmed']] },
    emergency:{ title:'Emergency & Triage', subtitle:'Emergency tracking, acuity, trauma activation, resuscitation, observation and disposition.', metrics:[['Emergency census','83','Network'],['Critical acuity','9','Assigned'],['Door-to-triage','7 min','Median'],['Boarding > 4h','12','Review']] },
    'clinical-documentation':{ title:'Clinical Documentation', subtitle:'History and physical, progress notes, consults, procedures, care plans and discharge summaries.', metrics:[['Unsigned notes','31','Across network'],['Discharge summaries due','18','Within 24h'],['Smart templates','146','Approved'],['Documentation completion','94%','Today']] },
    nursing:{ title:'Nursing Care Workspace', subtitle:'Patient lists, assessments, care plans, medication administration, intake/output and shift handoff.', metrics:[['Due tasks','86','14 overdue'],['Medication administrations','1,921','99.1% scanned'],['High EWS alerts','8','2 unassigned'],['Handoffs pending','22','End of shift']] },
    pharmacy:{ title:'Pharmacy & Medication Management', subtitle:'Formulary, verification, dispensing, medication reconciliation, controlled medicines and inventory.', metrics:[['Verification queue','47','5 urgent'],['Ready to dispense','63','12 waiting'],['Stock-out risks','9','3 critical'],['eMAR match rate','99.1%','Stable']] },
    laboratory:{ title:'Laboratory / LIS', subtitle:'Electronic orders, barcodes, specimen tracking, analyzers, validation, blood bank linkage and critical results.', metrics:[['Open specimens','286','27 urgent'],['Median TAT','52 min','Down 9%'],['Critical results','6','1 unacknowledged'],['Analyzers online','41 / 43','95.3%']] },
    'blood-bank':{ title:'Blood Bank & Transfusion', subtitle:'Type and screen, crossmatch, inventory, issue, transfusion monitoring and traceability.', metrics:[['Units available','418','All products'],['Crossmatches pending','17','6 STAT'],['Massive transfusion','1','MOI active'],['Expiring < 48h','12','Review']] },
    radiology:{ title:'Radiology & PACS', subtitle:'Protocoling, scheduling, modality worklists, DICOM imaging, reporting and critical finding communication.', metrics:[['Open studies','118','12 urgent'],['CT turnaround','74 min','Down 13%'],['Critical findings','4','2 pending'],['Modalities online','26 / 28','92.9%']] },
    theatre:{ title:'Theatre & Procedures', subtitle:'Case scheduling, pre-op readiness, implants, intra-operative record, sterilization and recovery.', metrics:[['Cases today','42','7 urgent'],['On-time starts','78%','Target 85%'],['Delayed cases','6','2 blood-related'],['OR utilization','83%','MNH + MOI']] },
    anesthesia:{ title:'Anesthesia', subtitle:'Pre-anesthesia assessment, airway, medications, device observations, intra-operative events and PACU handoff.', metrics:[['Active anesthetics','11','Network'],['Pre-op reviews due','19','Today'],['PACU census','14','3 extended'],['Device feeds','96%','2 offline']] },
    maternity:{ title:'Maternity, Newborn & Child Health', subtitle:'ANC, labour, digital partograph, delivery, newborn linkage, PNC, immunization and danger-sign alerts.', metrics:[['Women in labour','24','5 high risk'],['Births today','17','MNH network'],['PPH risk alerts','3','Assigned'],['PNC follow-up due','68','Next 7 days']] },
    cardiology:{ title:'JKCI Cardiology & Cardiac Surgery', subtitle:'ECG, echo, cath lab, hemodynamics, cardiac surgery, devices and longitudinal specialty care.', metrics:[['Cardiology census','122','Today'],['Cath lab cases','8','2 urgent'],['Critical echo findings','3','Acknowledgement'],['ICU occupancy','89%','JKCI']] },
    orthopaedics:{ title:'MOI Orthopaedics, Trauma & Neurosurgery', subtitle:'Trauma activation, neurovascular observations, implants, theatre, rehabilitation and outcomes.', metrics:[['Trauma patients','42','8 red acuity'],['Theatre cases','18','6 urgent'],['ICU occupancy','92%','22 / 24'],['Implant traceability','100%','Today']] },
    oncology:{ title:'ORCI Oncology & Infusion', subtitle:'Staging, protocols, chemotherapy, radiotherapy, infusion safety, toxicity monitoring and outcomes.', metrics:[['Infusions today','86','7 delayed'],['Protocol checks','100%','Passed'],['Neutropenia alerts','5','Assigned'],['Radiotherapy fractions','112','Today']] },
    'critical-care':{ title:'Critical Care', subtitle:'ICU flowsheets, ventilator/device data, early warning, multidisciplinary rounds and capacity.', metrics:[['ICU occupancy','91%','63 / 69'],['Ventilated patients','24','6 at MOI'],['High EWS alerts','8','2 unassigned'],['Device feeds online','94%','3 offline']] },
    rehab:{ title:'Rehabilitation, Mental Health & Dental', subtitle:'Configurable assessments, treatment plans, outcomes, scheduling and patient education.', metrics:[['Appointments today','196','Services'],['Plans due review','34','This week'],['Outcome forms complete','82%','Target 90%'],['Tele-consults','18','Today']] },
    revenue:{ title:'Revenue Cycle, Insurance & Claims', subtitle:'Eligibility, authorization, charge capture, cashiering, coding, claims, denials and reconciliation.', metrics:[['Claims submitted','2,184','Today'],['First-pass acceptance','91.6%','Target 95%'],['Denial workqueue','312','TZS 418M'],['Cashier variance','0.4%','Within target']] },
    supply:{ title:'Supply Chain & Assets', subtitle:'Procurement, warehouse, stock, batch/expiry, cold chain, equipment and maintenance.', metrics:[['Stock-out risks','19','6 critical'],['Expiring < 90 days','TZS 84M','Review'],['Open purchase orders','74','18 overdue'],['Devices down','12','Network']] },
    'public-health':{ title:'Public Health, Registries & Surveillance', subtitle:'Notifiable diseases, HIV/TB/NCD registries, immunization, outbreak thresholds and automated reporting.', metrics:[['Notifiable events','18','Today'],['Unverified alerts','4','Investigate'],['DHIS2 completeness','97.2%','Current month'],['Care gaps open','4,118','Registry']] },
    quality:{ title:'Quality, Safety & Infection Prevention', subtitle:'Incidents, near misses, HAI monitoring, antimicrobial stewardship, audits and accreditation.', metrics:[['Open incidents','21','4 severe'],['HAI rate','3.1 / 1,000','Down 0.4'],['IPC audits due','9','This week'],['AMS interventions','34','71% accepted']] },
    analytics:{ title:'Analytics, M&E & Research', subtitle:'Operational, clinical, financial, public-health and research intelligence with governed access.', metrics:[['Data completeness','96.4%','Mandatory fields'],['Interface success','99.2%','24h'],['Dashboard users','1,288','Today'],['Research workspaces','14','Approved']] },
    workforce:{ title:'Workforce, Credentialing & Learning', subtitle:'Provider directory, licence verification, rosters, competency, training and in-system learning.', metrics:[['Active users','8,426','Pilot network'],['Credentials expiring','37','Next 60 days'],['Training complete','84%','Cohort'],['Open shifts','26','Today']] },
    telehealth:{ title:'Telehealth & Remote Care', subtitle:'Scheduled video, audio and store-and-forward care linked to appointments, encounters, documentation and orders.', metrics:[['Scheduled sessions','24','Today'],['In progress','6','Live'],['Readiness tasks','11','3 due'],['Completed','43','Last 24h']] },
    admin:{ title:'System Administration & Security', subtitle:'Users, roles, facilities, terminology, interfaces, audit, downtime, release governance and service management.', metrics:[['Core availability','99.96%','30 days'],['Open incidents','19','3 priority 1/2'],['Interfaces healthy','84 / 87','96.6%'],['Privileged access reviews','12','Due']] }
  };

  const state = {
    role:'physician', route:'today-patients', facility:'MNH-UPANGA', language:'en', facilities:[], modules:[], accessCatalog:null, adminUsers:[], selectedPatientId:'TZ-MPI-00073100', selectedEncounterId:null, selectedFlowSheetId:null, selectedWorkqueueId:null, notificationSince:null, notificationPoller:null, chartTab:'summary', tracker:[], notifications:4, registrationMatches:[], pendingRegistration:null, recentDischarges:[], token:sessionStorage.getItem('umojaAfyaToken')||'', account:null, offlineSession:false, speechRecognition:null, mediaRecorder:null, audioStream:null, audioChunks:[], audioBlob:null, audioObjectUrl:null, audioStartedAt:null, audioTimer:null, audioSessionId:null, pendingAudioDraft:'', v9AudioSessionId:null, patientStationWorkspace:'summary', registrationWorkspace:'identity', selectedBedUnit:null, orderCatalogCategories:[], orderCatalogItems:[], selectedOrderable:null, orderCatalogSearch:'', orderCatalogCategory:'', messageFolder:'INBOX', selectedMessageId:null, selectedAdminUserId:null, adminMatrixScope:'functions', facilityContextTree:null, selectedSpecialty:'GENERAL_MEDICINE', countryCode:localStorage.getItem('umojaCountry')||'', countrySelected:false
  };

  async function api(path, options = {}) {
    const offline=window.UmojaOffline;
    const authHeader = state.token ? {Authorization:`Bearer ${state.token}`} : {};
    const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
    const countryHeader=state.countryCode?{'X-Country-Code':state.countryCode}:{};
    const defaultHeaders = isFormData ? {...authHeader,...countryHeader} : {'Content-Type':'application/json', ...authHeader, ...countryHeader};
    const config = { ...options, headers:{...defaultHeaders, ...(options.headers || {})} };
    const method=String(config.method||'GET').toUpperCase();
    const queueable=Boolean(offline?.queueable(path,config));
    const operationId=queueable?offline.createOperationId():null;
    const createdAt=operationId?new Date().toISOString():null;
    if(operationId)config.headers['X-Idempotency-Key']=operationId;
    if(method!=='GET'&&!navigator.onLine){
      if(!queueable)throw new Error('This safety-critical workflow requires an online connection.');
      const queued=await offline.enqueue(path,config,{operationId,createdAt,countryCode:state.countryCode,facilityCode:operationFacility()});
      updateOfflineUi();
      toast('Saved securely offline','The transaction is in the encrypted outbox and will synchronize after reconnection.');
      return queued;
    }
    let response;
    try{response=await fetch(`${API}${path}`, config);}
    catch(error){
      if(method==='GET'){
        const cached=await offline?.cachedResponse(path);
        if(cached!==null&&cached!==undefined)return cached;
      }
      if(queueable){
        const queued=await offline.enqueue(path,config,{operationId,createdAt,countryCode:state.countryCode,facilityCode:operationFacility()});
        updateOfflineUi();
        toast('Connection interrupted','The transaction was secured in the local outbox for reconciliation.');
        return queued;
      }
      throw error;
    }
    let data = null;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) data = await response.json();
    else data = await response.text();
    if (!response.ok) {
      let message=response.statusText || 'Request failed';
      if(typeof data==='object'){
        if(Array.isArray(data.detail)) message=data.detail.map(item=>`${(item.loc||[]).slice(-1)[0]||'field'}: ${item.msg}`).join(' · ');
        else message=data.detail?.message || data.detail || data.message || message;
      } else if(data) message=data;
      const error = new Error(String(message));
      error.status = response.status;
      error.data = data;
      throw error;
    }
    if(method==='GET')await offline?.cacheResponse(path,data);
    return data;
  }

  async function apiBlob(path){
    const headers=state.token?{Authorization:`Bearer ${state.token}`}:{},country=state.countryCode?{'X-Country-Code':state.countryCode}:{};
    const response=await fetch(`${API}${path}`,{headers:{...headers,...country},cache:'no-store'});
    if(response.status===404)return null;
    if(!response.ok){let detail=response.statusText||'Profile photo request failed';try{const data=await response.json();detail=data.detail||detail;}catch(_){}throw new Error(String(detail));}
    return response.blob();
  }

  async function v1016ProfilePhotoObjectUrl(user){
    if(!user?.profile_photo_url)return null;
    state.v1016ProfilePhotoCache=state.v1016ProfilePhotoCache||new Map();
    if(state.v1016ProfilePhotoCache.has(user.profile_photo_url))return state.v1016ProfilePhotoCache.get(user.profile_photo_url);
    const blob=await apiBlob(user.profile_photo_url);if(!blob)return null;
    const url=URL.createObjectURL(blob);state.v1016ProfilePhotoCache.set(user.profile_photo_url,url);return url;
  }

  async function v1016HydrateProfilePhoto(element,user){
    if(!element)return;const url=await v1016ProfilePhotoObjectUrl(user);if(!url)return;
    if(element.tagName==='IMG')element.src=url;else element.innerHTML=`<img src="${url}" alt="${esc(user.display_name||'User')} profile photo">`;
  }

  function fmtDate(value) {
    if (!value) return '—';
    return new Intl.DateTimeFormat('en-GB', { dateStyle:'medium', timeStyle:value.includes?.('T') ? 'short' : undefined }).format(new Date(value));
  }
  function minutesSince(value) { return Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60000)); }
  function formatDuration(seconds = 0) {
    const h = Math.floor(seconds / 3600), m = Math.floor((seconds % 3600) / 60), s = seconds % 60;
    return [h,m,s].map(v=>String(v).padStart(2,'0')).join(':');
  }
  function statusLabel(status) { return String(status || '').replaceAll('_',' ').toLowerCase().replace(/\b\w/g,c=>c.toUpperCase()); }
  function badgeClass(value) {
    const v = String(value || '').toUpperCase();
    if (['CRITICAL','HIGH','STAT','UNACKNOWLEDGED','STOPPED'].includes(v)) return 'danger';
    if (['MEDIUM','URGENT','PAUSED','WAITING_RESULTS','READY_FOR_DISCHARGE'].includes(v)) return 'warning';
    if (['LOW','RUNNING','FINAL','ACKNOWLEDGED','DISCHARGED','VERIFIED','OBTAINED'].includes(v)) return 'success';
    return 'neutral';
  }

  function saveState() {
    localStorage.setItem('umojaAfyaEnterpriseState', JSON.stringify({ role:state.role, facility:state.facility }));
  }
  function loadState() {
    try {
      const saved = JSON.parse(localStorage.getItem('umojaAfyaEnterpriseState') || '{}');
      if (roles.some(r=>r.id===saved.role)) state.role=saved.role;
      if (saved.facility) state.facility=saved.facility;
    } catch (_) {}
  }
  function currentRole() { const template=roles.find(r=>r.id===state.role)||roles[0]; if(!state.account)return template; const initials=state.account.display_name.split(/\s+/).map(x=>x[0]).filter(Boolean).slice(0,2).join('').toUpperCase(); return {...template,user:state.account.display_name,name:statusLabel(state.account.role_code||'Custom access'),initials}; }
  function currentFacility() { return state.facilities.find(f=>f.code===state.facility) || state.facilities[0] || {code:'MNH-UPANGA',name:'MNH Upanga'}; }

  async function init() {
    loadState();
    bindGlobalEvents();
    try{await window.UmojaOffline?.init();window.UmojaOffline?.subscribe(updateOfflineUi);}catch(error){console.warn('Offline vault unavailable',error);}
    try {
      const countryQuery=state.countryCode?`?country_code=${encodeURIComponent(state.countryCode)}`:'';
      const [health, facilities, modules] = await Promise.all([api('/health'), api('/facilities'+countryQuery), api('/modules')]);
      state.facilities = facilities;
      state.modules = modules;
      $('#apiStatus').textContent = `● API online · ${health.environment}`;
      $('#apiStatus').classList.remove('down');
      renderCountryLanding();
      if(state.token){
        try {
          const me=await api('/auth/me');
          if(me.authenticated){state.account=me;state.role=roles.some(r=>r.id===me.role_code)?me.role_code:'physician';state.facility=(me.facilities||[])[0]||me.facility_code||state.facility;openAuthenticatedApp();}
        } catch(_){state.token='';sessionStorage.removeItem('umojaAfyaToken');}
      }
    } catch (error) {
      $('#apiStatus').textContent = '● API unavailable';
      $('#apiStatus').classList.add('down');
      const offlineState=window.UmojaOffline?.state();
      $('#offlineUnlockPanel')?.classList.toggle('hidden',!offlineState?.enrolled||offlineState?.expired);
      toast(offlineState?.enrolled&&!offlineState?.expired?'Offline access available':'Backend unavailable',offlineState?.enrolled&&!offlineState?.expired?'Unlock the protected device vault to continue with cached records.':'Reconnect to the Umoja Afya server, then retry.');
    }
    renderFacilitySelect();
    if ('serviceWorker' in navigator && location.protocol !== 'file:') navigator.serviceWorker.register('/service-worker.js').then(registration=>registration.update()).catch(()=>{});
    document.body.classList.toggle('offline',!navigator.onLine);
    window.addEventListener('online',()=>{document.body.classList.remove('offline');updateOfflineUi();queueMicrotask(syncOfflineOutbox);});
    window.addEventListener('offline',()=>{document.body.classList.add('offline');updateOfflineUi();});
    window.addEventListener('umoja-offline-sync-request',syncOfflineOutbox);
    updateOfflineUi();
  }

  function renderFacilitySelect() {
    const select = $('#facilitySelect');
    const allowed=new Set(state.account?.facilities||[]);
    const visible=state.facilities.filter(f=>(!state.account||allowed.has(f.code))&&(!state.countryCode||f.country_code===state.countryCode));
    const items = visible.length ? visible : (state.facilities.length ? state.facilities : [{code:'MNH-UPANGA',name:'Muhimbili National Hospital — Upanga'}]);
    select.innerHTML = `${items.length>1?'<option value="ALL">All assigned facilities</option>':''}${items.map(f=>`<option value="${esc(f.code)}">${esc(f.name)}</option>`).join('')}`;
    select.value = [...select.options].some(option=>option.value===state.facility) ? state.facility : items[0].code;
    state.facility=select.value;
  }
  async function enterApp(usernameOverride=null) {
    const username=(usernameOverride||$('#loginUsername')?.value||'').trim();
    const password=$('#loginPassword')?.value || '';
    if(!username||!password)return toast('Sign-in incomplete','Enter both username and password.');
    const submit=$('#loginSubmit'); if(submit){submit.disabled=true;submit.textContent='Signing in…';}
    try {
      const auth=await api('/auth/login',{method:'POST',body:JSON.stringify({username,password,country_code:state.countryCode||'TZ'})});
      state.token=auth.access_token; state.account=auth.user; state.countryCode=auth.user.country_code||state.countryCode; localStorage.setItem('umojaCountry',state.countryCode); sessionStorage.setItem('umojaAfyaToken',state.token);
      state.offlineSession=false;
      state.role=roles.some(r=>r.id===auth.user.role_code)?auth.user.role_code:'physician';
      {const assigned=auth.user.facilities||[]; state.facility=assigned.includes('MNH-UPANGA')?'MNH-UPANGA':(auth.user.facility_code&&assigned.includes(auth.user.facility_code)?auth.user.facility_code:(assigned[0]||auth.user.facility_code||state.facility));}
      openAuthenticatedApp();
      queueMicrotask(syncOfflineOutbox);
    } catch(error) { toast('Sign-in failed',error.message); }
    finally {if(submit){submit.disabled=false;submit.textContent='Sign in';}}
  }
  function firstAllowedRoute(){
    const preference=[roleDefaults[state.role]||'dashboard','dashboard','patient-flow','patient-search','chart'];
    return preference.find(canOpenRoute)||Object.keys(routeFunctionMap).find(canOpenRoute)||'dashboard';
  }
  function openAuthenticatedApp(){
    state.route=canOpenRoute(state.route)?state.route:firstAllowedRoute(); saveState();
    $('#countryLanding')?.classList.add('hidden'); $('#loginOverlay').classList.add('hidden'); $('#app').setAttribute('aria-hidden','false'); applyCountryBranding();
    updateChrome(); renderFacilitySelect(); renderSidebar(); navigate(state.route); startNotificationPolling();
    updateOfflineUi();
  }
  function updateChrome() {
    const role=currentRole();
    $('#userInitials').textContent=role.initials; $('#userName').textContent=role.user; $('#userRole').textContent=role.name; $('#workspaceRole').textContent=`${role.name} Workspace`; $('#notificationCount').textContent=state.notifications;
  }
  function renderSidebar() {
    $('#primaryNav').innerHTML=navGroups.map(group=>{const items=group.items.filter(([route])=>canOpenRoute(route));return items.length?`<section class="nav-group"><h3>${esc(group.title)}</h3>${items.map(([route,label,icon])=>`<button class="nav-item ${state.route===route?'active':''}" data-route="${route}"><span>${icon}</span><em>${esc(label)}</em></button>`).join('')}</section>`:'';}).join('');
  }
  function navigate(route) {
    if(!canOpenRoute(route)){toast('Function not assigned','Ask IT to add this function to your user access matrix.');route=firstAllowedRoute();}
    state.route=route; renderSidebar(); render(); history.replaceState(null,'',`?route=${route}`); $('#mainContent').focus(); $('#sidebar')?.classList.remove('open'); document.body.classList.remove('mobile-nav-open');
  }

  function bindGlobalEvents() {
    document.addEventListener('click', async event => {
      const actionButton=event.target.closest('[data-action]'); if(actionButton) return handleAction(actionButton.dataset.action, actionButton);
      const modalAction=event.target.closest('[data-modal-action]'); if(modalAction) return handleModalAction(modalAction.dataset.modalAction, modalAction);
      const flowsheetButton=event.target.closest('[data-flowsheet-id]'); if(flowsheetButton){state.selectedFlowSheetId=flowsheetButton.dataset.flowsheetId;if(flowsheetButton.dataset.route)state.route=flowsheetButton.dataset.route;return navigate('flowsheets');}
      const patientButton=event.target.closest('[data-patient-id]'); if(patientButton){state.selectedPatientId=patientButton.dataset.patientId;if(patientButton.dataset.encounterId)state.selectedEncounterId=patientButton.dataset.encounterId;saveState();return navigate('chart');}
      const routeButton=event.target.closest('[data-route]'); if(routeButton) return navigate(routeButton.dataset.route,{preservePatient:routeButton.dataset.preservePatient==='true',source:'route-button'});
    });
    document.addEventListener('input', event=>{if(event.target.id==='patientSearchInput') debouncePatientSearch(event.target.value);});
    document.addEventListener('change', event=>{if(event.target.id==='usrTemplate') applyAccessTemplate(event.target.value);});
    $('#loginSubmit').addEventListener('click',()=>enterApp());
    $('#loginPassword').addEventListener('keydown',event=>{if(event.key==='Enter')enterApp();});
    $('#loginUsername').addEventListener('keydown',event=>{if(event.key==='Enter')enterApp();});
    $('#facilitySelect').addEventListener('change', event=>{state.facility=event.target.value;saveState();render();});
    $('#globalSearchButton').addEventListener('click',()=>navigate('patient-search'));
    $('#languageToggle').addEventListener('click',()=>{state.language=state.language==='en'?'sw':'en';$('#languageToggle').textContent=state.language.toUpperCase();toast('Language changed',state.language==='sw'?'Kiswahili interface selected.':'English interface selected.');render();});
    $('#notificationsButton').addEventListener('click',showNotifications);
    $('#userMenuButton').addEventListener('click',()=>{state.token='';state.account=null;state.offlineSession=false;sessionStorage.removeItem('umojaAfyaToken');window.UmojaOffline?.lock();$('#app').setAttribute('aria-hidden','true');$('#loginOverlay').classList.add('hidden');$('#countryLanding').classList.remove('hidden');toast('Signed out','Your Umoja Afya session has ended and the offline vault is locked.');});
    $('#modalClose').addEventListener('click',closeModal);
    $('#modalBackdrop').addEventListener('click',e=>{if(e.target.id==='modalBackdrop')closeModal();});
    $('#sidebarToggle').addEventListener('click',()=>$('#sidebar').classList.toggle('open'));
  }


  async function selectedPatient() {
    if(!state.selectedPatientId)return null;
    try{return await api(`/patients/${state.selectedPatientId}`);}catch(_){return null;}
  }
  function patientContextBanner(patient){
    if(!patient)return `<section class="patient-context-empty"><div><p class="eyebrow">Patient context required</p><h2>Select a patient record</h2><p>Clinical actions begin from patient lookup and the longitudinal chart.</p></div><button class="btn btn-primary" data-route="patient-search">Patient Search</button></section>`;
    return `<section class="patient-banner compact-patient-banner"><div><p class="eyebrow">Selected longitudinal record</p><h2>${esc(patient.full_name)}</h2><p>${esc(patient.mpi_id)} · ${esc(patient.mrn)} · ${esc(patient.sex)} · ${patient.date_of_birth?fmtDate(patient.date_of_birth):'DOB unavailable'} · ${esc(patient.payer||'Coverage not verified')}</p></div><div class="page-actions"><span class="badge ${patient.allergies&&String(patient.allergies).toLowerCase().includes('no known')?'success':'danger'}">${esc(patient.allergies||'Allergies not reviewed')}</span><button class="btn btn-sm" data-route="patient-search">Change patient</button><button class="btn btn-sm" data-route="chart">Open chart</button></div></section>`;
  }

  function pageHeader(eyebrow,title,subtitle,actions='') { return `<header class="page-header"><div><p class="eyebrow">${esc(eyebrow)}</p><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div><div class="page-actions">${actions}</div></header>`; }
  function metricCard(label,value,note,cls='') { return `<article class="metric-card ${cls}"><p>${esc(label)}</p><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`; }
  function renderLoading(title='Loading clinical workspace…') {
    const meta=typeof COUNTRY_META!=='undefined'?(COUNTRY_META[state.countryCode]||COUNTRY_META.TZ):null;
    $('#mainContent').innerHTML=`<div class="ua-branded-loader" role="status" aria-live="polite">
      <div class="ua-loader-orbit"><img src="/assets/umoja-logo-mark.png" alt="" /><span></span></div>
      <h2>${esc(title)}</h2><p>${esc(meta?.name||'Umoja Afya')} · Securing the current connected record</p>
    </div>`;
  }
  function releaseNotice() { return `<div class="module-disclaimer"><strong>Enterprise workflow:</strong> Record-driven clinical functions, closed-loop actions and audited access controls are active.</div>`; }

  async function render() {
    const map={ dashboard:renderDashboard, 'today-patients':renderTodayPatients, workqueues:renderWorkqueues, 'patient-flow':renderPatientFlow, registration:renderRegistration, 'patient-search':renderPatientSearch, chart:renderChart, flowsheets:renderFlowsheets, orders:renderOrders, results:renderResults, 'recent-discharges':renderRecentDischarges, scheduling:renderScheduling, 'bed-board':renderBedBoard, 'clinical-documentation':renderClinicalDocumentation, nursing:renderMedicationWorkspace, pharmacy:renderMedicationWorkspace, revenue:renderRevenueCycle, supply:renderSupplyChain, telehealth:renderTelehealth, analytics:renderEnterpriseAnalytics, admin:renderSystemAdmin, 'public-health':renderPublicHealth, quality:renderQuality };
    try { if(map[state.route]) await map[state.route](); else await renderGenericModule(state.route); }
    catch(error){ console.error(error); $('#mainContent').innerHTML=`${pageHeader('Application Error','Unable to load workspace','The requested clinical workspace could not be retrieved.')}<div class="alert danger"><strong>${esc(error.message)}</strong><br/>Verify the backend is running and retry.</div>`; }
  }


  function operationFacility(){return state.facility==='ALL'?'MNH-UPANGA':state.facility;}
  function nextStepButton(row){
    const step=row.next_step||'OPEN_RECORD';
    if(step==='ARRIVE')return `<button class="btn btn-sm btn-primary" data-action="today-arrive" data-appointment="${esc(row.appointment_id)}">Arrive</button>`;
    const transitions={CHECK_IN:'REGISTERED',COMPLETE_REGISTRATION:'REGISTERED',SEND_TO_TRIAGE:'WAITING_TRIAGE',TRIAGE:'TRIAGED',READY_FOR_PROVIDER:'READY_FOR_PROVIDER',ROOM_PATIENT:'ROOMED',START_VISIT:'IN_PROGRESS',REVIEW_RESULTS:'WAITING_RESULTS',DISCHARGE:'READY_FOR_DISCHARGE'};
    if(transitions[step]&&row.encounter_id)return `<button class="btn btn-sm" data-action="today-status" data-encounter="${esc(row.encounter_id)}" data-status="${transitions[step]}">${esc(statusLabel(step))}</button>`;
    return `<button class="btn btn-sm" data-patient-id="${esc(row.patient.mpi_id)}">Open Chart</button>`;
  }

  async function renderTodayPatients(){
    renderLoading("Loading today's patient operations…");
    const facility=operationFacility();
    const [data,rosters,walkins]=await Promise.all([api(`/today-patients?facility_code=${encodeURIComponent(facility)}&limit=100`),api(`/duty-rosters?facility_code=${encodeURIComponent(facility)}`),api(`/walk-ins?facility_code=${encodeURIComponent(facility)}&hours=24`)]);
    const c=data.counts;
    $('#mainContent').innerHTML=`${pageHeader('Patient Access & Scheduling',"Today's Patients & Front Desk Workflow",'Manage scheduled patients, duty-roster service points, arrivals, triage routing and walk-ins.',`<button class="btn btn-primary" data-action="start-walkin">Register Walk-In</button><button class="btn" data-route="workqueues">Open Workqueues</button>`)}
      <section class="ops-metric-grid">${metricCard('Expected',c.expected,'Today')}${metricCard('Arrived',c.arrived,'Workflow notified','success')}${metricCard('Checked In',c.checked_in,'Registration complete')}${metricCard('Waiting',c.waiting,'Triage queues','warning')}${metricCard('Ready for Provider',c.ready_for_provider,'Duty team')}${metricCard('Completed',c.completed,'Closed encounters','success')}</section>
      <section class="ops-layout"><article class="card ops-primary"><div class="card-header"><div><h2>Today’s Patients Report</h2><p>Record-linked patient worklist; actions update the encounter and notify connected teams.</p></div><div class="inline-actions"><input id="todaySearch" class="compact-input" placeholder="Name, MRN, phone, NIDA…"><button class="btn btn-sm" data-action="filter-today">Search</button></div></div><div class="table-wrap"><table class="data-table enterprise-table"><thead><tr><th>Time</th><th>Patient</th><th>MRN</th><th>Service</th><th>Status</th><th>Queue / Location</th><th>On-Duty Team</th><th>Next Step</th></tr></thead><tbody>${data.rows.map(row=>`<tr><td>${new Date(row.scheduled_start).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</td><td><button class="link-button" data-patient-id="${esc(row.patient.mpi_id)}">${esc(row.patient.full_name)}</button></td><td>${esc(row.patient.mrn)}</td><td>${esc(row.service)}</td><td><span class="badge ${badgeClass(row.status)}">${esc(statusLabel(row.status))}</span></td><td>${esc(row.queue||row.location||'—')}</td><td>${esc(row.on_duty_team)}</td><td>${nextStepButton(row)}</td></tr>`).join('')}</tbody></table></div></article>
      <aside class="ops-side"><article class="card"><div class="card-header"><div><h2>On-Duty Teams & Service Points</h2><p>Government-facility scheduling is roster and service-point driven.</p></div></div><div class="compact-list">${rosters.slice(0,12).map(r=>`<div class="roster-row"><div><strong>${esc(r.service_point.name)}</strong><small>${esc(r.service_point.clinic)} · ${esc(r.service_point.room||'Room TBD')}</small></div><div><strong>${esc(r.lead_provider||r.team_name)}</strong><small>${esc(String(r.shift_start).slice(0,5))}–${esc(String(r.shift_end).slice(0,5))} · Cap ${r.service_point.queue_capacity}</small></div></div>`).join('')}</div></article>
      <article class="card"><div class="card-header"><div><h2>Walk-In Workflow</h2><p>Search/create → quick registration → arrival → service point → triage/queue → provider.</p></div></div><div class="walkin-stepper">${['Search / Create','Quick Registration','Arrival','Service Point','Queue / Triage','Provider'].map((x,i)=>`<div><b>${i+1}</b><span>${x}</span></div>`).join('')}</div><button class="btn btn-primary full-width" data-action="start-walkin">Start Walk-In Registration</button><div class="mini-summary"><span><strong>${walkins.filter(w=>!['COMPLETED','CANCELLED'].includes(w.status)).length}</strong> active walk-ins</span><span><strong>${c.walk_ins_waiting||0}</strong> waiting</span></div></article></aside></section>`;
  }

  async function renderWorkqueues(){
    renderLoading('Loading operational workqueues…');
    const facility=operationFacility();
    const summary=await api(`/workqueues/summary?facility_code=${encodeURIComponent(facility)}`);
    const queues=summary.queues||[]; const totals=summary.totals||{};
    if(!state.selectedWorkqueueId&&queues.length)state.selectedWorkqueueId=queues[0].queue_id;
    let detail=null; if(state.selectedWorkqueueId)detail=await api(`/workqueues/${encodeURIComponent(state.selectedWorkqueueId)}/items?limit=50`);
    $('#mainContent').innerHTML=`${pageHeader('Operational Follow-Up','Workqueue Management','Monitor, assign, defer, route and resolve record-linked operational work across departments.',`<button class="btn" data-action="refresh-workqueues">Refresh</button>`)}
      <section class="ops-metric-grid">${metricCard('Active Queues',totals.active_queues||0,'Configured')}${metricCard('Active Items',totals.active_items||0,'Needs action')}${metricCard('Deferred',totals.deferred_items||0,'Scheduled follow-up')}${metricCard('Overdue',totals.overdue_items||0,'SLA exceeded','danger')}${metricCard('High Priority',totals.high_priority||0,'Escalate','warning')}${metricCard('Total Items',totals.total_items||0,'All statuses')}</section>
      <section class="workqueue-layout"><article class="card"><div class="card-header"><div><h2>Workqueue List</h2><p>Queues are function and workflow driven, with record context opened only when processing an item.</p></div></div><div class="table-wrap"><table class="data-table enterprise-table"><thead><tr><th>Queue</th><th>Service Area</th><th>Owner / Team</th><th>Active</th><th>Deferred</th><th>Total</th><th>Aging</th><th>Priority</th><th>Status</th></tr></thead><tbody>${queues.map(q=>`<tr class="${q.queue_id===state.selectedWorkqueueId?'selected-row':''}"><td><button class="link-button" data-action="open-workqueue" data-id="${esc(q.queue_id)}">${esc(q.name)}</button></td><td>${esc(q.service_area)}</td><td>${esc(q.owner_team)}</td><td>${q.metrics.active}</td><td>${q.metrics.deferred}</td><td>${q.metrics.total}</td><td>${q.metrics.avg_age_days} d</td><td><span class="badge ${q.metrics.high_priority?'warning':'neutral'}">${q.metrics.high_priority}</span></td><td><span class="badge success">Active</span></td></tr>`).join('')}</tbody></table></div></article>
      <aside class="card queue-detail"><div class="card-header"><div><h2>${esc(detail?.queue?.name||'Select a queue')}</h2><p>${esc(detail?.queue?.owner_team||'')}</p></div></div>${detail?`<div class="queue-detail-metrics">${metricCard('Active',detail.metrics.active,'')}${metricCard('Deferred',detail.metrics.deferred,'')}${metricCard('Overdue',detail.metrics.overdue,'','danger')}${metricCard('Oldest',detail.metrics.oldest_age_days+' d','')}</div><div class="queue-items">${detail.items.slice(0,20).map(item=>`<article class="queue-item"><div><strong>${esc(item.title)}</strong><p>${esc(item.patient?.full_name||'No patient context')} · ${esc(item.patient?.mrn||'')} · ${esc(item.reason)}</p><small>${esc(item.assigned_to||'Unassigned')} · Due ${fmtDate(item.due_at)}</small></div><div><span class="badge ${badgeClass(item.priority)}">${esc(item.priority)}</span><button class="btn btn-sm" data-action="queue-item-action" data-id="${esc(item.item_id)}" data-op="COMPLETE">Complete</button><button class="btn btn-sm" data-action="queue-item-action" data-id="${esc(item.item_id)}" data-op="DEFER">Defer</button>${item.patient?`<button class="btn btn-sm" data-patient-id="${esc(item.patient.mpi_id)}">Chart</button>`:''}</div></article>`).join('')}</div>`:'<div class="empty-state"><p>Select a queue.</p></div>'}</aside></section>`;
  }

  async function showWalkInModal(){
    const points=await api(`/service-points?facility_code=${encodeURIComponent(operationFacility())}`);
    openModal('Register Walk-In',`<div class="walkin-stepper modal-steps">${['Search / Create Patient','Reason','Register Arrival','Service Point / Queue','Coverage','Route'].map((x,i)=>`<div><b>${i+1}</b><span>${x}</span></div>`).join('')}</div><div class="form-grid"><label class="field full"><span>Patient MPI / selected record</span><input id="walkPatient" value="${esc(state.selectedPatientId||'')}" placeholder="Search patient first or enter MPI" /></label><label class="field full"><span>Reason for visit</span><textarea id="walkReason" required>Walk-in clinical assessment</textarea></label><label class="field"><span>Service point</span><select id="walkPoint">${points.map(p=>`<option value="${esc(p.service_point_id)}">${esc(p.name)} · ${esc(p.clinic)} · ${esc(p.room||'Room TBD')}</option>`).join('')}</select></label><label class="field"><span>Coverage route</span><select id="walkCoverage"><option>NHIF</option><option>Cash</option><option>Private Insurance</option><option>Exempted</option><option>Emergency</option></select></label><label class="field full"><span>Arrival notes</span><textarea id="walkNotes">Registered at front desk and routed using duty roster.</textarea></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="create-walkin">Register Arrival & Notify</button>`,'Walk-In Registration');
  }

  async function pollWorkflowNotifications(){
    if(!state.token)return;
    try{const data=await api(`/notifications?facility_code=${encodeURIComponent(operationFacility())}&limit=10`);const latest=data[0];if(latest&&latest.notification_id!==state.notificationSince){state.notificationSince=latest.notification_id;const message=state.language==='sw'?latest.message_sw:latest.message_en;toast('Workflow Notification',message,latest.payload?.duration_ms||1000);}}catch(_){}
  }
  function startNotificationPolling(){if(state.notificationPoller)return;pollWorkflowNotifications();state.notificationPoller=setInterval(pollWorkflowNotifications,APP_REFRESH_INTERVAL_MS);}

  async function renderDashboard() {
    renderLoading('Loading enterprise command summary…');
    const facility=state.facility==='ALL'?null:state.facility;
    const summary=await api(`/enterprise/summary${facility?`?facility_code=${facility}`:''}`);
    const flowAction=canOpenRoute('patient-flow')?'<button class="btn btn-primary" data-route="patient-flow">Open Patient Tracker</button>':'';
    const analyticsAction=canOpenRoute('analytics')?'<button class="btn" data-route="analytics">Analytics & M&E</button>':'';
    $('#mainContent').innerHTML=`${pageHeader('Enterprise Command Center','MNH First-Wave Operations','Aggregate hospital operations, safety and throughput indicators. Patient-level clinical detail remains inside the selected record.',`${analyticsAction}${flowAction}`)}
      <section class="grid grid-4">${metricCard('Active encounters',summary.active_encounters,'Current enterprise census')}${metricCard('Appointments / roster slots',summary.appointments_36h,'36-hour window')}${metricCard('Open referrals',summary.open_referrals,'Awaiting closure')}${metricCard('Open work items',summary.open_work_items,'Operational queues')}${metricCard('Unsigned notes',summary.unsigned_notes,'Documentation completion','warning')}${metricCard('Unverified medications',summary.medications_unverified,'Pharmacy safety queue','warning')}${metricCard('Available beds',summary.beds.available,`${summary.beds.total} total`,'success')}${metricCard('Stock-out risks',summary.stockout_risks,'Supply action','warning')}</section>
      <section class="split-panels"><article class="card"><div class="card-header"><div><h2>Bed and capacity summary</h2><p>Aggregate status only; use the ADT workspace for operational detail.</p></div></div><div class="card-body"><div class="grid grid-4">${metricCard('Available',summary.beds.available,'Ready')}${metricCard('Occupied',summary.beds.occupied,'In use')}${metricCard('Dirty / cleaning',summary.beds.dirty,'EVS workflow')}${metricCard('Blocked',summary.beds.blocked,'Operational hold')}</div></div></article><article class="card"><div class="card-header"><div><h2>Enterprise follow-up</h2><p>Summary indicators that require coordinated action.</p></div></div><div class="card-body"><div class="list"><div class="list-item"><span class="list-icon">▤</span><div><strong>${summary.unsigned_notes} unsigned clinical notes</strong><p>Open the selected patient record to review and sign.</p></div></div><div class="list-item"><span class="list-icon">Rx</span><div><strong>${summary.medications_unverified} medications awaiting verification</strong><p>Pharmacy action remains record-linked.</p></div></div><div class="list-item"><span class="list-icon">₮</span><div><strong>${summary.claim_denials} denied claims</strong><p>Current claim value ${formatTZS(summary.claim_value)}.</p></div></div></div></div></article></section>
      ${releaseNotice()}`;
  }

  const trackerColumns=[
    {key:'arrived',label:'Arrived / Registration',statuses:['PRE_REGISTERED','ARRIVED','WAITING_REGISTRATION','REGISTERED']},
    {key:'waiting',label:'Waiting for Triage',statuses:['WAITING_TRIAGE']},
    {key:'triaged',label:'Triaged / Ready',statuses:['TRIAGED','READY_FOR_PROVIDER']},
    {key:'roomed',label:'Roomed',statuses:['ROOMED']},
    {key:'progress',label:'In Progress / Results',statuses:['IN_PROGRESS','WAITING_RESULTS']},
    {key:'discharge',label:'Ready for Discharge',statuses:['READY_FOR_DISCHARGE']}
  ];
  function trackerActionButtons(encounter) {
    const s=encounter.status, actions=[];
    if(['PRE_REGISTERED','ARRIVED','WAITING_REGISTRATION'].includes(s)) actions.push(['REGISTERED','Register']);
    if(['ARRIVED','REGISTERED'].includes(s)) actions.push(['WAITING_TRIAGE','Send to Triage']);
    if(s==='WAITING_TRIAGE') return `<button class="tracker-primary-action" data-v1016-action="tracker-triage" data-patient-id="${esc(encounter.patient.mpi_id)}" data-encounter-id="${esc(encounter.encounter_id)}">Start Triage</button>`;
    if(s==='TRIAGED') return `<button class="tracker-primary-action" data-v1016-action="tracker-room" data-patient-id="${esc(encounter.patient.mpi_id)}" data-encounter-id="${esc(encounter.encounter_id)}">Room Patient</button><button data-v1016-action="provider-workflow" data-patient-id="${esc(encounter.patient.mpi_id)}" data-encounter-id="${esc(encounter.encounter_id)}">Provider Review</button>`;
    if(s==='READY_FOR_PROVIDER') return `<button class="tracker-primary-action" data-v1016-action="tracker-room" data-patient-id="${esc(encounter.patient.mpi_id)}" data-encounter-id="${esc(encounter.encounter_id)}">Room Patient</button><button data-v1016-action="provider-workflow" data-patient-id="${esc(encounter.patient.mpi_id)}" data-encounter-id="${esc(encounter.encounter_id)}">Provider Review</button>`;
    if(['ROOMED','IN_PROGRESS','WAITING_RESULTS'].includes(s)) return `<button class="tracker-primary-action" data-v1016-action="provider-workflow" data-patient-id="${esc(encounter.patient.mpi_id)}" data-encounter-id="${esc(encounter.encounter_id)}">${s==='WAITING_RESULTS'?'Resume Provider Review':s==='IN_PROGRESS'?'Open Visit':'Start Provider Visit'}</button>${s==='IN_PROGRESS'?`<button data-action="tracker-status" data-encounter="${esc(encounter.encounter_id)}" data-status="WAITING_RESULTS">Waiting Results</button>`:''}`;
    if(s==='READY_FOR_DISCHARGE') return `<button data-action="discharge" data-encounter="${encounter.encounter_id}">Discharge</button>`;
    return actions.map(([status,label])=>`<button data-action="tracker-status" data-encounter="${encounter.encounter_id}" data-status="${status}">${label}</button>`).join('');
  }
  function v10163CareReadyBoard(tracker,compact=false){
    const triaged=(tracker||[]).filter(item=>['TRIAGED','READY_FOR_PROVIDER'].includes(String(item.status))).slice(0,compact?5:12);
    const roomed=(tracker||[]).filter(item=>String(item.status)==='ROOMED').slice(0,compact?5:12);
    const lane=(title,items,kind)=>`<section class="v10163-care-lane"><header><div><span>${kind==='roomed'?'Roomed':'Triage completed'}</span><strong>${esc(title)}</strong></div><b>${items.length}</b></header><div>${items.map(item=>`<article><button class="v10163-care-patient" data-v1014-action="select-record" data-patient-id="${esc(item.patient.mpi_id)}"><strong>${esc(item.patient.full_name)}</strong><small>${esc(item.patient.mrn)} · ${esc(item.service)}</small><span>${esc(item.room||item.location||'Location pending')}</span></button>${kind==='roomed'?`<button class="ua-button compact primary" data-v1016-action="provider-workflow" data-patient-id="${esc(item.patient.mpi_id)}" data-encounter-id="${esc(item.encounter_id)}">Open visit</button>`:`<button class="ua-button compact primary" data-v1016-action="tracker-room" data-patient-id="${esc(item.patient.mpi_id)}" data-encounter-id="${esc(item.encounter_id)}">Room</button>`}</article>`).join('')||'<p>No patients in this stage.</p>'}</div></section>`;
    return `<section class="v10163-care-ready ${compact?'compact':''}" aria-label="Triage-complete and roomed patient lists"><div class="v10163-care-ready-title"><div><span>Patient Care</span><strong>Ready-to-see patients</strong><small>Completed triage and rooming stay linked to the active encounter.</small></div><button class="ua-button compact" data-route="patient-flow">Open full tracker</button></div><div class="v10163-care-lanes">${lane('Awaiting room or provider',triaged,'triaged')}${lane('Placed and ready',roomed,'roomed')}</div></section>`;
  }
  async function renderPatientFlow() {
    renderLoading();
    const query=state.facility==='ALL'?'':`?facility_code=${state.facility}`;
    const [tracker,discharges]=await Promise.all([api(`/tracker${query}`),api(`/recent-discharges?hours=24${state.facility==='ALL'?'':`&facility_code=${state.facility}`}`)]);
    state.tracker=tracker;
    $('#mainContent').innerHTML=`${pageHeader('Hospital Operations','Provider Patient Tracker','Providers can immediately see patients who have arrived, are waiting, triaged, roomed, in progress, awaiting results or ready for discharge.',`<button class="btn" data-route="recent-discharges">Recent Discharges (${discharges.length})</button><button class="btn btn-secondary" data-route="registration">+ Register / Arrive</button>`)}
      <section class="tracker-toolbar"><label class="field"><span>Service filter</span><select id="trackerServiceFilter"><option value="ALL">All services</option>${[...new Set(tracker.map(e=>e.service))].map(s=>`<option>${esc(s)}</option>`).join('')}</select></label><label class="field"><span>Acuity</span><select id="trackerAcuityFilter"><option value="ALL">All acuities</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></select></label><button class="btn" data-action="refresh-tracker">Refresh</button><span class="v10163-refresh-note">Background refresh: every 5 minutes</span></section>
      ${v10163CareReadyBoard(tracker)}
      <section class="patient-tracker">${trackerColumns.map(column=>{const items=tracker.filter(e=>column.statuses.includes(e.status));return `<article class="tracker-column"><header><h3>${column.label}</h3><span class="tracker-count">${items.length}</span></header>${items.map(e=>`<div class="tracker-card acuity-${String(e.acuity).toLowerCase().replaceAll(' ','-')}" data-patient-id="${e.patient.mpi_id}" data-encounter-id="${esc(e.encounter_id)}"><div class="patient-name">${esc(e.patient.full_name)}</div><div class="patient-meta"><span>${esc(e.patient.mrn)}</span><span>${esc(e.service)}</span><span>${esc(e.location)}</span></div><div class="patient-meta"><span class="badge ${badgeClass(e.acuity)}">${esc(e.acuity)}</span><span class="wait-time">${minutesSince(e.arrival_at)} min since arrival</span></div><div class="tracker-actions" onclick="event.stopPropagation()">${trackerActionButtons(e)}</div></div>`).join('')||'<div class="empty-state"><p>No patients</p></div>'}</article>`;}).join('')}</section>
      <div class="alert info"><strong>Workflow principle:</strong> Each status transition writes an audit event and updates the same encounter. Recent discharges remain available without crowding the active provider list.</div>`;
  }

  async function renderRegistration() {
    $('#mainContent').innerHTML=`${pageHeader('Patient Registration','Patient Identity, Registration & Consent','Search the national MPI before creating a record, then complete demographics, coverage, consent, arrival and encounter creation.',`<button class="btn" data-action="clear-registration">Clear</button><button class="btn btn-primary" data-action="submit-registration">Search & Register</button>`)}
      <div class="stepper"><div class="step active">1. Identity Search</div><div class="step">2. Demographics</div><div class="step">3. Coverage & Consent</div><div class="step">4. Encounter & Arrival</div></div>
      <section class="registration-layout"><article class="card"><div class="card-header"><div><h2>National MPI and registration</h2><p>Required fields vary by registration mode and facility policy.</p></div></div><div class="card-body"><form id="registrationForm" class="form-grid">
        <div class="field"><label>Registration mode</label><select name="registration_mode" id="regMode"><option value="STANDARD">Standard registration</option><option value="PRE_REGISTRATION">Pre-registration</option><option value="EMERGENCY">Emergency</option><option value="UNKNOWN">Unknown patient</option><option value="NEWBORN">Newborn</option></select></div>
        <div class="field"><label>Facility</label><select name="facility_code">${state.facilities.filter(f=>f.code!=='MUHAS').map(f=>`<option value="${f.code}" ${f.code===currentFacility().code?'selected':''}>${esc(f.name)}</option>`).join('')}</select></div>
        <div class="field"><label>First name *</label><input name="first_name" required /></div><div class="field"><label>Middle name</label><input name="middle_name" /></div><div class="field"><label>Last name *</label><input name="last_name" required /></div><div class="field"><label>Date of birth</label><input name="date_of_birth" type="date" /></div>
        <div class="field"><label>Sex *</label><select name="sex"><option>Female</option><option>Male</option><option>Unknown</option><option>Intersex</option></select></div><div class="field"><label>Phone</label><input name="phone" placeholder="+255" /></div><div class="field"><label>NIDA number</label><input name="nida_number" /></div><div class="field"><label>Next of kin</label><input name="next_of_kin" placeholder="Name and relationship" /></div>
        <div class="field full"><label>Address</label><input name="address" /></div><div class="field"><label>Region</label><input name="region" value="Dar es Salaam" /></div><div class="field"><label>District</label><input name="district" /></div>
        <div class="field"><label>Payer</label><select name="payer"><option>NHIF</option><option>UHI</option><option>iCHF</option><option>Cash</option><option>Employer</option><option>Exempt</option></select></div><div class="field"><label>Member number</label><input name="member_number" /></div><div class="field"><label>Consent status</label><select name="consent_status"><option value="OBTAINED">Obtained</option><option value="EMERGENCY_BASIS">Emergency legal basis</option><option value="GUARDIAN_OBTAINED">Guardian obtained</option><option value="DECLINED_OPTIONAL_SHARING">Declined optional sharing</option></select></div><div class="field"><label>Proxy / guardian</label><input name="proxy_name" /></div>
        <div class="field"><label>Encounter type</label><select name="encounter_type"><option>OUTPATIENT</option><option>EMERGENCY</option><option>INPATIENT</option><option>INFUSION</option><option>PROCEDURE</option></select></div><div class="field"><label>Service</label><input name="service" value="General Medicine" /></div><div class="field full"><label>Reason for visit</label><textarea name="reason_for_visit" placeholder="Chief complaint or referral reason"></textarea></div>
      </form><div class="alert info"><strong>Duplicate prevention:</strong> NIDA, phone, date of birth, first name and surname are checked before a new national MPI identity is created.</div></div></article>
      <aside><article class="card"><div class="card-header"><h2>Possible matches</h2></div><div class="card-body" id="registrationMatches">${state.registrationMatches.length?state.registrationMatches.map(renderDuplicate).join(''):'<div class="empty-state"><p>No search performed.</p></div>'}</div></article><article class="card"><div class="card-header"><h2>Registration controls</h2></div><div class="card-body"><div class="list"><div class="list-item"><span class="list-icon">◎</span><div><strong>Unknown patient workflow</strong><p>Creates a temporary identity that must be reconciled.</p></div></div><div class="list-item"><span class="list-icon">◌</span><div><strong>Newborn workflow</strong><p>Links infant and maternal records while awaiting formal identifiers.</p></div></div><div class="list-item"><span class="list-icon">▤</span><div><strong>Consent and proxy</strong><p>Captures legal basis, guardian and access restrictions.</p></div></div><div class="list-item"><span class="list-icon">₮</span><div><strong>Coverage</strong><p>Stores payer/member context for eligibility and claims.</p></div></div></div></div></article></aside></section>${releaseNotice()}`;
  }
  function renderDuplicate(p){return `<button class="duplicate-result" data-patient-id="${p.mpi_id}"><strong>${esc(p.full_name)} · ${esc(p.mpi_id)}</strong><small>${esc(p.mrn)} · DOB ${esc(p.date_of_birth||'unknown')} · ${esc(p.phone||'no phone')} · ${esc(p.payer||'no payer')}</small></button>`;}

  let patientSearchTimer;
  function debouncePatientSearch(value){clearTimeout(patientSearchTimer);patientSearchTimer=setTimeout(()=>performPatientSearch(value),250);}
  async function renderPatientSearch(){
    $('#mainContent').innerHTML=`${pageHeader('National Master Patient Index','Patient Search & MPI','Search by name, national MPI ID, MRN, phone or NIDA number.',`<button class="btn btn-primary" data-route="registration">+ New Registration</button>`)}<div class="search-bar"><input id="patientSearchInput" autofocus placeholder="Search name, MPI, MRN, phone or NIDA…" /><button class="btn" data-action="run-patient-search">Search</button></div><section class="card"><div class="card-header"><div><h2>Search results</h2><p>Open the longitudinal chart or review potential duplicates.</p></div></div><div class="card-body" id="patientSearchResults"><div class="empty-state"><p>Enter at least one search term.</p></div></div></section>`;
    await performPatientSearch('');
  }
  async function performPatientSearch(value){
    const target=$('#patientSearchResults');if(!target)return;target.innerHTML='<div class="empty-state"><p>Searching…</p></div>';
    const patients=await api(`/patients${value.trim()?`?search=${encodeURIComponent(value.trim())}`:''}`);
    target.innerHTML=patients.length?`<div class="table-wrap"><table><thead><tr><th>Patient</th><th>Identifiers</th><th>Demographics</th><th>Coverage</th><th></th></tr></thead><tbody>${patients.map(p=>`<tr><td><strong>${esc(p.full_name)}</strong><br/><small>${esc(p.mpi_id)}</small></td><td>${esc(p.mrn)}<br/><small>${esc(p.nida_number||'No NIDA')}</small></td><td>${esc(p.sex)} · ${esc(p.date_of_birth||'DOB unknown')}<br/><small>${esc(p.phone||'No phone')}</small></td><td>${esc(p.payer||'Not verified')}<br/><small>${esc(p.consent_status)}</small></td><td><button class="btn btn-sm" data-patient-id="${p.mpi_id}">Open Chart</button></td></tr>`).join('')}</tbody></table></div>`:'<div class="empty-state"><p>No matching patients.</p></div>';
  }

  const CHART_INPATIENT_TEMPLATES=new Set(['ADULT_INPATIENT','PAEDIATRIC_INPATIENT','NEONATAL','ICU_DEVICE','INTAKE_OUTPUT']);
  const CHART_INACTIVE_ADMIT_STATUSES=new Set(['CANCELLED','ON_HOLD','STOPPED','VOIDED','DISCONTINUED']);

  function chartHasAdmitOrder(orders,encounter){
    if(!encounter)return false;
    return (orders||[]).some(order=>{
      if(order.encounter_id!==encounter.encounter_id||CHART_INACTIVE_ADMIT_STATUSES.has(String(order.status||'').toUpperCase()))return false;
      const searchable=`${order.order_type||''} ${order.order_name||''}`.toLowerCase();
      return String(order.order_type||'').toUpperCase()==='ADT'||/\badmit\b|admission|inpatient/.test(searchable);
    });
  }
  function chartFlowScope(template){
    if(template?.code==='TRIAGE_AMBULATORY')return 'TRIAGE';
    if(CHART_INPATIENT_TEMPLATES.has(template?.code))return 'INPATIENT';
    return 'SPECIALTY';
  }
  function chartLatestObservation(flowsheets,templateCode,row){
    const candidates=[];
    (flowsheets||[]).filter(sheet=>sheet.template_code===templateCode).forEach(sheet=>(sheet.observations||[]).forEach(observation=>{
      if(observation.parameter===row.label||observation.parameter===row.code)candidates.push(observation);
    }));
    return candidates.sort((a,b)=>new Date(b.recorded_at)-new Date(a.recorded_at))[0]||null;
  }
  function chartFlowEntry(row,template,disabled){
    const common=`class="chart-flow-entry" data-chart-flow-input data-template-code="${esc(template.code)}" data-parameter="${esc(row.label)}" data-unit="${esc(row.unit||'')}" ${disabled?'disabled':''}`;
    if(row.type==='calculated')return '<span class="chart-flow-calculated">Calculated from documented values</span>';
    if(row.type==='choice'||row.type==='multiselect')return `<select ${common}><option value="">Select…</option>${(row.choices||[]).map(choice=>`<option value="${esc(choice)}">${esc(choice)}</option>`).join('')}</select>`;
    if(row.type==='boolean')return `<select ${common}><option value="">Select…</option><option value="Yes">Yes</option><option value="No">No</option></select>`;
    return `<input ${common} type="${row.type==='number'?'number':'text'}" ${row.type==='number'?'step="any"':''} placeholder="Document now">`;
  }
  function renderChartFlowSpreadsheet(patient,orders,flowsheets,templates,active){
    const admitted=chartHasAdmitOrder(orders,active);
    const canEdit=v1014Can('flowsheets.manage')&&!['DISCHARGED','TRANSFERRED','LEFT_WITHOUT_BEING_SEEN'].includes(active?.status);
    const rows=(templates||[]).flatMap(template=>v5FlattenTemplate(template).map(row=>({template,row,scope:chartFlowScope(template)})));
    return `<article class="card chart-flow-card">
      <div class="card-header chart-flow-heading"><div><p class="eyebrow">Always-ready clinical observations</p><h2>Chart Flowsheet</h2><p>Document triage, ambulatory and specialty values here. Inpatient rows activate only after an admit order exists for this encounter.</p></div><div class="chart-flow-status"><span class="badge success">Triage active</span><span class="badge ${admitted?'success':'neutral'}">Inpatient ${admitted?'active':'locked'}</span></div></div>
      <div class="chart-flow-toolbar"><label><span>View</span><select id="chartFlowScope"><option value="ALL">All variables</option><option value="TRIAGE">Triage & ambulatory</option><option value="INPATIENT">Inpatient</option><option value="SPECIALTY">Specialty</option></select></label><label class="chart-flow-search"><span>Find variable</span><input id="chartFlowSearch" placeholder="e.g. blood pressure, GCS, intake"></label><div class="chart-flow-encounter"><span>Recording against</span><strong>${esc(active?.encounter_id||'Longitudinal record')}</strong><small>${esc(active?.service||'No active encounter')}</small></div></div>
      ${!admitted?`<div class="chart-flow-lock-note"><strong>Inpatient rows are safely locked.</strong> Place an “Admit to inpatient service” order for ${esc(active?.encounter_id||'an active encounter')} to enable them.</div>`:''}
      <div class="chart-flow-table-wrap"><table class="chart-flow-table"><thead><tr><th>Scope</th><th>Group</th><th>Variable</th><th>Unit</th><th>Latest</th><th>Recorded</th><th>Document now</th></tr></thead><tbody>${rows.map(({template,row,scope})=>{
        const inpatient=scope==='INPATIENT';const locked=!canEdit||(inpatient&&!admitted);const latest=chartLatestObservation(flowsheets,template.code,row);
        return `<tr data-chart-flow-row data-scope="${scope}" data-search="${esc(`${template.name} ${row.group} ${row.label} ${row.code}`.toLowerCase())}" class="${locked?'locked':''}"><td><span class="chart-flow-scope ${scope.toLowerCase()}">${statusLabel(scope)}</span></td><td>${esc(row.group)}</td><td><strong>${esc(row.label)}</strong><small>${esc(template.name)} · ${esc(row.code)}</small></td><td>${esc(row.unit||'—')}</td><td>${latest?`<strong>${esc(latest.value)} ${esc(latest.unit||'')}</strong>`:'<span class="muted">—</span>'}</td><td>${latest?`${fmtDate(latest.recorded_at)}<small>${esc(latest.recorded_by||'')}</small>`:'<span class="muted">Not recorded</span>'}</td><td>${locked?`<span class="chart-flow-locked">${canEdit?'Admit order required':'Read only'}</span>`:chartFlowEntry(row,template,false)}</td></tr>`;
      }).join('')}</tbody></table></div>
      <div class="chart-flow-footer"><span>${rows.length} governed variables · values are patient and encounter linked</span><div><button class="btn" data-route="flowsheets">Open full flowsheet history</button><button class="btn btn-primary" data-action="save-chart-flowsheet" ${canEdit?'':'disabled'}>Save entered values</button></div></div>
    </article>`;
  }
  function filterChartFlowRows(){
    const scope=$('#chartFlowScope')?.value||'ALL';const query=($('#chartFlowSearch')?.value||'').trim().toLowerCase();
    $$('[data-chart-flow-row]').forEach(row=>{row.hidden=(scope!=='ALL'&&row.dataset.scope!==scope)||(query&&!row.dataset.search.includes(query));});
  }
  async function saveChartFlowEntries(){
    const context=state.chartFlowData;if(!context)throw new Error('Reload the patient chart and try again.');
    const entries=$$('[data-chart-flow-input]').filter(input=>!input.disabled&&String(input.value||'').trim());
    if(!entries.length)throw new Error('Enter at least one flowsheet value.');
    const grouped=new Map();entries.forEach(input=>{const code=input.dataset.templateCode;if(!grouped.has(code))grouped.set(code,[]);grouped.get(code).push(input);});
    let saved=0;
    for(const [templateCode,inputs] of grouped){
      const template=context.templates.find(item=>item.code===templateCode);const inpatient=CHART_INPATIENT_TEMPLATES.has(templateCode);
      if(inpatient&&!context.admitted)throw new Error('An active admit patient order is required before inpatient observations can be saved.');
      let sheet=context.flowsheets.find(item=>item.template_code===templateCode&&(item.encounter_id||null)===(context.active?.encounter_id||null)&&item.status!=='STOPPED');
      if(!sheet)sheet=await api('/flowsheets',{method:'POST',body:JSON.stringify({patient_mpi_id:context.patient.mpi_id,encounter_id:context.active?.encounter_id||null,name:template?.name||'Clinical Flowsheet',template_code:templateCode,cadence_minutes:template?.cadence_minutes||15,parameters:v5FlattenTemplate(template).map(row=>row.label),owner:currentRole().user})});
      for(const input of inputs){await api(`/flowsheets/${sheet.flowsheet_id}/observations`,{method:'POST',body:JSON.stringify({parameter:input.dataset.parameter,value:String(input.value).trim(),unit:input.dataset.unit||null,source:'MANUAL',recorded_by:currentRole().user})});saved++;}
    }
    toast('Chart flowsheet saved',`${saved} observation${saved===1?'':'s'} recorded for ${context.patient.full_name}.`);return renderChart();
  }

  async function renderChart(){
    renderLoading('Loading longitudinal record…');
    const patient=await api(`/patients/${state.selectedPatientId}`);
    const [orders,results,flowsheets,templates]=await Promise.all([api(`/orders?patient_mpi_id=${state.selectedPatientId}`),api(`/results?patient_mpi_id=${state.selectedPatientId}`),api(`/flowsheets?patient_mpi_id=${state.selectedPatientId}`),api('/flowsheet-templates')]);
    const active=patient.encounters.find(e=>e.encounter_id===state.selectedEncounterId)||patient.encounters.find(e=>!['DISCHARGED','TRANSFERRED','LEFT_WITHOUT_BEING_SEEN'].includes(e.status))||patient.encounters[0];
    state.selectedEncounterId=active?.encounter_id||null;
    state.chartFlowData={patient,orders,flowsheets,templates,active,admitted:chartHasAdmitOrder(orders,active)};
    $('#mainContent').innerHTML=`${pageHeader('Longitudinal Clinical Record','Patient Chart','One patient identity, shared problems, medications, allergies, encounters, results and follow-up.',`<button class="btn" data-route="patient-flow">Back to Tracker</button><button class="btn btn-secondary" data-action="new-flowsheet">+ Flowsheet</button><button class="btn btn-primary" data-action="new-order" data-encounter="${active?.encounter_id||''}">+ Order</button>`)}
      <section class="chart-banner"><div><h2>${esc(patient.full_name)}</h2><p>${esc(patient.mpi_id)} · ${esc(patient.mrn)} · ${esc(patient.sex)} · DOB ${esc(patient.date_of_birth||'unknown')} · ${esc(patient.phone||'no phone')}</p><label class="chart-encounter-picker"><span>Working encounter</span><select id="chartEncounterSelect">${patient.encounters.map(e=>`<option value="${esc(e.encounter_id)}" ${e.encounter_id===active?.encounter_id?'selected':''}>${esc(e.encounter_id)} · ${esc(e.service)} · ${esc(statusLabel(e.status))} · ${fmtDate(e.arrival_at)}</option>`).join('')}</select><small>${['DISCHARGED','TRANSFERRED','LEFT_WITHOUT_BEING_SEEN'].includes(active?.status)?'Historical encounter — review only; create a new visit for new physical care.':'All visit activity will be linked to this encounter.'}</small></label></div><div class="chart-alerts"><span class="chart-alert">Allergies: ${esc(patient.allergies)}</span><span class="chart-alert">Problems: ${esc(patient.problems)}</span></div></section>
      <div class="tabbar">${[['summary','Summary'],['encounters','Encounters'],['orders','Orders'],['results','Results'],['flowsheets','Flowsheets'],['notes','Notes'],['medications','Medications'],['audit','Audit']].map(([id,label])=>`<button class="tab ${state.chartTab===id?'active':''}" data-action="chart-tab" data-tab="${id}">${label}</button>`).join('')}</div>
      <section class="chart-workspace" id="chartWorkspace">${renderChartTab(patient,orders,results,flowsheets,templates,active)}</section>`;
  }
  function renderChartTab(patient,orders,results,flowsheets,templates,active){
    if(state.chartTab==='summary')return `<section class="grid grid-main"><article class="card"><div class="card-header"><h2>Clinical snapshot</h2></div><div class="card-body"><div class="grid grid-2"><div><p class="eyebrow">Active problems</p><p>${esc(patient.problems)}</p></div><div><p class="eyebrow">Medication list</p><p>${esc(patient.medications)}</p></div><div><p class="eyebrow">Allergies</p><p>${esc(patient.allergies)}</p></div><div><p class="eyebrow">Coverage and consent</p><p>${esc(patient.payer||'Not verified')} · ${esc(patient.consent_status)}</p></div></div></div></article><article class="card"><div class="card-header"><h2>Current encounter</h2></div><div class="card-body">${active?`<div class="list-item"><span class="list-icon">↔</span><div><strong>${esc(active.service)}</strong><p>${statusLabel(active.status)} · ${esc(active.location)} · ${fmtDate(active.arrival_at)}</p><small>${esc(active.encounter_id)}</small></div></div>`:'No encounters'}</div></article></section>${renderChartFlowSpreadsheet(patient,orders,flowsheets,templates,active)}`;
    if(state.chartTab==='encounters')return `<div class="list">${patient.encounters.map(e=>`<button class="list-item chart-encounter-row ${e.encounter_id===active?.encounter_id?'active':''}" data-v1016-action="select-chart-encounter" data-encounter-id="${esc(e.encounter_id)}"><span class="list-icon">${e.status==='DISCHARGED'?'✓':'↔'}</span><div><strong>${esc(e.service)} · ${esc(e.encounter_type)}</strong><p>${esc(e.facility.name)} · ${statusLabel(e.status)} · ${fmtDate(e.arrival_at)}</p>${e.discharge_summary?`<p>${esc(e.discharge_summary)}</p>`:''}<small>${esc(e.encounter_id)}</small></div><div class="list-meta"><span class="badge ${badgeClass(e.acuity)}">${esc(e.acuity)}</span><span>Work in this encounter</span></div></button>`).join('')}</div>`;
    if(state.chartTab==='orders')return ordersTable(orders);
    if(state.chartTab==='results')return resultsTable(results);
    if(state.chartTab==='flowsheets')return `<div class="list">${flowsheets.map(f=>`<button class="list-item" data-route="flowsheets" data-flowsheet-id="${f.flowsheet_id}"><span class="list-icon">⌁</span><div><strong>${esc(f.name)}</strong><p>${statusLabel(f.status)} · ${formatDuration(f.elapsed_seconds)} · every ${f.cadence_minutes} min</p></div><div class="list-meta"><span class="badge ${badgeClass(f.status)}">${f.status}</span></div></button>`).join('')||'<div class="empty-state"><p>No flowsheets.</p></div>'}</div>`;
    if(state.chartTab==='notes')return `<div class="grid grid-2"><article class="card"><div class="card-header"><h2>Clinical documentation</h2><button class="btn btn-primary btn-sm" data-v9-action="new-note">+ New Note</button></div><div class="card-body"><div class="list"><div class="list-item"><span class="list-icon">▤</span><div><strong>Admission history and physical</strong><p>Signed · current encounter</p></div></div><div class="list-item"><span class="list-icon">▤</span><div><strong>Progress note</strong><p>Smart template with problem-oriented assessment and plan</p></div></div><div class="list-item"><span class="list-icon">▤</span><div><strong>Discharge summary</strong><p>Pulls reconciled problems, medications, results and follow-up</p></div></div></div></div></article><article class="card"><div class="card-header"><h2>Documentation tools</h2></div><div class="card-body"><div class="alert info"><strong>Smart tools:</strong> reusable phrases, templates, order sets and care-plan content should be governed centrally and locally configurable.</div></div></article></div>`;
    if(state.chartTab==='medications')return `<div class="grid grid-2"><article class="card"><div class="card-header"><h2>Home and active medications</h2></div><div class="card-body"><p>${esc(patient.medications)}</p></div></article><article class="card"><div class="card-header"><h2>Medication safety</h2></div><div class="card-body"><div class="alert danger"><strong>Allergy review:</strong> ${esc(patient.allergies)}</div><div class="alert info" style="margin-top:10px">Medication reconciliation, formulary, renal dosing and interaction checking connect to Pharmacy and eMAR.</div></div></article></div>`;
    return `<div class="empty-state"><h2>Audit access</h2><p>Use the System Administration workspace to review detailed access and change history.</p><button class="btn" data-route="admin">Open Audit Workspace</button></div>`;
  }

  async function renderFlowsheets(){
    renderLoading('Loading flowsheets…');
    const patient=await selectedPatient();
    if(!patient){$('#mainContent').innerHTML=`${pageHeader('Nursing and Device Documentation','Patient-linked Flowsheets','Select a patient record before reviewing flowsheets.')}${patientContextBanner(null)}`;return;}
    const flowsheets=await api(`/flowsheets?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`);
    if(!state.selectedFlowSheetId&&flowsheets[0])state.selectedFlowSheetId=flowsheets[0].flowsheet_id;
    const selected=flowsheets.find(f=>f.flowsheet_id===state.selectedFlowSheetId)||flowsheets[0];
    $('#mainContent').innerHTML=`${pageHeader('Nursing and Device Documentation','Flowsheets with Start, Pause, Resume, Change & Stop','Time-controlled clinical documentation for observations, devices, neurovascular checks, infusions, intake/output and specialty monitoring.',`<button class="btn" data-route="chart">Open Patient Chart</button><button class="btn btn-primary" data-action="new-flowsheet">+ New Flowsheet</button>`)}
      ${patientContextBanner(patient)}<section class="flowsheet-grid"><aside><div class="card"><div class="card-header"><div><h2>Patient flowsheets</h2><p>Select an active or historical sheet.</p></div></div><div class="card-body">${flowsheets.map(f=>`<button class="flowsheet-card ${selected?.flowsheet_id===f.flowsheet_id?'selected':''}" data-flowsheet-id="${f.flowsheet_id}"><header><h3>${esc(f.name)}</h3><span class="badge ${badgeClass(f.status)}">${f.status}</span></header><p>${esc(f.patient_name)} · ${formatDuration(f.elapsed_seconds)} · ${f.cadence_minutes} min cadence</p></button>`).join('')||'<div class="empty-state"><p>No flowsheets for this patient.</p></div>'}</div></div></aside>
      <main>${selected?renderFlowSheetDetail(selected):'<div class="empty-state"><h2>Create a flowsheet</h2><p>Start with a clinical template or a custom parameter list.</p><button class="btn btn-primary" data-action="new-flowsheet">Create</button></div>'}</main></section>${releaseNotice()}`;
    if(selected?.status==='RUNNING')startTimerTicker(selected.flowsheet_id,selected.elapsed_seconds);
  }
  function renderFlowSheetDetail(f){
    return `<article class="card"><div class="card-header"><div><h2>${esc(f.name)}</h2><p>${esc(f.patient_name)} · ${esc(f.flowsheet_id)} · ${esc(f.template_code)}</p></div><div class="timer" id="flowsheetTimer" data-seconds="${f.elapsed_seconds}">${formatDuration(f.elapsed_seconds)}</div></div><div class="card-body">
      <div class="control-strip">${f.status==='DRAFT'?'<button class="btn btn-primary" data-action="flowsheet-control" data-control="START">Start</button>':''}${f.status==='RUNNING'?'<button class="btn btn-warning" data-action="flowsheet-control" data-control="PAUSE">Pause</button>':''}${f.status==='PAUSED'?'<button class="btn btn-primary" data-action="flowsheet-control" data-control="RESUME">Resume</button>':''}${f.status!=='STOPPED'?'<button class="btn" data-action="change-flowsheet">Change</button><button class="btn btn-danger" data-action="flowsheet-control" data-control="STOP">Stop</button>':''}<span class="badge ${badgeClass(f.status)}">${statusLabel(f.status)}</span><span class="badge neutral">Every ${f.cadence_minutes} min</span></div>
      <h3>Record observation</h3><div class="observation-entry"><label class="field"><span>Parameter</span><select id="obsParameter">${f.parameters.map(p=>`<option>${esc(p)}</option>`).join('')}</select></label><label class="field"><span>Value</span><input id="obsValue" /></label><label class="field"><span>Unit</span><input id="obsUnit" /></label><button class="btn btn-primary" data-action="record-observation">Record</button></div>
      <div class="grid grid-2"><section><h3>Latest observations</h3><table class="parameter-table"><thead><tr><th>Parameter</th><th>Value</th><th>Recorded</th></tr></thead><tbody>${f.observations.slice(0,12).map(o=>`<tr><td>${esc(o.parameter)}</td><td><strong>${esc(o.value)} ${esc(o.unit||'')}</strong></td><td>${fmtDate(o.recorded_at)}<br/><small>${esc(o.recorded_by)}</small></td></tr>`).join('')||'<tr><td colspan="3">No observations recorded.</td></tr>'}</tbody></table></section><section><h3>Control and audit history</h3><div class="event-log">${f.events.map(e=>`<div class="event-row"><strong>${esc(e.action)}</strong><span>${fmtDate(e.occurred_at)} · ${esc(e.actor)}${e.note?`<br/>${esc(e.note)}`:''}</span></div>`).join('')}</div></section></div>
    </div></article>`;
  }
  let timerInterval;
  function startTimerTicker(id,seconds){clearInterval(timerInterval);let current=seconds;timerInterval=setInterval(()=>{if(state.selectedFlowSheetId!==id){clearInterval(timerInterval);return;}current++;const el=$('#flowsheetTimer');if(el)el.textContent=formatDuration(current);},1000);}

  async function renderOrders(){
    renderLoading();
    const patient=await selectedPatient();
    if(!patient){$('#mainContent').innerHTML=`${pageHeader('Order Entry','Patient-linked Orders','Select a patient before reviewing or creating orders.')}${patientContextBanner(null)}`;return;}
    const orders=await api(`/orders?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`);
    $('#mainContent').innerHTML=`${pageHeader('Computerized Provider Order Entry','Orders for the Selected Record','Create and manage laboratory, imaging, medication, blood, procedure and referral orders within the patient chart.',`<button class="btn btn-primary" data-action="new-order">+ New Order</button>`)}${patientContextBanner(patient)}${ordersTable(orders)}${releaseNotice()}`;
  }
  function orderCourseButtons(order){
    const status=String(order.status||'').toUpperCase();
    const buttons=[];
    if(['SIGNED','SCHEDULED','COLLECTED','READY','IN_PROGRESS'].includes(status))buttons.push(`<button class="btn btn-sm" data-action="order-course" data-id="${order.order_id}" data-op="HOLD">Hold</button>`);
    if(status==='ON_HOLD')buttons.push(`<button class="btn btn-sm btn-primary" data-action="order-course" data-id="${order.order_id}" data-op="RESUME">Resume</button>`);
    if(['SIGNED','SCHEDULED','COLLECTED','READY','IN_PROGRESS','ON_HOLD'].includes(status))buttons.push(`<button class="btn btn-sm" data-action="order-course" data-id="${order.order_id}" data-op="CANCEL">Cancel</button>`);
    if(status==='CANCELLED')buttons.push(`<button class="btn btn-sm btn-primary" data-action="order-course" data-id="${order.order_id}" data-op="REINSTATE">Reinstate</button>`);
    return buttons.join('');
  }
  function ordersTable(orders){return `<section class="card"><div class="card-header"><div><h2>Patient order activity</h2><p>Current state, course-change controls and complete order history.</p></div></div><div class="card-body"><div class="table-wrap"><table><thead><tr><th>Order</th><th>Type</th><th>Priority</th><th>Status</th><th>Ordered</th><th>Course</th></tr></thead><tbody>${orders.map(o=>`<tr><td><strong>${esc(o.order_name)}</strong><br/><small>${esc(o.indication||'No indication documented')} · ${esc(o.order_id)}</small>${o.history?.length?`<details><summary>${o.history.length} course change(s)</summary>${o.history.map(h=>`<small>${fmtDate(h.occurred_at)} · ${esc(h.action)} · ${esc(h.actor)} · ${esc(h.reason)}</small><br/>`).join('')}</details>`:''}</td><td>${esc(o.order_type)}</td><td><span class="badge ${badgeClass(o.priority)}">${esc(o.priority)}</span></td><td>${dot(o.status)}${statusLabel(o.status)}</td><td>${fmtDate(o.ordered_at)}<br/><small>${esc(o.ordered_by)}</small></td><td><div class="bed-actions">${orderCourseButtons(o)||'<span class="muted">No course change available</span>'}</div></td></tr>`).join('')||'<tr><td colspan="6">No orders for this patient.</td></tr>'}</tbody></table></div></div></section>`;}


  async function renderResults(){
    renderLoading();
    const patient=await selectedPatient();
    if(!patient){$('#mainContent').innerHTML=`${pageHeader('Results Review','Patient-linked Results','Select a patient before reviewing diagnostic results.')}${patientContextBanner(null)}`;return;}
    const results=await api(`/results?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`);
    $('#mainContent').innerHTML=`${pageHeader('Results Review','Diagnostic Results for the Selected Record','Review laboratory and diagnostic results, prioritize critical values and record acknowledgement.',`<button class="btn" data-action="refresh-results">Refresh</button>`)}${patientContextBanner(patient)}${resultsTable(results)}${releaseNotice()}`;
  }
  function resultsTable(results){return `<section class="card"><div class="card-header"><div><h2>Patient results</h2><p>Critical and abnormal results remain visible until acknowledged.</p></div></div><div class="card-body"><div class="table-wrap"><table><thead><tr><th>Test</th><th>Result</th><th>Flag</th><th>Source / time</th><th>Action</th></tr></thead><tbody>${results.map(r=>`<tr><td><strong>${esc(r.test_name)}</strong></td><td>${esc(r.value)} ${esc(r.unit||'')}</td><td><span class="badge ${badgeClass(r.flag)}">${esc(r.flag)}</span></td><td>${esc(r.source)}<br/><small>${fmtDate(r.issued_at)}</small></td><td>${r.acknowledged?`<span class="badge success">Acknowledged</span><br/><small>${esc(r.acknowledged_by||'')}</small>`:`<button class="btn btn-sm btn-danger" data-action="ack-result" data-result="${r.result_id}">Acknowledge</button>`}</td></tr>`).join('')||'<tr><td colspan="5">No results for this patient.</td></tr>'}</tbody></table></div></div></section>`;}


  async function renderRecentDischarges(){
    renderLoading();const discharges=await api(`/recent-discharges?hours=168${state.facility==='ALL'?'':`&facility_code=${state.facility}`}`);state.recentDischarges=discharges;
    $('#mainContent').innerHTML=`${pageHeader('Transitions of Care','Recent Discharges','Recently discharged patients remain visible for summary completion, medication reconciliation, follow-up, readmission prevention and patient contact.',`<button class="btn" data-route="patient-flow">Active Tracker</button>`)}
      <section class="grid grid-4">${metricCard('Discharged patients',discharges.length,'Last 7 days')}${metricCard('Summaries available',discharges.filter(d=>d.discharge_summary).length,'Transition record')}${metricCard('Follow-up documented',discharges.filter(d=>d.follow_up).length,'Closed-loop')}${metricCard('Home disposition',discharges.filter(d=>String(d.discharge_disposition).includes('Home')).length,'Patients')}</section>
      <section>${discharges.map(d=>`<article class="discharge-card"><header><div><h3>${esc(d.patient.full_name)}</h3><small>${esc(d.patient.mpi_id)} · ${esc(d.service)} · ${esc(d.facility.name)}</small></div><span class="badge success">Discharged ${fmtDate(d.discharge_at)}</span></header><p class="summary"><strong>Summary:</strong> ${esc(d.discharge_summary||'Summary pending')}</p><p class="summary"><strong>Disposition:</strong> ${esc(d.discharge_disposition||'—')}<br/><strong>Follow-up:</strong> ${esc(d.follow_up||'Not documented')}</p><div class="page-actions"><button class="btn btn-sm" data-patient-id="${d.patient.mpi_id}">Open Chart</button><button class="btn btn-sm" data-action="copy-discharge" data-encounter="${d.encounter_id}">Copy Summary</button><button class="btn btn-sm">Contact Patient</button></div></article>`).join('')||'<div class="empty-state"><p>No recent discharges.</p></div>'}</section>`;
  }


  const formatTZS=value=>new Intl.NumberFormat('en-TZ',{style:'currency',currency:'TZS',maximumFractionDigits:0}).format(Number(value||0));
  const dot=value=>`<i class="status-dot-inline ${String(value||'').toLowerCase()}"></i>`;

  async function renderScheduling(){
    renderLoading('Loading scheduling, duty rosters and referral operations…');
    const q=state.facility==='ALL'?'':`?facility_code=${state.facility}`;
    const [appointments,referrals]=await Promise.all([api(`/appointments${q}`),api(`/referrals${q}`)]);
    const appointmentActions=x=>{
      const buttons=[];
      if(x.status==='SCHEDULED')buttons.push(`<button class="btn btn-sm" data-action="appointment-status" data-id="${x.appointment_id}" data-status="CONFIRMED">Confirm</button>`);
      if(['SCHEDULED','CONFIRMED'].includes(x.status))buttons.push(`<button class="btn btn-sm btn-primary" data-action="appointment-status" data-id="${x.appointment_id}" data-status="ARRIVED">Arrive</button>`);
      if(['SCHEDULED','CONFIRMED'].includes(x.status))buttons.push(`<button class="btn btn-sm" data-action="appointment-status" data-id="${x.appointment_id}" data-status="CANCELLED">Cancel</button>`);
      if(['CANCELLED','NO_SHOW'].includes(x.status))buttons.push(`<button class="btn btn-sm btn-primary" data-action="appointment-status" data-id="${x.appointment_id}" data-status="REINSTATED">Reinstate</button>`);
      return buttons.join('')||'<span class="muted">In patient-flow workflow</span>';
    };
    $('#mainContent').innerHTML=`${pageHeader('Scheduling and Access Operations','Government Duty-Roster & Private Provider Scheduling','Public facilities can schedule to a service, clinic, shift or duty team; private facilities can require a named provider. Arrival feeds the live patient-flow workflow.',`<button class="btn" data-route="registration">Patient Registration</button><button class="btn btn-primary" data-action="new-appointment">+ Appointment</button>`)}
      <section class="grid grid-4">${metricCard('Scheduled records',appointments.length,'Selected period')}${metricCard('Arrived',appointments.filter(x=>x.status==='ARRIVED').length,'Sent to patient flow')}${metricCard('Open referrals',referrals.filter(x=>!['CLOSED','DECLINED'].includes(x.status)).length,'Across institutions')}${metricCard('Cancelled / no-show',appointments.filter(x=>['CANCELLED','NO_SHOW'].includes(x.status)).length,'Can be reinstated')}</section>
      <section class="split-panels"><article class="card"><div class="card-header"><div><h2>Comprehensive schedule</h2><p>Appointment status history is preserved. Cancelling and reinstating require a documented reason.</p></div></div><div class="card-body table-wrap"><table class="enterprise-table"><thead><tr><th>Time</th><th>Patient</th><th>Service / Duty Team / Provider</th><th>Facility</th><th>Status</th><th>Actions</th></tr></thead><tbody>${appointments.map(x=>`<tr><td>${fmtDate(x.scheduled_start)}</td><td><button class="link-button" data-patient-id="${x.patient.mpi_id}"><strong>${esc(x.patient.full_name)}</strong></button><br/><small>${esc(x.patient.mrn)}</small></td><td>${esc(x.service)}<br/><small>${esc(x.provider||'Duty roster / next available clinician')}</small></td><td>${esc(x.facility.code)}</td><td>${dot(x.status)}${statusLabel(x.status)}${x.history?.[0]?`<br/><small>${statusLabel(x.history[0].action)} · ${fmtDate(x.history[0].occurred_at)}</small>`:''}</td><td><div class="bed-actions">${appointmentActions(x)}</div></td></tr>`).join('')||'<tr><td colspan="6">No appointments in the selected period.</td></tr>'}</tbody></table></div></article>
      <article class="card"><div class="card-header"><div><h2>Referral intake</h2><p>Requests stay open until accepted, scheduled, completed and acknowledged by the referring team.</p></div></div><div class="card-body"><div class="list">${referrals.map(x=>`<div class="list-item"><span class="list-icon">↔</span><div><strong>${esc(x.patient.full_name)} · ${esc(x.service)}</strong><p>${esc(x.source_facility_code)} → ${esc(x.destination_facility_code)} · ${esc(x.reason)}</p><small>${fmtDate(x.requested_at)} · ${esc(x.requested_by)}</small></div><div class="list-meta"><span class="badge ${badgeClass(x.priority)}">${esc(x.priority)}</span><span class="badge ${badgeClass(x.status)}">${statusLabel(x.status)}</span><div class="bed-actions">${x.status==='NEW'?`<button class="btn btn-sm" data-action="referral-status" data-id="${x.referral_id}" data-status="ACCEPTED">Accept</button>`:''}${['ACCEPTED','NEW'].includes(x.status)?`<button class="btn btn-sm" data-action="referral-status" data-id="${x.referral_id}" data-status="SCHEDULED">Schedule</button>`:''}${x.status==='SCHEDULED'?`<button class="btn btn-sm btn-primary" data-action="referral-status" data-id="${x.referral_id}" data-status="CLOSED">Close loop</button>`:''}</div></div></div>`).join('')||'<div class="empty-state"><p>No referrals.</p></div>'}</div></div></article></section>${releaseNotice()}`;
  }

  async function renderBedBoard(){
    renderLoading('Loading ADT and bed capacity…');
    const beds=await api(`/beds${state.facility==='ALL'?'':`?facility_code=${state.facility}`}`);
    const byStatus=s=>beds.filter(x=>x.status===s).length;
    $('#mainContent').innerHTML=`${pageHeader('Hospital Operations','ADT, Capacity & Bed Board','Coordinate admissions, assignments, occupancy, EVS cleaning, operational blocks and patient movement.',`<button class="btn" data-route="patient-flow">Patient Tracker</button><button class="btn btn-primary" data-action="refresh-beds">Refresh Capacity</button>`)}
      <section class="grid grid-4">${metricCard('Configured beds',beds.length,'Selected network')}${metricCard('Available',byStatus('AVAILABLE'),'Ready for assignment','success')}${metricCard('Occupied',byStatus('OCCUPIED'),'Current census')}${metricCard('EVS / blocked',byStatus('DIRTY')+byStatus('CLEANING')+byStatus('BLOCKED'),'Needs action','warning')}</section>
      <section class="card"><div class="card-header"><div><h2>Live bed inventory</h2><p>Bed actions update the linked encounter location and create an immutable audit event.</p></div></div><div class="card-body"><div class="bed-board-grid">${beds.map(x=>`<article class="bed-card ${String(x.status).toLowerCase()}"><header><div><strong>${esc(x.unit)} · ${esc(x.room)}-${esc(x.bed_label)}</strong><small>${esc(x.facility.code)} · ${esc(x.bed_type)}</small></div><span class="badge ${badgeClass(x.status)}">${statusLabel(x.status)}</span></header>${x.patient?`<div class="patient-name">${esc(x.patient.full_name)}</div><small>${esc(x.patient.mrn)} · ${esc(x.encounter?.service||'')}</small>`:'<div class="muted">No patient assigned</div>'}<div class="bed-actions">${x.status==='AVAILABLE'?`<button class="btn btn-sm btn-primary" data-action="bed-action" data-id="${x.bed_id}" data-control="ASSIGN">Assign</button><button class="btn btn-sm" data-action="bed-action" data-id="${x.bed_id}" data-control="BLOCK">Block</button>`:''}${x.status==='ASSIGNED'?`<button class="btn btn-sm btn-primary" data-action="bed-action" data-id="${x.bed_id}" data-control="OCCUPY" data-encounter="${x.encounter?.encounter_id||''}">Occupy</button>`:''}${x.status==='OCCUPIED'?`<button class="btn btn-sm" data-action="bed-action" data-id="${x.bed_id}" data-control="MARK_DIRTY">Discharge / Dirty</button>`:''}${x.status==='DIRTY'?`<button class="btn btn-sm btn-primary" data-action="bed-action" data-id="${x.bed_id}" data-control="START_CLEANING">Start Cleaning</button>`:''}${x.status==='CLEANING'?`<button class="btn btn-sm btn-primary" data-action="bed-action" data-id="${x.bed_id}" data-control="MARK_AVAILABLE">Mark Available</button>`:''}${x.status==='BLOCKED'?`<button class="btn btn-sm" data-action="bed-action" data-id="${x.bed_id}" data-control="UNBLOCK">Unblock</button>`:''}</div></article>`).join('')}</div></div></section>${releaseNotice()}`;
  }

  async function renderClinicalDocumentation(){
    renderLoading('Loading the selected longitudinal record…');
    const patient=await selectedPatient();
    if(!patient){$('#mainContent').innerHTML=`${pageHeader('Longitudinal Clinical Record','Clinical Documentation','Select a patient record before documenting.')}${patientContextBanner(null)}`;return;}
    const active=patient.encounters.find(x=>x.status!=='DISCHARGED')||patient.encounters[0]||null;
    const [notes,advisoryResponse]=await Promise.all([
      api(`/notes?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`),
      api(`/practice-advisories?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}${active?`&encounter_id=${encodeURIComponent(active.encounter_id)}`:''}&language=${state.language}`)
    ]);
    const advisories=advisoryResponse.advisories||[];
    $('#mainContent').innerHTML=`${pageHeader('Longitudinal Clinical Record','Clinical Documentation & Assisted Note Composer','Documentation, audio annotation and practice advisories are anchored to the selected patient and encounter.',`<button class="btn" data-route="chart">Patient Chart</button><button class="btn" data-action="audio-note">Audio / Dictation</button><button class="btn btn-primary" data-action="new-note">+ New Note</button>`)}
      ${patientContextBanner(patient)}
      <section class="grid grid-4">${metricCard('Patient notes',notes.length,patient.mpi_id)}${metricCard('Draft',notes.filter(x=>x.status==='DRAFT').length,'Requires review/signature','warning')}${metricCard('Signed',notes.filter(x=>x.status==='SIGNED').length,'Legal record','success')}${metricCard('Practice advisories',advisories.filter(x=>!['ACKNOWLEDGE','DISMISS'].includes(x.latest_action)).length,'Patient-specific')}</section>
      <section class="split-panels"><article class="card"><div class="card-header"><div><h2>Documentation activity</h2><p>Signed notes require an addendum; assisted drafts remain unsigned until clinician review.</p></div></div><div class="card-body"><div class="list">${notes.map(x=>`<article class="list-item"><span class="list-icon">▤</span><div><strong>${esc(x.title)}</strong><p>${esc(x.note_type)} · ${esc(x.service)} · ${esc(x.author)} · ${fmtDate(x.created_at)}</p><div class="release-banner" style="margin-top:8px">${esc(x.body)}</div></div><div class="list-meta"><span class="badge ${badgeClass(x.status)}">${statusLabel(x.status)}</span>${x.status==='DRAFT'?`<button class="btn btn-sm btn-primary" data-action="sign-note" data-id="${x.note_id}">Sign</button>`:''}</div></article>`).join('')||'<div class="empty-state"><p>No notes for the selected patient.</p></div>'}</div></div></article>
      <article class="card"><div class="card-header"><div><h2>Practice advisories</h2><p>Rule-driven prompts support care; they do not diagnose or replace clinical judgment.</p></div></div><div class="card-body"><div class="list">${advisories.map(a=>`<article class="list-item"><span class="list-icon">!</span><div><strong>${esc(a.title)}</strong><p>${esc(a.message)}</p><small>${esc(a.source)}${a.latest_action?` · ${statusLabel(a.latest_action)}`:''}</small></div><div class="list-meta"><span class="badge ${badgeClass(a.severity)}">${esc(a.severity)}</span>${a.latest_action!=='ACKNOWLEDGE'?`<button class="btn btn-sm" data-action="advisory-action" data-key="${esc(a.key)}" data-op="ACKNOWLEDGE" data-encounter="${esc(active?.encounter_id||'')}">Acknowledge</button>`:''}</div></article>`).join('')||'<div class="empty-state"><p>No active advisories for this record.</p></div>'}</div></div></article></section>${releaseNotice()}`;
  }

  async function renderMedicationWorkspace(){
    renderLoading('Loading medication management and eMAR…');
    const patient=await selectedPatient();
    if(!patient){$('#mainContent').innerHTML=`${pageHeader('Medication Management','Patient-linked Medication Record','Select a patient before reviewing medication orders or eMAR.')}${patientContextBanner(null)}`;return;}
    const meds=await api(`/medications?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`);
    const isPharmacy=state.route==='pharmacy'||state.role==='pharmacy';
    $('#mainContent').innerHTML=`${pageHeader(isPharmacy?'Pharmacy Medication Operations':'Nursing Medication Administration','Pharmacy Verification, Dispensing & eMAR','Medication orders flow through pharmacist verification and barcode-supported administration with held/refused documentation.',`<button class="btn" data-route="chart">Patient Chart</button><button class="btn btn-primary" data-action="new-medication">+ Medication Order</button>`)}
      ${patientContextBanner(patient)}<section class="grid grid-4">${metricCard('Active orders',meds.filter(x=>x.status==='ACTIVE').length,'Selected patient')}${metricCard('Awaiting verification',meds.filter(x=>!x.verified_at).length,'Pharmacy queue','warning')}${metricCard('Verified',meds.filter(x=>x.verified_at).length,'Eligible for administration','success')}${metricCard('Administrations',meds.reduce((n,x)=>n+x.administrations.length,0),'Recorded eMAR events')}</section>
      <section class="card"><div class="card-header"><div><h2>${isPharmacy?'Verification workqueue':'Medication administration record'}</h2><p>GIVEN administrations are blocked until pharmacy verification is complete.</p></div></div><div class="card-body table-wrap"><table class="enterprise-table"><thead><tr><th>Patient</th><th>Medication</th><th>Order</th><th>Verification</th><th>Latest eMAR</th><th>Actions</th></tr></thead><tbody>${meds.map(x=>`<tr><td><button class="link-button" data-patient-id="${x.patient.mpi_id}">${esc(x.patient.full_name)}</button><br/><small>${esc(x.encounter?.service||'')}</small></td><td><strong>${esc(x.medication_name)}</strong><br/><small>${esc(x.indication||'No indication documented')}</small></td><td>${esc(x.dose)} · ${esc(x.route)} · ${esc(x.frequency)}</td><td>${x.verified_at?`${dot('completed')}Verified by ${esc(x.verified_by)}<br/><small>${fmtDate(x.verified_at)}</small>`:`${dot('pending')}Pending pharmacist review`}</td><td>${x.administrations[0]?`${statusLabel(x.administrations[0].action)} · ${fmtDate(x.administrations[0].administered_at)}<br/><small>${esc(x.administrations[0].administered_by)}</small>`:'No administrations'}</td><td><div class="bed-actions">${!x.verified_at?`<button class="btn btn-sm btn-primary" data-action="verify-med" data-id="${x.medication_order_id}">Verify</button>`:''}<button class="btn btn-sm" data-action="administer-med" data-id="${x.medication_order_id}" data-med="${esc(x.medication_name)}" ${!x.verified_at?'disabled':''}>eMAR</button></div></td></tr>`).join('')||'<tr><td colspan="6">No medication orders for the selected patient.</td></tr>'}</tbody></table></div></section>${releaseNotice()}`;
  }

  async function renderRevenueCycle(){
    renderLoading('Loading billing and claims operations…');
    const [claims,charges,tasks]=await Promise.all([api('/claims'),api('/charges'),api('/work-items')]);
    const denials=claims.filter(x=>x.status==='DENIED');
    $('#mainContent').innerHTML=`${pageHeader('Financial Operations','Revenue Cycle, NHIF/UHI Claims & Payments','Connect eligibility, authorization, charge capture, coding, claims, denials, cashiering and reconciliation to the documented encounter.',`<button class="btn" data-action="new-charge">+ Charge</button><button class="btn btn-primary" data-action="new-claim">+ Claim</button>`)}
      <section class="grid grid-4">${metricCard('Claims',claims.length,'Current workqueue')}${metricCard('Outstanding value',formatTZS(claims.filter(x=>!['PAID','VOID'].includes(x.status)).reduce((n,x)=>n+x.amount,0)),'Ready through denied')}${metricCard('Denials',denials.length,formatTZS(denials.reduce((n,x)=>n+x.amount,0)),'warning')}${metricCard('Posted charges',formatTZS(charges.reduce((n,x)=>n+x.total,0)),`${charges.length} transactions`)}</section>
      <section class="split-panels"><article class="card"><div class="card-header"><div><h2>Claims workqueue</h2><p>Submission and denial actions create interface events and auditable work items.</p></div></div><div class="card-body table-wrap"><table class="enterprise-table"><thead><tr><th>Claim</th><th>Patient / Encounter</th><th>Payer</th><th>Amount</th><th>Status</th><th>Actions</th></tr></thead><tbody>${claims.map(x=>`<tr><td><strong>${esc(x.claim_id)}</strong><br/><small>${esc(x.authorization_number||'No authorization')}</small></td><td>${esc(x.patient.full_name)}<br/><small>${esc(x.encounter?.encounter_id||'')}</small></td><td>${esc(x.payer)}<br/><small>${esc(x.member_number||'')}</small></td><td class="money">${formatTZS(x.amount)}</td><td>${dot(x.status)}${statusLabel(x.status)}${x.denial_reason?`<br/><small>${esc(x.denial_code||'')} ${esc(x.denial_reason)}</small>`:''}</td><td><div class="bed-actions">${x.status==='DRAFT'?`<button class="btn btn-sm" data-action="claim-status" data-id="${x.claim_id}" data-status="READY">Ready</button>`:''}${x.status==='READY'?`<button class="btn btn-sm btn-primary" data-action="claim-status" data-id="${x.claim_id}" data-status="SUBMITTED">Submit</button>`:''}${x.status==='DENIED'?`<button class="btn btn-sm" data-action="claim-status" data-id="${x.claim_id}" data-status="READY">Correct</button>`:''}${x.status==='ACCEPTED'?`<button class="btn btn-sm btn-primary" data-action="claim-status" data-id="${x.claim_id}" data-status="PAID">Reconcile</button>`:''}</div></td></tr>`).join('')}</tbody></table></div></article>
      <article class="card"><div class="card-header"><div><h2>Revenue work items</h2><p>Exceptions, denials and reconciliation tasks.</p></div></div><div class="card-body"><div class="list">${tasks.filter(x=>x.queue.includes('CLAIM')||x.task_type.includes('DENIAL')).map(x=>`<div class="list-item"><span class="list-icon">₮</span><div><strong>${esc(x.subject)}</strong><p>${esc(x.details||'')}</p></div><div class="list-meta"><span class="badge ${badgeClass(x.priority)}">${esc(x.priority)}</span><button class="btn btn-sm" data-action="complete-task" data-id="${x.work_item_id}">Complete</button></div></div>`).join('')||'<div class="empty-state"><p>No revenue exceptions.</p></div>'}</div></div></article></section>${releaseNotice()}`;
  }

  async function renderSupplyChain(){
    renderLoading('Loading supply chain and inventory…');
    const items=await api(`/inventory${state.facility==='ALL'?'':`?facility_code=${state.facility}`}`);
    $('#mainContent').innerHTML=`${pageHeader('Enterprise Resource Operations','Supply Chain, Pharmacy Stock & Assets','Track on-hand quantities, reorder thresholds, batches, expiry and transactions linked to dispensing and procedures.',`<button class="btn btn-primary" data-action="refresh-inventory">Refresh Inventory</button>`)}
      <section class="grid grid-4">${metricCard('Inventory items',items.length,'Selected facilities')}${metricCard('Stock risks',items.filter(x=>x.stock_status!=='OK').length,'Below reorder level','warning')}${metricCard('Critical',items.filter(x=>x.stock_status==='CRITICAL').length,'Immediate replenishment')}${metricCard('Connected eLMIS','Online','Outbox enabled','success')}</section>
      <section class="card"><div class="card-header"><div><h2>Inventory control</h2><p>Receipts, issues, waste and adjustments update balances and write audit events.</p></div></div><div class="card-body table-wrap"><table class="enterprise-table"><thead><tr><th>Item</th><th>Facility / Location</th><th>Batch / Expiry</th><th>On hand</th><th>Reorder</th><th>Status</th><th>Action</th></tr></thead><tbody>${items.map(x=>`<tr><td><strong>${esc(x.item_name)}</strong><br/><small>${esc(x.item_code)} · ${esc(x.category)}</small></td><td>${esc(x.facility)}<br/><small>${esc(x.location)}</small></td><td>${esc(x.batch_number||'—')}<br/><small>${fmtDate(x.expiry_at)}</small></td><td class="money">${x.on_hand} ${esc(x.unit)}</td><td>${x.reorder_level} ${esc(x.unit)}</td><td>${dot(x.stock_status)}${statusLabel(x.stock_status)}</td><td><button class="btn btn-sm" data-action="inventory-txn" data-id="${x.item_id}" data-name="${esc(x.item_name)}">Transaction</button></td></tr>`).join('')}</tbody></table></div></section>${releaseNotice()}`;
  }

  async function renderEnterpriseAnalytics(){
    renderLoading('Calculating enterprise operating metrics…');
    const q=state.facility==='ALL'?'':`?facility_code=${state.facility}`;
    const summary=await api(`/analytics/summary${q}`);
    const tasks=await api('/work-items');
    const integrations=(state.account?.functions||[]).includes('system.interfaces.manage')?await api('/integration-events'):[];
    $('#mainContent').innerHTML=`${pageHeader('Enterprise Intelligence','Operational, Clinical, Financial & Interoperability Analytics','Actionable metrics drawn from the same transactional record—not disconnected presentation-only dashboards.',`<button class="btn" data-route="dashboard">Command Center</button>`)}
      <section class="grid grid-4">${metricCard('Active encounters',summary.active_encounters,'Current census')}${metricCard('Open work items',summary.open_work_items,'All operational pools')}${metricCard('Unsigned notes',summary.unsigned_notes,'Documentation completion','warning')}${metricCard('Unverified medications',summary.medications_unverified,'Pharmacy safety queue','warning')}${metricCard('Available beds',summary.beds.available,`${summary.beds.total} total`,'success')}${metricCard('Claim denials',summary.claim_denials,formatTZS(summary.claim_value))}${metricCard('Stock-out risks',summary.stockout_risks,'Supply action')}${metricCard('Appointments',summary.appointments_36h,'36-hour window')}</section>
      <section class="split-panels"><article class="card"><div class="card-header"><h2>Priority work distribution</h2></div><div class="card-body"><div class="list">${tasks.slice(0,12).map(x=>`<div class="list-item"><span class="list-icon">${x.priority==='CRITICAL'?'!':'✓'}</span><div><strong>${esc(x.subject)}</strong><p>${esc(x.queue)} · ${esc(x.assigned_to||'Unassigned')} · due ${fmtDate(x.due_at)}</p></div><span class="badge ${badgeClass(x.priority)}">${esc(x.priority)}</span></div>`).join('')}</div></div></article><article class="card"><div class="card-header"><h2>National interface outbox</h2></div><div class="card-body"><div class="timeline">${integrations.slice(0,10).map(x=>`<div class="timeline-item"><strong>${esc(x.system)}</strong><div>${dot(x.status)}<strong>${esc(x.event_type)}</strong><p>${esc(x.resource_type)} ${esc(x.resource_id)} · ${fmtDate(x.created_at)}</p></div></div>`).join('')}</div></div></article></section>${releaseNotice()}`;
  }

  async function renderSystemAdmin(){
    renderLoading('Loading user access matrices, audit and interface administration…');
    const [users,catalog]=await Promise.all([api('/admin/users'),api('/admin/access-catalog')]);
    const assigned=new Set(state.account?.functions||[]);
    const audit=assigned.has('system.audit.view')?await api('/audit?limit=40'):[];
    const integrations=assigned.has('system.interfaces.manage')?await api('/integration-events?limit=40'):[];
    state.adminUsers=users;state.accessCatalog=catalog;
    $('#mainContent').innerHTML=`${pageHeader('System Administration','User Accounts & Longitudinal Access Matrices','Create individual accounts and assign functions, departments and facilities independently. Job profiles are starting templates only.',`<button class="btn" onclick="window.open('/api/v1/docs','_blank')">API Docs</button><button class="btn btn-primary" data-action="new-user">+ Add User</button>`)}
      <section class="grid grid-4">${metricCard('Active users',users.filter(x=>x.active).length,'Provisioned accounts')}${metricCard('Cross-department users',users.filter(x=>(x.departments||[]).length>1).length,'Multiple departments')}${metricCard('Multi-facility users',users.filter(x=>(x.facilities||[]).length>1).length,'Longitudinal facility access')}${metricCard('Interface exceptions',integrations.filter(x=>x.status==='FAILED').length,'Current outbox')}</section>
      <section class="grid grid-main"><article class="card"><div class="card-header"><div><h2>User directory</h2><p>Every account can cross functions and departments according to its checkbox matrix.</p></div></div><div class="card-body table-wrap"><table class="enterprise-table"><thead><tr><th>User</th><th>Access template</th><th>Functions</th><th>Departments</th><th>Facilities</th><th>Status</th><th>Actions</th></tr></thead><tbody>${users.map(x=>`<tr><td><strong>${esc(x.display_name)}</strong><br/><small>${esc(x.username)} · ${esc(x.user_id)}</small></td><td>${statusLabel(x.role_code)}</td><td><strong>${(x.functions||[]).length}</strong><br/><small>${esc((x.functions||[]).slice(0,3).join(', '))}${(x.functions||[]).length>3?'…':''}</small></td><td>${esc((x.departments||[]).join(', ')||'None')}</td><td>${esc((x.facilities||[]).join(', '))}</td><td>${dot(x.active?'ACTIVE':'INACTIVE')}${x.active?'Active':'Inactive'}<br/><small>${fmtDate(x.last_login_at)}</small></td><td><div class="bed-actions"><button class="btn btn-sm btn-primary" data-action="edit-user" data-id="${x.user_id}">Edit matrix</button><button class="btn btn-sm" data-action="toggle-user" data-id="${x.user_id}" data-active="${x.active?'false':'true'}">${x.active?'Disable':'Enable'}</button><button class="btn btn-sm" data-action="reset-user-password" data-id="${x.user_id}" data-name="${esc(x.display_name)}">Password</button></div></td></tr>`).join('')}</tbody></table></div></article><article class="card"><div class="card-header"><h2>Recent audit</h2></div><div class="card-body"><div class="timeline">${audit.slice(0,18).map(x=>`<div class="timeline-item"><strong>${fmtDate(x.occurred_at)}</strong><div><strong>${esc(x.action)}</strong><p>${esc(x.actor)} · ${esc(x.resource_type)} ${esc(x.resource_id||'')}</p></div></div>`).join('')}</div></div></article></section>${releaseNotice()}`;
  }


  async function renderTelehealth(){
    renderLoading('Loading record-linked remote care…');
    const patient=await selectedPatient();
    if(!patient){$('#mainContent').innerHTML=`${pageHeader('Telehealth & Remote Care','Record-Linked Remote Care','Select a patient record before scheduling or conducting a remote clinical encounter.')}${patientContextBanner(null)}`;return;}
    const sessions=await api(`/telehealth-sessions?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`);
    const open=sessions.filter(x=>!['COMPLETED','CANCELLED'].includes(x.status));
    $('#mainContent').innerHTML=`${pageHeader('Telehealth & Remote Care','Connected Remote-Care Workflow','Video, audio and store-and-forward visits remain part of the selected longitudinal record and provider workqueues.',`<button class="btn" data-route="chart">Patient Chart</button><button class="btn btn-primary" data-action="new-telehealth">+ Schedule Session</button>`)}${patientContextBanner(patient)}
      <section class="grid grid-4">${metricCard('Open sessions',open.length,'Selected patient')}${metricCard('In progress',sessions.filter(x=>x.status==='IN_PROGRESS').length,'Active remote care','success')}${metricCard('Paused',sessions.filter(x=>x.status==='PAUSED').length,'Requires action','warning')}${metricCard('Completed',sessions.filter(x=>x.status==='COMPLETED').length,'Closed loop')}</section>
      <section class="card"><div class="card-header"><div><h2>Remote-care history</h2><p>Each session can create encounter documentation, orders and follow-up while preserving audit history.</p></div></div><div class="card-body table-wrap"><table class="enterprise-table"><thead><tr><th>Patient</th><th>Service / Provider</th><th>Schedule</th><th>Modality</th><th>Status</th><th>Secure session</th><th>Actions</th></tr></thead><tbody>${sessions.map(x=>`<tr><td><strong>${esc(x.patient.full_name)}</strong><br/><small>${esc(x.patient.mpi_id)} · ${esc(x.patient.mrn)}</small></td><td>${esc(x.service)}<br/><small>${esc(x.provider)} · ${esc(x.facility.code)}</small></td><td>${fmtDate(x.scheduled_start)}<br/><small>${esc(x.reason||'No reason documented')}</small></td><td>${esc(statusLabel(x.modality))}</td><td>${dot(x.status)}${statusLabel(x.status)}</td><td><code>${esc(x.join_code)}</code><br/><small>No clinical data embedded</small></td><td><div class="bed-actions">${['SCHEDULED','READY'].includes(x.status)?`<button class="btn btn-sm btn-primary" data-action="telehealth-action" data-id="${x.session_id}" data-op="START">Start</button>`:''}${x.status==='IN_PROGRESS'?`<button class="btn btn-sm" data-action="telehealth-action" data-id="${x.session_id}" data-op="PAUSE">Pause</button><button class="btn btn-sm btn-primary" data-action="telehealth-action" data-id="${x.session_id}" data-op="COMPLETE">Complete</button>`:''}${x.status==='PAUSED'?`<button class="btn btn-sm" data-action="telehealth-action" data-id="${x.session_id}" data-op="RESUME">Resume</button><button class="btn btn-sm btn-primary" data-action="telehealth-action" data-id="${x.session_id}" data-op="COMPLETE">Complete</button>`:''}${!['COMPLETED','CANCELLED'].includes(x.status)?`<button class="btn btn-sm" data-action="telehealth-action" data-id="${x.session_id}" data-op="CANCEL">Cancel</button>`:''}</div></td></tr>`).join('')||'<tr><td colspan="7"><div class="empty-state"><h3>No remote-care sessions</h3><p>Schedule a patient-linked visit.</p></div></td></tr>'}</tbody></table></div></section>${releaseNotice()}`;
  }

  async function renderPublicHealth(){
    renderLoading('Loading registries and surveillance…');
    const events=await api('/public-health-events');
    $('#mainContent').innerHTML=`${pageHeader('Population Health and Surveillance','Public Health, Registries & eIDSR','Convert validated diagnoses and results into governed notifiable events, registry tasks and national reporting.',`<button class="btn btn-primary" data-action="new-public-health">+ Report Event</button>`)}<section class="grid grid-4">${metricCard('Events',events.length,'Current queue')}${metricCard('Pending verification',events.filter(x=>x.status==='PENDING_VERIFICATION').length,'Requires epidemiology review','warning')}${metricCard('Reported',events.filter(x=>x.reported_at).length,'eIDSR / DHIS2')}${metricCard('Regions represented',new Set(events.map(x=>x.region).filter(Boolean)).size,'Geographic coverage')}</section><section class="card"><div class="card-header"><h2>Surveillance event queue</h2></div><div class="card-body table-wrap"><table class="enterprise-table"><thead><tr><th>Patient</th><th>Condition</th><th>Location</th><th>Destination</th><th>Status</th><th>Created</th></tr></thead><tbody>${events.map(x=>`<tr><td>${esc(x.patient.full_name)}<br/><small>${esc(x.patient.mpi_id)}</small></td><td><strong>${esc(x.condition_name)}</strong><br/><small>${esc(x.condition_code)} · ${esc(x.event_type)}</small></td><td>${esc(x.district||'—')}, ${esc(x.region||'—')}</td><td>${esc(x.reported_to)}</td><td>${dot(x.status)}${statusLabel(x.status)}</td><td>${fmtDate(x.created_at)}</td></tr>`).join('')}</tbody></table></div></section>${releaseNotice()}`;
  }

  async function renderQuality(){
    renderLoading('Loading quality and patient safety…');
    const incidents=await api('/quality-incidents');
    $('#mainContent').innerHTML=`${pageHeader('Learning Health System','Quality, Patient Safety & Infection Prevention','Report incidents and near misses, assign accountable owners and preserve follow-through from identification to closure.',`<button class="btn btn-primary" data-action="new-quality">+ Report Incident</button>`)}<section class="grid grid-4">${metricCard('Open incidents',incidents.filter(x=>x.status!=='CLOSED').length,'All facilities')}${metricCard('High / critical',incidents.filter(x=>['HIGH','CRITICAL'].includes(x.severity)).length,'Immediate review','warning')}${metricCard('Assigned owners',incidents.filter(x=>x.owner).length,'Accountability')}${metricCard('Closed',incidents.filter(x=>x.status==='CLOSED').length,'Learning complete','success')}</section><section class="card"><div class="card-header"><h2>Safety workqueue</h2></div><div class="card-body"><div class="list">${incidents.map(x=>`<div class="list-item"><span class="list-icon">!</span><div><strong>${esc(x.category)} · ${esc(x.facility)}</strong><p>${esc(x.description)}</p><small>${x.patient?`${esc(x.patient.full_name)} · `:''}${esc(x.reported_by)} · ${fmtDate(x.reported_at)}</small></div><div class="list-meta"><span class="badge ${badgeClass(x.severity)}">${esc(x.severity)}</span><span class="badge ${badgeClass(x.status)}">${statusLabel(x.status)}</span><small>${esc(x.owner||'Unassigned')}</small></div></div>`).join('')}</div></div></section>${releaseNotice()}`;
  }

  const routeModuleCodes={emergency:'EMERGENCY',laboratory:'LABORATORY','blood-bank':'BLOOD_BANK',radiology:'RADIOLOGY',theatre:'THEATRE',anesthesia:'ANESTHESIA',maternity:'MATERNITY',cardiology:'CARDIOLOGY',orthopaedics:'MOI',oncology:'ONCOLOGY','critical-care':'CRITICAL_CARE',rehab:'REHAB',workforce:'WORKFORCE'};
  async function renderGenericModule(route){
    const m=genericModules[route]||{title:'Enterprise Module',subtitle:'Configured module workspace.',metrics:[['Work queue','0','Ready'],['Safety alerts','0','None'],['Interfaces','Online','Stable'],['Data quality','98%','Current']]};
    const code=routeModuleCodes[route]||String(route).toUpperCase().replaceAll('-','_');
    renderLoading(`Loading ${m.title}…`);
    const patient=await selectedPatient();
    if(!patient){$('#mainContent').innerHTML=`${pageHeader('Umoja Afya Integrated Module',m.title,'Select a longitudinal patient record before opening this clinical module.')}${patientContextBanner(null)}`;return;}
    const allActivities=await api(`/module-activities?module_code=${encodeURIComponent(code)}`);
    const activities=allActivities.filter(x=>x.patient?.mpi_id===patient.mpi_id);
    $('#mainContent').innerHTML=`${pageHeader('Umoja Afya Integrated Module',m.title,m.subtitle,`<button class="btn" data-route="chart">Patient Chart</button><button class="btn btn-primary" data-action="new-module-activity" data-code="${code}" data-title="${esc(m.title)}">+ New Activity</button>`)}${patientContextBanner(patient)}<section class="grid grid-4">${metricCard('Open activities',activities.filter(x=>!['COMPLETED','CANCELLED'].includes(x.status)).length,'Selected record')}${metricCard('High priority',activities.filter(x=>['HIGH','CRITICAL','STAT'].includes(x.priority)&&x.status!=='COMPLETED').length,'Immediate attention','warning')}${metricCard('Completed',activities.filter(x=>x.status==='COMPLETED').length,'Closed loop','success')}${metricCard('National interfaces','Online','Connected')}</section><section class="grid grid-main"><article class="card"><div class="card-header"><div><h2>Patient-linked module activity</h2><p>Every item belongs to the selected record and may link to an encounter.</p></div></div><div class="card-body"><div class="list">${activities.map(x=>`<div class="list-item"><span class="list-icon">${x.priority==='CRITICAL'?'!':'1'}</span><div><strong>${esc(x.title)}</strong><p>${esc(x.activity_type)} · ${esc(x.patient?.full_name||patient.full_name)} · ${esc(x.patient?.mrn||patient.mrn)}</p><small>${esc(x.details||'')} · ${esc(x.assigned_to||'Unassigned')} · ${fmtDate(x.created_at)}</small></div><div class="list-meta"><span class="badge ${badgeClass(x.priority)}">${esc(x.priority)}</span><span class="badge ${badgeClass(x.status)}">${statusLabel(x.status)}</span><div class="bed-actions">${x.status==='NEW'?`<button class="btn btn-sm" data-action="module-activity-status" data-id="${x.activity_id}" data-status="IN_PROGRESS">Start</button>`:''}${['NEW','IN_PROGRESS','WAITING'].includes(x.status)?`<button class="btn btn-sm btn-primary" data-action="module-activity-status" data-id="${x.activity_id}" data-status="COMPLETED">Complete</button>`:''}</div></div></div>`).join('')||'<div class="empty-state"><h3>No activity for this record</h3><p>Create the first governed module activity for the selected patient.</p></div>'}</div></div></article><article class="card"><div class="card-header"><h2>Connected record workflow</h2></div><div class="card-body"><div class="module-workflow-strip"><span>National MPI</span><span>Encounter</span><span>Orders & Results</span><span>Charges & Claims</span><span>Work Queues</span><span>Audit</span><span>FHIR/HIE</span></div><div class="alert info" style="margin-top:12px"><strong>Record-driven design:</strong> specialty activity references the same patient, encounter, diagnostics, medication and financial record.</div></div></article></section>${releaseNotice()}`;
  }

  function showAppointmentModal(){
    openModal('Schedule Patient Care',`<div class="alert info"><strong>Tanzania scheduling model:</strong> choose public duty-roster scheduling for government facilities or named-provider scheduling for private practice.</div><div class="form-grid" style="margin-top:12px"><label class="field"><span>Patient MPI</span><input id="aptPatient" value="${esc(state.selectedPatientId)}" readonly /></label><label class="field"><span>Facility</span><select id="aptFacility">${state.facilities.filter(x=>x.code!=='MUHAS').map(x=>`<option value="${x.code}" ${x.code===currentFacility().code?'selected':''}>${esc(x.name)}</option>`).join('')}</select></label><label class="field"><span>Scheduling model</span><select id="aptMode"><option value="PUBLIC_DUTY_ROSTER">Government: service / duty roster</option><option value="PRIVATE_NAMED_PROVIDER">Private: named provider</option><option value="PROCEDURE_SLOT">Procedure / theatre slot</option><option value="FOLLOW_UP">Follow-up clinic</option></select></label><label class="field"><span>Service / clinic</span><input id="aptService" value="General Medicine Clinic" /></label><label class="field"><span>Duty team or named provider</span><input id="aptProvider" value="Duty roster / next available clinician" /></label><label class="field"><span>Date and time</span><input id="aptStart" type="datetime-local" /></label><label class="field"><span>Duration minutes</span><input id="aptDuration" type="number" value="30" min="5" /></label><label class="field full"><span>Schedule notes</span><textarea id="aptNotes">Public service queue; assign to the duty team on arrival unless a named provider is required.</textarea></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="create-appointment">Schedule</button>`,'Scheduling and access');
    const d=new Date(Date.now()+86400000); d.setMinutes(d.getMinutes()-d.getTimezoneOffset()); $('#aptStart').value=d.toISOString().slice(0,16);
  }
  async function handleBedAction(el){
    const action=el.dataset.control;
    if(action==='ASSIGN') return openModal('Assign Bed',`<div class="form-grid"><label class="field full"><span>Encounter ID</span><input id="bedEncounter" placeholder="ENC-…" value="${esc(state.tracker.find(x=>x.patient.mpi_id===state.selectedPatientId)?.encounter_id||'')}" /></label><label class="field full"><span>Assignment note</span><textarea id="bedReason">Bed selected based on service, acuity and current capacity.</textarea></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="assign-bed" data-id="${el.dataset.id}">Assign</button>`,'ADT and capacity');
    const encounter=el.dataset.encounter||null;
    await api(`/beds/${el.dataset.id}/actions`,{method:'POST',body:JSON.stringify({action,encounter_id:encounter,actor:currentRole().user,reason:'Updated from enterprise bed board'})});toast('Bed updated',statusLabel(action));renderBedBoard();
  }
  function showNoteModal(prefill=''){
    const encounter=state.tracker.find(x=>x.patient.mpi_id===state.selectedPatientId)?.encounter_id||'';
    openModal('Create Clinical Note',`<div class="form-grid"><label class="field"><span>Patient MPI</span><input id="notePatient" value="${esc(state.selectedPatientId)}" readonly /></label><label class="field"><span>Encounter ID</span><input id="noteEncounter" value="${esc(encounter)}" /></label><label class="field"><span>Note type</span><select id="noteType"><option>PROGRESS_NOTE</option><option>HISTORY_AND_PHYSICAL</option><option>CONSULT_NOTE</option><option>PROCEDURE_NOTE</option><option>DISCHARGE_SUMMARY</option><option>ADDENDUM</option></select></label><label class="field"><span>Service</span><input id="noteService" value="${esc(state.tracker.find(x=>x.patient.mpi_id===state.selectedPatientId)?.service||'Clinical Service')}" /></label><label class="field full"><span>Title</span><input id="noteTitle" value="Progress note" /></label><label class="field full"><span>Clinical note</span><textarea id="noteBody" class="editor">${esc(prefill)}</textarea></label><label class="field full"><span><input id="noteCosign" type="checkbox" /> Cosign required</span></label></div><div class="alert warning"><strong>Legal record:</strong> Review all imported or assisted text before saving and signing.</div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="create-note">Save Draft</button>`,'Patient-linked clinical documentation');
  }

  function showMedicationModal(){
    const encounter=state.tracker.find(x=>x.patient.mpi_id===state.selectedPatientId)?.encounter_id||'';
    openModal('Order Medication',`<div class="form-grid"><label class="field"><span>Patient MPI</span><input id="medPatient" value="${esc(state.selectedPatientId)}" /></label><label class="field"><span>Encounter ID</span><input id="medEncounter" value="${esc(encounter)}" /></label><label class="field full"><span>Medication</span><input id="medName" value="Paracetamol" /></label><label class="field"><span>Dose</span><input id="medDose" value="1 g" /></label><label class="field"><span>Route</span><select id="medRoute"><option>PO</option><option>IV</option><option>IM</option><option>SC</option><option>INHALATION</option><option>TOPICAL</option></select></label><label class="field"><span>Frequency</span><input id="medFrequency" value="Every 8 hours PRN" /></label><label class="field full"><span>Indication</span><textarea id="medIndication">Pain or fever.</textarea></label></div><div class="alert warning"><strong>Safety workflow:</strong> Allergy, interaction, duplicate therapy, dose-range and renal/pregnancy checks must be governed clinical content before production activation.</div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="create-medication">Sign Order</button>`,'Medication ordering');
  }
  function showAdministrationModal(id,name){
    openModal('Record eMAR Administration',`<div class="alert info"><strong>${esc(name)}</strong> · verify the patient, medication, dose, route, time and indication before recording.</div><div class="form-grid" style="margin-top:12px"><label class="field"><span>Action</span><select id="marAction"><option>GIVEN</option><option>HELD</option><option>REFUSED</option><option>NOT_GIVEN</option></select></label><label class="field"><span>Dose given</span><input id="marDose" /></label><label class="field full"><span>Reason / comment</span><textarea id="marReason">Administered as ordered.</textarea></label><label class="field full"><span><input id="marBarcode" type="checkbox" checked /> Barcode verification completed</span></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="record-mar" data-id="${id}">Record</button>`,'Medication administration');
  }
  function showChargeModal(){
    const encounter=state.tracker.find(x=>x.patient.mpi_id===state.selectedPatientId)?.encounter_id||'';
    openModal('Post Charge',`<div class="form-grid"><label class="field"><span>Patient MPI</span><input id="chgPatient" value="${esc(state.selectedPatientId)}" /></label><label class="field"><span>Encounter ID</span><input id="chgEncounter" value="${esc(encounter)}" /></label><label class="field"><span>Service code</span><input id="chgCode" value="CONS-001" /></label><label class="field"><span>Payer</span><input id="chgPayer" value="NHIF" /></label><label class="field full"><span>Description</span><input id="chgDescription" value="Specialist consultation" /></label><label class="field"><span>Quantity</span><input id="chgQty" type="number" value="1" /></label><label class="field"><span>Unit price (TZS)</span><input id="chgPrice" type="number" value="50000" /></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="create-charge">Post Charge</button>`,'Revenue cycle');
  }
  function showClaimModal(){
    const encounter=state.tracker.find(x=>x.patient.mpi_id===state.selectedPatientId)?.encounter_id||'';
    openModal('Create Claim',`<div class="form-grid"><label class="field"><span>Patient MPI</span><input id="clmPatient" value="${esc(state.selectedPatientId)}" /></label><label class="field"><span>Encounter ID</span><input id="clmEncounter" value="${esc(encounter)}" /></label><label class="field"><span>Payer</span><select id="clmPayer"><option>NHIF</option><option>UHI</option><option>iCHF</option><option>Employer</option></select></label><label class="field"><span>Member number</span><input id="clmMember" /></label><label class="field"><span>Amount (TZS)</span><input id="clmAmount" type="number" value="250000" /></label><label class="field"><span>Authorization</span><input id="clmAuth" /></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="create-claim">Create Draft</button>`,'Claims management');
  }
  function showInventoryModal(id,name){
    openModal('Inventory Transaction',`<div class="alert info"><strong>${esc(name)}</strong></div><div class="form-grid" style="margin-top:12px"><label class="field"><span>Transaction</span><select id="stkType"><option>RECEIPT</option><option>ISSUE</option><option>ADJUSTMENT_IN</option><option>ADJUSTMENT_OUT</option><option>TRANSFER_IN</option><option>TRANSFER_OUT</option><option>WASTE</option></select></label><label class="field"><span>Quantity</span><input id="stkQty" type="number" value="1" min="1" /></label><label class="field full"><span>Reason</span><textarea id="stkReason">Routine inventory transaction.</textarea></label><label class="field full"><span>Reference</span><input id="stkReference" placeholder="Purchase order, dispense, procedure or adjustment reference" /></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="inventory-transaction" data-id="${id}">Post Transaction</button>`,'Supply chain');
  }
  function accessCheckboxes(items,selected,scope){
    const selectedSet=new Set(selected||[]);
    const groups=[...new Set(items.map(item=>item.group))];
    return groups.map(group=>`<fieldset class="matrix-group"><legend>${esc(group)}</legend><div class="matrix-checks">${items.filter(item=>item.group===group).map(item=>`<label class="matrix-check"><input type="checkbox" data-access-scope="${scope}" value="${esc(item.code)}" ${selectedSet.has(item.code)?'checked':''}/><span><strong>${esc(item.label)}</strong><small>${esc(item.description||item.code)}</small></span></label>`).join('')}</div></fieldset>`).join('');
  }
  function generatedPassword(){return `Ua#${Math.random().toString(36).slice(2,8)}${new Date().getFullYear()}!X`;}
  function selectedAccess(scope){return $$(`[data-access-scope="${scope}"]:checked`,$('#modalBody')).map(input=>input.value);}
  function applyAccessTemplate(code){
    const template=state.accessCatalog?.templates?.[code];if(!template)return;
    const functions=new Set(template.functions||[]),departments=new Set(template.departments||[]);
    $$('[data-access-scope="function"]',$('#modalBody')).forEach(input=>input.checked=functions.has(input.value));
    $$('[data-access-scope="department"]',$('#modalBody')).forEach(input=>input.checked=departments.has(input.value));
  }
  function setMatrixScope(scope,checked){
    $$(`[data-access-scope="${scope}"]`,$('#modalBody')).forEach(input=>input.checked=checked);
  }
  function showUserCreatedModal(user,password){
    const credentials=`Username: ${user.username}\nTemporary password: ${password}\nFacilities: ${(user.facilities||[]).join(', ')}\nFunctions: ${(user.functions||[]).length}`;
    openModal('User Account Created',`<div class="alert success"><strong>${esc(user.display_name)} can now sign in.</strong><br/>The account and longitudinal access matrix were saved to the database and audited.</div><div class="credential-card"><label class="field"><span>Username</span><input id="createdUsername" value="${esc(user.username)}" readonly /></label><label class="field"><span>Temporary password</span><input id="createdPassword" value="${esc(password)}" readonly /></label><p><strong>${(user.functions||[]).length}</strong> functions · <strong>${(user.departments||[]).length}</strong> departments · <strong>${(user.facilities||[]).length}</strong> facilities</p><textarea id="createdCredentials" class="hidden">${esc(credentials)}</textarea></div><div class="alert warning"><strong>Handover control:</strong> deliver the temporary password through an approved channel. Government SSO and MFA must replace local passwords in production.</div>`,`<button class="btn" data-modal-action="close">Close</button><button class="btn btn-primary" data-action="copy-user-credentials">Copy Credentials</button>`,'Account provisioning complete');
  }
  function showUserModal(user=null){
    if(!state.accessCatalog)return toast('Access catalogue unavailable','Refresh the administration workspace and retry.');
    const editing=Boolean(user);
    const template=user?.role_code||'custom';
    const password=generatedPassword();
    const templates=Object.entries(state.accessCatalog.templates).map(([code,item])=>`<option value="${esc(code)}" ${code===template?'selected':''}>${esc(item.label)}</option>`).join('');
    const functions=user?.functions||state.accessCatalog.templates[template]?.functions||[];
    const departments=user?.departments||state.accessCatalog.templates[template]?.departments||[];
    const facilities=user?.facilities||[(state.facility==='ALL'?'MNH-UPANGA':state.facility)];
    openModal(editing?'Edit User and Access Matrix':'Create User Account',`<div id="userFormError" class="alert danger hidden"></div><div class="form-grid"><label class="field"><span>Username</span><input id="usrUsername" value="${esc(user?.username||'')}" ${editing?'disabled':''} autocomplete="off" /></label><label class="field"><span>Display name</span><input id="usrDisplay" value="${esc(user?.display_name||'')}" /></label><label class="field"><span>Access template</span><select id="usrTemplate">${templates}</select><small>Template selections are only a starting point. Every box remains independently editable.</small></label><label class="field"><span><input id="usrMfa" type="checkbox" ${user?.requires_mfa===false?'':'checked'} /> Require MFA when the production identity provider is enabled</span></label>${editing?'':`<label class="field full"><span>Temporary password</span><div class="inline-field"><input id="usrPassword" type="text" value="${password}" autocomplete="new-password"/><button class="btn btn-sm" type="button" data-action="generate-user-password">Generate</button></div><small>At least 12 characters with upper, lower, number and symbol.</small></label>`}<label class="field full"><span>Access change reason</span><input id="usrAccessReason" value="${editing?'Operational access update':'Initial account provisioning'}" /></label></div><div class="matrix-toolbar"><div><strong>Function matrix</strong><span>Select every function this user needs. Users may cross departments.</span></div><div><button class="btn btn-sm" type="button" data-action="matrix-all" data-scope="function">Select all</button><button class="btn btn-sm" type="button" data-action="matrix-none" data-scope="function">Clear</button></div></div><div class="access-matrix">${accessCheckboxes(state.accessCatalog.functions,functions,'function')}</div><div class="matrix-toolbar"><strong>Department matrix</strong><div><button class="btn btn-sm" type="button" data-action="matrix-all" data-scope="department">Select all</button><button class="btn btn-sm" type="button" data-action="matrix-none" data-scope="department">Clear</button></div></div><div class="access-matrix">${accessCheckboxes(state.accessCatalog.departments,departments,'department')}</div><div class="matrix-toolbar"><strong>Facility matrix</strong><div><button class="btn btn-sm" type="button" data-action="matrix-all" data-scope="facility">Select all</button><button class="btn btn-sm" type="button" data-action="matrix-none" data-scope="facility">Clear</button></div></div><div class="access-matrix">${accessCheckboxes(state.accessCatalog.facilities,facilities,'facility')}</div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="${editing?'update-user':'create-user'}" ${editing?`data-id="${user.user_id}"`:''}>${editing?'Save User':'Create User'}</button>`,'Function, department and facility access administration');
  }


  function showAppointmentStatusModal(id,status){
    const verb=status==='REINSTATED'?'Reinstate':'Cancel';
    openModal(`${verb} Appointment`,`<div class="alert warning"><strong>${verb} requires a reason.</strong> The prior status is preserved in appointment history.</div><label class="field" style="margin-top:12px"><span>Reason</span><textarea id="appointmentStatusReason">${status==='REINSTATED'?'Patient or clinic requested reinstatement.':'Patient, clinical service or operational reason.'}</textarea></label>`,`<button class="btn" data-modal-action="close">Back</button><button class="btn btn-primary" data-modal-action="confirm-appointment-status" data-id="${esc(id)}" data-status="${esc(status)}">${verb}</button>`,'Scheduling course change');
  }

  function showOrderCourseModal(id,operation){
    openModal(`${statusLabel(operation)} Order`,`<div class="alert warning"><strong>${statusLabel(operation)} is an auditable course change.</strong> The original order remains in the longitudinal record.</div><label class="field" style="margin-top:12px"><span>Clinical or operational reason</span><textarea id="orderCourseReason">${operation==='REINSTATE'?'Clinical need reassessed; reinstate the original order.':'Clinical status, duplicate order, patient decision or operational reason.'}</textarea></label>`,`<button class="btn" data-modal-action="close">Back</button><button class="btn btn-primary" data-modal-action="confirm-order-course" data-id="${esc(id)}" data-op="${esc(operation)}">Confirm</button>`,'Order course management');
  }

  function resetAudioCapture({preserveSession=false}={}){
    try{if(state.speechRecognition)state.speechRecognition.stop();}catch(_){ }
    state.speechRecognition=null;
    try{if(state.mediaRecorder&&state.mediaRecorder.state!=='inactive')state.mediaRecorder.stop();}catch(_){ }
    if(state.audioStream){state.audioStream.getTracks().forEach(track=>track.stop());}
    if(state.audioTimer)clearInterval(state.audioTimer);
    if(state.audioObjectUrl)URL.revokeObjectURL(state.audioObjectUrl);
    state.mediaRecorder=null;state.audioStream=null;state.audioChunks=[];state.audioBlob=null;state.audioObjectUrl=null;state.audioStartedAt=null;state.audioTimer=null;
    if(!preserveSession)state.audioSessionId=null;
  }

  function audioElapsed(){return state.audioStartedAt?Math.max(0,Math.floor((Date.now()-state.audioStartedAt)/1000)):0;}
  function updateAudioStatus(message,kind='info'){
    const box=$('#audioCaptureStatus');if(box){box.className=`audio-capture-status ${kind}`;box.innerHTML=message;}
    const timer=$('#audioTimer');if(timer)timer.textContent=formatDuration(audioElapsed());
  }
  function updateAudioPreview(blob,name='clinical-audio.webm'){
    if(state.audioObjectUrl)URL.revokeObjectURL(state.audioObjectUrl);
    state.audioBlob=blob;state.audioObjectUrl=URL.createObjectURL(blob);
    const player=$('#audioPreview');if(player){player.src=state.audioObjectUrl;player.classList.remove('hidden');}
    const label=$('#audioFileName');if(label)label.textContent=`${name} · ${(blob.size/1024/1024).toFixed(2)} MB`;
    const transcribe=$('#transcribeAudioButton');if(transcribe)transcribe.disabled=false;
    updateAudioStatus('<strong>Audio ready.</strong> Play it back, then send it to the secure transcription service.','success');
  }

  async function showAudioNoteModal(){
    if(!state.selectedPatientId)return toast('Patient record required','Select a patient before using audio-assisted documentation.');
    resetAudioCapture();
    let patient=null;try{patient=await selectedPatient();}catch(_){ }
    const selectedEncounter=$('#v9NoteEncounter')?.value;
    const encounter=selectedEncounter||v5CurrentEncounter(patient||{})?.encounter_id||patient?.encounters?.[0]?.encounter_id||state.tracker.find(x=>x.patient?.mpi_id===state.selectedPatientId)?.encounter_id||'';
    let capabilities={server_transcription_configured:false,max_audio_bytes:50*1024*1024,minimum_confidence:.55};
    try{capabilities=await api('/notes/audio-capabilities');}catch(_){ }
    const speechAvailable=Boolean(window.SpeechRecognition||window.webkitSpeechRecognition);
    const serverMessage=capabilities.server_transcription_available?`Secure server transcription is ready${capabilities.server_transcription_model?` (${capabilities.server_transcription_model})`:''}.`:capabilities.server_transcription_configured?'The transcription service is starting or temporarily unavailable; browser dictation and typed transcript remain available.':'Server transcription is not configured; browser dictation and typed transcript remain available.';
    openModal('Clinical Audio Annotation Studio',`<div class="alert info"><strong>Record-linked and clinician controlled.</strong> Audio creates an unsigned transcript and draft only. The clinician must compare the recording, correct the transcript, review the note, and sign through the normal documentation workflow.</div>
      <div class="audio-context-grid"><label class="field"><span>Patient MPI</span><input id="audioPatient" value="${esc(state.selectedPatientId)}" readonly></label><label class="field"><span>Encounter</span><input id="audioEncounter" value="${esc(encounter)}" readonly></label><label class="field"><span>Language</span><select id="audioLanguage"><option value="en" ${state.language==='en'?'selected':''}>English (Tanzania)</option><option value="sw" ${state.language==='sw'?'selected':''}>Kiswahili</option></select></label><label class="field"><span>Note type</span><select id="audioNoteType"><option value="PROGRESS_NOTE">Progress Note</option><option value="HISTORY_AND_PHYSICAL">History & Physical</option><option value="ED_PROVIDER_NOTE">ED Provider Note</option><option value="NURSING_SHIFT_NOTE">Nursing Shift Note</option><option value="CONSULT_NOTE">Consult Note</option><option value="PROCEDURE_NOTE">Procedure Note</option><option value="DISCHARGE_SUMMARY">Discharge Summary</option><option value="DEATH_PRONOUNCEMENT_NOTE">Death Pronouncement Note</option></select></label></div>
      <label class="audio-consent"><input id="audioConsent" type="checkbox"><span>I confirm clinical audio capture is permitted for this encounter and the patient/authorized representative has been informed according to facility policy.</span></label>
      <div class="audio-studio-grid"><section class="audio-recorder-card"><header><div><h3>Record or upload</h3><p>${esc(serverMessage)}</p></div><span id="audioTimer">00:00:00</span></header><div class="audio-controls"><button class="btn btn-primary" data-action="start-audio-recording">● Record</button><button class="btn" data-action="pause-audio-recording" id="pauseAudioButton" disabled>Pause</button><button class="btn" data-action="resume-audio-recording" id="resumeAudioButton" disabled>Resume</button><button class="btn" data-action="stop-audio-recording" id="stopAudioButton" disabled>Stop</button><button class="btn" data-action="clear-audio-recording">Clear</button></div><label class="audio-upload"><span>Upload WAV, MP3, M4A, OGG or WebM</span><input id="audioFileInput" type="file" accept="audio/*,.wav,.mp3,.m4a,.ogg,.webm"></label><audio id="audioPreview" class="hidden" controls></audio><small id="audioFileName">No recording selected</small><div id="audioCaptureStatus" class="audio-capture-status info"><strong>Ready.</strong> Confirm consent, then record or upload a clinical annotation.</div><button class="btn btn-primary full-width" data-action="transcribe-audio" id="transcribeAudioButton" disabled>${capabilities.server_transcription_available?'Transcribe Recording':'Retry Server Transcription'}</button></section>
      <section class="audio-recorder-card"><header><div><h3>Live browser dictation</h3><p>Fallback only; accuracy depends on browser and device.</p></div></header><div class="audio-controls"><button class="btn" data-action="start-dictation" ${speechAvailable?'':'disabled'}>Start Dictation</button><button class="btn" data-action="stop-dictation" disabled id="stopDictationButton">Stop</button></div><p class="muted">${speechAvailable?'Uses '+(state.language==='sw'?'sw-TZ':'en-TZ')+' speech recognition.':'Browser speech recognition is unavailable.'}</p></section></div>
      <label class="field full"><span>Transcript / annotation</span><textarea id="audioTranscript" class="editor audio-transcript" placeholder="The transcript appears here. Correct names, doses, measurements and clinical terminology against the source audio."></textarea></label>
      <div id="audioProvenance" class="audio-provenance hidden"></div><div id="audioDraftPanel" class="hidden"><div class="audio-draft-head"><h3>Unsigned assisted draft</h3><span>Clinician review required</span></div><textarea id="audioDraft" class="editor"></textarea><div class="audio-draft-actions"><button class="btn" data-action="insert-audio-draft">Insert into New Note</button><button class="btn btn-primary" data-action="replace-with-audio-draft">Open as New Note</button></div></div>`,`<button class="btn" data-modal-action="close">Close</button><button class="btn btn-primary" data-modal-action="generate-audio-draft">Generate Draft from Transcript</button>`,'High-fidelity audio capture, transcription provenance and clinical review');
    $('#modal')?.classList.add('audio-annotation-modal');
  }

  async function startAudioRecording(){
    if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder)return toast('Recording unavailable','This browser does not support secure microphone recording.');
    if(!$('#audioConsent')?.checked)return toast('Consent confirmation required','Confirm clinical audio capture permission before recording.');
    resetAudioCapture({preserveSession:true});
    try{
      const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1}});state.audioStream=stream;
      const candidates=['audio/webm;codecs=opus','audio/ogg;codecs=opus','audio/webm','audio/mp4'];const mime=candidates.find(x=>MediaRecorder.isTypeSupported?.(x))||'';
      const recorder=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);state.mediaRecorder=recorder;state.audioChunks=[];state.audioStartedAt=Date.now();
      recorder.ondataavailable=e=>{if(e.data?.size)state.audioChunks.push(e.data);};
      recorder.onstop=()=>{const type=recorder.mimeType||'audio/webm';const blob=new Blob(state.audioChunks,{type});state.audioStream?.getTracks().forEach(t=>t.stop());state.audioStream=null;if(state.audioTimer)clearInterval(state.audioTimer);state.audioTimer=null;if(blob.size)updateAudioPreview(blob,`clinical-note-${Date.now()}.${type.includes('ogg')?'ogg':type.includes('mp4')?'m4a':'webm'}`);};
      recorder.onerror=e=>{updateAudioStatus(`<strong>Recording error.</strong> ${esc(e.error?.message||'Microphone recording failed.')}`,'danger');};
      recorder.start(1000);state.audioTimer=setInterval(()=>updateAudioStatus('<strong>Recording…</strong> Speak clearly and state clinical measurements with units.','recording'),500);
      $('#stopAudioButton').disabled=false;$('#pauseAudioButton').disabled=false;updateAudioStatus('<strong>Recording…</strong> Speak clearly and state clinical measurements with units.','recording');
    }catch(error){resetAudioCapture({preserveSession:true});toast('Microphone unavailable',error.message||'Permission was denied or no microphone was found.');}
  }
  function pauseAudioRecording(){if(state.mediaRecorder?.state==='recording'){state.mediaRecorder.pause();$('#pauseAudioButton').disabled=true;$('#resumeAudioButton').disabled=false;updateAudioStatus('<strong>Paused.</strong> Resume when ready.','warning');}}
  function resumeAudioRecording(){if(state.mediaRecorder?.state==='paused'){state.mediaRecorder.resume();$('#pauseAudioButton').disabled=false;$('#resumeAudioButton').disabled=true;updateAudioStatus('<strong>Recording resumed.</strong>','recording');}}
  function stopAudioRecording(){if(state.mediaRecorder&&state.mediaRecorder.state!=='inactive'){state.mediaRecorder.stop();$('#stopAudioButton').disabled=true;$('#pauseAudioButton').disabled=true;$('#resumeAudioButton').disabled=true;updateAudioStatus('<strong>Finalizing audio…</strong>','info');}}
  function clearAudioRecording(){resetAudioCapture({preserveSession:true});const p=$('#audioPreview');if(p){p.src='';p.classList.add('hidden');}const f=$('#audioFileInput');if(f)f.value='';const n=$('#audioFileName');if(n)n.textContent='No recording selected';const b=$('#transcribeAudioButton');if(b)b.disabled=true;updateAudioStatus('<strong>Cleared.</strong> Record or upload another annotation.','info');}

  function startDictation(){
    const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SpeechRecognition)return toast('Dictation unavailable','This browser does not expose speech recognition.');
    if(!$('#audioConsent')?.checked)return toast('Consent confirmation required','Confirm clinical audio capture permission before dictation.');
    if(state.speechRecognition)state.speechRecognition.stop();
    const recognition=new SpeechRecognition();recognition.lang=$('#audioLanguage')?.value==='sw'?'sw-TZ':'en-TZ';recognition.continuous=true;recognition.interimResults=true;recognition.maxAlternatives=3;
    state.dictationStopRequested=false;state.dictationHadError=false;
    let finalText=$('#audioTranscript')?.value||'';
    recognition.onresult=event=>{let interim='';for(let i=event.resultIndex;i<event.results.length;i++){const text=event.results[i][0].transcript.trim();if(event.results[i].isFinal&&text){const prefix=finalText&&!/[\s\n]$/.test(finalText)?' ':'';finalText+=prefix+text;}else interim+=text;}const box=$('#audioTranscript');if(box)box.value=`${finalText}${interim?` ${finalText?' ':''}${interim}`:''}`;};
    recognition.onerror=event=>{state.dictationHadError=true;const errors={"not-allowed":"Microphone permission was denied. Allow microphone access for umojaehr.online, then try again.","service-not-allowed":"This browser has blocked its online speech service. Use Record and secure server transcription above, or try Chrome/Edge with speech recognition enabled.","audio-capture":"No working microphone was detected. Check the device input and browser permission.","network":"The browser speech service lost its network connection. Your finalized transcript has been preserved.","no-speech":"No speech was detected. Move closer to the microphone and try again."};toast('Browser dictation stopped',errors[event.error]||`Speech recognition error: ${event.error||'unknown'}`);};recognition.onend=()=>{state.speechRecognition=null;const stop=$('#stopDictationButton');if(stop)stop.disabled=true;};
    state.speechRecognition=recognition;recognition.start();const stop=$('#stopDictationButton');if(stop)stop.disabled=false;toast('Dictation started','Review every clinical term before generating the note.');
  }
  function stopDictation(){state.dictationStopRequested=true;if(state.speechRecognition){state.speechRecognition.stop();state.speechRecognition=null;}const stop=$('#stopDictationButton');if(stop)stop.disabled=true;toast('Dictation stopped','Your transcript was preserved. Correct names, medicines, doses and measurements before generating a draft.');}

  function showAudioResult(result){
    state.audioSessionId=result.session_id||null;const transcript=$('#audioTranscript');if(transcript)transcript.value=result.transcript||'';const draft=$('#audioDraft');if(draft)draft.value=result.draft_note||'';
    const panel=$('#audioDraftPanel');panel?.classList.remove('hidden');const provenance=$('#audioProvenance');if(provenance){const conf=result.confidence_percent==null?'Not calculated':`${result.confidence_percent}%`;const low=String(result.status||'').includes('LOW_CONFIDENCE');provenance.className=`audio-provenance ${low?'low':'ok'}`;provenance.innerHTML=`<strong>${low?'Low-confidence transcription — verify against audio':'Transcription provenance recorded'}</strong><span>Engine: ${esc(result.engine||'manual/browser')} ${result.engine_model?`· Model: ${esc(result.engine_model)}`:''} · Confidence: ${esc(conf)} · Duration: ${result.duration_seconds?formatDuration(result.duration_seconds):'—'} · Raw audio retained: ${result.raw_audio_retained?'Yes':'No'}</span>`;}
  }
  async function transcribeCapturedAudio(){
    if(!state.audioBlob)throw new Error('Record or upload audio first.');if(!$('#audioConsent')?.checked)throw new Error('Confirm clinical audio capture permission.');
    const form=new FormData();form.append('patient_mpi_id',$('#audioPatient').value);form.append('encounter_id',$('#audioEncounter').value||'');form.append('language',$('#audioLanguage').value);form.append('note_type',$('#audioNoteType').value);form.append('created_by',currentRole().user);form.append('consent_confirmed','true');form.append('file',state.audioBlob,state.audioBlob.name||'clinical-audio.webm');
    updateAudioStatus('<strong>Transcribing securely…</strong> Do not close this window.','info');const result=await api('/notes/audio-transcriptions',{method:'POST',body:form});showAudioResult(result);updateAudioStatus('<strong>Transcription complete.</strong> Compare it with the recording and correct any errors.','success');toast('Audio transcribed','Accuracy and provenance are displayed for clinician review.');
  }
  async function generateAudioDraftFromTranscript(){
    const transcript=$('#audioTranscript')?.value.trim();if(!transcript||transcript.length<3)throw new Error('Record, transcribe, paste or type an annotation first.');
    const result=await api('/notes/audio-annotations',{method:'POST',body:JSON.stringify({patient_mpi_id:$('#audioPatient').value,encounter_id:$('#audioEncounter').value||null,language:$('#audioLanguage').value,note_type:$('#audioNoteType').value,transcript,created_by:currentRole().user})});showAudioResult(result);toast('Unsigned draft generated','Review and edit before saving or signing.');
  }
  function useAudioDraft(replace=false){
    const draft=$('#audioDraft')?.value||'';if(!draft.trim())return toast('No draft available','Transcribe audio or generate a draft first.');
    state.pendingAudioDraft=draft;state.v9AudioSessionId=state.audioSessionId||null;state.v9NoteMode='new';state.v9SelectedNoteId=null;closeModal();
    if(state.route!=='clinical-documentation')navigate('clinical-documentation');else renderClinicalDocumentation().then(()=>{const box=$('#v9NoteBody');if(box){if(replace||!box.value.trim())box.value=draft;else v9InsertAtCursor(box,`\n\n${draft}`);}});
  }

  function showPasswordResetModal(userId,name){
    openModal('Reset User Password',`<div class="alert warning"><strong>${esc(name||userId)}</strong><br/>Reset is audited. The password must be changed through government IAM when SSO is activated.</div><div class="form-grid" style="margin-top:12px"><label class="field full"><span>New temporary password</span><input id="resetPassword" type="password" autocomplete="new-password" placeholder="12+ characters, upper/lower/number/symbol" /></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="confirm-reset-password" data-id="${esc(userId)}">Reset Password</button>`,'Privileged access control');
  }

  function showTelehealthModal(){
    const facilityOptions=state.facilities.map(f=>`<option value="${esc(f.code)}" ${f.code===state.facility?'selected':''}>${esc(f.name)}</option>`).join('');
    const start=new Date(Date.now()+60*60*1000);start.setMinutes(Math.ceil(start.getMinutes()/15)*15,0,0);
    openModal('Schedule Telehealth Session',`<div class="form-grid"><label class="field"><span>Patient MPI</span><input id="telPatient" value="${esc(state.selectedPatientId)}" /></label><label class="field"><span>Facility</span><select id="telFacility">${facilityOptions}</select></label><label class="field"><span>Service</span><input id="telService" value="Remote Follow-up" /></label><label class="field"><span>Provider</span><input id="telProvider" value="${esc(currentRole().user)}" /></label><label class="field"><span>Modality</span><select id="telModality"><option>VIDEO</option><option>AUDIO</option><option>STORE_AND_FORWARD</option></select></label><label class="field"><span>Scheduled start</span><input id="telStart" type="datetime-local" value="${start.toISOString().slice(0,16)}" /></label><label class="field full"><span>Reason and preparation</span><textarea id="telReason">Remote clinical review and follow-up.</textarea></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="create-telehealth">Schedule</button>`,'Connected mHealth');
  }

  function showPublicHealthModal(){
    openModal('Create Public Health Event',`<div class="form-grid"><label class="field"><span>Patient MPI</span><input id="phePatient" value="${esc(state.selectedPatientId)}" /></label><label class="field"><span>Condition code</span><input id="pheCode" value="A00" /></label><label class="field full"><span>Condition</span><input id="pheName" value="Suspected notifiable condition" /></label><label class="field"><span>Event type</span><select id="pheType"><option>NOTIFIABLE_CONDITION</option><option>SYNDROMIC_SIGNAL</option><option>OUTBREAK_CONTACT</option><option>IMMUNIZATION_REGISTRY</option></select></label><label class="field"><span>Report to</span><select id="pheDestination"><option>eIDSR</option><option>DHIS2</option><option>National Registry</option></select></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="create-public-health">Create Event</button>`,'Public health surveillance');
  }
  function showQualityModal(){
    openModal('Report Quality or Safety Incident',`<div class="form-grid"><label class="field"><span>Facility</span><select id="qsiFacility">${state.facilities.filter(x=>x.code!=='MUHAS').map(x=>`<option value="${x.code}" ${x.code===currentFacility().code?'selected':''}>${esc(x.name)}</option>`).join('')}</select></label><label class="field"><span>Patient MPI, optional</span><input id="qsiPatient" value="${esc(state.selectedPatientId||'')}" /></label><label class="field"><span>Category</span><input id="qsiCategory" value="Patient Safety" /></label><label class="field"><span>Severity</span><select id="qsiSeverity"><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></label><label class="field full"><span>Description</span><textarea id="qsiDescription">Describe what happened, immediate actions and current patient condition.</textarea></label><label class="field full"><span>Owner</span><input id="qsiOwner" value="Quality and Safety Pool" /></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="create-quality">Report</button>`,'Quality and safety');
  }

  function showModuleActivityModal(code,title){
    const encounter=state.tracker.find(x=>x.patient.mpi_id===state.selectedPatientId)?.encounter_id||'';
    openModal(`New ${title} Activity`,`<div class="form-grid"><label class="field"><span>Module code</span><input id="actModule" value="${esc(code)}" readonly /></label><label class="field"><span>Activity type</span><input id="actType" value="WORKQUEUE_ITEM" /></label><label class="field"><span>Patient MPI, optional</span><input id="actPatient" value="${esc(state.selectedPatientId||'')}" /></label><label class="field"><span>Encounter ID, optional</span><input id="actEncounter" value="${esc(encounter)}" /></label><label class="field"><span>Priority</span><select id="actPriority"><option>ROUTINE</option><option>MEDIUM</option><option>HIGH</option><option>URGENT</option><option>STAT</option><option>CRITICAL</option></select></label><label class="field"><span>Assigned to</span><input id="actAssigned" value="${esc(title)} Pool" /></label><label class="field full"><span>Title</span><input id="actTitle" value="New ${esc(title)} activity" /></label><label class="field full"><span>Details</span><textarea id="actDetails">Document the activity, clinical or operational context, expected outcome and escalation criteria.</textarea></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="create-module-activity">Create Activity</button>`,'Configurable module workflow');
  }

  async function handleAction(action, el){
    try {
      if(action==='refresh-tracker')return renderPatientFlow();
      if(action==='refresh-workqueues')return renderWorkqueues();
      if(action==='open-workqueue'){state.selectedWorkqueueId=el.dataset.id;return renderWorkqueues();}
      if(action==='start-walkin')return showWalkInModal();
      if(action==='filter-today'){const term=$('#todaySearch')?.value||'';const url=`/today-patients?facility_code=${encodeURIComponent(operationFacility())}&search=${encodeURIComponent(term)}&limit=100`;const result=await api(url);toast('Patient list filtered',`${result.total} matching records.`);return renderTodayPatients();}
      if(action==='today-arrive'){const result=await api(`/appointments/${el.dataset.appointment}`,{method:'PATCH',body:JSON.stringify({status:'ARRIVED',actor:currentRole().user,note:'Patient arrived; workflow notification published.'})});toast(result.notification?.title||'Patient Arrived',result.notification?.message||'Registration, triage and clinical workflows notified.',1000);return renderTodayPatients();}
      if(action==='today-status'){await api(`/encounters/${el.dataset.encounter}/status`,{method:'PATCH',body:JSON.stringify({status:el.dataset.status,actor:currentRole().user,location:statusLabel(el.dataset.status)})});toast('Workflow updated',statusLabel(el.dataset.status),1000);return renderTodayPatients();}
      if(action==='queue-item-action'){await api(`/workqueue-items/${el.dataset.id}`,{method:'PATCH',body:JSON.stringify({action:el.dataset.op,actor:currentRole().user,defer_hours:el.dataset.op==='DEFER'?24:null,note:'Updated from Workqueue Management.'})});toast('Workqueue item updated',statusLabel(el.dataset.op));return renderWorkqueues();}
      if(action==='run-patient-search')return performPatientSearch($('#patientSearchInput')?.value||'');
      if(action==='clear-registration'){state.registrationMatches=[];return renderRegistration();}
      if(action==='submit-registration')return submitRegistration(false);
      if(action==='tracker-status')return updateTrackerStatus(el.dataset.encounter,el.dataset.status);
      if(action==='discharge')return showDischargeModal(el.dataset.encounter);
      if(action==='chart-tab'){state.chartTab=el.dataset.tab;return renderChart();}
      if(action==='save-chart-flowsheet')return saveChartFlowEntries();
      if(action==='new-flowsheet')return showNewFlowSheetModal();
      if(action==='flowsheet-control')return controlFlowSheet(el.dataset.control);
      if(action==='change-flowsheet')return showChangeFlowSheetModal();
      if(action==='record-observation')return recordObservation();
      if(action==='new-order')return showOrderModal(el.dataset.encounter);
      if(action==='order-course')return showOrderCourseModal(el.dataset.id,el.dataset.op);
      if(action==='ack-result')return acknowledgeResult(el.dataset.result);
      if(action==='refresh-results')return renderResults();
      if(action==='copy-discharge')return copyDischargeSummary(el.dataset.encounter);
      if(action==='new-appointment')return showAppointmentModal();
      if(action==='appointment-status'){
        if(['CANCELLED','REINSTATED'].includes(el.dataset.status))return showAppointmentStatusModal(el.dataset.id,el.dataset.status);
        const result=await api(`/appointments/${el.dataset.id}`,{method:'PATCH',body:JSON.stringify({status:el.dataset.status,actor:currentRole().user,note:el.dataset.status==='ARRIVED'?'Patient arrived and workflow teams notified.':null})});
        if(result.notification)toast(result.notification.title||'Patient arrived',result.notification.message||'Workflow teams notified.',result.notification.duration_ms||1000);else toast('Appointment updated',statusLabel(el.dataset.status));
        return renderScheduling();
      }
      if(action==='referral-status'){await api(`/referrals/${el.dataset.id}`,{method:'PATCH',body:JSON.stringify({status:el.dataset.status,actor:currentRole().user,note:el.dataset.status==='CLOSED'?'Referral completed and returned summary acknowledged.':null})});toast('Referral updated',statusLabel(el.dataset.status));return renderScheduling();}
      if(action==='refresh-beds')return renderBedBoard();
      if(action==='bed-action')return handleBedAction(el);
      if(action==='new-note'){state.v9NoteMode='new';state.v9SelectedNoteId=null;return navigate('clinical-documentation');}
      if(action==='audio-note')return showAudioNoteModal();
      if(action==='start-audio-recording')return startAudioRecording();
      if(action==='pause-audio-recording')return pauseAudioRecording();
      if(action==='resume-audio-recording')return resumeAudioRecording();
      if(action==='stop-audio-recording')return stopAudioRecording();
      if(action==='clear-audio-recording')return clearAudioRecording();
      if(action==='transcribe-audio')return transcribeCapturedAudio();
      if(action==='start-dictation')return startDictation();
      if(action==='stop-dictation')return stopDictation();
      if(action==='insert-audio-draft')return useAudioDraft(false);
      if(action==='replace-with-audio-draft')return useAudioDraft(true);
      if(action==='advisory-action'){await api('/practice-advisories/actions',{method:'POST',body:JSON.stringify({patient_mpi_id:state.selectedPatientId,encounter_id:el.dataset.encounter||null,advisory_key:el.dataset.key,action:el.dataset.op,actor:currentRole().user})});toast('Advisory recorded',statusLabel(el.dataset.op));return renderClinicalDocumentation();}
      if(action==='sign-note'){await api(`/notes/${el.dataset.id}/sign`,{method:'POST',body:JSON.stringify({signer:currentRole().user,attestation:'Electronically signed in Umoja Afya.'})});toast('Note signed','The note is now part of the legal health record.');return renderClinicalDocumentation();}
      if(action==='new-medication')return showMedicationModal();
      if(action==='verify-med'){await api(`/medications/${el.dataset.id}/verify`,{method:'POST',body:JSON.stringify({pharmacist:currentRole().user})});toast('Medication verified','The order is eligible for eMAR administration.');return renderMedicationWorkspace();}
      if(action==='administer-med')return showAdministrationModal(el.dataset.id,el.dataset.med);
      if(action==='claim-status'){await api(`/claims/${el.dataset.id}`,{method:'PATCH',body:JSON.stringify({status:el.dataset.status,actor:currentRole().user})});toast('Claim updated',statusLabel(el.dataset.status));return renderRevenueCycle();}
      if(action==='new-charge')return showChargeModal();
      if(action==='new-claim')return showClaimModal();
      if(action==='complete-task'){await api(`/work-items/${el.dataset.id}`,{method:'PATCH',body:JSON.stringify({status:'COMPLETED',actor:currentRole().user,note:'Completed from workqueue.'})});toast('Task completed','Closed-loop work item updated.');return renderRevenueCycle();}
      if(action==='inventory-txn')return showInventoryModal(el.dataset.id,el.dataset.name);
      if(action==='refresh-inventory')return renderSupplyChain();
      if(action==='new-user')return showUserModal();
      if(action==='edit-user')return showUserModal(state.adminUsers.find(x=>x.user_id===el.dataset.id)||null);
      if(action==='generate-user-password'){const input=$('#usrPassword');if(input)input.value=generatedPassword();return;}
      if(action==='matrix-all'){setMatrixScope(el.dataset.scope,true);return;}
      if(action==='matrix-none'){setMatrixScope(el.dataset.scope,false);return;}
      if(action==='copy-user-credentials'){const value=$('#createdCredentials')?.value||'';try{await navigator.clipboard.writeText(value);toast('Credentials copied','Use an approved secure channel for delivery.');}catch(_){toast('Copy unavailable','Select and copy the username and password manually.');}return;}
      if(action==='toggle-user'){await api(`/admin/users/${el.dataset.id}`,{method:'PATCH',body:JSON.stringify({active:el.dataset.active==='true',actor:currentRole().user,access_reason:'Account status change'})});toast('User account updated',el.dataset.active==='true'?'Account enabled.':'Account disabled.');return renderSystemAdmin();}
      if(action==='reset-user-password')return showPasswordResetModal(el.dataset.id,el.dataset.name);
      if(action==='new-telehealth')return showTelehealthModal();
      if(action==='telehealth-action'){await api(`/telehealth-sessions/${el.dataset.id}/actions`,{method:'POST',body:JSON.stringify({action:el.dataset.op,actor:currentRole().user,note:'Updated from remote-care workspace.'})});toast('Telehealth session updated',statusLabel(el.dataset.op));return renderTelehealth();}
      if(action==='new-public-health')return showPublicHealthModal();
      if(action==='new-quality')return showQualityModal();
      if(action==='new-module-activity')return showModuleActivityModal(el.dataset.code,el.dataset.title);
      if(action==='module-activity-status'){await api(`/module-activities/${el.dataset.id}`,{method:'PATCH',body:JSON.stringify({status:el.dataset.status,actor:currentRole().user,note:'Updated from module workqueue.'})});toast('Activity updated',statusLabel(el.dataset.status));return renderGenericModule(state.route);}
    } catch(error){toast('Action failed',error.message);}
  }

  async function updateTrackerStatus(encounterId,status){
    const locationMap={REGISTERED:'Patient Registration',WAITING_TRIAGE:'Triage Queue',TRIAGED:'Triage Complete',READY_FOR_PROVIDER:'Provider Queue',ROOMED:'Examination Room',IN_PROGRESS:'With Provider',WAITING_RESULTS:'Diagnostic Hold',READY_FOR_DISCHARGE:'Discharge Workqueue'};
    await api(`/encounters/${encounterId}/status`,{method:'PATCH',body:JSON.stringify({status,location:locationMap[status],provider:status==='IN_PROGRESS'?currentRole().user:undefined,actor:currentRole().user})});
    toast('Patient flow updated',`${encounterId} moved to ${statusLabel(status)}.`);renderPatientFlow();
  }

  async function submitRegistration(forceCreate){
    const form=$('#registrationForm');
    let data;
    if(forceCreate&&state.pendingRegistration){data={...state.pendingRegistration,force_create:true};}
    else {
      if(!form)return;
      data=Object.fromEntries(new FormData(form).entries());
      if(!data.first_name||!data.last_name)return toast('Registration incomplete','First and last name are required.');
      data.force_create=false;if(!data.date_of_birth)delete data.date_of_birth;
      state.pendingRegistration={...data};
    }
    try {
      const result=await api('/registration',{method:'POST',body:JSON.stringify(data)});
      state.pendingRegistration=null;state.registrationMatches=[];state.selectedPatientId=result.patient.mpi_id;saveState();toast('Patient registered',`${result.patient.full_name} · ${result.patient.mpi_id}`);navigate('chart');
    } catch(error){
      if(error.status===409&&error.data?.detail?.matches){state.registrationMatches=error.data.detail.matches;renderRegistration();openModal('Possible Duplicate Found',`<div class="alert warning"><strong>Review required:</strong> A new national identity was not created because possible matches exist.</div><div style="margin-top:12px">${state.registrationMatches.map(renderDuplicate).join('')}</div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-danger" data-modal-action="force-registration">Create Anyway</button>`,'National MPI safety');return;}
      throw error;
    }
  }

  function showDischargeModal(encounterId){
    const encounter=state.tracker.find(e=>e.encounter_id===encounterId);
    openModal('Discharge Patient',`<div class="alert info"><strong>${esc(encounter?.patient.full_name||encounterId)}</strong> · medication reconciliation, pending results and follow-up should be completed before discharge.</div><div class="form-grid" style="margin-top:12px"><label class="field"><span>Disposition</span><select id="disposition"><option>Home</option><option>Home with services</option><option>Transfer to another facility</option><option>Against medical advice</option><option>Deceased</option></select></label><label class="field full"><span>Discharge summary</span><textarea id="dischargeSummary">Clinical condition improved and patient is stable for discharge.</textarea></label><label class="field full"><span>Follow-up plan</span><textarea id="dischargeFollowup">Follow up in clinic as scheduled; return immediately for danger signs.</textarea></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="confirm-discharge" data-encounter="${encounterId}">Complete Discharge</button>`,'Transitions of care');
  }

  async function showNewFlowSheetModal(){
    const [patient,templates]=await Promise.all([selectedPatient(),api('/flowsheet-templates')]);
    if(!patient)throw new Error('Select a patient record before creating a flowsheet.');
    state.v5Patient=patient;state.v5FlowTemplates=templates;
    return showCreateTemplateFlowsheetV5('TRIAGE_AMBULATORY');
  }
  function showChangeFlowSheetModal(){
    openModal('Change Flowsheet',`<div class="form-grid"><label class="field"><span>New cadence minutes</span><input id="changeCadence" type="number" value="15" min="1" /></label><label class="field"><span>New name, optional</span><input id="changeName" placeholder="Leave blank to retain current name" /></label><label class="field full"><span>Replacement parameters, optional</span><textarea id="changeParameters" placeholder="Comma-separated; leave blank to retain existing parameters"></textarea></label><label class="field full"><span>Reason for change</span><textarea id="changeReason">Clinical condition or monitoring frequency changed.</textarea></label></div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="confirm-change-flowsheet">Apply Change</button>`,'Flowsheet control');
  }
  async function controlFlowSheet(control,note){
    if(!state.selectedFlowSheetId)return;
    await api(`/flowsheets/${state.selectedFlowSheetId}/actions`,{method:'POST',body:JSON.stringify({action:control,actor:currentRole().user,note:note||`${control} from clinical workspace`})});
    toast('Flowsheet updated',`${control} recorded in the audit history.`);renderFlowsheets();
  }
  async function recordObservation(){
    const parameter=$('#obsParameter')?.value,value=$('#obsValue')?.value.trim(),unit=$('#obsUnit')?.value.trim();
    if(!value)return toast('Observation incomplete','Enter a value.');
    await api(`/flowsheets/${state.selectedFlowSheetId}/observations`,{method:'POST',body:JSON.stringify({parameter,value,unit,recorded_by:currentRole().user})});toast('Observation recorded',`${parameter}: ${value} ${unit||''}`);renderFlowsheets();
  }
  function showOrderModal(encounterId){
    const resolved=encounterId||state.tracker.find(e=>e.patient.mpi_id===state.selectedPatientId)?.encounter_id||'';
    openModal('Place Order',`<div class="form-grid"><label class="field"><span>Encounter ID</span><input id="orderEncounter" value="${esc(resolved)}" /></label><label class="field"><span>Order type</span><select id="orderType"><option>Laboratory</option><option>Imaging</option><option>Medication</option><option>Blood</option><option>Procedure</option><option>Referral</option></select></label><label class="field"><span>Priority</span><select id="orderPriority"><option>ROUTINE</option><option>URGENT</option><option>STAT</option></select></label><label class="field full"><span>Order</span><input id="orderName" value="Complete blood count" /></label><label class="field full"><span>Clinical indication</span><textarea id="orderIndication">Evaluate current clinical condition.</textarea></label></div><div class="alert danger" style="margin-top:12px"><strong>Decision support:</strong> allergy, duplicate, interaction, renal dosing and pregnancy checks should run before signature.</div>`,`<button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-modal-action="submit-order">Sign Order</button>`,'CPOE and clinical decision support');
  }
  async function acknowledgeResult(resultId){
    await api(`/results/${resultId}/acknowledge`,{method:'POST',body:JSON.stringify({actor:currentRole().user,action_taken:'Reviewed in results worklist and incorporated into plan of care.'})});state.notifications=Math.max(0,state.notifications-1);updateChrome();toast('Result acknowledged','The action was recorded in the audit trail.');renderResults();
  }

  async function handleModalAction(action,el){
    const showFormError=message=>{const box=$('#userFormError');if(box){box.textContent=message;box.classList.remove('hidden');}else toast('Action failed',message);};
    try {
      if(action==='close')return closeModal();
      if(action==='force-registration'){closeModal();return submitRegistration(true);}
      if(action==='confirm-discharge'){await api(`/encounters/${el.dataset.encounter}/discharge`,{method:'POST',body:JSON.stringify({disposition:$('#disposition').value,summary:$('#dischargeSummary').value,follow_up:$('#dischargeFollowup').value,actor:currentRole().user})});closeModal();toast('Patient discharged','The patient moved to Recent Discharges and follow-up is available.');return renderPatientFlow();}
      if(action==='confirm-change-flowsheet'){const cadence=Number($('#changeCadence').value);const note=$('#changeReason').value;const name=$('#changeName').value.trim()||null;const parameterText=$('#changeParameters').value.trim();const parameters=parameterText?parameterText.split(',').map(x=>x.trim()).filter(Boolean):null;await api(`/flowsheets/${state.selectedFlowSheetId}/actions`,{method:'POST',body:JSON.stringify({action:'CHANGE',actor:currentRole().user,note,cadence_minutes:cadence,name,parameters})});closeModal();toast('Flowsheet changed',`Cadence set to ${cadence} minutes${name?`; name changed to ${name}`:''}.`);return renderFlowsheets();}
      if(action==='submit-order'){const payload={encounter_id:$('#orderEncounter').value,order_type:$('#orderType').value,order_name:$('#orderName').value,priority:$('#orderPriority').value,indication:$('#orderIndication').value,ordered_by:currentRole().user};await api('/orders',{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Order signed',`${payload.order_name} routed to ${payload.order_type}.`);return state.route==='chart'?renderChart():renderOrders();}
      if(action==='confirm-order-course'){const reason=$('#orderCourseReason').value.trim();if(!reason)throw new Error('A reason is required.');await api(`/orders/${el.dataset.id}/actions`,{method:'POST',body:JSON.stringify({action:el.dataset.op,reason,actor:currentRole().user})});closeModal();toast('Order course updated',`${statusLabel(el.dataset.op)} recorded with history.`);return state.route==='chart'?renderChart():renderOrders();}
      if(action==='create-appointment'){const payload={patient_mpi_id:$('#aptPatient').value,facility_code:$('#aptFacility').value,service:$('#aptService').value,provider:$('#aptProvider').value||'Duty roster / next available clinician',appointment_type:$('#aptMode')?.value||'PUBLIC_DUTY_ROSTER',scheduled_start:new Date($('#aptStart').value).toISOString(),duration_minutes:Number($('#aptDuration').value),notes:$('#aptNotes').value,created_by:currentRole().user};await api('/appointments',{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Appointment scheduled',`${payload.service} schedule record created.`);return renderScheduling();}
      if(action==='confirm-appointment-status'){const reason=$('#appointmentStatusReason').value.trim();if(!reason)throw new Error('A reason is required.');const result=await api(`/appointments/${el.dataset.id}`,{method:'PATCH',body:JSON.stringify({status:el.dataset.status,actor:currentRole().user,note:reason})});closeModal();toast('Appointment updated',statusLabel(result.status||el.dataset.status));return renderScheduling();}
      if(action==='assign-bed'){await api(`/beds/${el.dataset.id}/actions`,{method:'POST',body:JSON.stringify({action:'ASSIGN',encounter_id:$('#bedEncounter').value,actor:currentRole().user,reason:$('#bedReason').value})});closeModal();toast('Bed assigned','Encounter location updated.');return renderBedBoard();}
      if(action==='create-note'){const payload={patient_mpi_id:$('#notePatient').value,encounter_id:$('#noteEncounter').value||null,note_type:$('#noteType').value,title:$('#noteTitle').value,body:$('#noteBody').value,author:currentRole().user,service:$('#noteService').value,cosign_required:$('#noteCosign').checked};await api('/notes',{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Note saved','Draft documentation is available for review and signature.');return renderClinicalDocumentation();}
      if(action==='generate-audio-draft')return generateAudioDraftFromTranscript();
      if(action==='create-medication'){const payload={patient_mpi_id:$('#medPatient').value,encounter_id:$('#medEncounter').value,medication_name:$('#medName').value,dose:$('#medDose').value,route:$('#medRoute').value,frequency:$('#medFrequency').value,indication:$('#medIndication').value,ordered_by:currentRole().user};await api('/medications',{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Medication ordered','Routed to pharmacy verification.');return renderMedicationWorkspace();}
      if(action==='record-mar'){const payload={action:$('#marAction').value,dose_given:$('#marDose').value||null,administered_by:currentRole().user,reason:$('#marReason').value,barcode_verified:$('#marBarcode').checked};await api(`/medications/${el.dataset.id}/administrations`,{method:'POST',body:JSON.stringify(payload)});closeModal();toast('eMAR recorded',statusLabel(payload.action));return renderMedicationWorkspace();}
      if(action==='create-charge'){const payload={patient_mpi_id:$('#chgPatient').value,encounter_id:$('#chgEncounter').value,service_code:$('#chgCode').value,description:$('#chgDescription').value,quantity:Number($('#chgQty').value),unit_price:Number($('#chgPrice').value),payer:$('#chgPayer').value,posted_by:currentRole().user};await api('/charges',{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Charge posted',formatTZS(payload.quantity*payload.unit_price));return renderRevenueCycle();}
      if(action==='create-claim'){const payload={patient_mpi_id:$('#clmPatient').value,encounter_id:$('#clmEncounter').value,payer:$('#clmPayer').value,member_number:$('#clmMember').value||null,amount:Number($('#clmAmount').value),authorization_number:$('#clmAuth').value||null};await api('/claims',{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Claim created','Draft claim added to the workqueue.');return renderRevenueCycle();}
      if(action==='inventory-transaction'){const payload={transaction_type:$('#stkType').value,quantity:Number($('#stkQty').value),reason:$('#stkReason').value,reference:$('#stkReference').value||null,actor:currentRole().user};await api(`/inventory/${el.dataset.id}/transactions`,{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Inventory updated',`${payload.transaction_type}: ${payload.quantity}`);return renderSupplyChain();}
      if(action==='create-walkin'){const patient=$('#walkPatient').value.trim();if(!patient)throw new Error('Select or enter a patient MPI.');const result=await api('/walk-ins',{method:'POST',body:JSON.stringify({patient_mpi_id:patient,facility_code:operationFacility(),service_point_id:$('#walkPoint').value,reason:$('#walkReason').value,notes:$('#walkNotes').value,coverage_route:$('#walkCoverage').value,created_by:currentRole().user})});closeModal();toast('Patient Arrived',state.language==='sw'?result.notification.message_sw:result.notification.message_en,result.notification.duration_ms||1000);return renderTodayPatients();}
      if(action==='create-user'||action==='update-user'){
        const editing=action==='update-user';
        const username=$('#usrUsername')?.value.trim();const displayName=$('#usrDisplay')?.value.trim();const functions=selectedAccess('function');const departments=selectedAccess('department');const facilities=selectedAccess('facility');const reason=$('#usrAccessReason')?.value.trim();
        if(!displayName||(!editing&&!username))return showFormError('Username and display name are required.');
        if(!functions.length)return showFormError('Select at least one function.');
        if(!departments.length)return showFormError('Select at least one department.');
        if(!facilities.length)return showFormError('Select at least one facility.');
        if(!reason)return showFormError('Enter an access provisioning or change reason.');
        const payload={display_name:displayName,role_code:$('#usrTemplate').value,requires_mfa:$('#usrMfa').checked,function_codes:functions,department_codes:departments,facility_codes:facilities,access_reason:reason,actor:currentRole().user};
        let temporaryPassword='';
        if(!editing){temporaryPassword=$('#usrPassword').value;Object.assign(payload,{username,password:temporaryPassword,facility_code:facilities[0]});}
        const result=await api(editing?`/admin/users/${el.dataset.id}`:'/admin/users',{method:editing?'PATCH':'POST',body:JSON.stringify(payload)});
        if(editing){closeModal();toast('User updated',`${result.display_name}'s access matrix was saved.`);return renderSystemAdmin();}
        state.adminUsers=[...state.adminUsers.filter(item=>item.user_id!==result.user_id),result];showUserCreatedModal(result,temporaryPassword);return;
      }
      if(action==='confirm-reset-password'){const password=$('#resetPassword').value;if(!password)throw new Error('Enter a new temporary password.');await api(`/admin/users/${el.dataset.id}/reset-password`,{method:'POST',body:JSON.stringify({password,actor:currentRole().user})});closeModal();toast('Password reset','The account password was updated and audited.');return renderSystemAdmin();}
      if(action==='create-telehealth'){const payload={patient_mpi_id:$('#telPatient').value,facility_code:$('#telFacility').value,service:$('#telService').value,provider:$('#telProvider').value,modality:$('#telModality').value,scheduled_start:new Date($('#telStart').value).toISOString(),reason:$('#telReason').value,created_by:currentRole().user};await api('/telehealth-sessions',{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Remote-care session scheduled',`${payload.service} session added to the selected record.`);return renderTelehealth();}
      if(action==='create-public-health'){const payload={patient_mpi_id:$('#phePatient').value,condition_code:$('#pheCode').value,condition_name:$('#pheName').value,event_type:$('#pheType').value,reported_to:$('#pheDestination').value};await api('/public-health-events',{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Public health event created','Routed through the national interface outbox.');return renderPublicHealth();}
      if(action==='create-quality'){const payload={facility_code:$('#qsiFacility').value,patient_mpi_id:$('#qsiPatient').value||null,category:$('#qsiCategory').value,severity:$('#qsiSeverity').value,description:$('#qsiDescription').value,reported_by:currentRole().user,owner:$('#qsiOwner').value||null};await api('/quality-incidents',{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Incident reported','Quality and Safety work item created.');return renderQuality();}
      if(action==='create-module-activity'){const payload={module_code:$('#actModule').value,activity_type:$('#actType').value,title:$('#actTitle').value,patient_mpi_id:$('#actPatient').value||null,encounter_id:$('#actEncounter').value||null,priority:$('#actPriority').value,assigned_to:$('#actAssigned').value||null,details:$('#actDetails').value,payload:{source:'web-workspace'},created_by:currentRole().user};await api('/module-activities',{method:'POST',body:JSON.stringify(payload)});closeModal();toast('Module activity created',payload.title);return renderGenericModule(state.route);}
    } catch(error){
      if(['create-user','update-user'].includes(action))showFormError(error.message);else toast('Action failed',error.message);
    }
  }

  async function copyDischargeSummary(encounterId){
    const item=state.recentDischarges.find(d=>d.encounter_id===encounterId);
    if(!item)return toast('Copy failed','Discharge record was not found.');
    const text=`${item.patient.full_name} (${item.patient.mpi_id})\nFacility: ${item.facility.name}\nService: ${item.service}\nDischarged: ${fmtDate(item.discharge_at)}\nDisposition: ${item.discharge_disposition||'—'}\nSummary: ${item.discharge_summary||'Summary pending'}\nFollow-up: ${item.follow_up||'Not documented'}`;
    try {
      if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(text);
      else {const area=document.createElement('textarea');area.value=text;document.body.appendChild(area);area.select();document.execCommand('copy');area.remove();}
      toast('Discharge summary copied','The transition-of-care summary is ready to paste.');
    } catch(_){toast('Copy failed','Browser clipboard access is unavailable.');}
  }

  function openModal(title,body,footer='',eyebrow='Umoja Afya workflow'){ $('#modalTitle').textContent=title;$('#modalEyebrow').textContent=eyebrow;$('#modalBody').innerHTML=body;$('#modalFooter').innerHTML=footer;$('#modalBackdrop').classList.remove('hidden'); }
  function closeModal(){ $('#modalBackdrop').classList.add('hidden'); }
  function showNotifications(){openModal('Notifications',`<div class="list"><div class="list-item"><span class="list-icon">!</span><div><strong>Critical result requires acknowledgement</strong><p>Creatinine 238 µmol/L · MNH Core Laboratory</p></div></div><div class="list-item"><span class="list-icon">↔</span><div><strong>Patients waiting for providers</strong><p>Open the Provider Patient Tracker for current status.</p></div></div><div class="list-item"><span class="list-icon">✓</span><div><strong>Recent discharges available</strong><p>Review summaries and follow-up tasks.</p></div></div></div>`,`<button class="btn btn-primary" data-modal-action="close">Close</button>`);}
  function toast(title,message,duration=60000){const region=$('#toastRegion');if(!region)return;const node=document.createElement('div');node.className='toast';node.setAttribute('role','status');node.innerHTML=`<button class="toast-close" type="button" aria-label="Dismiss notification">×</button><strong>${esc(title)}</strong><span>${esc(message)}</span><i class="toast-progress" aria-hidden="true"></i>`;region.appendChild(node);const visibleFor=Math.max(60000,Number(duration)||60000);node.style.setProperty('--toast-duration',`${visibleFor}ms`);const remove=()=>{node.classList.add('leaving');setTimeout(()=>node.remove(),180);};node.querySelector('.toast-close').addEventListener('click',remove);setTimeout(remove,visibleFor);}

  /* ==========================================================================
     Umoja Afya v4 high-fidelity interface layer
     ========================================================================== */
  routeFunctionMap['patient-station']='patient.chart';
  roleDefaults.registration='today-patients';
  roleDefaults.admin='today-patients';
  roleDefaults.physician='patient-station';

  const v4IconPaths = {
    home:'M3 11.5 12 4l9 7.5M5 10.5V21h5v-6h4v6h5V10.5',
    patient:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
    queue:'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
    chart:'M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z',
    document:'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h8M8 9h2',
    orders:'M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11',
    result:'M6 20V10M12 20V4M18 20v-7',
    referral:'M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3',
    pharmacy:'M10.5 2.5l11 11-8 8-11-11zM8 8l8 8M14.5 5.5l-9 9',
    lab:'M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3M7.5 15h9',
    bed:'M3 7v11M21 18V9a2 2 0 0 0-2-2h-7v11M3 13h18M3 18h18M7 7a2 2 0 1 0 0 4h5V7Z',
    finance:'M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7H14a3.5 3.5 0 0 1 0 7H6',
    audit:'M12 3l8 4v5c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V7zM9 12l2 2 4-4',
    radiology:'M12 3a9 9 0 1 0 9 9M12 7v5l3 3M12 12 8 4M12 12l-8 4',
    billing:'M5 3h14v18l-3-2-4 2-4-2-3 2zM8 8h8M8 12h8M8 16h5',
    records:'M4 4h16v16H4zM8 2v4M16 2v4M4 9h16M8 13h3M13 13h3M8 17h5',
    registration:'M8 7a4 4 0 1 0 0-8M2 21v-2a6 6 0 0 1 6-6h3M17 11v6M14 14h6',
    schedule:'M3 5h18v16H3zM16 3v4M8 3v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01',
    reports:'M4 19V9M10 19V5M16 19v-7M22 19V2',
    tools:'M14.7 6.3a4 4 0 0 0-5 5L3 18l3 3 6.7-6.7a4 4 0 0 0 5-5l-3 3-3-3z',
    settings:'M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1 1.55V20h-3v-.09a1.7 1.7 0 0 0-1-1.55 1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 15a1.7 1.7 0 0 0-1.55-1H5v-3h.09A1.7 1.7 0 0 0 6.64 10a1.7 1.7 0 0 0-.34-1.88l-.06-.06L8.36 5.94l.06.06a1.7 1.7 0 0 0 1.88.34A1.7 1.7 0 0 0 11.85 5V5h3v.09a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06a1.7 1.7 0 0 0-.34 1.88A1.7 1.7 0 0 0 21 11.85V12h-3v-.09A1.7 1.7 0 0 0 19.4 15Z',
    transfer:'M17 3l4 4-4 4M3 7h18M7 21l-4-4 4-4M21 17H3',
    discharge:'M9 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4M16 17l5-5-5-5M21 12H9',
    print:'M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v8H6z',
    shield:'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10ZM9 12l2 2 4-4',
    team:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M19 8v6M16 11h6',
    scan:'M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 8h10v8H7z',
    search:'M21 21l-4.35-4.35M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
    userplus:'M15 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M8 11a4 4 0 1 0 0-8M19 8v6M16 11h6'
  };
  function v4Icon(name,cls=''){const p=v4IconPaths[name]||v4IconPaths.document;return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${p}"></path></svg>`;}

  const v4RailItems=[
    ['dashboard','Home','home'],['patient-station','Patient Station','patient'],['workqueues','Workqueues','queue'],['chart','Chart Review','chart'],['clinical-documentation','Documents','document'],['orders','Orders','orders'],['results','Results','result'],['scheduling','Referrals','referral'],['pharmacy','Pharmacy','pharmacy'],['laboratory','Lab','lab'],['bed-board','Bed Board','bed'],['revenue','Finance','finance'],['admin','Audit','audit']
  ];
  const v4ModuleTabs=[
    {label:'Scheduling',route:'scheduling',icon:'schedule',routes:['scheduling']},
    {label:'Registration/ADT',route:'today-patients',icon:'registration',routes:['today-patients','registration','bed-board','patient-search']},
    {label:'Patient Care',route:'patient-station',icon:'patient',routes:['patient-station','patient-flow','chart','flowsheets','orders','results','clinical-documentation','nursing']},
    {label:'Health Records',route:'chart',icon:'records',routes:['chart','clinical-documentation','recent-discharges']},
    {label:'Radiology',route:'radiology',icon:'radiology',routes:['radiology']},
    {label:'Billing',route:'revenue',icon:'billing',routes:['revenue']},
    {label:'Reports',route:'analytics',icon:'reports',routes:['analytics','public-health','quality']},
    {label:'Tools',route:'dashboard',icon:'tools',routes:['dashboard','supply','telehealth','workforce']},
    {label:'Settings',route:'admin',icon:'settings',routes:['admin']}
  ];
  const v4LauncherMap={
    'Patient Care':[['Patient Station','patient-station','patient','Open selected patient record'],['Chart','chart','chart','Longitudinal clinical chart'],['Provider Patient Tracker','patient-flow','queue','Arrived, waiting, triaged and roomed'],['Clinical Documentation','clinical-documentation','document','Notes and encounter documentation'],['Flowsheets & eMAR','flowsheets','result','Start, pause, resume, change and stop'],['Orders','orders','orders','Record-driven orders and course changes'],['Results Review','results','result','Critical results and acknowledgement']],
    'Radiology':[['Front Desk','radiology','radiology','Imaging scheduling and arrival'],['Protocol Worklist','radiology','queue','Protocol and prioritize studies'],['Study Images','radiology','chart','DICOM/PACS review'],['Imaging Audit Trail','radiology','audit','Access and change history']],
    'Billing':[['Hospital Account','revenue','billing','Account and guarantor'],['Claim Workqueues','workqueues','queue','Claim edit and follow-up'],['Cash Drawer','revenue','finance','Cash collection and reconciliation'],['Estimates','revenue','reports','Patient estimates'],['Payment Collection','revenue','finance','NHIF, cash and private payer']],
    'Health Records':[['Chart Review','chart','chart','Open longitudinal record'],['Documents','clinical-documentation','document','Scan and manage documents'],['Release of Information','chart','records','Controlled disclosure'],['HIM Reports','analytics','reports','Documentation and coding reports']],
    'Registration/ADT':[['Today’s Patients','today-patients','patient','Arrivals, check-in and walk-ins'],['Registration','registration','registration','MPI, demographics and coverage'],['Patient Station','patient-station','patient','Encounter and registration record'],['Bed Control','bed-board','bed','Beds and capacity'],['Transfer Center','bed-board','transfer','Transfers and referrals']],
    'Scheduling':[['Appointments','scheduling','schedule','Service-point and provider scheduling'],['View Schedules','scheduling','schedule','Duty rosters and provider calendars'],['Arrived','today-patients','patient','Arrivals and front-desk workflow'],['Workqueue List','workqueues','queue','Scheduling follow-up'],['Status Board','today-patients','reports','Today’s patient status']],
    'Reports':[['ADT Reports','analytics','reports','Admission, discharge and transfer'],['My Reports','analytics','reports','Saved reports'],['My Dashboards','dashboard','reports','Operational summaries'],['M&E Analytics','analytics','reports','Indicators and outcomes']],
    'Tools':[['Command Center','dashboard','home','Enterprise operations'],['Supply Chain','supply','tools','Inventory and assets'],['Telehealth','telehealth','patient','Remote care'],['Quality & Safety','quality','shield','Incidents and follow-up']],
    'Settings':[['User Administration','admin','settings','Function × department × facility matrix'],['Access Review','admin','audit','Review and recertification'],['Configuration','admin','tools','Facilities, terminology and workflows'],['Audit Trail','admin','audit','Security and clinical audit']]
  };

  function renderModuleNavigation(){
    const target=$('#moduleNav'); if(!target)return;
    target.innerHTML=v4ModuleTabs.filter(x=>canOpenRoute(x.route)).map(item=>`<button class="module-tab ${item.routes.includes(state.route)?'active':''}" data-route="${item.route}"><span class="module-icon">${v4Icon(item.icon)}</span>${esc(item.label)}<span class="drop">⌄</span></button>`).join('');
  }
  renderSidebar=function(){
    const target=$('#primaryNav'); if(!target)return;
    const allowed=v4RailItems.filter(([route])=>canOpenRoute(route));
    target.innerHTML=allowed.map(([route,label,icon])=>`<button class="rail-item ${(state.route===route||(state.route==='today-patients'&&route==='patient-station'))?'active':''}" data-route="${route}">${v4Icon(icon)}<span>${esc(label)}</span></button>`).join('');
    const mobile=$('#mobileWorkflowNav');
    if(mobile){
      const preferred=['today-patients','patient-station','workqueues','clinical-documentation'];
      const shortcuts=preferred.map(route=>allowed.find(item=>item[0]===route)).filter(Boolean);
      mobile.innerHTML=shortcuts.map(([route,label,icon])=>`<button class="mobile-workflow-item ${(state.route===route||(state.route==='today-patients'&&route==='patient-station'))?'active':''}" data-route="${route}">${v4Icon(icon)}<span>${esc(route==='clinical-documentation'?'Notes':label)}</span></button>`).join('')+`<button class="mobile-workflow-item more" data-mobile-nav-more="true">${v4Icon('tools')}<span>More</span></button>`;
    }
    renderModuleNavigation();
  };
  function renderLauncherCategories(active='Patient Care'){
    const cats=$('#launcherCategories'), acts=$('#launcherActivities'); if(!cats||!acts)return;
    cats.innerHTML=Object.keys(v4LauncherMap).map(name=>`<button class="launcher-category ${name===active?'active':''}" data-launcher-category="${esc(name)}"><span class="cat-icon">${v4Icon(v4ModuleTabs.find(x=>x.label===name)?.icon||'tools')}</span>${esc(name)}<span class="cat-chevron">›</span></button>`).join('');
    acts.innerHTML=(v4LauncherMap[active]||[]).filter(([,route])=>canOpenRoute(route)).map(([label,route,icon,detail])=>`<button class="launcher-activity" data-route="${route}"><span class="activity-icon">${v4Icon(icon)}</span><span><strong>${esc(label)}</strong><small>${esc(detail)}</small></span></button>`).join('');
  }
  updateChrome=function(){
    const role=currentRole();
    const display=state.account?.display_name||role.user||'Neema K.';
    $('#userInitials').textContent=role.initials;
    $('#userName').textContent=display;
    $('#userRole').textContent=state.account?.role_code?statusLabel(state.account.role_code):role.name;
    $('#workspaceRole').textContent=`${role.name} Workspace`;
    $('#notificationCount').textContent=state.notifications;
    $('#userAvatar').src='/assets/avatars/neema-k.png';
    if(state.account?.profile_photo_url)queueMicrotask(()=>v1016HydrateProfilePhoto($('#userAvatar'),state.account));
    renderModuleNavigation(); renderLauncherCategories();
    const now=new Date();
    if($('#statusDate'))$('#statusDate').textContent=now.toLocaleDateString('en-GB',{weekday:'long',day:'2-digit',month:'short',year:'numeric'});
    if($('#statusTime'))$('#statusTime').textContent=now.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
  };
  navigate=function(route){
    if(!canOpenRoute(route)){toast('Function not assigned','Ask IT to add this function to your user access matrix.');route=firstAllowedRoute();}
    state.route=route; renderSidebar(); render(); history.replaceState(null,'',`?route=${route}`); $('#mainContent').focus(); $('#sidebar')?.classList.remove('open'); document.body.classList.remove('mobile-nav-open');
    $('#launcherPanel')?.classList.add('hidden'); $('#launcherButton')?.setAttribute('aria-expanded','false');
  };

  function uaStatusClass(value){const v=String(value||'').toUpperCase();if(['ARRIVED','COMPLETED','DISCHARGED','ACTIVE'].includes(v))return 'arrived';if(['REGISTERED','CHECKED_IN'].includes(v))return 'checked-in';if(['WAITING_TRIAGE','WAITING','TRIAGED','ROOMED','IN_PROGRESS','WAITING_RESULTS'].includes(v))return 'waiting';if(['READY_FOR_PROVIDER','READY_FOR_DISCHARGE'].includes(v))return 'ready';return 'scheduled';}
  function initials(name='Patient'){return name.split(/\s+/).filter(Boolean).slice(0,2).map(x=>x[0]).join('').toUpperCase();}
  function patientAvatar(patient,selected=false){const isPrimary=patient?.mpi_id===state.selectedPatientId||selected;return `<span class="patient-mini-avatar">${isPrimary?'<img src="/assets/avatars/juma-ally-mwangi.png" alt="">':esc(initials(patient?.full_name))}</span>`;}
  function nextStepButtonV4(row){
    const step=row.next_step||'OPEN_RECORD';
    if(step==='ARRIVE')return `<button class="next-step-btn" data-action="today-arrive" data-appointment="${esc(row.appointment_id)}">Arrive</button>`;
    const transitions={CHECK_IN:'REGISTERED',COMPLETE_REGISTRATION:'REGISTERED',SEND_TO_TRIAGE:'WAITING_TRIAGE',TRIAGE:'TRIAGED',READY_FOR_PROVIDER:'READY_FOR_PROVIDER',ROOM_PATIENT:'ROOMED',START_VISIT:'IN_PROGRESS',REVIEW_RESULTS:'WAITING_RESULTS',DISCHARGE:'READY_FOR_DISCHARGE'};
    if(transitions[step]&&row.encounter_id)return `<button class="next-step-btn" data-action="today-status" data-encounter="${esc(row.encounter_id)}" data-status="${transitions[step]}">${esc(statusLabel(step))}</button>`;
    return `<button class="next-step-btn" data-patient-id="${esc(row.patient.mpi_id)}" data-open-station="true">Open Record</button>`;
  }
  function uaPageTitle(title,subtitle,actions=''){return `<div class="ua-page-title"><div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div><div class="ua-page-actions">${actions}</div></div>`;}
  function uaKpi(label,value,note,cls=''){return `<div class="ua-kpi ${cls}"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`;}

  renderTodayPatients=async function(){
    renderLoading("Loading today's patient operations…");
    const facility=operationFacility();
    const [data,rosters,walkins]=await Promise.all([api(`/today-patients?facility_code=${encodeURIComponent(facility)}&limit=100`),api(`/duty-rosters?facility_code=${encodeURIComponent(facility)}`),api(`/walk-ins?facility_code=${encodeURIComponent(facility)}&hours=24`)]);
    const rows=data.rows||[], c=data.counts||{};
    const rosterRows=rosters.slice(0,10);
    const privateRows=rows.filter(r=>r.provider).slice(0,5);
    $('#mainContent').innerHTML=`<section class="ua-page today-page">
      <div class="today-main">
        ${uaPageTitle("Today's Patients & Front Desk Workflow",'Manage scheduled visits, arrivals, and walk-ins')}
        <article class="ua-card">
          <div class="today-tabs"><button>Yesterday (198)</button><button class="active">Today (${data.total||c.expected||0})</button><button>Tomorrow (156)</button><button>Walk-Ins (${walkins.length})</button></div>
          <div class="today-filterbar"><div class="ua-search-filter">${v4Icon('search')}<input id="todaySearch" placeholder="Search patients..." /></div><select class="simple-select"><option>All Services</option></select><select class="simple-select"><option>All Clinics</option></select><select class="simple-select"><option>All Queues</option></select><select class="simple-select"><option>All Statuses</option></select><button class="ua-button compact" data-action="filter-today">Filter</button></div>
          <div class="today-metrics">
            ${[['Expected Patients',c.expected||data.total||0,'Scheduled','document'],['Arrived',c.arrived||0,`${Math.round((c.arrived||0)/Math.max(c.expected||1,1)*100)}%`,'patient'],['Checked In',c.checked_in||0,'Registration','registration'],['Waiting',c.waiting||0,'Triage queues','queue'],['Ready for Provider',c.ready_for_provider||0,'Duty team','patient'],['Completed',c.completed||0,'Closed','orders']].map(x=>`<div class="today-metric"><span class="today-metric-icon">${v4Icon(x[3])}</span><div><span>${esc(x[0])}</span><strong>${esc(x[1])}</strong><small>${esc(x[2])}</small></div></div>`).join('')}
          </div>
          <div class="table-wrap"><table class="ua-data-table"><thead><tr><th>Time</th><th>Patient Name</th><th>MRN</th><th>Service</th><th>Arrival Status</th><th>Queue</th><th>On-Duty Team</th><th>Next Step</th><th></th></tr></thead><tbody>${rows.slice(0,12).map((row,i)=>`<tr><td>${new Date(row.scheduled_start).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</td><td><button class="ua-link patient-name-cell" data-patient-id="${esc(row.patient.mpi_id)}" data-open-station="true">${patientAvatar(row.patient,i===0)}<span>${esc(row.patient.full_name)}</span></button></td><td>${esc(row.patient.mrn)}</td><td>${esc(row.service)}</td><td><span class="ua-status ${uaStatusClass(row.status)}">● ${esc(statusLabel(row.status))}</span></td><td>${esc(row.queue||row.location||'—')}</td><td>${esc(row.on_duty_team||'Duty roster')}</td><td>${nextStepButtonV4(row)}</td><td>⋮</td></tr>`).join('')}</tbody></table></div>
          <div class="ua-pagination"><span>Showing 1 to ${Math.min(rows.length,12)} of ${data.total||rows.length}</span><span style="margin-left:auto">‹</span><span class="page">1</span><span>2</span><span>3</span><span>4</span><span>5</span><span>…</span><span>26</span><span>›</span></div>
        </article>
        <div class="today-bottom">
          <article class="ua-card"><div class="ua-card-header"><h2>Front Desk Actions</h2></div><div class="ua-card-body action-grid">
            ${[['Arrive','Mark patient arrived','patient','arrive'],['Check In','Check in patient','registration','check-in'],['Send to Triage','Send to triage queue','transfer','triage'],['Assign Queue','Assign service queue','queue','assign'],['Register Walk-In','Quick walk-in reg','userplus','walkin'],['Print Label','Patient label / wristband','print','print'],['Benefit Check','Check NHIF / Insurance','shield','benefit'],['Open Patient Station','Open registration','patient','station'],['Travel Screening','Screen travel / symptoms','document','screen'],['More Actions','Additional shortcuts','tools','more']].map(([a,b,ic,op])=>`<button class="front-action" data-v4-action="front-${op}"><span class="big-icon">${v4Icon(ic)}</span><strong>${esc(a)}</strong><small>${esc(b)}</small></button>`).join('')}
          </div></article>
          <article class="ua-card walkin-panel"><h2>Walk-In Workflow</h2><p>Follow the steps to register and route walk-in patients</p><div class="workflow-steps-v4">${['Search / Create Patient','Quick Registration','Arrival','Select Service Point','Queue / Triage','Provider'].map((x,i)=>`<div class="workflow-step-v4"><b>${i+1}</b><span>${x}</span></div>`).join('')}</div><p>Use this flow for patients without appointments.</p><button class="ua-button primary" style="width:100%;justify-content:center;margin-top:14px" data-action="start-walkin">Start Walk-In Registration</button></article>
        </div>
      </div>
      <div class="today-side">
        <article class="ua-card roster-card"><div class="ua-card-header"><h2>On-Duty Team & Service Points</h2></div><div class="ua-card-body"><table class="ua-data-table roster-table"><thead><tr><th>Service Point</th><th>Clinic / Department</th><th>On-Duty Team</th><th>Shift</th><th>Room</th><th>Queue Cap.</th></tr></thead><tbody>${rosterRows.map(r=>`<tr><td>${esc(r.service_point.name)}</td><td>${esc(r.service_point.clinic||r.service_point.department)}</td><td>${esc(r.lead_provider||r.team_name)}</td><td>${esc(String(r.shift_start).slice(0,5))} - ${esc(String(r.shift_end).slice(0,5))}</td><td>${esc(r.service_point.room||'—')}</td><td>${r.service_point.queue_capacity}</td></tr>`).join('')}</tbody></table><div class="roster-total"><span>Total Queue Capacity <b>${rosterRows.reduce((n,r)=>n+(r.service_point.queue_capacity||0),0)}</b></span><span>Total On-Duty Staff <b>${rosterRows.length+2}</b></span></div></div></article>
        <article class="ua-card private-appointments"><div class="ua-card-header"><h2>Private Provider Appointments</h2><button class="ua-link" data-route="scheduling">View Full Schedule</button></div><div class="ua-card-body"><table class="ua-data-table"><thead><tr><th>Time</th><th>Provider</th><th>Service</th><th>Patient</th><th>Status</th></tr></thead><tbody>${privateRows.map(r=>`<tr><td>${new Date(r.scheduled_start).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</td><td>${esc(r.provider)}</td><td>${esc(r.service)}</td><td>${esc(r.patient.full_name)}</td><td><span class="ua-status arrived">Confirmed</span></td></tr>`).join('')||'<tr><td colspan="5">No named-provider appointments in this view.</td></tr>'}</tbody></table><div class="ua-pagination">${privateRows.length} of ${Math.max(privateRows.length,18)} appointments today</div></div></article>
        <article class="ua-card"><div class="ua-card-header"><h2>Queue & Operations Overview</h2></div><div class="ua-card-body"><div class="ops-overview-grid">${[['Expected Today',c.expected||0,'Patients'],['Patients Waiting',c.waiting||0,'Across all queues'],['Walk-Ins Waiting',c.walk_ins_waiting||0,'To be registered'],['Travel Screening',3,'To be screened']].map(x=>`<div class="ops-overview-cell"><span>${esc(x[0])}</span><strong>${esc(x[1])}</strong><small>${esc(x[2])}</small></div>`).join('')}</div><div class="alert-list-v4"><div class="alert-row-v4"><span class="alert-triangle">▲</span><span>3 patients in queue waiting over 60 minutes</span><time>10:18 AM</time></div><div class="alert-row-v4"><span class="alert-triangle">▲</span><span>Maternity Point A queue capacity at 90%</span><time>10:15 AM</time></div><div class="alert-row-v4"><span class="alert-triangle">▲</span><span>2 walk-ins require travel screening</span><time>10:12 AM</time></div></div><a class="chart-link" href="#" data-v4-action="notifications">View all notifications</a></div></article>
      </div>
    </section>`;
  };

  renderWorkqueues=async function(){
    renderLoading('Loading operational workqueues…');
    const facility=operationFacility();
    const summary=await api(`/workqueues/summary?facility_code=${encodeURIComponent(facility)}`);
    const queues=summary.queues||[], totals=summary.totals||{};
    if(!state.selectedWorkqueueId&&queues.length)state.selectedWorkqueueId=queues.find(q=>q.name.includes('Walk-In'))?.queue_id||queues[0].queue_id;
    const detail=state.selectedWorkqueueId?await api(`/workqueues/${encodeURIComponent(state.selectedWorkqueueId)}/items?limit=50`):null;
    state.v4QueueDetail=detail;
    const selected=queues.find(q=>q.queue_id===state.selectedWorkqueueId)||queues[0];
    const avgAge=queues.length?(queues.reduce((n,q)=>n+Number(q.metrics.avg_age_days||0),0)/queues.length).toFixed(1):'0.0';
    const oldest=detail?.metrics?.oldest_age_days||23;
    $('#mainContent').innerHTML=`<section class="ua-page workqueue-page">
      ${uaPageTitle('Workqueue Management','Monitor, manage, and act on operational workqueues across departments.',`<span class="ua-refresh-time">Last refreshed: ${new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</span><button class="ua-button" data-action="refresh-workqueues">↻ Refresh</button><button class="ua-icon-button">•••</button>`)}
      <article class="ua-card">
        <div class="ua-tabs">${['Account','Registration','Claims','Follow-up','Patient','Referral/Authorization','Walk-Ins'].map((x,i)=>`<button class="ua-tab ${i===0?'active':''}">${x}</button>`).join('')}</div>
        <div class="ua-filter-row"><div class="ua-filter"><small>Queue Ownership</small><strong>My Queues</strong></div><div class="ua-filter"><small>Service Area</small><strong>All Service Areas</strong></div><div class="ua-filter"><small>Queue Status</small><strong>Active</strong></div><div class="ua-search-filter">${v4Icon('search')}<input placeholder="Search queues by name..." /></div><button class="ua-button">▽ Filters <span class="ua-status active">2</span></button></div>
        <div class="ua-kpi-grid">${uaKpi('Active Queues',totals.active_queues||queues.length,'of 26 total')}${uaKpi('Total Items',(totals.total_items||0).toLocaleString(),'Across active queues')}${uaKpi('Deferred Items',totals.deferred_items||0,'6.9% of total')}${uaKpi('Overdue Items',totals.overdue_items||0,'25.0% of total','danger')}${uaKpi('High Priority',totals.high_priority||0,'11.9% of total','warning')}${uaKpi('Avg Age (Days)',avgAge,'Across all items')}${uaKpi('Oldest Item',oldest,'Days in queue')}</div>
        <div class="workqueue-body">
          <div class="queue-list-panel"><div class="table-wrap"><table class="ua-data-table"><thead><tr><th>☆</th><th>Queue Name</th><th>Service Area</th><th>Owner/Team</th><th>Active Count</th><th>Deferred</th><th>Total Count</th><th>Aging ⓘ</th><th>Priority</th><th>Status</th><th>Last Refreshed</th></tr></thead><tbody>${queues.slice(0,10).map(q=>`<tr class="${q.queue_id===state.selectedWorkqueueId?'selected':''}"><td><span class="ua-check ${q.queue_id===state.selectedWorkqueueId?'checked':''}">${q.queue_id===state.selectedWorkqueueId?'✓':''}</span></td><td><button class="ua-link" data-action="open-workqueue" data-id="${esc(q.queue_id)}">${esc(q.name)}</button></td><td>${esc(q.service_area)}</td><td>${esc(q.owner_team)}</td><td>${q.metrics.active}</td><td>${q.metrics.deferred}</td><td>${q.metrics.total}</td><td>${q.metrics.avg_age_days}</td><td><span class="ua-priority ${q.metrics.high_priority>10?'high':q.metrics.high_priority>5?'medium':'low'}">${q.metrics.high_priority>10?'↑ High':q.metrics.high_priority>5?'▲ Medium':'↓ Low'}</span></td><td><span class="ua-status active">Active</span></td><td>10:24 AM</td></tr>`).join('')}</tbody></table></div><div class="ua-pagination"><span>Showing 1 to ${Math.min(queues.length,10)} of ${queues.length} queues</span><span style="margin-left:auto">‹</span><span class="page">1</span><span>›</span></div></div>
          <aside class="queue-detail-panel"><small>Selected Queue</small><div class="queue-detail-title"><h2>${esc(selected?.name||'Select a queue')}</h2><span class="ua-status active">Active</span><span style="margin-left:auto">☆ &nbsp; •••</span></div><p>${esc(selected?.service_area||'')} &nbsp; • &nbsp; Owned by: ${esc(selected?.owner_team||'')}</p><h3 style="font-size:9px;margin:0">Queue Summary</h3><div class="queue-summary-grid">${[['Active',detail?.metrics?.active||0,''],['Deferred',detail?.metrics?.deferred||0,''],['Total',selected?.metrics?.total||0,''],['Overdue',detail?.metrics?.overdue||0,'danger'],['High Priority',selected?.metrics?.high_priority||0,'danger'],['Avg Age (Days)',selected?.metrics?.avg_age_days||0,'']].map(x=>`<div class="queue-summary-cell ${x[2]}"><span>${x[0]}</span><strong>${x[1]}</strong></div>`).join('')}</div><div class="queue-oldest"><span>Oldest Item</span><strong>${oldest} days</strong></div><div class="suggested-actions"><h3>Suggested Actions</h3>${[['Open Queue','View and process items in this queue','queue','open-queue'],['Reassign','Reassign items to another user or team','team','reassign'],['Route','Route items based on rules or work type','transfer','route'],['Defer','Defer items with reason and date','schedule','defer'],['Create Task','Create a task for follow-up or resolution','document','task'],['View Rules','Review routing and assignment rules','settings','rules']].map(([a,b,ic,op])=>`<div class="suggested-action" data-v4-action="queue-${op}"><span class="action-icon">${v4Icon(ic)}</span><span><strong>${a}</strong><small>${b}</small></span><span class="arrow">›</span></div>`).join('')}</div></aside>
        </div>
      </article>
      <div class="workqueue-analytics"><article class="ua-card chart-card"><h3>Queue Volume Trend (7 Days)</h3><div class="chart-legend"><span><i style="background:#1776b9"></i>Total Items</span><span><i style="background:#2ca64c"></i>Resolved Items</span></div><div class="bar-chart-v4">${[['Sat 24 May',186,142],['Sun 25 May',172,128],['Mon 26 May',214,165],['Tue 27 May',208,176],['Wed 28 May',233,189],['Thu 29 May',219,198],['Fri 30 May',180,142]].map(([d,a,b])=>`<div class="bar-group-v4"><span class="bar-v4 blue" style="height:${a/2.5}px"><em>${a}</em></span><span class="bar-v4 green" style="height:${b/2.5}px"><em>${b}</em></span><b>${d}</b></div>`).join('')}</div><a class="chart-link">View full analytics</a></article><article class="ua-card chart-card"><h3>Items by Aging Bucket</h3><div class="donut-wrap"><div class="donut-v4"></div><div class="donut-legend"><div><i style="background:#219d4e"></i><span>0–2 days</span><b>78 (46.4%)</b></div><div><i style="background:#f3a20c"></i><span>3–7 days</span><b>45 (26.8%)</b></div><div><i style="background:#ef6d16"></i><span>8–14 days</span><b>28 (16.7%)</b></div><div><i style="background:#d9272e"></i><span>15+ days</span><b>17 (10.1%)</b></div></div></div><a class="chart-link">View aging report</a></article><article class="ua-card chart-card"><h3>Recent Activity</h3><div class="recent-activity-list"><div><strong>Neema K. reassigned 14</strong>to Registration Team B 10:12 AM</div><div><strong>System routed 23 items</strong>to priority rules</div><div><strong>A task was created for 8</strong>overdue items</div><div><strong>Dr. Rehema M. deferred 6</strong>items</div><div><strong>NHIF eligibility check</strong>completed for 125 items</div></div><a class="chart-link">View all activity</a></article></div>
    </section>`;
  };

  async function renderPatientStation(){
    renderLoading('Loading Patient Station…');
    const facility=operationFacility();
    if(!state.selectedPatientId){const list=await api('/patients?limit=1');state.selectedPatientId=list[0]?.mpi_id;}
    const [patient,today,summary,tracker]=await Promise.all([selectedPatient(),api(`/today-patients?facility_code=${encodeURIComponent(facility)}&limit=20`),api(`/workqueues/summary?facility_code=${encodeURIComponent(facility)}`),api(`/tracker?facility_code=${encodeURIComponent(facility)}`)]);
    if(!patient){$('#mainContent').innerHTML=patientContextBanner(null);return;}
    state.tracker=tracker;
    const current=tracker.find(x=>x.patient.mpi_id===patient.mpi_id)||tracker[0];
    const queueSummary=(summary.queues||[]).slice(0,5);
    const todayRows=today.rows||[];
    const selectedName=patient.full_name;
    const dob=patient.date_of_birth?new Date(patient.date_of_birth):null;
    const age=dob?Math.max(0,new Date().getFullYear()-dob.getFullYear()):35;
    $('#mainContent').innerHTML=`<section class="ua-page patient-station-grid">
      <div class="patient-station-left">
        <article class="ua-card"><div class="ua-card-header"><h2>Today's Patients Report</h2><span>↻ &nbsp; ⚙</span></div><div class="patient-report-tabs"><button>Yesterday (198)</button><button class="active">Today (${today.total||todayRows.length})</button><button>Tomorrow (156)</button></div><div class="today-filterbar" style="padding:8px"><div class="ua-search-filter"><input placeholder="Search patients..." /></div><select class="simple-select"><option>All Services</option></select></div><div class="table-wrap"><table class="ua-data-table compact-table-v4"><thead><tr><th>MRN</th><th>Patient Name</th><th>Time</th><th>Service</th><th>Status</th></tr></thead><tbody>${todayRows.slice(0,10).map((r,i)=>`<tr class="${r.patient.mpi_id===patient.mpi_id?'selected':''}"><td>${esc(r.patient.mrn)}</td><td><button class="ua-link" data-patient-id="${esc(r.patient.mpi_id)}" data-open-station="true">${esc(r.patient.full_name)}</button></td><td>${new Date(r.scheduled_start).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</td><td>${esc(r.service)}</td><td><span class="ua-status ${uaStatusClass(r.status)}">${esc(statusLabel(r.status))}</span></td></tr>`).join('')}</tbody></table></div><div class="ua-pagination">Showing 1 to ${Math.min(todayRows.length,10)} of ${today.total||todayRows.length}<span style="margin-left:auto">‹ 1 2 3 4 5 … 32 ›</span></div></article>
        <article class="ua-card"><div class="ua-card-header"><h2>Workqueues Summary</h2><span>Last updated: 10:24 AM</span></div><div class="ua-card-body" style="padding:0 10px">${queueSummary.map((q,i)=>`<div class="suggested-action" data-route="workqueues"><span class="action-icon">${v4Icon(['shield','orders','document','records','userplus'][i]||'queue')}</span><span><strong>${esc(q.name)}</strong><small>${esc(q.service_area)} follow-up</small></span><span class="ua-status ${i===2?'checked-in':'scheduled'}">${q.metrics.active}</span></div>`).join('')}<div class="suggested-action" data-route="workqueues"><strong>View All Workqueues</strong><span class="arrow">→</span></div></div></article>
      </div>
      <div class="patient-station-center">
        <article class="ua-card patient-header-v4"><div class="patient-identity"><img class="patient-photo" src="/assets/avatars/juma-ally-mwangi.png" alt="Patient photograph" /><div><h1>${esc(selectedName)} <span style="color:#1671c3">${patient.sex==='Male'?'♂':patient.sex==='Female'?'♀':''}</span></h1><div class="identifiers">MRN: ${esc(patient.mrn)} &nbsp; | &nbsp; NIDA: ${esc(patient.nida_number||'Not recorded')}</div><div class="patient-demographics"><span>♙ ${age} Y</span><span>♙ ${esc(patient.sex)}</span><span>▧ Tanzanian</span><span>⌘ ${state.language==='sw'?'Kiswahili':'English / Kiswahili'}</span></div><div class="patient-contact"><span>⌕ ${esc(patient.phone||'No phone')}</span><span>✉ ${esc(patient.email||'patient@demo.local')}</span><span>⌖ ${esc(patient.address||'Dar es Salaam')}</span></div></div></div><div class="patient-header-block"><span class="label">Encounter Status</span><span class="ua-status arrived">${esc(statusLabel(current?.status||'ARRIVED'))}</span><span class="label" style="display:block;margin-top:12px">Visit ID</span><strong>${esc(current?.encounter_id||'VST-2025-05-29-0142')}</strong><span class="label" style="display:block;margin-top:12px">Current Location</span><strong>${esc(current?.location||'OPD Clinic – Room 12')}</strong><small>${esc(current?.facility?.name||'Muhimbili NH – Service Point A')}</small></div><div class="patient-header-block"><span class="label">Care Team</span><dl class="care-team-list"><dt>Attending</dt><dd>${esc(current?.provider||'Dr. Rehema Msuya')}</dd><dt>Nurse</dt><dd>Sr. Amina Salehe</dd><dt>Registration</dt><dd>${esc(state.account?.display_name||'Neema Kerefu')}</dd></dl><button class="ua-link" style="margin-top:18px;color:#1764aa">♙ View Care Team</button></div></article>
        <div class="patient-action-grid">${[['Open Chart','View full medical record','chart','blue','chart'],['Update Registration','Edit patient demographics','registration','orange','registration'],['Transfer Patient','Move to another unit/service','transfer','teal','transfer'],['Discharge Patient','End visit & close encounter','discharge','red','discharge'],['Print Forms','Print AVS, labels, receipts','print','purple','print'],['Encounter Summary','View visit & clinical summary','document','teal','summary'],['Benefit Check','Check NHIF/Insurance','shield','green','benefit'],['Assign Team','Assign providers & care team','team','blue','team'],['Scan Documents','Upload & manage documents','scan','orange','scan']].map(([a,b,ic,color,op])=>`<button class="patient-action-card ${color}" data-v4-action="patient-${op}" ${op==='discharge'&&current?`data-encounter="${esc(current.encounter_id)}"`:''}><span class="patient-action-icon">${v4Icon(ic)}</span><span><strong>${a}</strong><small>${b}</small></span></button>`).join('')}</div>
        <div class="patient-mid-grid"><article class="ua-card"><div class="ua-card-header"><h2>Today's Encounters</h2><button class="ua-button compact" data-v4-action="add-encounter">+ Add Encounter</button></div><table class="ua-data-table compact-table-v4"><thead><tr><th>Time</th><th>Service</th><th>Type</th><th>Provider</th><th>Status</th></tr></thead><tbody><tr><td>${current?.arrival_at?new Date(current.arrival_at).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):'08:42 AM'}</td><td>${esc(current?.service||'OPD Clinic')}</td><td>${esc(current?.encounter_type||'Outpatient')}</td><td>${esc(current?.provider||'Dr. Rehema Msuya')}</td><td><span class="ua-status arrived">${esc(statusLabel(current?.status||'Arrived'))}</span></td></tr></tbody></table><div class="ua-card-header"><h2>Previous Encounters (Last 12 months)</h2></div><table class="ua-data-table compact-table-v4"><tbody><tr><td>10 Mar 2026</td><td>OPD Clinic</td><td>Outpatient</td><td>Dr. Rehema Msuya</td><td><span class="ua-status completed">Completed</span></td></tr><tr><td>12 Jan 2026</td><td>OPD Clinic</td><td>Outpatient</td><td>Dr. Hamis Kilonzo</td><td><span class="ua-status completed">Completed</span></td></tr><tr><td>30 Nov 2025</td><td>Emergency</td><td>Emergency</td><td>Dr. Neema R.</td><td><span class="ua-status completed">Completed</span></td></tr></tbody></table></article><article class="ua-card"><div class="ua-card-header"><h2>Coverage & Payment</h2><button class="ua-link" data-v4-action="patient-benefit">Edit</button></div><div class="coverage-block"><div class="coverage-row"><span>Primary Coverage</span><strong>${esc(patient.payer||'NHIF')} (National Health Insurance Fund)<br><small>Membership # ${esc(patient.member_number||'123456789012')}</small></strong><span class="ua-status active">Active</span></div><div class="coverage-row"><span>Plan</span><strong>${esc(patient.payer||'NHIF')} – Outpatient<br><small>Valid until 31 Dec 2026</small></strong><span></span></div><div class="coverage-row"><span>Co-Pay</span><strong>TZS 2,000</strong><span></span></div><div class="coverage-row"><span>Payment Type</span><strong>${esc(patient.payer||'NHIF')}</strong><span></span></div><div style="font-size:8px;font-weight:800;margin-top:12px">Patient Responsibility (Estimated)</div><div class="coverage-row"><span>Deductible</span><strong>TZS 0.00</strong><span></span></div><div class="coverage-row"><span>Balance</span><strong style="color:#13864e">TZS 0.00</strong><span></span></div></div></article></div>
        <article class="ua-card"><div class="ua-card-header"><h2>Clinical Alerts & Flags</h2></div><div class="alert-chips"><span class="alert-chip ${String(patient.allergies||'').toLowerCase().includes('no known')?'good':'warn'}">${esc(patient.allergies||'No Known Allergies')}</span><span class="alert-chip">${esc(patient.medications||'No Active Medications')}</span><span class="alert-chip warn">No Advance Directive</span><span class="alert-chip good">Not a Fall Risk</span></div><div class="ua-pagination">Alerts last reviewed: ${new Date().toLocaleString()} by ${esc(state.account?.display_name||'Neema K.')}<button class="ua-link" style="margin-left:auto">Review Alerts</button></div></article>
      </div>
      <div class="patient-station-right"><article class="ua-card"><div class="ua-card-header"><h2>Checklist & Verification</h2><span>↻ ⚙</span></div>${[['Patient','4 of 5',['Verify Demographics','Verify Contacts','Verify Identity (NIDA/ID)','Review Allergies','Review Alerts & Flags']],['Account','3 of 4',['Guarantor Verified','Payment Type Confirmed','Estimate Generated','Deposit Collected (if required)']],['Coverage','2 of 4',['NHIF Eligibility Verified','Benefits Checked','Pre-Authorization (if needed)','Coverage Documents Scanned']],['Walk-In Readiness','2 of 3',['Walk-In Triage Completed','Service Point Assigned','Ready for Clinical Triage']]].map(([h,n,items])=>`<div class="checklist-section"><div class="checklist-heading"><span>${h}</span><span>${n}</span></div>${items.map((x,i)=>`<div class="checklist-item"><span class="${i<2||h==='Patient'&&i<4?'check-good':i===2?'check-warn':'check-empty'}">${i<2||h==='Patient'&&i<4?'●':i===2?'▲':'○'}</span><span>${x}</span></div>`).join('')}</div>`).join('')}<div class="ua-pagination"><span class="check-good">● Complete</span><span class="check-warn">▲ In Progress</span><span>○ Incomplete</span></div></article><article class="ua-card walkin-callout"><div class="ua-card-header"><h2>Walk-In Workflow</h2></div><button data-action="start-walkin">♙ &nbsp; Start Walk-In<br><small>Quickly register and route walk-in patients</small></button></article></div>
    </section>`;
  }

  showWalkInModal=async function(){
    const points=await api(`/service-points?facility_code=${encodeURIComponent(operationFacility())}`);
    openModal('Walk-In Workflow – New Patient Arrival',`<div class="walkin-modal-steps">${['Search / Create Patient','Walk-In Triage / Reason','Register Arrival','Assign Service / Queue','Coverage / Cash Review','Route to Waiting / Triage / Provider'].map((x,i)=>`<div class="walkin-modal-step ${i===0?'active':''}"><b>${i+1}</b><span>${x}</span></div>`).join('')}</div><div class="walkin-form-two"><div class="walkin-form-box"><h3>Search for existing patient</h3><div class="walkin-inline"><input id="walkPatient" value="${esc(state.selectedPatientId||'')}" placeholder="Search by name, NIDA, phone, or MRN..." /><button class="ua-button primary" data-route="patient-search">Search</button></div><div class="or-divider">OR</div><button class="ua-button" data-route="registration">${v4Icon('userplus')} Create New Patient</button><div style="margin-top:13px"><label class="field"><span>Service point</span><select id="walkPoint">${points.map(p=>`<option value="${esc(p.service_point_id)}">${esc(p.name)} · ${esc(p.clinic)} · ${esc(p.room||'Room TBD')}</option>`).join('')}</select></label><label class="field" style="margin-top:8px"><span>Coverage route</span><select id="walkCoverage"><option>NHIF</option><option>Cash</option><option>Private Insurance</option><option>Exempted</option><option>Emergency</option></select></label></div></div><div class="walkin-form-box"><h3>Quick Triage Reason (Optional)</h3><label class="field"><span>Reason for visit</span><select id="walkReason"><option>Walk-in clinical assessment</option><option>Acute illness</option><option>Injury / trauma</option><option>Maternal or newborn concern</option><option>Medication refill</option><option>Referral follow-up</option></select></label><label class="field" style="margin-top:9px"><span>Walk-In Notes</span><textarea id="walkNotes" placeholder="Add brief notes about patient arrival...">Registered at front desk and routed using duty roster.</textarea></label></div></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-modal-action="create-walkin">Next</button>`,'Walk-In Workflow');
    $('#modal').classList.add('walkin-workflow-modal');
  };
  const v4OriginalCloseModal=closeModal;
  closeModal=function(){resetAudioCapture({preserveSession:true});v4OriginalCloseModal();$('#modal')?.classList.remove('walkin-workflow-modal','audio-annotation-modal');};

  render=async function(){
    const map={dashboard:renderDashboard,'today-patients':renderTodayPatients,workqueues:renderWorkqueues,'patient-station':renderPatientStation,'patient-flow':renderPatientFlow,registration:renderRegistration,'patient-search':renderPatientSearch,chart:renderChart,flowsheets:renderFlowsheets,orders:renderOrders,results:renderResults,'recent-discharges':renderRecentDischarges,scheduling:renderScheduling,'bed-board':renderBedBoard,'clinical-documentation':renderClinicalDocumentation,nursing:renderMedicationWorkspace,pharmacy:renderMedicationWorkspace,revenue:renderRevenueCycle,supply:renderSupplyChain,telehealth:renderTelehealth,analytics:renderEnterpriseAnalytics,admin:renderSystemAdmin,'public-health':renderPublicHealth,quality:renderQuality};
    try{if(map[state.route])await map[state.route]();else await renderGenericModule(state.route);}catch(error){console.error(error);$('#mainContent').innerHTML=`${pageHeader('Application Error','Unable to load workspace','The requested workspace could not be retrieved.')}<div class="alert danger"><strong>${esc(error.message)}</strong><br>Verify the backend is running and retry.</div>`;}
  };

  function openV4QueueItems(){
    const d=state.v4QueueDetail;if(!d)return toast('Queue unavailable','Select a workqueue first.');
    openModal(d.queue.name,`<div class="table-wrap"><table class="ua-data-table"><thead><tr><th>Item</th><th>Patient</th><th>Reason</th><th>Priority</th><th>Due</th><th>Actions</th></tr></thead><tbody>${d.items.slice(0,25).map(item=>`<tr><td><strong>${esc(item.title)}</strong></td><td>${item.patient?`<button class="ua-link" data-patient-id="${esc(item.patient.mpi_id)}" data-open-station="true">${esc(item.patient.full_name)}</button><br><small>${esc(item.patient.mrn)}</small>`:'No patient context'}</td><td>${esc(item.reason)}</td><td><span class="ua-priority ${String(item.priority).toLowerCase()}">${esc(item.priority)}</span></td><td>${fmtDate(item.due_at)}</td><td><button class="ua-button compact" data-action="queue-item-action" data-id="${esc(item.item_id)}" data-op="COMPLETE">Complete</button> <button class="ua-button compact" data-action="queue-item-action" data-id="${esc(item.item_id)}" data-op="DEFER">Defer</button></td></tr>`).join('')}</tbody></table></div>`,`<button class="ua-button" data-modal-action="close">Close</button>`,'Operational Workqueue');
  }
  function showV4Profile(){openModal('User Profile',`<div style="display:flex;gap:16px;align-items:center"><img id="v1016MyProfilePhoto" src="/assets/avatars/neema-k.png" style="width:68px;height:68px;border-radius:50%;object-fit:cover"><div><h3 style="margin:0">${esc(state.account?.display_name||currentRole().user)}</h3><p class="muted">${esc(state.account?.username||currentRole().username||'review user')} · ${esc(statusLabel(state.account?.role_code||state.role))}</p><p class="muted">Facilities: ${esc((state.account?.facilities||[operationFacility()]).join(', '))}</p><p class="muted">Profile photos are managed by authorized administrators.</p></div></div>`,`<button class="ua-button" data-v4-action="sign-out">Sign Out</button><button class="ua-button primary" data-modal-action="close">Close</button>`,'Umoja Afya Account');queueMicrotask(()=>v1016HydrateProfilePhoto($('#v1016MyProfilePhoto'),state.account));}

  function installV4ChromeHandlers(){
    const launcher=$('#launcherPanel'),button=$('#launcherButton');
    button?.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();if(window.matchMedia('(max-width: 900px)').matches){const sidebar=$('#sidebar');const open=!sidebar.classList.contains('open');sidebar.classList.toggle('open',open);document.body.classList.toggle('mobile-nav-open',open);button.setAttribute('aria-expanded',String(open));launcher.classList.add('hidden');return;}const open=launcher.classList.toggle('hidden')===false;button.setAttribute('aria-expanded',String(open));if(open)renderLauncherCategories();});
    document.addEventListener('click',e=>{if(!launcher?.contains(e.target)&&!button?.contains(e.target)){launcher?.classList.add('hidden');if(window.matchMedia('(max-width: 900px)').matches){$('#sidebar')?.classList.remove('open');document.body.classList.remove('mobile-nav-open');}button?.setAttribute('aria-expanded','false');}});
    document.addEventListener('click',e=>{const cat=e.target.closest('[data-launcher-category]');if(cat){e.preventDefault();e.stopPropagation();renderLauncherCategories(cat.dataset.launcherCategory);return;}const p=e.target.closest('[data-patient-id][data-open-station]');if(p){e.preventDefault();e.stopImmediatePropagation();state.selectedPatientId=p.dataset.patientId;saveState();navigate('patient-station',{preservePatient:true});return;}const a=e.target.closest('[data-v4-action]');if(!a)return;const op=a.dataset.v4Action;e.preventDefault();e.stopImmediatePropagation();if(op==='queue-open-queue')return openV4QueueItems();if(op.startsWith('queue-'))return toast('Workqueue action',`${statusLabel(op.replace('queue-',''))} workflow opened for the selected queue.`);if(op==='front-walkin')return showWalkInModal();if(op==='front-station')return navigate('patient-station');if(op==='front-benefit')return navigate('patient-station');if(op==='front-arrive')return toast('Select a patient','Choose a patient row, then use Arrive.');if(op==='front-check-in'||op==='front-triage'||op==='front-assign')return toast('Record context required','Select a patient from Today’s Patients to continue.');if(op==='front-print')return toast('Print workflow','Patient labels and wristbands require a selected patient record.');if(op==='front-screen')return toast('Travel screening','Travel and symptom screening form opened.');if(op==='notifications')return showNotifications();if(op==='patient-chart')return navigate('chart');if(op==='patient-registration')return navigate('registration');if(op==='patient-transfer')return toast('Transfer workflow','Select destination service, bed and receiving team.');if(op==='patient-discharge'){const id=a.dataset.encounter;if(id)return showDischargeModal(id);return toast('No current encounter','Select an active encounter.');}if(op==='patient-print')return toast('Print forms','AVS, labels, consent and receipt options opened.');if(op==='patient-summary')return navigate('chart');if(op==='patient-benefit')return toast('NHIF benefit check','Coverage verification request submitted.');if(op==='patient-team')return toast('Care team assignment','Provider and nursing assignment panel opened.');if(op==='patient-scan')return toast('Document capture','Upload or scanner capture workflow opened.');if(op==='add-encounter')return navigate('registration');if(op==='sign-out'){state.token='';state.account=null;state.offlineSession=false;sessionStorage.removeItem('umojaAfyaToken');window.UmojaOffline?.lock();closeModal();$('#app').setAttribute('aria-hidden','true');$('#loginOverlay').classList.remove('hidden');return;}} ,true);
    $('#userMenuButton')?.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();showV4Profile();},true);
    $('#mobileWorkflowNav')?.addEventListener('click',e=>{const more=e.target.closest('[data-mobile-nav-more]');if(!more)return;e.preventDefault();e.stopPropagation();const sidebar=$('#sidebar');sidebar?.classList.add('open');document.body.classList.add('mobile-nav-open');$('#launcherButton')?.setAttribute('aria-expanded','true');});
    document.body.addEventListener('click',e=>{if(!document.body.classList.contains('mobile-nav-open'))return;if(e.target.closest('#sidebar')||e.target.closest('#launcherButton')||e.target.closest('[data-mobile-nav-more]'))return;$('#sidebar')?.classList.remove('open');document.body.classList.remove('mobile-nav-open');$('#launcherButton')?.setAttribute('aria-expanded','false');});
    $('#launcherSearch')?.addEventListener('input',e=>{const q=e.target.value.toLowerCase();$$('.launcher-activity','#launcherActivities').forEach(x=>x.style.display=x.textContent.toLowerCase().includes(q)?'':'none');});
    document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();navigate('patient-search');}if(e.key==='Escape'){launcher?.classList.add('hidden');button?.setAttribute('aria-expanded','false');}});
  }

  /* --------------------------------------------------------------------------
     Enterprise record-context, event-management, device and IT administration
     enhancements. These functions deliberately extend the established v4 shell
     rather than creating a second patient application.
  --------------------------------------------------------------------------- */
  routeFunctionMap.messages='dashboard.view';
  routeFunctionMap['event-management']='dashboard.view';
  if(!v4RailItems.some(x=>x[0]==='messages'))v4RailItems.splice(3,0,['messages','Messages','document']);
  if(!v4RailItems.some(x=>x[0]==='emergency'))v4RailItems.splice(9,0,['emergency','ED Track Board','patient']);
  if(!v4RailItems.some(x=>x[0]==='event-management'))v4RailItems.push(['event-management','Event History','audit']);
  v4LauncherMap['Patient Care'].push(['Messages','messages','document','Secure clinical and operational messaging'],['Event Management','event-management','audit','Cancel, correct and undo with history']);
  v4LauncherMap['Registration/ADT'].push(['Emergency Track Board','emergency','patient','ED arrival, triage, care and disposition'],['Event Management','event-management','audit','Reversible ADT and workflow events']);
  v4LauncherMap['Settings'].push(['Event Audit & Correction','event-management','audit','Authorized event correction history']);
  v4ModuleTabs.find(x=>x.label==='Patient Care')?.routes.push('messages','event-management');
  v4ModuleTabs.find(x=>x.label==='Registration/ADT')?.routes.push('emergency');

  const v5RecordRoutes = new Set([
    'chart','clinical-documentation','orders','results','flowsheets','nursing','pharmacy',
    'telehealth','maternity','cardiology','orthopaedics','oncology','critical-care',
    'rehab','anesthesia','theatre'
  ]);
  const v5SpecialtyCodes = {
    maternity:'MATERNITY', cardiology:'CARDIOLOGY', orthopaedics:'ORTHO_TRAUMA',
    oncology:'ONCOLOGY', 'critical-care':'CRITICAL_CARE', rehab:'MENTAL_HEALTH',
    anesthesia:'SURGERY', theatre:'SURGERY'
  };
  function v5NeedsRecord(route){ return v5RecordRoutes.has(route); }
  function v5CurrentEncounter(patient){
    return (patient?.encounters||[]).find(e=>!['DISCHARGED','TRANSFERRED','LEFT_WITHOUT_BEING_SEEN'].includes(String(e.status))) || patient?.encounters?.[0] || null;
  }
  function v5RecordGate(route){
    if(!v5NeedsRecord(route)||state.selectedPatientId)return true;
    toast('Patient chart required','Search for and select a patient record before opening this function.');
    state.route='patient-search'; return false;
  }
  function v5PatientImage(patient){
    const primary=patient?.mpi_id==='TZ-MPI-00073100' || patient?.mpi_id===state.selectedPatientId;
    return primary?'/assets/avatars/juma-ally-mwangi.png':'';
  }
  function v5RecordHeader(patient, encounter, compact=false){
    if(!patient)return patientContextBanner(null);
    const img=v5PatientImage(patient);
    const deceased=String(patient.record_status||'ACTIVE')==='DECEASED';
    return `<section class="v5-record-header ${compact?'compact':''} ${deceased?'deceased-record':''}">
      <div class="v5-record-identity">${img?`<img src="${img}" alt="Patient profile">`:`<span class="v5-record-initials">${esc(initials(patient.full_name))}</span>`}
        <div><p class="eyebrow">${deceased?'Deceased longitudinal record':'Active longitudinal record'}</p><h2>${esc(patient.full_name)}</h2>
        <p><strong>MRN:</strong> ${esc(patient.mrn||'Auto-assignment pending')} &nbsp;|&nbsp; <strong>MPI:</strong> ${esc(patient.mpi_id)} &nbsp;|&nbsp; <strong>NIDA:</strong> ${esc(patient.nida_number||'Not recorded')}</p>
        <p>${esc(patient.sex||'—')} · ${patient.date_of_birth?fmtDate(patient.date_of_birth):'DOB unavailable'} · ${esc(patient.region||'Tanzania')} · ${esc(patient.phone||'No phone')}</p></div></div>
      <div class="v5-record-encounter"><span>Encounter</span><strong>${esc(encounter?.encounter_id||'No active encounter')}</strong><span>Status</span><b class="ua-status ${uaStatusClass(encounter?.status)}">${esc(statusLabel(encounter?.status||patient.record_status||'No encounter'))}</b><span>Location</span><strong>${esc([encounter?.location,encounter?.room].filter(Boolean).join(' · ')||'Not assigned')}</strong></div>
      <div class="v5-record-actions"><button class="ua-button" data-route="patient-search">Change Patient</button><button class="ua-button" data-v5-action="clear-patient-context">Close Chart</button>${!deceased?`<button class="ua-button danger-outline" data-v5-action="expire-patient">Record Death</button>`:''}</div>
    </section>`;
  }
  function v5EmptyRecordWorkspace(title){
    return `${pageHeader('Record-driven workflow',title,'This function opens only after a patient chart is selected.')}<section class="patient-context-empty v5-empty-record"><div><p class="eyebrow">No active patient chart</p><h2>Search and select a record</h2><p>Orders, results, documentation, medication and flowsheet actions are not exposed as unrestricted all-patient reports.</p></div><button class="btn btn-primary" data-route="patient-search">Open Patient Lookup</button></section>`;
  }
  function v5WorkspaceTabs(active, items, attr='patient-workspace'){
    return `<div class="v5-workspace-tabs">${items.map(([code,label])=>`<button class="${active===code?'active':''}" data-v5-action="switch-workspace" data-workspace-attr="${attr}" data-value="${code}">${esc(label)}</button>`).join('')}</div>`;
  }
  function v5FlattenTemplate(template){
    const rows=[];
    (template?.groups||[]).forEach(group=>(group.rows||[]).forEach(row=>rows.push({...row,group:group.name})));
    if(!rows.length)(template?.parameters||[]).forEach((label,i)=>rows.push({code:`P${i+1}`,label,unit:'',type:'text',group:'Observations'}));
    return rows;
  }
  function v5ObservationColumns(observations){
    const grouped=new Map();
    (observations||[]).forEach(o=>{const d=new Date(o.recorded_at);const key=Number.isNaN(d.getTime())?'Unknown':d.toISOString().slice(0,16);if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(o);});
    return [...grouped.entries()].sort((a,b)=>a[0].localeCompare(b[0])).slice(-12);
  }

  const v5OriginalNavigate=navigate;
  navigate=function(route){
    if(!v5RecordGate(route)){renderSidebar();render();return;}
    return v5OriginalNavigate(route);
  };

  async function renderMessages(){
    renderLoading('Opening secure messages…');
    const [mail,recipients]=await Promise.all([api(`/messages?folder=${encodeURIComponent(state.messageFolder||'INBOX')}&limit=100`),api('/messages/recipients')]);
    state.notifications=mail.unread||0; if($('#messageCount'))$('#messageCount').textContent=mail.unread||0;
    if(!state.selectedMessageId&&mail.items.length)state.selectedMessageId=mail.items[0].message_id;
    const selected=mail.items.find(x=>x.message_id===state.selectedMessageId)||mail.items[0];
    $('#mainContent').innerHTML=`${pageHeader('Secure Collaboration','Messages','Internal clinical and operational messaging with optional patient and encounter context.',`<button class="btn btn-primary" data-v5-action="compose-message">Compose</button>`)}
      <section class="v5-messages-layout"><aside class="ua-card v5-mail-folders">${['INBOX','SENT','ARCHIVED'].map(folder=>`<button class="${state.messageFolder===folder?'active':''}" data-v5-action="message-folder" data-folder="${folder}">${folder==='INBOX'?'Inbox':statusLabel(folder)}${folder==='INBOX'?` <b>${mail.unread||0}</b>`:''}</button>`).join('')}<hr><p class="muted">Messages remain in the institutional audit and retention boundary.</p></aside>
      <article class="ua-card v5-mail-list"><div class="ua-card-header"><h2>${statusLabel(state.messageFolder)}</h2><input id="messageSearch" class="v5-inline-search" placeholder="Search messages"></div>${mail.items.length?mail.items.map(m=>`<button class="v5-mail-row ${m.message_id===selected?.message_id?'active':''} ${m.status==='UNREAD'?'unread':''}" data-v5-action="open-message" data-message-id="${esc(m.message_id)}"><span>${esc((state.messageFolder==='SENT'?m.recipient:m.sender)?.display_name||'System')}</span><strong>${esc(m.subject)}</strong><small>${esc(m.body.slice(0,100))}</small><time>${fmtDate(m.sent_at)}</time></button>`).join(''):'<div class="empty-state"><p>No messages in this folder.</p></div>'}</article>
      <article class="ua-card v5-message-reader">${selected?`<div class="ua-card-header"><div><p class="eyebrow">${esc(selected.priority)} priority</p><h2>${esc(selected.subject)}</h2><p>${esc(selected.sender?.display_name||'System')} → ${esc(selected.recipient?.display_name||'')}</p></div><div><button class="ua-button" data-v5-action="message-action" data-message-id="${esc(selected.message_id)}" data-message-action="${selected.status==='UNREAD'?'READ':'UNREAD'}">${selected.status==='UNREAD'?'Mark read':'Mark unread'}</button><button class="ua-button" data-v5-action="message-action" data-message-id="${esc(selected.message_id)}" data-message-action="ARCHIVE">Archive</button></div></div><div class="v5-message-body">${selected.patient?`<button class="v5-context-link" data-patient-id="${esc(selected.patient.mpi_id)}">Patient: ${esc(selected.patient.full_name)} · ${esc(selected.patient.mrn)}</button>`:''}<p>${esc(selected.body).replaceAll('\n','<br>')}</p><small>Sent ${fmtDate(selected.sent_at)}</small></div>`:'<div class="empty-state"><p>Select a message.</p></div>'}</article></section>`;
    state.v5MessageRecipients=recipients;
  }

  async function renderRegistrationV5(){
    const patient=await selectedPatient();
    const encounter=v5CurrentEncounter(patient);
    const tabs=[['identity','1. Identity & MPI'],['demographics','2. Demographics & Contacts'],['coverage','3. Coverage & Consent'],['encounter','4. Encounter & Arrival']];
    const active=state.registrationWorkspace||'identity';
    const identity=`<section class="v5-form-card"><h3>Identity Search and Duplicate Prevention</h3><p class="muted">Search before create using MRN, MPI, NIDA, name, date of birth or phone.</p><div class="form-grid"><label class="field full"><span>Lookup</span><div class="walkin-inline"><input id="regLookup" placeholder="Name, phone, NIDA, MRN or MPI"><button class="ua-button primary" data-v5-action="registration-lookup">Search</button></div></label><label class="field"><span>Registration mode</span><select id="regMode"><option>STANDARD</option><option>PRE_REGISTRATION</option><option>EMERGENCY</option><option>UNKNOWN</option><option>NEWBORN</option></select></label><label class="field"><span>MRN</span><input value="Auto-assigned by facility on Save" readonly></label></div><div id="regLookupResults" class="v5-inline-results"></div></section>`;
    const demographics=`<section class="v5-form-card"><h3>Demographics and Contacts</h3><div class="form-grid"><label class="field"><span>First name</span><input id="regFirst" value="${esc(patient?.first_name||'')}"></label><label class="field"><span>Middle name</span><input id="regMiddle" value="${esc(patient?.middle_name||'')}"></label><label class="field"><span>Last name</span><input id="regLast" value="${esc(patient?.last_name||'')}"></label><label class="field"><span>Date of birth</span><input id="regDob" type="date" value="${patient?.date_of_birth?String(patient.date_of_birth).slice(0,10):''}"></label><label class="field"><span>Sex</span><select id="regSex"><option ${patient?.sex==='Female'?'selected':''}>Female</option><option ${patient?.sex==='Male'?'selected':''}>Male</option><option>Unknown</option></select></label><label class="field"><span>NIDA number</span><input id="regNida" value="${esc(patient?.nida_number||'')}"></label><label class="field"><span>Phone</span><input id="regPhone" value="${esc(patient?.phone||'')}"></label><label class="field"><span>Region</span><input id="regRegion" value="${esc(patient?.region||'Dar es Salaam')}"></label><label class="field full"><span>Address</span><input id="regAddress" value="${esc(patient?.address||'')}"></label><label class="field full"><span>Next of kin / guardian</span><input id="regNok" value="${esc(patient?.next_of_kin||'')}"></label></div></section>`;
    const coverage=`<section class="v5-form-card"><h3>Coverage, Account and Consent</h3><div class="form-grid"><label class="field"><span>Payment route</span><select id="regPayer"><option ${patient?.payer==='NHIF'?'selected':''}>NHIF</option><option>Cash</option><option>Private Insurance</option><option>iCHF</option><option>Exempted</option><option>Emergency</option></select></label><label class="field"><span>Member number</span><input id="regMember" value="${esc(patient?.member_number||'')}"></label><label class="field"><span>Consent status</span><select id="regConsent"><option>OBTAINED</option><option>PROXY</option><option>EMERGENCY_BASIS</option><option>DECLINED</option><option>PENDING</option></select></label><label class="field"><span>Proxy / guardian</span><input id="regProxy"></label><label class="field full"><span>Coverage notes</span><textarea id="regCoverageNotes">Eligibility and benefit verification required.</textarea></label></div><div class="v5-check-grid"><label><input type="checkbox" checked> Verify identity</label><label><input type="checkbox"> Scan ID</label><label><input type="checkbox"> Scan coverage card</label><label><input type="checkbox"> Collect required consent</label></div>${patient?`<div class="v5-action-row registration-financial-actions"><button class="ua-button" data-v1014-action="consents">Consent Forms</button><button class="ua-button" data-v1014-action="new-estimate" ${encounter?'':'disabled'}>Generate Estimate</button><button class="ua-button primary" data-v1014-action="collect-payment">Collect Payment / Balance</button></div>`:''}</section>`;
    const encounterPanel=`<section class="v5-form-card"><h3>Encounter, Service Point and Arrival</h3><div class="form-grid"><label class="field"><span>Facility</span><input id="regFacility" value="${esc(operationFacility())}" readonly></label><label class="field"><span>Encounter type</span><select id="regEncounterType"><option>OUTPATIENT</option><option>EMERGENCY</option><option>INPATIENT</option><option>DAY_CASE</option><option>MATERNITY</option><option>TELEHEALTH</option></select></label><label class="field"><span>Service</span><input id="regService" value="${esc(encounter?.service||'General OPD Clinic')}"></label><label class="field"><span>Reason for visit</span><input id="regReason" value="${esc(encounter?.reason_for_visit||'Clinical assessment')}"></label><label class="field"><span>Current encounter</span><input value="${esc(encounter?.encounter_id||'Created automatically with registration')}" readonly></label><label class="field"><span>Status</span><input value="${esc(statusLabel(encounter?.status||'New'))}" readonly></label></div><div class="v5-action-row"><button class="ua-button" data-route="today-patients">Return to Today’s Patients</button><button class="ua-button primary" data-v5-action="save-registration">${patient?'Save Registration Changes':'Create Patient & Encounter'}</button></div></section>`;
    const body=[['identity',identity],['demographics',demographics],['coverage',coverage],['encounter',encounterPanel]].map(([code,html])=>`<div class="v5-registration-panel ${active===code?'active':'hidden'}">${html}</div>`).join('');
    $('#mainContent').innerHTML=`${pageHeader('Registration / ADT',patient?'Update Selected Patient Record':'New Registration Workspace',patient?`Editing ${esc(patient.full_name)} · ${esc(patient.mrn)}. Search is not repeated because this record is already selected.`:'Search the MPI first, then create a patient and server-numbered encounter.')}<section class="v5-registration-shell">${v5WorkspaceTabs(active,tabs,'registrationWorkspace')}<div class="v5-registration-content">${patient?v5RecordHeader(patient,encounter,true):''}${body}</div><aside class="v5-registration-progress"><h3>Registration readiness</h3>${['Identity search completed','Demographics verified','Coverage/payment captured','Consent/legal basis documented','Encounter/service point created','Arrival routed to workflow'].map((x,i)=>`<div><span class="${i<(patient?4:1)?'done':''}">${i<(patient?4:1)?'✓':'○'}</span>${x}</div>`).join('')}<div class="alert info"><strong>${patient?'Selected record protected':'MRN assignment'}:</strong> ${patient?'Saving updates this patient only and writes an audit event.':'The backend allocates the next unique facility MRN during creation; users cannot type or reuse it.'}</div></aside></section>`;
  }

  async function renderPatientStationV5(){
    renderLoading('Loading patient station…');
    const facility=operationFacility();
    const [patient,today,summary]=await Promise.all([selectedPatient(),api(`/today-patients?facility_code=${encodeURIComponent(facility)}&limit=40`),api(`/workqueues/summary?facility_code=${encodeURIComponent(facility)}`)]);
    if(!patient){$('#mainContent').innerHTML=v5EmptyRecordWorkspace('Patient Station');return;}
    const encounter=v5CurrentEncounter(patient); const workspace=state.patientStationWorkspace||'summary';
    const encounterRows=(patient.encounters||[]).slice(0,10).map(e=>`<tr><td>${fmtDate(e.arrival_at)}</td><td>${esc(e.service)}</td><td>${esc(e.encounter_type)}</td><td>${esc(e.provider||'Duty roster')}</td><td><span class="ua-status ${uaStatusClass(e.status)}">${esc(statusLabel(e.status))}</span></td></tr>`).join('');
    const summaryPane=`<div class="v5-station-actions">${[['chart','Open Chart','Full longitudinal record','blue'],['registration','Update Registration','Demographics and identity','orange'],['transfer','Transfer Patient','Unit/service transfer','teal'],['discharge','Discharge Patient','Close active encounter','red'],['print','Print Forms','Labels, AVS and receipts','purple'],['events','Event Management','Cancel, undo and history','teal'],['benefit','Benefit Check','NHIF and coverage','green'],['team','Assign Team','On-duty team and roles','blue'],['scan','Scan Documents','ID, consent and clinical media','orange']].map(([code,label,desc,color])=>`<button class="patient-action-card ${color}" data-v5-action="station-action" data-station-action="${code}" ${code==='discharge'&&!encounter?'disabled':''}><span class="patient-action-icon">${v4Icon(code==='chart'?'chart':code==='registration'?'registration':code==='transfer'?'transfer':code==='print'?'documents':code==='events'?'reports':code==='benefit'?'shield':code==='team'?'patient':'documents')}</span><span><strong>${label}</strong><small>${desc}</small></span></button>`).join('')}</div><div class="patient-mid-grid"><article class="ua-card"><div class="ua-card-header"><h2>Current and Previous Encounters</h2></div><div class="table-wrap"><table class="ua-data-table compact-table-v4"><thead><tr><th>Arrival</th><th>Service</th><th>Type</th><th>Provider</th><th>Status</th></tr></thead><tbody>${encounterRows||'<tr><td colspan="5">No encounters</td></tr>'}</tbody></table></div></article><article class="ua-card"><div class="ua-card-header"><h2>Coverage & Payment</h2></div><div class="coverage-block"><div class="coverage-row"><span>Primary coverage</span><strong>${esc(patient.payer||'Not recorded')}</strong><b class="ua-status arrived">${patient.payer?'Active':'Review'}</b></div><div class="coverage-row"><span>Member</span><strong>${esc(patient.member_number||'Not recorded')}</strong></div><div class="coverage-row"><span>Consent</span><strong>${esc(statusLabel(patient.consent_status||'Pending'))}</strong></div><div class="coverage-row"><span>Patient balance</span><strong>TZS 0.00</strong></div></div></article></div><article class="ua-card"><div class="ua-card-header"><h2>Clinical Alerts & Flags</h2></div><div class="alert-chips"><span class="alert-chip ${String(patient.allergies||'').toLowerCase().includes('no known')?'good':'warn'}">${esc(patient.allergies||'Allergies not reviewed')}</span><span class="alert-chip">${esc(patient.medications||'Medication reconciliation due')}</span><span class="alert-chip warn">Practice advisories require clinician review</span><span class="alert-chip good">Identity ${esc(patient.identity_status||'review')}</span></div></article>`;
    const regPane=`<article class="ua-card v5-pane-body"><div class="ua-card-header"><div><h2>Registration Snapshot</h2><p>Open the dedicated four-part registration workspace to modify data.</p></div><button class="ua-button primary" data-route="registration">Open Registration Workspace</button></div><div class="v5-detail-grid">${[['MRN',patient.mrn],['MPI',patient.mpi_id],['NIDA',patient.nida_number||'Not recorded'],['Phone',patient.phone||'Not recorded'],['Region',patient.region||'Not recorded'],['District',patient.district||'Not recorded'],['Address',patient.address||'Not recorded'],['Next of kin',patient.next_of_kin||'Not recorded'],['Payer',patient.payer||'Not recorded'],['Member number',patient.member_number||'Not recorded'],['Consent',statusLabel(patient.consent_status||'Pending')],['Record status',patient.record_status||'ACTIVE']].map(([k,v])=>`<div><span>${k}</span><strong>${esc(v)}</strong></div>`).join('')}</div></article>`;
    const adtPane=`<article class="ua-card v5-pane-body"><div class="ua-card-header"><div><h2>Encounter and ADT History</h2><p>Admission, transfer, discharge and reversible event controls.</p></div><button class="ua-button" data-route="event-management">Event History</button></div><div class="table-wrap"><table class="ua-data-table"><thead><tr><th>Encounter</th><th>Arrival</th><th>Facility</th><th>Service</th><th>Location</th><th>Status</th><th>Action</th></tr></thead><tbody>${(patient.encounters||[]).map(e=>`<tr><td>${esc(e.encounter_id)}</td><td>${fmtDate(e.arrival_at)}</td><td>${esc(e.facility?.name||'')}</td><td>${esc(e.service)}</td><td>${esc([e.location,e.room].filter(Boolean).join(' / '))}</td><td><span class="ua-status ${uaStatusClass(e.status)}">${esc(statusLabel(e.status))}</span></td><td><button class="ua-button compact" data-v5-action="open-event-history" data-encounter-id="${esc(e.encounter_id)}">History</button></td></tr>`).join('')}</tbody></table></div></article>`;
    const docPane=`<section class="v5-two-pane"><article class="ua-card"><div class="ua-card-header"><h2>Documents and Media</h2><button class="ua-button" data-v5-action="station-action" data-station-action="scan">Add Document</button></div><div class="v5-document-list">${['Photo ID','NHIF / Insurance Card','Hospital Consent for Treatment','Referral Letter','Clinical Media / External Result'].map((d,i)=>`<div><span>${v4Icon('documents')}</span><strong>${d}</strong><small>${i<3?'Received / verified':'Not on file'}</small></div>`).join('')}</div></article><article class="ua-card"><div class="ua-card-header"><h2>Checklist & Verification</h2></div>${[['Patient',['Verify demographics','Verify contacts','Verify identity (NIDA/ID)','Review allergies','Review alerts & flags']],['Account',['Guarantor verified','Payment type confirmed','Estimate generated','Deposit collected if required']],['Coverage',['NHIF eligibility verified','Benefits checked','Pre-authorization if needed','Coverage documents scanned']]].map(([h,items])=>`<div class="checklist-section"><div class="checklist-heading"><span>${h}</span><span>${items.length-1} of ${items.length}</span></div>${items.map((x,i)=>`<div class="checklist-item"><span class="${i<items.length-1?'check-good':'check-empty'}">${i<items.length-1?'●':'○'}</span><span>${x}</span></div>`).join('')}</div>`).join('')}</article></section>`;
    const pane={summary:summaryPane,registration:regPane,adt:adtPane,documents:docPane}[workspace];
    const todayRows=(today.items||[]).slice(0,14);
    const queueList=(summary.queues||[]).slice(0,6);
    $('#mainContent').innerHTML=`<section class="patient-station-v5"><aside class="v5-station-list"><article class="ua-card v5-station-patients"><div class="ua-card-header"><h2>Today’s Patients Report</h2><button class="ua-icon-button" data-v5-action="refresh-station">↻</button></div><div class="v5-day-tabs"><button>Yesterday</button><button class="active">Today (${today.total||todayRows.length})</button><button>Tomorrow</button></div><input id="stationPatientSearch" class="v5-inline-search" placeholder="Search patients"><div class="v5-patient-list">${todayRows.map(row=>`<button class="${row.patient?.mpi_id===patient.mpi_id?'active':''}" data-patient-id="${esc(row.patient?.mpi_id)}" data-open-station="true"><span>${esc(row.patient?.mrn||'')}</span><strong>${esc(row.patient?.full_name||'')}</strong><small>${esc(row.service||'')} · ${esc(statusLabel(row.status||row.arrival_status||''))}</small></button>`).join('')}</div></article><article class="ua-card v5-queue-summary"><div class="ua-card-header"><h2>Workqueues Summary</h2></div>${queueList.map(q=>`<button data-route="workqueues"><span>${esc(q.name)}</span><b>${q.metrics?.active||0}</b></button>`).join('')}<button data-route="workqueues">View All Workqueues →</button></article></aside>
      <main class="v5-station-main">${v5RecordHeader(patient,encounter)}${v5WorkspaceTabs(workspace,[['summary','Summary & Actions'],['registration','Registration'],['adt','Encounters / ADT'],['documents','Documents / Verification']],'patientStationWorkspace')}<div class="v5-station-workspace">${pane}</div></main>
      <aside class="v5-station-right"><article class="ua-card"><div class="ua-card-header"><h2>Checklist & Verification</h2></div>${[['Patient',4,5],['Account',3,4],['Coverage',2,4],['Walk-In Readiness',2,3]].map(([h,n,d])=>`<div class="checklist-section"><div class="checklist-heading"><span>${h}</span><span>${n} of ${d}</span></div>${Array.from({length:d},(_,i)=>`<div class="checklist-item"><span class="${i<n?'check-good':'check-empty'}">${i<n?'●':'○'}</span><span>${['Verification complete','Task confirmed','Review required','Pending supporting document','Final check'][i]}</span></div>`).join('')}</div>`).join('')}</article><article class="ua-card walkin-callout"><div class="ua-card-header"><h2>Walk-In Workflow</h2></div><button data-v4-action="front-walkin">Start Walk-In<br><small>Register, arrive and route</small></button></article></aside></section>`;
  }

  state.v1016OrderMode=state.v1016OrderMode||'catalog';
  state.v1016OrderBasket=state.v1016OrderBasket||[];
  state.v1016OrderSets=state.v1016OrderSets||[];
  state.v1016OrderFavorites=state.v1016OrderFavorites||(()=>{try{return JSON.parse(localStorage.getItem('umoja-order-favorites')||'[]');}catch(_){return [];}})();
  state.v1016OrderRecents=state.v1016OrderRecents||(()=>{try{return JSON.parse(localStorage.getItem('umoja-order-recents')||'[]');}catch(_){return [];}})();
  let v1016OrderSearchTimer=0;

  function v1016OpenOrderEncounters(patient){return (patient?.encounters||[]).filter(e=>!['DISCHARGED','TRANSFERRED','LEFT_WITHOUT_BEING_SEEN'].includes(String(e.status).toUpperCase()));}
  function v1016OrderFavorite(item){return (state.v1016OrderFavorites||[]).some(x=>x.orderable_code===item?.orderable_code);}
  function v1016SaveOrderShortcuts(){localStorage.setItem('umoja-order-favorites',JSON.stringify((state.v1016OrderFavorites||[]).slice(0,100)));localStorage.setItem('umoja-order-recents',JSON.stringify((state.v1016OrderRecents||[]).slice(0,20)));}
  function v1016FindOrderable(code){return (state.orderCatalogItems||[]).find(x=>x.orderable_code===code)||(state.v1016OrderSets||[]).flatMap(x=>x.items||[]).find(x=>x.orderable_code===code)||(state.v1016OrderFavorites||[]).find(x=>x.orderable_code===code)||(state.v1016OrderRecents||[]).find(x=>x.orderable_code===code);}
  function v1016QueueOrderSearch(value){clearTimeout(v1016OrderSearchTimer);state.orderCatalogSearch=String(value||'').trim().replace(/\s+/g,' ');v1016OrderSearchTimer=setTimeout(()=>renderOrdersV5(true),240);}
  function v1016OrderField(label,key,value='',placeholder='',type='text',options=[]){return `<label class="field"><span>${esc(label)}</span>${options.length?`<select data-order-detail="${esc(key)}">${options.map(x=>`<option value="${esc(x)}" ${String(x)===String(value)?'selected':''}>${esc(x)}</option>`).join('')}</select>`:`<input type="${esc(type)}" data-order-detail="${esc(key)}" value="${esc(value||'')}" placeholder="${esc(placeholder)}">`}</label>`;}
  function v1016OrderDetailFields(item){
    const category=String(item?.category||'').toUpperCase(),route=item?.route||'',specimen=item?.specimen||'';
    if(category==='MEDICATION')return `<div class="v1016-composer-grid">${v1016OrderField('Dose','dose','','e.g. 500 mg')}${v1016OrderField('Route','route',route,'', 'text',route?[route,'PO','IV','IM','SC','SL','PR','INHALED','TOPICAL']:['PO','IV','IM','SC','SL','PR','INHALED','TOPICAL'])}${v1016OrderField('Frequency','frequency','','e.g. Every 8 hours')}${v1016OrderField('Duration','duration','','e.g. 5 days')}${v1016OrderField('PRN reason','prn_reason','','Leave blank if scheduled')}${v1016OrderField('Start','start','Now','', 'text',['Now','Today','Tomorrow','At next medication pass'])}</div>`;
    if(['LABORATORY','BLOOD_BANK'].includes(category))return `<div class="v1016-composer-grid">${v1016OrderField('Specimen','specimen',specimen,'Specimen type')}${v1016OrderField('Collection','collection_timing','Next collection','', 'text',['Now','Next collection','Timed','Patient-collected'])}${v1016OrderField('Fasting','fasting','Not required','', 'text',['Not required','Required','Confirm with protocol'])}${v1016OrderField('Special handling','special_handling','','Transport, temperature or isolation')}</div>`;
    if(category==='IMAGING')return `<div class="v1016-composer-grid">${v1016OrderField('Body site','body_site','','Anatomical site')}${v1016OrderField('Laterality','laterality','Not applicable','', 'text',['Not applicable','Left','Right','Bilateral'])}${v1016OrderField('Contrast','contrast','Per protocol','', 'text',['Per protocol','Without contrast','With contrast','With and without contrast'])}${v1016OrderField('Pregnancy status','pregnancy_status','Not assessed','', 'text',['Not applicable','Not assessed','Negative','Positive','Unknown'])}${v1016OrderField('Sedation','sedation','Not anticipated','', 'text',['Not anticipated','May be required','Required'])}</div>`;
    if(['CONSULT','REFERRAL'].includes(category))return `<div class="v1016-composer-grid">${v1016OrderField('Requested service','requested_service',item.department||'','Service or specialty')}${v1016OrderField('Response timeframe','response_time','Routine','', 'text',['Routine','Within 24 hours','Urgent','Immediate'])}${v1016OrderField('Clinical question','clinical_question','','Question to answer')}</div>`;
    if(['NURSING','RESPIRATORY','DIET','ACTIVITY'].includes(category))return `<div class="v1016-composer-grid">${v1016OrderField('Frequency','frequency','','e.g. Every 4 hours')}${v1016OrderField('Start','start','Now','', 'text',['Now','Today','Next shift','Post procedure'])}${v1016OrderField('Stop / review','review','','Date, time or clinical milestone')}${v1016OrderField('Precautions','precautions','','Safety parameters')}</div>`;
    if(category==='ADT')return `<div class="v1016-composer-grid">${v1016OrderField('Destination service','destination_service','','Admitting service')}${v1016OrderField('Level of care','level_of_care','Ward','', 'text',['Ward','High dependency','ICU','Observation'])}${v1016OrderField('Requested unit / bed','requested_bed','','Unit, ward or bed')}${v1016OrderField('Isolation','isolation','None','', 'text',['None','Contact','Droplet','Airborne','Protective'])}</div>`;
    return `<div class="v1016-composer-grid">${v1016OrderField(item?.clinical?'Frequency / timing':'Needed by','timing',item?.clinical?'Now':'Routine','Timing')}${v1016OrderField(item?.clinical?'Care location':'Delivery location','location','','Unit, room or service point')}${v1016OrderField('Assigned department','assigned_department',item?.department||'','Responsible team')}${v1016OrderField('Contact / handoff','handoff','','Name or handoff instructions')}</div>`;
  }
  function v1016OrderComposerPayload(item){
    const details={};$$('[data-order-detail]').forEach(field=>{if(String(field.value||'').trim())details[field.dataset.orderDetail]=field.value.trim();});
    return {encounter_id:$('#v1016OrderEncounter')?.value||'',orderable_code:item.orderable_code,priority:$('#v1016OrderPriority')?.value||item.default_priority||'ROUTINE',indication:$('#v1016OrderIndication')?.value.trim()||null,instructions:$('#v1016OrderInstructions')?.value.trim()||null,details,ordered_by:currentRole().user};
  }
  function v1016OrderComposer(item,patient,encounter){
    const encounters=v1016OpenOrderEncounters(patient),selectedEncounter=state.v1016OrderEncounterId||encounter?.encounter_id||encounters[0]?.encounter_id||'';
    if(!item)return `<div class="v1016-composer-empty"><span>＋</span><h3>Choose an order</h3><p>Search the catalog, open an order set, or choose a favorite. The composer will adapt to the order type.</p></div>`;
    return `<div class="v1016-selected-order"><div><span class="v5-order-type ${item.clinical?'clinical':'operational'}">${item.clinical?'Clinical':'Operational'}</span><small>${esc(statusLabel(item.category))}${item.subcategory?` · ${esc(item.subcategory)}`:''}</small></div><button class="v1016-star ${v1016OrderFavorite(item)?'active':''}" data-v5-action="favorite-orderable" data-orderable-code="${esc(item.orderable_code)}" title="Favorite">★</button><h3>${esc(item.display_name)}</h3><p>${esc(item.orderable_code)}${item.department?` · routes to ${esc(item.department)}`:''}</p></div>${encounters.length?`<div class="v1016-context-strip"><strong>${esc(patient.full_name)}</strong><span>${esc(patient.allergies||'Allergies not reviewed')}</span><span>${esc(patient.medications||'Medication reconciliation pending')}</span></div><label class="field"><span>Encounter — required and never free text</span><select id="v1016OrderEncounter">${encounters.map(e=>`<option value="${esc(e.encounter_id)}" ${e.encounter_id===selectedEncounter?'selected':''}>${e.encounter_id===encounter?.encounter_id?'Current · ':''}${esc(e.encounter_id)} · ${esc(e.service)} · ${esc(statusLabel(e.status))}</option>`).join('')}</select></label><div class="v1016-composer-grid"><label class="field"><span>Priority</span><select id="v1016OrderPriority">${['ROUTINE','URGENT','STAT'].map(x=>`<option ${x===(item.default_priority||'ROUTINE')?'selected':''}>${x}</option>`).join('')}</select></label><label class="field"><span>Indication / clinical question ${item.requires_reason?'*':''}</span><input id="v1016OrderIndication" placeholder="Why is this order needed?"></label></div>${v1016OrderDetailFields(item)}<label class="field"><span>Instructions</span><textarea id="v1016OrderInstructions" rows="2" placeholder="Patient-specific instructions">${esc(item.default_instructions||'')}</textarea></label><button class="ua-button primary full-width v1016-add-basket" data-v5-action="add-order-basket">＋ Add to order basket</button>`:`<div class="alert warning"><strong>No active encounter.</strong> Physical care orders cannot be attached to a historical visit. Start or arrive the appropriate encounter first.</div>`}`;
  }
  function v1016CatalogRows(items,selected){return items.map(item=>`<article class="v1016-order-row ${selected?.orderable_code===item.orderable_code?'active':''}"><button class="v1016-order-select" data-v5-action="select-orderable" data-orderable-code="${esc(item.orderable_code)}"><span class="v1016-order-icon">${esc(({MEDICATION:'Rx',LABORATORY:'⚗',IMAGING:'◉',BLOOD_BANK:'◆',CONSULT:'↗',NURSING:'✚',ADT:'↔',EVS:'◇',EQUIPMENT:'▦'})[item.category]||'＋')}</span><span><strong>${esc(item.display_name)}</strong><small>${esc(statusLabel(item.category))}${item.subcategory?` · ${esc(item.subcategory)}`:''}${item.department?` · ${esc(item.department)}`:''}</small></span></button><button class="v1016-row-star ${v1016OrderFavorite(item)?'active':''}" data-v5-action="favorite-orderable" data-orderable-code="${esc(item.orderable_code)}" title="Favorite">★</button><button class="v1016-quick-add" data-v5-action="quick-add-order" data-orderable-code="${esc(item.orderable_code)}" title="Open composer">＋</button></article>`).join('')||'<div class="empty-state"><p>No approved orderables match these filters.</p></div>';}
  function v1016OrderSetCards(orderSets){return orderSets.map(set=>`<article class="v1016-order-set-card"><header><div><span>${esc(set.specialty||'Clinical panel')}</span><h3>${esc(set.name)}</h3></div><b>${set.items.length}</b></header><p>${esc(set.description||'Governed group of orderables.')}</p><div class="v1016-set-preview">${set.items.slice(0,5).map(item=>`<span>${item.required?'●':'○'} ${esc(item.display_name)}</span>`).join('')}${set.items.length>5?`<small>+ ${set.items.length-5} more</small>`:''}</div><footer><small>v${set.version} · ${esc(set.approved_by||'Clinical governance')}</small><button class="ua-button primary compact" data-v5-action="add-order-set" data-order-set-code="${esc(set.set_code)}">Add panel</button></footer></article>`).join('')||'<div class="empty-state"><p>No order sets match this context.</p></div>';}
  function v1016OrderBasket(){const basket=state.v1016OrderBasket||[];return `<aside class="ua-card v1016-order-basket"><div class="ua-card-header"><div><h2>Order Basket</h2><p>${basket.length?`${basket.length} ready for review`:'Build a safe signing session'}</p></div><span class="v1016-basket-count">${basket.length}</span></div><div class="v1016-basket-list">${basket.map((item,index)=>`<div><span class="v1016-basket-dot ${String(item.priority).toLowerCase()}"></span><p><strong>${esc(item.display_name)}</strong><small>${esc(item.priority)} · ${esc(statusLabel(item.category))}<br>${esc(item.encounter_id)}</small></p><button data-v5-action="remove-order-basket" data-index="${index}" title="Remove">×</button></div>`).join('')||'<section><span>🛒</span><strong>Your basket is empty</strong><small>Add individual orders or a governed order panel.</small></section>'}</div>${basket.length?`<div class="v1016-basket-actions"><button class="ua-button" data-v5-action="clear-order-basket">Clear</button>${v1014Can('system.configuration.manage')?'<button class="ua-button" data-v5-action="open-order-set-builder">Save as panel</button>':''}<button class="ua-button primary" data-v5-action="review-order-basket">Review & sign ${basket.length}</button></div>`:''}</aside>`;}

  async function renderOrdersV5(quiet=false){
    if(!state.selectedPatientId){$('#mainContent').innerHTML=v5EmptyRecordWorkspace('Orders');return;}
    if(!quiet)renderLoading('Opening smart order entry…');
    const patient=await selectedPatient();if(!patient){$('#mainContent').innerHTML=v5EmptyRecordWorkspace('Orders');return;}state.v5Patient=patient;
    const encounter=v1014OpenEncounter(patient)||v5CurrentEncounter(patient),search=state.orderCatalogSearch||'',category=state.orderCatalogCategory||'';
    const [catalog,categories,orderSets,orders]=await Promise.all([api(`/order-catalog?search=${encodeURIComponent(search)}&category=${encodeURIComponent(category)}&limit=200`),state.orderCatalogCategories.length?Promise.resolve(state.orderCatalogCategories):api('/order-catalog/categories'),api('/order-sets'),api(`/orders?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`)]);
    state.orderCatalogCategories=categories;state.orderCatalogItems=catalog.items;state.v1016OrderSets=orderSets;state.v1016OrderEncounterId=state.v1016OrderEncounterId||encounter?.encounter_id||v1016OpenOrderEncounters(patient)[0]?.encounter_id||'';
    if(state.selectedOrderable&&!v1016FindOrderable(state.selectedOrderable.orderable_code))state.selectedOrderable=null;
    const selected=state.selectedOrderable,mode=state.v1016OrderMode||'catalog',allShortcuts=mode==='favorites'?state.v1016OrderFavorites:state.v1016OrderRecents,shortcutItems=allShortcuts.filter(item=>!search||`${item.display_name} ${item.orderable_code} ${item.category} ${item.synonyms||''}`.toLowerCase().includes(search.toLowerCase()));
    const lookupBody=mode==='sets'?`<div class="v1016-order-sets">${v1016OrderSetCards(orderSets.filter(set=>!search||`${set.name} ${set.specialty} ${set.description}`.toLowerCase().includes(search.toLowerCase())))}</div>`:mode==='catalog'?`<div class="v1016-order-catalog-list">${v1016CatalogRows(catalog.items,selected)}</div>`:`<div class="v1016-order-catalog-list">${v1016CatalogRows(shortcutItems,selected)}</div>`;
    $('#mainContent').innerHTML=`${pageHeader('Computerized Provider Order Entry','Smart Orders','Fast, governed order entry with patient safety context, adaptive details, order panels and one reviewed signing session.',`${v1014Can('system.configuration.manage')?'<button class="btn" data-v5-action="open-custom-orderable">＋ Custom Orderable</button>':''}`)}${v5RecordHeader(patient,encounter,true)}<section class="v1016-cpoe-shell"><main class="ua-card v1016-order-lookup"><header class="v1016-cpoe-tabs">${[['catalog','Catalog'],['sets','Order Panels'],['favorites','Favorites'],['recent','Recent']].map(([code,label])=>`<button class="${mode===code?'active':''}" data-v5-action="order-mode" data-mode="${code}">${label}${code==='favorites'&&state.v1016OrderFavorites.length?` <b>${state.v1016OrderFavorites.length}</b>`:''}</button>`).join('')}</header><div class="v1016-order-search"><span>⌕</span><input id="orderCatalogSearch" value="${esc(search)}" placeholder="Type any part of an order, synonym, code or specialty…" autocomplete="off"><kbd>Live</kbd><button class="ua-button primary" data-v5-action="search-order-catalog">Search</button></div>${mode==='catalog'?`<div class="v1016-order-categories"><button class="${!category?'active':''}" data-v5-action="order-category" data-category="">All <b>${categories.reduce((n,c)=>n+c.total,0).toLocaleString()}</b></button>${categories.map(c=>`<button class="${category===c.category?'active':''}" data-v5-action="order-category" data-category="${esc(c.category)}">${esc(statusLabel(c.category))} <b>${c.total}</b></button>`).join('')}</div><div class="v1016-result-count"><span>${catalog.total.toLocaleString()} approved match${catalog.total===1?'':'es'}</span><small>The catalog is extensible by authorized clinical governance administrators.</small></div>`:''}${lookupBody}</main><aside class="ua-card v1016-order-composer"><div class="ua-card-header"><div><h2>Order Composer</h2><p>Patient + encounter + order-specific details</p></div></div>${v1016OrderComposer(selected,patient,encounter)}</aside>${v1016OrderBasket()}</section><article class="ua-card v5-current-orders"><div class="ua-card-header"><div><h2>Orders for ${esc(patient.full_name)}</h2><p>Every order remains linked to its encounter; hold, cancel and reinstate actions preserve the full event history.</p></div><b>${orders.length}</b></div><div class="table-wrap"><table class="ua-data-table"><thead><tr><th>Order</th><th>Encounter</th><th>Type</th><th>Priority</th><th>Status</th><th>Ordered by / time</th><th>Course</th></tr></thead><tbody>${orders.map(o=>`<tr><td><strong>${esc(o.order_name)}</strong><br><small>${esc(o.order_id)}${o.orderable_code?` · ${esc(o.orderable_code)}`:''}</small></td><td>${esc(o.encounter_id)}</td><td>${esc(statusLabel(o.order_type))}</td><td><span class="ua-priority ${String(o.priority).toLowerCase()}">${esc(o.priority)}</span></td><td><span class="ua-status ${uaStatusClass(o.status)}">${esc(statusLabel(o.status))}</span></td><td>${esc(o.ordered_by)}<br><small>${fmtDate(o.ordered_at)}</small></td><td>${['SIGNED','ACTIVE','RESUMED'].includes(String(o.status))?`<button class="ua-button compact" data-v5-action="order-course" data-order-id="${esc(o.order_id)}" data-course="HOLD">Hold</button><button class="ua-button compact danger-outline" data-v5-action="order-course" data-order-id="${esc(o.order_id)}" data-course="CANCEL">Cancel</button>`:''}${String(o.status)==='ON_HOLD'?`<button class="ua-button compact" data-v5-action="order-course" data-order-id="${esc(o.order_id)}" data-course="RESUME">Resume</button>`:''}${String(o.status)==='CANCELLED'?`<button class="ua-button compact" data-v5-action="order-course" data-order-id="${esc(o.order_id)}" data-course="REINSTATE">Reinstate</button>`:''}</td></tr>`).join('')||'<tr><td colspan="7">No orders for this patient record.</td></tr>'}</tbody></table></div></article>`;
  }

  const V1016_FLOW_DEFAULT_COLUMNS=['Heart rate','Systolic blood pressure','Diastolic blood pressure','Temperature','Respiratory rate','Oxygen saturation','Pain score','AVPU'];
  function v1016FlowCatalog(templates){
    const catalog=new Map();
    (templates||[]).forEach(template=>v5FlattenTemplate(template).forEach(row=>{const key=String(row.label).toLowerCase(),scope=chartFlowScope(template),item={...row,template_code:template.code,template_name:template.name,scope};const current=catalog.get(key);if(!current||current.scope==='INPATIENT'&&scope!=='INPATIENT')catalog.set(key,item);}));
    return [...catalog.values()];
  }
  function v1016FlowVariables(sheet,catalog){
    const configured=(state.v1016FlowDraftParameters?.length?state.v1016FlowDraftParameters:sheet?.parameters?.filter(Boolean))||V1016_FLOW_DEFAULT_COLUMNS;
    return configured.map((name,index)=>catalog.find(item=>item.label.toLowerCase()===String(name).toLowerCase())||{code:`CUSTOM_${index+1}`,label:String(name),unit:'',type:'text',group:'Custom',scope:'SPECIALTY'});
  }
  function v1016FlowTimeRows(observations){
    const groups=new Map();(observations||[]).forEach(item=>{const date=new Date(item.recorded_at),key=Number.isNaN(date.getTime())?'Unknown':date.toISOString().slice(0,16);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(item);});
    return [...groups.entries()].sort((a,b)=>b[0].localeCompare(a[0])).slice(0,24);
  }
  function v1016FlowEntry(variable,locked){
    const common=`class="v1016-flow-entry" data-v1016-flow-input data-flow-variable="${esc(variable.label)}" data-unit="${esc(variable.unit||'')}" ${locked?'disabled':''}`;
    if(variable.type==='choice'||variable.type==='multiselect')return `<select ${common}><option value="">—</option>${(variable.choices||[]).map(value=>`<option value="${esc(value)}">${esc(value)}</option>`).join('')}</select>`;
    if(variable.type==='boolean')return `<select ${common}><option value="">—</option><option>Yes</option><option>No</option></select>`;
    if(variable.type==='calculated')return '<span class="v1016-flow-calculated">Auto</span>';
    return `<input ${common} type="${variable.type==='number'?'number':'text'}" ${variable.type==='number'?'step="any"':''} placeholder="—">`;
  }
  function v1016FlowObservationValue(items,variable){const found=(items||[]).find(item=>String(item.parameter).toLowerCase()===String(variable.label).toLowerCase()||String(item.parameter).toUpperCase()===String(variable.code).toUpperCase());return found?`<strong>${esc(found.value)}</strong>${found.unit?`<small>${esc(found.unit)}</small>`:''}`:'<span class="muted">—</span>';}
  async function v1016EnsureFlowSheet(context,parameters){
    if(context.sheet)return context.sheet;if(!context.encounter)throw new Error('Select or create an encounter before recording flowsheet observations.');
    const created=await api('/flowsheets',{method:'POST',body:JSON.stringify({patient_mpi_id:context.patient.mpi_id,encounter_id:context.encounter.encounter_id,name:'Clinical Flowsheet',template_code:'LONGITUDINAL_GRID',cadence_minutes:15,parameters,owner:currentRole().user})});state.selectedFlowSheetId=created.flowsheet_id;state.v1016ForceNewFlowSheet=false;state.v1016FlowDraftParameters=null;return created;
  }
  function v1016FlowColumnModal(){
    const context=state.v1016FlowContext;if(!context)return;const draft=state.v1016FlowColumnDraft||[],catalog=context.catalog;
    openModal('Configure Flowsheet Columns',`<section class="v1016-flow-column-manager"><div class="alert info"><strong>Columns belong to this patient/encounter flowsheet.</strong> Reorder, add or remove variables. Prior observations remain in the legal history.</div><h3>Active columns</h3><div class="v1016-flow-active-columns">${draft.map((name,index)=>`<article><span>${index+1}</span><strong>${esc(name)}</strong><div><button class="ua-button compact" data-v5-action="flow-column-left" data-index="${index}" ${index===0?'disabled':''}>←</button><button class="ua-button compact" data-v5-action="flow-column-right" data-index="${index}" ${index===draft.length-1?'disabled':''}>→</button><button class="ua-button compact danger-outline" data-v5-action="flow-column-remove" data-index="${index}">Remove</button></div></article>`).join('')}</div><div class="v1016-flow-catalog-heading"><h3>Variable library</h3><input id="v1016FlowVariableSearch" placeholder="Find heart rate, GCS, intake…"></div><div class="v1016-flow-variable-library">${catalog.map(item=>`<button data-v5-action="flow-column-add" data-variable="${esc(item.label)}" data-flow-variable-option ${draft.includes(item.label)?'disabled':''}><span class="chart-flow-scope ${item.scope.toLowerCase()}">${esc(statusLabel(item.scope))}</span><strong>${esc(item.label)}</strong><small>${esc(item.group)}${item.unit?` · ${esc(item.unit)}`:''}</small></button>`).join('')}</div></section>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v5-action="save-flow-columns">Save Column Layout</button>`,'Encounter Flowsheet Configuration');
  }
  async function renderFlowsheetsV5(){
    if(!state.selectedPatientId){$('#mainContent').innerHTML=v5EmptyRecordWorkspace('Flowsheets');return;}
    renderLoading('Loading permanent patient flowsheet…');const patient=await selectedPatient();if(!patient){$('#mainContent').innerHTML=v5EmptyRecordWorkspace('Flowsheets');return;}
    const [sheets,templates,devices,readings,orders]=await Promise.all([api(`/flowsheets?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`),api('/flowsheet-templates'),api(`/devices?facility_code=${encodeURIComponent(operationFacility())}`),api(`/device-readings?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}&limit=50`),api(`/orders?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`)]);
    const encounter=patient.encounters.find(item=>item.encounter_id===state.selectedEncounterId)||v5CurrentEncounter(patient),encounterSheets=sheets.filter(item=>(item.encounter_id||null)===(encounter?.encounter_id||null));
    let sheet=state.v1016ForceNewFlowSheet?null:encounterSheets.find(item=>item.flowsheet_id===state.selectedFlowSheetId)||encounterSheets.find(item=>item.status!=='STOPPED')||encounterSheets[0]||null;if(sheet)state.selectedFlowSheetId=sheet.flowsheet_id;else state.selectedFlowSheetId=null;
    const catalog=v1016FlowCatalog(templates),variables=v1016FlowVariables(sheet,catalog),timeRows=v1016FlowTimeRows(sheet?.observations||[]),admitted=chartHasAdmitOrder(orders,encounter),closedEncounter=!encounter||['DISCHARGED','TRANSFERRED','LEFT_WITHOUT_BEING_SEEN'].includes(encounter.status),canEdit=v1014Can('flowsheets.manage')&&!closedEncounter&&sheet?.status!=='STOPPED';
    const lockedCount=variables.filter(item=>item.scope==='INPATIENT'&&!admitted).length,template=templates.find(item=>item.code===sheet?.template_code)||templates.find(item=>item.code==='TRIAGE_AMBULATORY')||templates[0];
    state.v1016FlowContext={patient,encounter,sheet,sheets,templates,catalog,variables,admitted,canEdit};state.v5Patient=patient;state.v5FlowTemplates=templates;state.v5FlowSheet=sheet;state.v5FlowTemplate=template;
    const sheetControls=sheet?`${sheet.status==='DRAFT'?`<button class="ua-button compact primary" data-v5-action="flowsheet-control" data-course="START">Start</button>`:''}${sheet.status==='RUNNING'?`<button class="ua-button compact" data-v5-action="flowsheet-control" data-course="PAUSE">Pause</button>`:''}${sheet.status==='PAUSED'?`<button class="ua-button compact primary" data-v5-action="flowsheet-control" data-course="RESUME">Resume</button>`:''}${sheet.status!=='STOPPED'?`<button class="ua-button compact danger-outline" data-v5-action="flowsheet-control" data-course="STOP">Stop</button>`:''}`:'';
    $('#mainContent').innerHTML=`${pageHeader('Encounter Clinical Documentation','Patient Flowsheet','A permanent time-by-variable spreadsheet. Configure the columns once, chart a row in seconds, and keep every value linked to the selected encounter.',`<button class="btn" data-route="chart">Open Patient Chart</button><button class="btn btn-primary" data-v5-action="open-flow-columns" ${canEdit?'':'disabled'}>Configure Columns</button>`)}${v5RecordHeader(patient,encounter,true)}
      <article class="ua-card v1016-flow-card"><header class="v1016-flow-header"><div><p class="eyebrow">Always available</p><h2>${esc(sheet?.name||'Clinical Flowsheet')}</h2><p>${esc(encounter?.encounter_id||'No active encounter')} · ${esc(encounter?.service||'Select a visit before charting')} · ${variables.length} columns</p></div><div class="v1016-flow-status"><span class="ua-status ${sheet?uaStatusClass(sheet.status):'neutral'}">${esc(sheet?statusLabel(sheet.status):'Ready')}</span><span class="ua-status ${admitted?'success':'neutral'}">Inpatient ${admitted?'enabled':'locked'}</span>${sheetControls}</div></header>
        <div class="v1016-flow-toolbar"><label><span>Encounter</span><select id="v1016FlowEncounterSelect">${patient.encounters.map(item=>`<option value="${esc(item.encounter_id)}" ${item.encounter_id===encounter?.encounter_id?'selected':''}>${esc(item.encounter_id)} · ${esc(item.service)} · ${esc(statusLabel(item.status))}</option>`).join('')}</select></label><label><span>Flowsheet history</span><select id="v1016FlowSheetSelect"><option value="">New / always-ready grid</option>${encounterSheets.map(item=>`<option value="${esc(item.flowsheet_id)}" ${item.flowsheet_id===sheet?.flowsheet_id?'selected':''}>${esc(item.name)} · ${esc(statusLabel(item.status))}</option>`).join('')}</select></label><div class="v1016-flow-preset"><label><span>Compact template library</span><select id="v1016FlowPreset" ${canEdit?'':'disabled'}>${templates.map(item=>`<option value="${esc(item.code)}" ${item.code===template?.code?'selected':''} ${CHART_INPATIENT_TEMPLATES.has(item.code)&&!admitted?'disabled':''}>${esc(item.name)} · ${v5FlattenTemplate(item).length}</option>`).join('')}</select></label><button class="ua-button" data-v5-action="apply-flow-preset" ${canEdit?'':'disabled'}>Apply</button></div><button class="ua-button" data-v5-action="open-flow-columns" ${canEdit?'':'disabled'}>＋ / Reorder columns</button></div>
        ${lockedCount?`<div class="chart-flow-lock-note"><strong>${lockedCount} inpatient column${lockedCount===1?' is':'s are'} visible but locked.</strong> An active “Admit to inpatient service” order for ${esc(encounter?.encounter_id||'this encounter')} is required before entry.</div>`:''}${closedEncounter?'<div class="alert warning"><strong>Review only.</strong> Select an open encounter before recording new physical observations.</div>':''}
        <div class="v1016-flow-grid-wrap"><table class="v1016-flow-table"><thead><tr><th class="v1016-flow-time">Time / author</th>${variables.map(variable=>`<th><strong>${esc(variable.label)}</strong><span>${esc(variable.unit||variable.group||'Observation')}</span><small class="chart-flow-scope ${variable.scope.toLowerCase()}">${esc(statusLabel(variable.scope))}</small></th>`).join('')}</tr></thead><tbody>
          <tr class="v1016-flow-now"><th><strong>Now</strong><span>${esc(currentRole().user)}</span><small>Manual entry</small></th>${variables.map(variable=>`<td class="${variable.scope==='INPATIENT'&&!admitted?'locked':''}">${v1016FlowEntry(variable,!canEdit||variable.scope==='INPATIENT'&&!admitted)}</td>`).join('')}</tr>
          ${timeRows.map(([key,items])=>`<tr><th><strong>${key==='Unknown'?'Unknown time':new Date(`${key}:00Z`).toLocaleString([], {month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'})}</strong><span>${esc(items[0]?.recorded_by||'')}</span><small>${esc(items[0]?.source||'')}</small></th>${variables.map(variable=>`<td>${v1016FlowObservationValue(items,variable)}</td>`).join('')}</tr>`).join('')||`<tr class="v1016-flow-empty"><td colspan="${variables.length+1}">No prior rows yet. The spreadsheet stays here and the first saved row starts encounter history.</td></tr>`}
        </tbody></table></div><footer class="v1016-flow-footer"><div><strong>${variables.length} variable columns</strong><span>${timeRows.length} historical time rows · ${lockedCount} locked</span></div><div><button class="ua-button" data-v5-action="open-flow-columns">Customize columns</button><button class="ua-button primary" data-v5-action="save-flow-row" ${canEdit?'':'disabled'}>Save Current Row</button></div></footer>
      </article><details class="ua-card v1016-flow-utilities"><summary>Devices, templates and flowsheet utilities</summary><div><section><h3>Device feeds</h3>${devices.slice(0,6).map(device=>`<div class="v5-device-row"><span class="${device.status==='ONLINE'?'online':'offline'}"></span><div><strong>${esc(device.name)}</strong><small>${esc(device.protocol)} · ${esc(device.unit||'Unassigned')}</small></div>${sheet&&encounter?`<button class="ua-button compact" data-v5-action="test-device-ingest" data-device-id="${esc(device.device_id)}">Test</button>`:''}</div>`).join('')||'<p>No device feeds configured.</p>'}</section><section><h3>Recent device values</h3>${readings.slice(0,8).map(item=>`<div class="v5-reading-row"><span>${esc(item.parameter_name)}</span><strong>${esc(item.numeric_value??item.text_value??'')} ${esc(item.unit||'')}</strong><small>${fmtDate(item.recorded_at)}</small></div>`).join('')||'<p>No recent device values.</p>'}</section></div></details>`;
  }

  async function renderBedBoardV5(){
    renderLoading('Loading unit manager…');
    const facility=operationFacility(); const units=await api(`/bed-units?facility_code=${encodeURIComponent(facility)}`);
    if(!state.selectedBedUnit&&units.length)state.selectedBedUnit=units[0].unit;
    const beds=state.selectedBedUnit?await api(`/beds?facility_code=${encodeURIComponent(facility)}&unit=${encodeURIComponent(state.selectedBedUnit)}`):[];
    $('#mainContent').innerHTML=`${pageHeader('ADT and Capacity','Unit Manager','Select one unit first; beds and patient details are never rendered as a hospital-wide wall of records.',`<button class="btn" data-v5-action="change-context">Change Context</button>`)}
      <section class="v5-unit-manager"><aside class="ua-card v5-unit-list"><div class="ua-card-header"><h2>Units</h2></div>${units.map(u=>`<button class="${u.unit===state.selectedBedUnit?'active':''}" data-v5-action="select-bed-unit" data-unit="${esc(u.unit)}"><strong>${esc(u.unit)}</strong><span>${u.occupied}/${u.total} occupied</span><div class="v5-capacity-bar"><i style="width:${u.occupancy_percent}%"></i></div><small>${u.available} available · ${u.turnover} turnover · ${u.blocked} blocked</small></button>`).join('')||'<div class="empty-state"><p>No bed units configured at this facility.</p></div>'}</aside>
      <main class="ua-card v5-bed-workspace"><div class="ua-card-header"><div><h2>${esc(state.selectedBedUnit||'Select a unit')}</h2><p>${beds.length} beds in selected unit</p></div><div class="v5-bed-legend"><span class="available">Available</span><span class="occupied">Occupied</span><span class="turnover">Turnover</span><span class="blocked">Blocked</span></div></div><div class="v5-bed-grid">${beds.map(b=>`<article class="v5-bed-tile ${String(b.status).toLowerCase()}"><header><strong>${esc(b.room)} · ${esc(b.bed_label)}</strong><span>${esc(statusLabel(b.status))}</span></header>${b.patient?`<button data-patient-id="${esc(b.patient.mpi_id)}"><b>${esc(b.patient.full_name)}</b><small>${esc(b.patient.mrn)} · ${esc(b.encounter?.encounter_id||'')}</small></button>`:'<div class="v5-empty-bed">No patient assigned</div>'}<footer><small>${esc(b.bed_type||'Standard')} ${b.isolation?`· ${esc(b.isolation)}`:''}</small><button class="ua-button compact" data-v5-action="bed-actions" data-bed-id="${esc(b.bed_id)}" data-bed-status="${esc(b.status)}">Actions</button></footer></article>`).join('')}</div></main></section>`;
  }

  function v1016ManageUserPhoto(user){
    if(!user)return toast('Select a user','Choose the account whose photo an administrator should manage.');
    openModal('Manage User Profile Photo',`<section class="v1016-user-photo-manager"><div id="v1016AdminPhotoPreview" class="v1016-user-photo-preview"><span>${esc(initials(user.display_name))}</span></div><div><h3>${esc(user.display_name)}</h3><p>${esc(user.username)} · ${esc(statusLabel(user.role_code))}</p><label class="field"><span>Profile photo</span><input id="v1016UserPhotoFile" type="file" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"><small>PNG, JPEG or WebP; maximum 2 MB. A square head-and-shoulders image works best.</small></label><label class="field"><span>Administrative reason</span><input id="v1016UserPhotoReason" value="Authorized workforce profile update"></label><div class="alert info"><strong>Administrator controlled:</strong> individual users cannot upload or replace their own photos. Uploads and removals are hashed, time-stamped and written to the security audit trail.</div></div></section>`,`<button class="ua-button danger-outline" data-v5-action="remove-user-photo" data-user-id="${esc(user.user_id)}" ${user.has_profile_photo?'':'disabled'}>Remove Photo</button><button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v5-action="upload-user-photo" data-user-id="${esc(user.user_id)}">Upload Photo</button>`,'Administrator-only profile management');
    queueMicrotask(()=>v1016HydrateProfilePhoto($('#v1016AdminPhotoPreview'),user));
  }

  async function renderSystemAdminV5(){
    renderLoading('Loading IT access matrix…');
    const [users,catalog]=await Promise.all([api('/admin/users'),api('/admin/access-catalog')]);
    state.adminUsers=users; state.accessCatalog=catalog;
    if(!state.selectedAdminUserId&&users.length)state.selectedAdminUserId=users[0].user_id;
    const user=users.find(u=>u.user_id===state.selectedAdminUserId)||users[0];
    const scope=state.adminMatrixScope||'functions'; const catalogKey=scope; const items=catalog[scope]||[]; const selectedSet=new Set(user?.[scope]||[]);
    $('#mainContent').innerHTML=`${pageHeader('ICT Administration','Users and Access Matrix','Users are rows; functions, departments and facilities are independently checked longitudinally. Job titles are templates, not the authorization boundary.',`<button class="btn btn-primary" data-v5-action="create-user">Add User</button>`)}
      <section class="v5-admin-shell"><aside class="ua-card v5-admin-users"><div class="ua-card-header"><h2>Users</h2><input id="adminUserSearch" class="v5-inline-search" placeholder="Search users"></div>${users.map(u=>`<button class="${u.user_id===user?.user_id?'active':''}" data-v5-action="select-admin-user" data-user-id="${esc(u.user_id)}"><span class="v5-user-avatar">${esc(initials(u.display_name))}</span><div><strong>${esc(u.display_name)}</strong><small>${esc(u.username)} · ${esc(statusLabel(u.role_code))}</small></div><i class="${u.active?'online':'offline'}"></i></button>`).join('')}</aside>
      <main class="ua-card v5-admin-matrix"><div class="ua-card-header"><div class="v1016-admin-user-heading"><span id="v1016SelectedAdminPhoto" class="v1016-admin-photo">${esc(initials(user?.display_name||'User'))}</span><div><h2>${esc(user?.display_name||'Select user')}</h2><p>${esc(user?.username||'')} · ${user?.functions?.length||0} functions · ${user?.departments?.length||0} departments · ${user?.countries?.length||0} countries · ${user?.facilities?.length||0} facilities</p></div></div><div><button class="ua-button" data-v5-action="manage-user-photo">Manage Photo</button><button class="ua-button" data-v5-action="edit-user-profile">Edit Profile</button><button class="ua-button" data-v5-action="reset-user-password">Reset Password</button></div></div><div class="v5-matrix-tabs">${[['functions','Functions'],['departments','Departments'],['countries','Countries'],['facilities','Facilities']].map(([code,label])=>`<button class="${scope===code?'active':''}" data-v5-action="admin-matrix-scope" data-scope="${code}">${label} <b>${user?.[code]?.length||0}</b></button>`).join('')}</div><div class="v5-matrix-toolbar"><input id="matrixSearch" class="v5-inline-search" placeholder="Filter ${scope}"><button class="ua-button" data-v5-action="matrix-toggle-all" data-checked="true">Select All</button><button class="ua-button" data-v5-action="matrix-toggle-all" data-checked="false">Clear</button><span>Changes require an auditable reason.</span></div><div class="v5-matrix-grid">${items.map(item=>`<label class="v5-matrix-cell"><input type="checkbox" data-v5-matrix-scope="${scope}" value="${esc(item.code)}" ${selectedSet.has(item.code)?'checked':''}><span><strong>${esc(item.label)}</strong><small>${esc(item.group||'')} · ${esc(item.description||item.code)}</small></span></label>`).join('')}</div><div class="v5-matrix-save"><label class="field"><span>Access change reason</span><input id="matrixReason" value="Access matrix review and approved workflow assignment"></label><button class="ua-button primary" data-v5-action="save-user-matrix">Save ${statusLabel(scope)} Matrix</button></div></main>
      <aside class="ua-card v5-it-summary"><h2>Account Controls</h2>${[['Status',user?.active?'Active':'Inactive'],['Profile photo',user?.has_profile_photo?'Administrator assigned':'Initials only'],['MFA',user?.requires_mfa?'Required':'Not required'],['Failed logins',user?.failed_login_count||0],['Primary facility',user?.facility_code||'—'],['Last login',user?.last_login_at?fmtDate(user.last_login_at):'Never'],['Password change',user?.must_change_password?'Required':'Current']].map(([k,v])=>`<div><span>${k}</span><strong>${esc(v)}</strong></div>`).join('')}<button class="ua-button full-width" data-v5-action="toggle-user-active" data-active="${user?.active?'false':'true'}">${user?.active?'Disable Account':'Enable Account'}</button><button class="ua-button full-width" data-v5-action="unlock-user">Unlock Account</button><hr><p class="muted">Every profile, status and matrix change records the administrator, reason and timestamp.</p></aside></section>`;
    state.v5AdminUser=user;
    if(user?.profile_photo_url)queueMicrotask(()=>v1016HydrateProfilePhoto($('#v1016SelectedAdminPhoto'),user));
  }

  async function renderEventManagementV5(){
    renderLoading('Loading event history…');
    const query=state.selectedPatientId?`?patient_mpi_id=${encodeURIComponent(state.selectedPatientId)}&limit=300`:'?limit=300';
    const [events,patient]=await Promise.all([api(`/event-management${query}`),selectedPatient()]);
    $('#mainContent').innerHTML=`${pageHeader('Audit and Course Correction','Event Management','Cancel, reverse or correct eligible events without deleting the original action or its audit history.',`<button class="btn" data-v5-action="clear-patient-context">Clear patient filter</button>`)}${patient?v5RecordHeader(patient,v5CurrentEncounter(patient),true):'<div class="alert info">Showing enterprise event history. Select a patient to narrow the list.</div>'}<article class="ua-card"><div class="table-wrap"><table class="ua-data-table"><thead><tr><th>Time</th><th>Entity</th><th>Action</th><th>Patient / Encounter</th><th>Status Before</th><th>Status After</th><th>Actor</th><th>Reason</th><th>Correction</th></tr></thead><tbody>${events.map(e=>`<tr><td>${fmtDate(e.occurred_at)}</td><td>${esc(e.entity_type)}<br><small>${esc(e.entity_id)}</small></td><td><strong>${esc(statusLabel(e.action))}</strong></td><td>${e.patient?`<button class="ua-link" data-patient-id="${esc(e.patient.mpi_id)}">${esc(e.patient.full_name)}</button><br><small>${esc(e.encounter_id||'')}</small>`:'—'}</td><td>${esc(statusLabel(e.status_before||'—'))}</td><td>${esc(statusLabel(e.status_after||'—'))}</td><td>${esc(e.actor)}</td><td>${esc(e.reason||'')}</td><td>${e.reversible&&!e.reversed_by_event_id?`<button class="ua-button compact danger-outline" data-v5-action="undo-event" data-event-id="${esc(e.event_id)}">Undo</button>`:e.reversed_by_event_id?'<span class="ua-status checked-in">Reversed</span>':'—'}</td></tr>`).join('')||'<tr><td colspan="9">No managed events.</td></tr>'}</tbody></table></div></article>`;
  }

  async function renderEmergencyV5(){
    renderLoading('Loading emergency department board…');
    const data=await api(`/emergency/board?facility_code=${encodeURIComponent(operationFacility())}`);
    const labels={ARRIVAL:'Arrival / Registration',TRIAGE:'Triage',RESUSCITATION:'Resuscitation',CARE_IN_PROGRESS:'Care in Progress',DISPOSITION:'Disposition'};
    $('#mainContent').innerHTML=`${pageHeader('Emergency Services','Emergency Department Track Board','Arrival, triage, trauma activation, resuscitation, active care, results and disposition with reversible event history.',`<button class="btn btn-primary" data-route="registration">Emergency Registration</button>`)}<section class="v5-ed-board">${Object.entries(data.columns||{}).map(([key,items])=>`<article class="v5-ed-column"><header><h2>${labels[key]}</h2><b>${items.length}</b></header><div>${items.map(e=>`<section class="v5-ed-card acuity-${String(e.acuity||'unknown').toLowerCase()}"><button data-patient-id="${esc(e.patient.mpi_id)}"><strong>${esc(e.patient.full_name)}</strong><small>${esc(e.patient.mrn)} · ${esc(e.patient.sex||'')}</small></button><p>${esc(e.reason_for_visit||'Reason not documented')}</p><div><span class="ua-status ${uaStatusClass(e.status)}">${esc(statusLabel(e.status))}</span><span>${esc(e.acuity||'Acuity pending')}</span></div><small>${minutesSince(e.arrival_at)} min · ${esc(e.location||'ED')}</small><select data-v5-ed-action data-encounter-id="${esc(e.encounter_id)}"><option value="">Change course…</option>${['TRIAGE','TRAUMA_ACTIVATION','MOVE_TO_RESUS','START_CARE','WAITING_RESULTS','READY_FOR_DISPOSITION','ADMIT','TRANSFER','DISCHARGE','LEFT_WITHOUT_BEING_SEEN','UNDO_LAST'].map(a=>`<option value="${a}">${statusLabel(a)}</option>`).join('')}</select></section>`).join('')||'<div class="empty-state"><p>No patients</p></div>'}</div></article>`).join('')}</section>`;
  }

  async function renderSpecialtyV5(route){
    if(!state.selectedPatientId){$('#mainContent').innerHTML=v5EmptyRecordWorkspace(moduleContent[route]?.title||'Specialty Workflow');return;}
    const [patient,data]=await Promise.all([selectedPatient(),api('/specialty-workflows')]); if(!patient){$('#mainContent').innerHTML=v5EmptyRecordWorkspace('Specialty Workflow');return;}
    const code=v5SpecialtyCodes[route]||state.selectedSpecialty||'GENERAL_MEDICINE'; const wf=(data.workflows||[]).find(x=>x.code===code)||data.workflows?.[0]; const encounter=v5CurrentEncounter(patient);
    $('#mainContent').innerHTML=`${pageHeader('Specialty Care',wf?.name||'Specialty Workflow','Patient-specific specialty pathway linked to the same longitudinal chart, orders, results, notes and flowsheets.')}${v5RecordHeader(patient,encounter,true)}<section class="v5-specialty-shell"><article class="ua-card"><div class="ua-card-header"><h2>Pathway Stages</h2></div><div class="v5-stage-ribbon">${(wf?.stages||[]).map((s,i)=>`<button class="${i===0?'active':''}" data-v5-action="specialty-stage"><b>${i+1}</b><span>${esc(s)}</span></button>`).join('')}</div><div class="v5-specialty-workspace"><h3>${esc(wf?.stages?.[0]||'Assessment')}</h3><p>Document the current stage, link findings to the problem list and order specialty-specific tests or treatment.</p><div class="v5-specialty-actions"><button class="patient-action-card blue" data-route="clinical-documentation"><span class="patient-action-icon">${v4Icon('chart')}</span><span><strong>Document</strong><small>Specialty note</small></span></button><button class="patient-action-card orange" data-route="orders"><span class="patient-action-icon">${v4Icon('orders')}</span><span><strong>Orders</strong><small>Specialty order sets</small></span></button><button class="patient-action-card teal" data-route="results"><span class="patient-action-icon">${v4Icon('results')}</span><span><strong>Results</strong><small>Review diagnostics</small></span></button><button class="patient-action-card purple" data-route="flowsheets"><span class="patient-action-icon">${v4Icon('reports')}</span><span><strong>Flowsheets</strong><small>Specialty observations</small></span></button><button class="patient-action-card green" data-route="chart"><span class="patient-action-icon">${v4Icon('patient')}</span><span><strong>Chart Review</strong><small>Longitudinal record</small></span></button><button class="patient-action-card red" data-route="event-management"><span class="patient-action-icon">${v4Icon('audit')}</span><span><strong>Events</strong><small>Cancel / undo history</small></span></button></div></div></article><aside class="ua-card"><h2>Specialty Safety Checklist</h2>${['Identity and encounter verified','Allergies and medication reconciliation reviewed','Relevant diagnostics reviewed','Consent and procedural readiness documented','Follow-up / referral closure assigned'].map((x,i)=>`<div class="checklist-item"><span class="${i<2?'check-good':'check-empty'}">${i<2?'●':'○'}</span><span>${x}</span></div>`).join('')}<hr><h3>Available pathways</h3>${(data.workflows||[]).map(x=>`<button class="v5-pathway-button" data-v5-action="select-specialty" data-specialty-code="${esc(x.code)}">${esc(x.name)}</button>`).join('')}</aside></section>`;
  }

  async function showChangeContextV5(){
    const data=await api('/facilities/context-tree?public_only=true'); state.facilityContextTree=data;
    openModal('Change Facility Context',`<div class="v5-context-toolbar"><input id="contextSearch" placeholder="Search hospital, HFR code, region or council"><span>${data.total} public facility contexts loaded</span></div><div id="contextResults" class="v5-context-results">${data.groups.map(g=>`<section><h3>${esc(g.region)}</h3>${g.facilities.map(f=>`<button data-v5-action="select-facility-context" data-facility-code="${esc(f.code)}"><strong>${esc(f.name)}</strong><small>${esc(f.hierarchy_level||f.facility_type)} · ${esc(f.council||'')} ${f.hfr_code?`· HFR ${esc(f.hfr_code)}`:''}</small></button>`).join('')}</section>`).join('')}</div>`,`<button class="ua-button" data-modal-action="close">Close</button><button class="ua-button" data-v5-action="open-hfr-import">Import Current HFR Export</button>`,'Tanzania Government Health System');
    $('#modal').classList.add('v5-context-modal');
  }

  function showExpirePatientV5(){
    if(!state.selectedPatientId)return toast('Select patient','A patient record is required.');
    openModal('Record Patient Death / Expiry',`<div class="alert danger"><strong>High-consequence workflow:</strong> this changes the longitudinal record to deceased, closes active encounters and creates mortuary/health-record tasks. It remains reversible only through authorized Event Management.</div><div class="form-grid"><label class="field"><span>Date and time</span><input id="expireAt" type="datetime-local" value="${new Date().toISOString().slice(0,16)}"></label><label class="field"><span>Location</span><input id="expireLocation" value="${esc(v5CurrentEncounter(state.v5Patient)?.location||'Hospital ward')}"></label><label class="field full"><span>Cause / clinical circumstances</span><textarea id="expireCause" required>Cause pending medical certification.</textarea></label><label class="field"><span>Death certificate number</span><input id="expireCertificate" placeholder="Optional / pending"></label><label class="field"><span><input id="expireMortuary" type="checkbox" checked> Create mortuary and death-registration work item</span></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button danger" data-v5-action="confirm-expire-patient">Confirm Death Record</button>`,'Patient Status Management');
  }

  function showComposeMessageV5(){
    const recipients=state.v5MessageRecipients||[];
    openModal('New Secure Message',`<div class="form-grid"><label class="field"><span>Recipient</span><select id="msgRecipient">${recipients.map(r=>`<option value="${esc(r.user_id)}">${esc(r.display_name)} · ${esc(statusLabel(r.role_code))}</option>`).join('')}</select></label><label class="field"><span>Priority</span><select id="msgPriority"><option>ROUTINE</option><option>HIGH</option><option>URGENT</option></select></label><label class="field full"><span>Subject</span><input id="msgSubject" value="Clinical / operational follow-up"></label><label class="field full"><span>Patient context (optional)</span><input id="msgPatient" value="${esc(state.selectedPatientId||'')}" readonly></label><label class="field full"><span>Message</span><textarea id="msgBody" required></textarea></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v5-action="send-message">Send Secure Message</button>`,'Secure Messaging');
  }

  function flowsheetEncounterOptions(patient,selectedEncounter){
    const current=selectedEncounter||v5CurrentEncounter(patient);const encounters=[...(patient?.encounters||[])].sort((a,b)=>new Date(b.arrival_at)-new Date(a.arrival_at));
    return `${encounters.map(encounter=>`<option value="${esc(encounter.encounter_id)}" ${encounter.encounter_id===current?.encounter_id?'selected':''}>${encounter.encounter_id===current?.encounter_id?'Current · ':''}${esc(encounter.encounter_id)} · ${esc(encounter.service)} · ${esc(statusLabel(encounter.status))}</option>`).join('')}<option value="">Longitudinal record only (non-inpatient)</option><option value="__NEW__">+ Create a new encounter — number assigned automatically</option>`;
  }
  function flowsheetNewEncounterFields(){
    const facilities=(state.facilities||[]).filter(facility=>facility.active!==false);
    return `<section class="flowsheet-new-encounter hidden" data-new-encounter-fields><div class="alert info"><strong>The system assigns the ENC number.</strong> Choose the clinical context; identifiers cannot be typed or overridden.</div><div class="form-grid"><label class="field"><span>Facility</span><select id="v5FsNewFacility">${facilities.map(facility=>`<option value="${esc(facility.code)}" ${facility.code===operationFacility()?'selected':''}>${esc(facility.name)}</option>`).join('')}</select></label><label class="field"><span>Encounter type</span><select id="v5FsNewType"><option value="OUTPATIENT">Outpatient</option><option value="EMERGENCY">Emergency</option><option value="DAY_CASE">Day case</option><option value="MATERNITY">Maternity</option><option value="TELEHEALTH">Telehealth</option><option value="PROCEDURE">Procedure</option><option value="INPATIENT">Inpatient registration</option></select></label><label class="field"><span>Service</span><input id="v5FsNewService" value="General OPD Clinic" required></label><label class="field full"><span>Reason for visit</span><textarea id="v5FsNewReason" placeholder="Clinical reason or referral context"></textarea></label></div></section>`;
  }
  async function resolveFlowsheetEncounter(patient){
    const value=$('#v5FsEncounter')?.value||'';
    if(value!=='__NEW__')return value||null;
    const service=$('#v5FsNewService')?.value.trim();if(!service)throw new Error('Choose a service for the new encounter.');
    const created=await api(`/patients/${encodeURIComponent(patient.mpi_id)}/encounters`,{method:'POST',body:JSON.stringify({facility_code:$('#v5FsNewFacility').value,encounter_type:$('#v5FsNewType').value,service,reason_for_visit:$('#v5FsNewReason').value.trim()||null,actor:currentRole().user})});
    return created.encounter_id;
  }
  function showCreateTemplateFlowsheetV5(templateCode){
    const patient=state.v5Patient;const encounter=v5CurrentEncounter(patient);const templates=state.v5FlowTemplates||[];const selected=templates.find(t=>t.code===templateCode)||templates[0];
    openModal('Create Patient Flowsheet',`<div class="form-grid"><label class="field full"><span>Template</span><select id="v5FsTemplate">${templates.map(t=>`<option value="${esc(t.code)}" ${t.code===selected?.code?'selected':''}>${esc(t.name)} · ${v5FlattenTemplate(t).length} variables</option>`).join('')}</select></label><label class="field"><span>Patient</span><input id="v5FsPatient" value="${esc(patient?.mpi_id||state.selectedPatientId)}" readonly></label><label class="field"><span>Encounter</span><select id="v5FsEncounter" data-flowsheet-encounter-select>${flowsheetEncounterOptions(patient,encounter)}</select><small>Pick a real encounter or let the system create and number one.</small></label><label class="field"><span>Name</span><input id="v5FsName" value="${esc(selected?.name||'Clinical Flowsheet')}"></label><label class="field"><span>Cadence minutes</span><input id="v5FsCadence" type="number" min="1" value="${selected?.cadence_minutes||60}"></label></div>${flowsheetNewEncounterFields()}<div class="alert warning flowsheet-admit-guidance ${CHART_INPATIENT_TEMPLATES.has(selected?.code)?'':'hidden'}"><strong>Inpatient safety rule:</strong> the selected encounter must have an active “Admit to inpatient service” order.</div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v5-action="confirm-create-template-flowsheet">Create Flowsheet</button>`,'Configurable clinical documentation');
  }

  async function v5RefreshMessageCount(){
    if(!state.token)return; try{const mail=await api('/messages?folder=INBOX&limit=1');if($('#messageCount'))$('#messageCount').textContent=mail.unread||0;}catch(_){}
  }

  function installV5EnhancementHandlers(){
    Object.assign(state,{v5Patient:null,v5FlowTemplates:[],v5MessageRecipients:[]});
    $('#messagesButton')?.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();navigate('messages');},true);
    document.addEventListener('change',async e=>{
      if(e.target.id==='v1016OrderEncounter'){
        const previous=state.v1016OrderEncounterId;state.v1016OrderEncounterId=e.target.value;
        if(previous&&previous!==e.target.value&&state.v1016OrderBasket.length){state.v1016OrderBasket=[];toast('Order basket cleared','The encounter changed, so unsigned orders were cleared to prevent cross-encounter signing.');return renderOrdersV5();}
        return;
      }
      if(e.target.id==='v1016UserPhotoFile'){
        const file=e.target.files?.[0];if(!file)return;
        if(file.size>2*1024*1024){e.target.value='';return toast('Photo too large','Choose a PNG, JPEG or WebP image no larger than 2 MB.');}
        if(!['image/png','image/jpeg','image/webp'].includes(file.type)){e.target.value='';return toast('Unsupported image','Choose a PNG, JPEG or WebP profile photo.');}
        const preview=$('#v1016AdminPhotoPreview');if(preview)preview.innerHTML=`<img src="${URL.createObjectURL(file)}" alt="Selected profile photo preview">`;return;
      }
      if(e.target.id==='chartFlowScope'){filterChartFlowRows();return;}
      if(e.target.id==='v1016FlowEncounterSelect'){state.selectedEncounterId=e.target.value||null;state.selectedFlowSheetId=null;state.v1016ForceNewFlowSheet=false;state.v1016FlowDraftParameters=null;return renderFlowsheetsV5();}
      if(e.target.id==='v1016FlowSheetSelect'){state.selectedFlowSheetId=e.target.value||null;state.v1016ForceNewFlowSheet=!e.target.value;state.v1016FlowDraftParameters=null;return renderFlowsheetsV5();}
      if(e.target.matches('[data-flowsheet-encounter-select]')){const panel=$('[data-new-encounter-fields]');if(panel)panel.classList.toggle('hidden',e.target.value!=='__NEW__');return;}
      if(e.target.id==='v5FsTemplate'){
        const template=(state.v5FlowTemplates||[]).find(item=>item.code===e.target.value);if(template){$('#v5FsName').value=template.name;$('#v5FsCadence').value=template.cadence_minutes||15;}
        $('.flowsheet-admit-guidance')?.classList.toggle('hidden',!CHART_INPATIENT_TEMPLATES.has(e.target.value));return;
      }
      const ed=e.target.closest('[data-v5-ed-action]'); if(ed&&ed.value){const action=ed.value;ed.value='';try{await api(`/emergency/encounters/${encodeURIComponent(ed.dataset.encounterId)}/events`,{method:'POST',body:JSON.stringify({action,actor:currentRole().user,note:`${statusLabel(action)} from ED track board`})});toast('ED event recorded',statusLabel(action));renderEmergencyV5();}catch(err){toast('ED action failed',err.message);}return;}
    },true);
    document.addEventListener('input',async e=>{
      if(e.target.id==='orderCatalogSearch'){v1016QueueOrderSearch(e.target.value);return;}
      if(e.target.id==='contextSearch'&&state.facilityContextTree){const q=e.target.value.toLowerCase();$$('[data-facility-code]','#contextResults').forEach(b=>b.style.display=b.textContent.toLowerCase().includes(q)?'':'none');}
      if(e.target.id==='matrixSearch'){$$('.v5-matrix-cell').forEach(x=>x.style.display=x.textContent.toLowerCase().includes(e.target.value.toLowerCase())?'':'none');}
      if(e.target.id==='adminUserSearch'){$$('.v5-admin-users > button').forEach(x=>x.style.display=x.textContent.toLowerCase().includes(e.target.value.toLowerCase())?'':'none');}
      if(e.target.id==='stationPatientSearch'){$$('.v5-patient-list > button').forEach(x=>x.style.display=x.textContent.toLowerCase().includes(e.target.value.toLowerCase())?'':'none');}
      if(e.target.id==='messageSearch'){$$('.v5-mail-row').forEach(x=>x.style.display=x.textContent.toLowerCase().includes(e.target.value.toLowerCase())?'':'none');}
      if(e.target.id==='chartFlowSearch')filterChartFlowRows();
      if(e.target.id==='v1016FlowVariableSearch'){const query=e.target.value.trim().toLowerCase();$$('[data-flow-variable-option]').forEach(option=>option.hidden=query&&!option.textContent.toLowerCase().includes(query));}
    });
    document.addEventListener('click',async e=>{
      const button=e.target.closest('[data-v5-action]'); if(!button)return;
      const action=button.dataset.v5Action;e.preventDefault();e.stopImmediatePropagation();
      try{
        if(action==='clear-patient-context'){state.selectedPatientId=null;state.selectedFlowSheetId=null;saveState();toast('Patient chart closed','Clinical functions are locked until another patient is selected.');return navigate('patient-search');}
        if(action==='switch-workspace'){state[button.dataset.workspaceAttr]=button.dataset.value;return state.route==='registration'?renderRegistrationV5():renderPatientStationV5();}
        if(action==='refresh-station')return renderPatientStationV5();
        if(action==='registration-lookup'){const q=$('#regLookup').value.trim();if(!q)return;const results=await api(`/patients?search=${encodeURIComponent(q)}&limit=20`);$('#regLookupResults').innerHTML=results.length?results.map(p=>`<button data-patient-id="${esc(p.mpi_id)}"><strong>${esc(p.full_name)}</strong><small>${esc(p.mrn)} · ${esc(p.phone||'')} · ${esc(p.nida_number||'No NIDA')}</small></button>`).join(''):'<div class="alert info">No matching identity found. Continue through demographics to create a patient.</div>';return;}
        if(action==='save-registration'){
          if(state.selectedPatientId){const payload={first_name:$('#regFirst')?.value||undefined,middle_name:$('#regMiddle')?.value||null,last_name:$('#regLast')?.value||undefined,date_of_birth:$('#regDob')?.value||null,sex:$('#regSex')?.value||undefined,phone:$('#regPhone')?.value||null,nida_number:$('#regNida')?.value||null,address:$('#regAddress')?.value||null,region:$('#regRegion')?.value||null,next_of_kin:$('#regNok')?.value||null,payer:$('#regPayer')?.value||null,member_number:$('#regMember')?.value||null,consent_status:$('#regConsent')?.value||null,actor:currentRole().user};await api(`/patients/${encodeURIComponent(state.selectedPatientId)}`,{method:'PATCH',body:JSON.stringify(payload)});toast('Registration updated','Demographic, coverage and consent changes were saved and audited.');return renderRegistrationV5();}
          const payload={facility_code:operationFacility(),registration_mode:$('#regMode')?.value||'STANDARD',first_name:$('#regFirst')?.value||'Unknown',middle_name:$('#regMiddle')?.value||null,last_name:$('#regLast')?.value||'Patient',date_of_birth:$('#regDob')?.value||'2000-01-01',sex:$('#regSex')?.value||'Unknown',phone:$('#regPhone')?.value||null,nida_number:$('#regNida')?.value||null,address:$('#regAddress')?.value||null,region:$('#regRegion')?.value||null,district:null,next_of_kin:$('#regNok')?.value||null,payer:$('#regPayer')?.value||'Cash',member_number:$('#regMember')?.value||null,consent_status:$('#regConsent')?.value||'PENDING',proxy_name:$('#regProxy')?.value||null,encounter_type:$('#regEncounterType')?.value||'OUTPATIENT',service:$('#regService')?.value||'General OPD Clinic',reason_for_visit:$('#regReason')?.value||'Clinical assessment',force_create:false};
          const result=await api('/registration',{method:'POST',body:JSON.stringify(payload)});state.selectedPatientId=result.patient.mpi_id;saveState();toast('Patient registered',`MRN ${result.patient.mrn} was assigned automatically.`);return navigate('patient-station',{preservePatient:true});
        }
        if(action==='station-action'){const op=button.dataset.stationAction;if(op==='chart')return navigate('chart');if(op==='registration')return navigate('registration');if(op==='events')return navigate('event-management');if(op==='discharge'){const encounter=v5CurrentEncounter(state.v5Patient);return encounter?showDischargeModal(encounter.encounter_id):toast('No active encounter','There is no active encounter to discharge.');}if(op==='transfer')return toast('Transfer workflow','Select destination facility, unit, bed and receiving service.');if(op==='print')return toast('Print workflow','Forms, labels, wristbands and encounter summaries are ready.');if(op==='benefit')return toast('Coverage check','NHIF / payer eligibility request queued.');if(op==='team')return toast('Care team','On-duty roster and patient-specific care team assignment opened.');if(op==='scan')return toast('Document capture','Scanner, camera and upload acquisition workflow opened.');}
        if(action==='open-flow-columns'){const context=state.v1016FlowContext;if(!context)throw new Error('Reload the flowsheet workspace.');if(!context.canEdit)throw new Error('This encounter or flowsheet is review-only. Start a new open flowsheet to change columns.');state.v1016FlowColumnDraft=context.variables.map(item=>item.label);return v1016FlowColumnModal();}
        if(action==='flow-column-add'){if(!state.v1016FlowColumnDraft.includes(button.dataset.variable))state.v1016FlowColumnDraft.push(button.dataset.variable);return v1016FlowColumnModal();}
        if(action==='flow-column-remove'){state.v1016FlowColumnDraft.splice(Number(button.dataset.index),1);return v1016FlowColumnModal();}
        if(action==='flow-column-left'||action==='flow-column-right'){const from=Number(button.dataset.index),to=action==='flow-column-left'?from-1:from+1;if(to>=0&&to<state.v1016FlowColumnDraft.length){const [item]=state.v1016FlowColumnDraft.splice(from,1);state.v1016FlowColumnDraft.splice(to,0,item);}return v1016FlowColumnModal();}
        if(action==='save-flow-columns'){const context=state.v1016FlowContext,parameters=state.v1016FlowColumnDraft.filter(Boolean);if(!context?.canEdit)throw new Error('This flowsheet is review-only.');if(!parameters.length)throw new Error('Keep at least one flowsheet column.');if(context.sheet){await api(`/flowsheets/${encodeURIComponent(context.sheet.flowsheet_id)}/actions`,{method:'POST',body:JSON.stringify({action:'CHANGE',actor:currentRole().user,note:'Flowsheet columns reordered or changed from the permanent grid',parameters})});state.v1016FlowDraftParameters=null;}else state.v1016FlowDraftParameters=parameters;closeModal();toast('Column layout saved',`${parameters.length} variable columns are ready.`);return renderFlowsheetsV5();}
        if(action==='apply-flow-preset'){const context=state.v1016FlowContext;if(!context?.canEdit)throw new Error('This flowsheet is review-only.');const template=context.templates.find(item=>item.code===$('#v1016FlowPreset').value);if(!template)throw new Error('Select a flowsheet template.');if(CHART_INPATIENT_TEMPLATES.has(template.code)&&!context.admitted)throw new Error('An active admit order is required before applying an inpatient template.');const parameters=v5FlattenTemplate(template).map(item=>item.label);if(context.sheet){await api(`/flowsheets/${encodeURIComponent(context.sheet.flowsheet_id)}/actions`,{method:'POST',body:JSON.stringify({action:'CHANGE',actor:currentRole().user,note:`Applied ${template.name} column preset`,cadence_minutes:template.cadence_minutes||15,parameters})});state.v1016FlowDraftParameters=null;}else state.v1016FlowDraftParameters=parameters;toast('Template applied',`${template.name} configured ${parameters.length} columns.`);return renderFlowsheetsV5();}
        if(action==='save-flow-row'){const context=state.v1016FlowContext;if(!context?.canEdit)throw new Error('This encounter or flowsheet is review-only.');if(!context.encounter)throw new Error('Select an open encounter before charting.');const inputs=$$('[data-v1016-flow-input]').filter(input=>!input.disabled&&String(input.value||'').trim());if(!inputs.length)throw new Error('Enter at least one flowsheet value.');const parameters=context.variables.map(item=>item.label),sheet=await v1016EnsureFlowSheet(context,parameters);for(const input of inputs)await api(`/flowsheets/${encodeURIComponent(sheet.flowsheet_id)}/observations`,{method:'POST',body:JSON.stringify({parameter:input.dataset.flowVariable,value:String(input.value).trim(),unit:input.dataset.unit||null,source:'MANUAL',recorded_by:currentRole().user})});toast('Flowsheet row saved',`${inputs.length} value${inputs.length===1?'':'s'} recorded for ${context.encounter.encounter_id}.`);return renderFlowsheetsV5();}
        if(action==='search-order-catalog'){state.orderCatalogSearch=$('#orderCatalogSearch')?.value.trim()||'';return renderOrdersV5();}
        if(action==='order-mode'){state.v1016OrderMode=button.dataset.mode;state.orderCatalogCategory='';return renderOrdersV5();}
        if(action==='order-category'){state.orderCatalogCategory=button.dataset.category;return renderOrdersV5();}
        if(action==='select-orderable'||action==='quick-add-order'){state.selectedOrderable=v1016FindOrderable(button.dataset.orderableCode)||null;return renderOrdersV5();}
        if(action==='favorite-orderable'){
          const item=v1016FindOrderable(button.dataset.orderableCode);if(!item)throw new Error('Orderable is no longer available.');
          const index=state.v1016OrderFavorites.findIndex(x=>x.orderable_code===item.orderable_code);if(index>=0)state.v1016OrderFavorites.splice(index,1);else state.v1016OrderFavorites.unshift({...item});v1016SaveOrderShortcuts();return renderOrdersV5();
        }
        if(action==='add-order-basket'){
          const item=state.selectedOrderable;if(!item)throw new Error('Select an orderable first.');const payload=v1016OrderComposerPayload(item);if(!payload.encounter_id)throw new Error('An active encounter is required.');
          if(state.v1016OrderBasket.some(x=>x.orderable_code===item.orderable_code))throw new Error('This order is already in the basket. Remove it before composing a replacement.');
          state.v1016OrderBasket.push({...item,...payload});state.v1016OrderRecents=[{...item},...state.v1016OrderRecents.filter(x=>x.orderable_code!==item.orderable_code)].slice(0,20);v1016SaveOrderShortcuts();toast('Added to basket',`${item.display_name} is ready for review.`);return renderOrdersV5();
        }
        if(action==='remove-order-basket'){state.v1016OrderBasket.splice(Number(button.dataset.index),1);return renderOrdersV5();}
        if(action==='clear-order-basket'){state.v1016OrderBasket=[];return renderOrdersV5();}
        if(action==='add-order-set'){
          const set=state.v1016OrderSets.find(x=>x.set_code===button.dataset.orderSetCode);if(!set)throw new Error('Order panel not found.');const encounterId=state.v1016OrderEncounterId||v1014OpenEncounter(state.v5Patient)?.encounter_id;if(!encounterId)throw new Error('Start or select an active encounter before adding an order panel.');
          let added=0;for(const item of set.items.filter(x=>x.selected_by_default||x.required)){if(state.v1016OrderBasket.some(x=>x.orderable_code===item.orderable_code))continue;state.v1016OrderBasket.push({...item,encounter_id:encounterId,priority:item.default_priority||'ROUTINE',indication:item.default_indication||null,instructions:item.default_instructions||null,details:item.details||{},ordered_by:currentRole().user,order_set_code:set.set_code});added++;}
          toast('Order panel added',`${added} ${set.name} order${added===1?'':'s'} added for review.`);return renderOrdersV5();
        }
        if(action==='review-order-basket'){
          const basket=state.v1016OrderBasket;if(!basket.length)throw new Error('The order basket is empty.');const encounterIds=new Set(basket.map(x=>x.encounter_id));if(encounterIds.size!==1)throw new Error('A signing session must contain orders for one encounter.');
          openModal('Review and Sign Orders',`<section class="v1016-sign-review"><div class="alert warning"><strong>Final clinical review:</strong> confirm the patient, encounter, allergies, indications, doses and routing before signing.</div>${basket.map((item,index)=>`<article><span>${index+1}</span><div><strong>${esc(item.display_name)}</strong><small>${esc(item.priority)} · ${esc(statusLabel(item.category))} · ${esc(item.encounter_id)}</small>${item.indication?`<p>${esc(item.indication)}</p>`:''}</div></article>`).join('')}<label class="field"><span>Signing attestation</span><input id="v1016OrderSignReason" value="Reviewed patient, encounter, allergies, indications and order details"></label></section>`,`<button class="ua-button" data-modal-action="close">Return to basket</button><button class="ua-button primary" data-v5-action="sign-order-basket">Sign & Route ${basket.length} Orders</button>`,'CPOE safety review');return;
        }
        if(action==='sign-order-basket'){
          const basket=state.v1016OrderBasket,result=await api('/orders/batch',{method:'POST',body:JSON.stringify({orders:basket.map(item=>({encounter_id:item.encounter_id,orderable_code:item.orderable_code,priority:item.priority,indication:item.indication,instructions:item.instructions,details:item.details||{},ordered_by:currentRole().user})),order_set_code:[...new Set(basket.map(x=>x.order_set_code).filter(Boolean))].join(',')||null,sign_reason:$('#v1016OrderSignReason')?.value.trim()||null})});state.v1016OrderBasket=[];closeModal();toast('Orders signed and routed',`${result.count} order${result.count===1?'':'s'} committed atomically to the selected encounter.`);return renderOrdersV5();
        }
        if(action==='open-custom-orderable'){
          openModal('Create Governed Orderable',`<div class="form-grid"><label class="field full"><span>Display name</span><input id="v1016CustomOrderName" placeholder="Clear clinician-facing order name"></label><label class="field"><span>Category</span><select id="v1016CustomOrderCategory">${['LABORATORY','MEDICATION','IMAGING','BLOOD_BANK','PROCEDURE','CONSULT','NURSING','RESPIRATORY','DIET','ACTIVITY','ADT','REFERRAL','TRANSPORT','EVS','EQUIPMENT','ADMINISTRATIVE'].map(x=>`<option>${x}</option>`).join('')}</select></label><label class="field"><span>Type</span><select id="v1016CustomOrderClinical"><option value="true">Clinical</option><option value="false">Operational / non-clinical</option></select></label><label class="field"><span>Department</span><input id="v1016CustomOrderDepartment" placeholder="Responsible department"></label><label class="field"><span>Synonyms</span><input id="v1016CustomOrderSynonyms" placeholder="Search terms, abbreviations"></label><label class="field"><span>Default priority</span><select id="v1016CustomOrderPriority"><option>ROUTINE</option><option>URGENT</option><option>STAT</option></select></label><label class="field"><span>Specimen / route</span><input id="v1016CustomOrderSpecimen" placeholder="Specimen or medication route"></label><label class="field full"><span>Default instructions</span><textarea id="v1016CustomOrderInstructions"></textarea></label><label class="field full"><span>Clinical governance reason</span><textarea id="v1016CustomOrderReason" placeholder="Approval, source and intended workflow"></textarea></label><label class="v1016-check"><input id="v1016CustomOrderRequiresReason" type="checkbox" checked> Require an indication / reason</label><label class="v1016-check"><input id="v1016CustomOrderRequiresCosign" type="checkbox"> Require cosign</label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v5-action="create-custom-orderable">Approve & Create</button>`,'Configuration administrator · audited');return;
        }
        if(action==='create-custom-orderable'){
          const category=$('#v1016CustomOrderCategory').value,payload={display_name:$('#v1016CustomOrderName').value.trim(),category,clinical:$('#v1016CustomOrderClinical').value==='true',department:$('#v1016CustomOrderDepartment').value.trim()||null,synonyms:$('#v1016CustomOrderSynonyms').value.trim()||null,default_priority:$('#v1016CustomOrderPriority').value,default_instructions:$('#v1016CustomOrderInstructions').value.trim()||null,specimen:category==='LABORATORY'?$('#v1016CustomOrderSpecimen').value.trim()||null:null,route:category==='MEDICATION'?$('#v1016CustomOrderSpecimen').value.trim()||null:null,requires_reason:$('#v1016CustomOrderRequiresReason').checked,requires_cosign:$('#v1016CustomOrderRequiresCosign').checked,governance_reason:$('#v1016CustomOrderReason').value.trim()};
          const created=await api('/order-catalog',{method:'POST',body:JSON.stringify(payload)});closeModal();state.orderCatalogSearch=created.display_name;state.orderCatalogCategory='';state.v1016OrderMode='catalog';state.selectedOrderable=created;toast('Orderable approved',`${created.display_name} is now available in the governed catalog.`);return renderOrdersV5();
        }
        if(action==='open-order-set-builder'){
          if(!state.v1016OrderBasket.length)throw new Error('Add orders to the basket before saving a panel.');openModal('Create Custom Order Panel',`<div class="form-grid"><label class="field full"><span>Panel name</span><input id="v1016SetName" placeholder="e.g. Cardiology admission — local"></label><label class="field"><span>Specialty / service</span><input id="v1016SetSpecialty" placeholder="Clinical service"></label><label class="field"><span>Encounter types</span><input id="v1016SetEncounterTypes" value="OUTPATIENT, EMERGENCY, INPATIENT"></label><label class="field full"><span>Description</span><textarea id="v1016SetDescription" placeholder="Intended patients and exclusions"></textarea></label><div class="field full v1016-panel-preview"><span>Orders in panel</span>${state.v1016OrderBasket.map(x=>`<small>• ${esc(x.display_name)} · ${esc(x.priority)}</small>`).join('')}</div><label class="field full"><span>Clinical governance reason / approval</span><textarea id="v1016SetReason" placeholder="Approved use, source and review context"></textarea></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v5-action="create-order-set">Approve & Save Panel</button>`,'Configuration administrator · versioned content');return;
        }
        if(action==='create-order-set'){
          const payload={name:$('#v1016SetName').value.trim(),specialty:$('#v1016SetSpecialty').value.trim()||null,encounter_types:$('#v1016SetEncounterTypes').value.split(',').map(x=>x.trim().toUpperCase()).filter(Boolean),description:$('#v1016SetDescription').value.trim()||null,governance_reason:$('#v1016SetReason').value.trim(),items:state.v1016OrderBasket.map(item=>({orderable_code:item.orderable_code,selected_by_default:true,required:false,default_priority:item.priority,default_indication:item.indication,default_instructions:item.instructions,details:item.details||{}}))};
          const created=await api('/order-sets',{method:'POST',body:JSON.stringify(payload)});closeModal();state.v1016OrderMode='sets';toast('Order panel approved',`${created.name} v${created.version} is available to authorized ordering users.`);return renderOrdersV5();
        }
        if(action==='order-course'){openModal(`${statusLabel(button.dataset.course)} Order`,`<label class="field"><span>Reason</span><textarea id="v5OrderCourseReason" required></textarea></label>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v5-action="confirm-order-course-v5" data-order-id="${esc(button.dataset.orderId)}" data-course="${esc(button.dataset.course)}">Confirm</button>`,'Order Event Management');return;}
        if(action==='confirm-order-course-v5'){const reason=$('#v5OrderCourseReason').value.trim();if(!reason)throw new Error('Reason required.');await api(`/orders/${button.dataset.orderId}/actions`,{method:'POST',body:JSON.stringify({action:button.dataset.course,reason,actor:currentRole().user})});closeModal();toast('Order course changed',statusLabel(button.dataset.course));return renderOrdersV5();}
        if(action==='create-template-flowsheet'){return showCreateTemplateFlowsheetV5(button.dataset.templateCode);}
        if(action==='confirm-create-template-flowsheet'){const template=(state.v5FlowTemplates||[]).find(t=>t.code===$('#v5FsTemplate').value);const patient=state.v5Patient||await selectedPatient();const encounterId=await resolveFlowsheetEncounter(patient);const result=await api('/flowsheets',{method:'POST',body:JSON.stringify({patient_mpi_id:patient.mpi_id,encounter_id:encounterId,name:$('#v5FsName').value,template_code:$('#v5FsTemplate').value,cadence_minutes:Number($('#v5FsCadence').value),parameters:v5FlattenTemplate(template).map(row=>row.label),owner:currentRole().user})});state.selectedPatientId=patient.mpi_id;state.selectedFlowSheetId=result.flowsheet_id;closeModal();toast('Flowsheet created',`${result.name} · ${result.encounter_id||'longitudinal record'}`);return state.route==='chart'?renderChart():renderFlowsheetsV5();}
        if(action==='flowsheet-control'){const course=button.dataset.course;if(course==='CHANGE'){openModal('Edit Flowsheet Variables',`<div class="form-grid"><label class="field"><span>Flowsheet name</span><input id="v5ChangeName" value="${esc(state.v5FlowSheet?.name||'')}"></label><label class="field"><span>Cadence minutes</span><input id="v5ChangeCadence" type="number" min="1" value="${state.v5FlowSheet?.cadence_minutes||60}"></label><label class="field full"><span>Variables — one per line</span><textarea id="v5ChangeParameters" rows="10">${esc((state.v5FlowSheet?.parameters||[]).join('\n'))}</textarea><small>Variables can be added, renamed, reordered or removed. Existing observations remain in the legal record.</small></label><label class="field full"><span>Reason for change</span><textarea id="v5ChangeReason">Clinical monitoring plan updated.</textarea></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v5-action="confirm-flowsheet-change">Save Variables</button>`,'Audited Flowsheet Change');return;}await api(`/flowsheets/${state.selectedFlowSheetId}/actions`,{method:'POST',body:JSON.stringify({action:course,actor:currentRole().user,note:`${statusLabel(course)} from patient chart`})});toast('Flowsheet updated',statusLabel(course));return renderFlowsheetsV5();}
        if(action==='confirm-flowsheet-change'){const parameters=$('#v5ChangeParameters').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);if(!parameters.length)throw new Error('Keep at least one flowsheet variable.');await api(`/flowsheets/${state.selectedFlowSheetId}/actions`,{method:'POST',body:JSON.stringify({action:'CHANGE',actor:currentRole().user,note:$('#v5ChangeReason').value,cadence_minutes:Number($('#v5ChangeCadence').value),name:$('#v5ChangeName').value.trim()||null,parameters})});closeModal();toast('Flowsheet variables updated',`${parameters.length} variables are now active; prior observations were retained.`);return renderFlowsheetsV5();}
        if(action==='save-flowsheet-column'){const inputs=$$('.v5-flow-input').filter(i=>i.value.trim());if(!inputs.length)throw new Error('Enter at least one observation.');for(const input of inputs)await api(`/flowsheets/${state.selectedFlowSheetId}/observations`,{method:'POST',body:JSON.stringify({parameter:input.dataset.flowRow,value:input.value,unit:input.dataset.unit||null,source:'MANUAL',recorded_by:currentRole().user})});toast('Flowsheet saved',`${inputs.length} observations recorded.`);return renderFlowsheetsV5();}
        if(action==='test-device-ingest'){const patient=await selectedPatient();const encounter=v5CurrentEncounter(patient);if(!encounter||!state.selectedFlowSheetId)throw new Error('Active encounter and flowsheet required.');await api(`/devices/${encodeURIComponent(button.dataset.deviceId)}/observations`,{method:'POST',body:JSON.stringify({patient_mpi_id:patient.mpi_id,encounter_id:encounter.encounter_id,flowsheet_id:state.selectedFlowSheetId,actor:'Interface Engine',readings:[{parameter_code:'HR',parameter_name:'Heart rate',numeric_value:82,unit:'bpm',quality:'VALID',source_message_id:`TEST-${Date.now()}`},{parameter_code:'SPO2',parameter_name:'Oxygen saturation',numeric_value:97,unit:'%',quality:'VALID',source_message_id:`TEST-${Date.now()}-2`} ]})});toast('Device observations ingested','Validated readings were written to the selected chart flowsheet.');return renderFlowsheetsV5();}
        if(action==='select-bed-unit'){state.selectedBedUnit=button.dataset.unit;return renderBedBoardV5();}
        if(action==='bed-actions'){const status=button.dataset.bedStatus;const actions=status==='AVAILABLE'?['ASSIGN','BLOCK']:status==='OCCUPIED'?['MARK_DIRTY','BLOCK']:['MARK_AVAILABLE','START_CLEANING','UNBLOCK'];openModal('Bed Actions',`<div class="form-grid"><label class="field"><span>Action</span><select id="v5BedAction">${actions.map(x=>`<option>${x}</option>`).join('')}</select></label><label class="field"><span>Encounter ID (for assignment)</span><input id="v5BedEncounter"></label><label class="field full"><span>Reason</span><textarea id="v5BedReason">Unit manager action.</textarea></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v5-action="confirm-bed-action" data-bed-id="${esc(button.dataset.bedId)}">Apply</button>`,'Unit Manager');return;}
        if(action==='confirm-bed-action'){await api(`/beds/${button.dataset.bedId}/actions`,{method:'POST',body:JSON.stringify({action:$('#v5BedAction').value,encounter_id:$('#v5BedEncounter').value||null,actor:currentRole().user,reason:$('#v5BedReason').value})});closeModal();return renderBedBoardV5();}
        if(action==='create-user')return showUserModal();
        if(action==='select-admin-user'){state.selectedAdminUserId=button.dataset.userId;return renderSystemAdminV5();}
        if(action==='admin-matrix-scope'){state.adminMatrixScope=button.dataset.scope;return renderSystemAdminV5();}
        if(action==='matrix-toggle-all'){$$(`[data-v5-matrix-scope="${state.adminMatrixScope}"]`).forEach(x=>x.checked=button.dataset.checked==='true');return;}
        if(action==='save-user-matrix'){const user=state.v5AdminUser;const values=$$(`[data-v5-matrix-scope="${state.adminMatrixScope}"]:checked`).map(x=>x.value);if(!values.length&&state.adminMatrixScope!=='departments')throw new Error('Select at least one item.');const payload={actor:currentRole().user,access_reason:$('#matrixReason').value};payload[state.adminMatrixScope==='functions'?'function_codes':state.adminMatrixScope==='departments'?'department_codes':state.adminMatrixScope==='countries'?'country_codes':'facility_codes']=values;await api(`/admin/users/${user.user_id}`,{method:'PATCH',body:JSON.stringify(payload)});toast('Access matrix saved',`${values.length} ${state.adminMatrixScope} assigned.`);return renderSystemAdminV5();}
        if(action==='manage-user-photo')return v1016ManageUserPhoto(state.v5AdminUser);
        if(action==='upload-user-photo'){
          const file=$('#v1016UserPhotoFile')?.files?.[0];if(!file)throw new Error('Choose a PNG, JPEG or WebP profile photo first.');
          const body=new FormData();body.append('photo',file,file.name);body.append('reason',$('#v1016UserPhotoReason')?.value.trim()||'Authorized workforce profile update');
          const updated=await api(`/admin/users/${encodeURIComponent(button.dataset.userId)}/profile-photo`,{method:'POST',body});
          if(updated.user_id===state.account?.user_id){state.account={...state.account,profile_photo_url:updated.profile_photo_url};updateChrome();}
          closeModal();toast('Profile photo updated',`${updated.display_name}'s photo was assigned by an administrator and audited.`);return renderSystemAdminV5();
        }
        if(action==='remove-user-photo'){
          const reason=$('#v1016UserPhotoReason')?.value.trim()||'Authorized workforce profile photo removal';
          const updated=await api(`/admin/users/${encodeURIComponent(button.dataset.userId)}/profile-photo?reason=${encodeURIComponent(reason)}`,{method:'DELETE'});
          if(updated.user_id===state.account?.user_id){state.account={...state.account,profile_photo_url:null};$('#userAvatar').src='/assets/avatars/neema-k.png';}
          closeModal();toast('Profile photo removed',`${updated.display_name} now uses initials until an administrator assigns a new photo.`);return renderSystemAdminV5();
        }
        if(action==='edit-user-profile')return showUserModal(state.v5AdminUser);
        if(action==='reset-user-password'){const password=generatedPassword();await api(`/admin/users/${state.v5AdminUser.user_id}/reset-password`,{method:'POST',body:JSON.stringify({password,actor:currentRole().user})});return showUserCreatedModal(state.v5AdminUser,password);}
        if(action==='toggle-user-active'){await api(`/admin/users/${state.v5AdminUser.user_id}`,{method:'PATCH',body:JSON.stringify({active:button.dataset.active==='true',actor:currentRole().user,access_reason:'Account status administration'})});return renderSystemAdminV5();}
        if(action==='unlock-user'){await api(`/admin/users/${state.v5AdminUser.user_id}/unlock`,{method:'POST',body:JSON.stringify({actor:currentRole().user,access_reason:'Authorized account unlock'})});toast('Account unlocked','Failed login counter and lockout cleared.');return renderSystemAdminV5();}
        if(action==='compose-message')return showComposeMessageV5();
        if(action==='message-folder'){state.messageFolder=button.dataset.folder;state.selectedMessageId=null;return renderMessages();}
        if(action==='open-message'){state.selectedMessageId=button.dataset.messageId;await api(`/messages/${button.dataset.messageId}`,{method:'PATCH',body:JSON.stringify({action:'READ'})});return renderMessages();}
        if(action==='message-action'){await api(`/messages/${button.dataset.messageId}`,{method:'PATCH',body:JSON.stringify({action:button.dataset.messageAction})});return renderMessages();}
        if(action==='send-message'){await api('/messages',{method:'POST',body:JSON.stringify({recipient_user_id:$('#msgRecipient').value,subject:$('#msgSubject').value,body:$('#msgBody').value,priority:$('#msgPriority').value,patient_mpi_id:$('#msgPatient').value||null})});closeModal();toast('Message sent','Secure internal message delivered.');return renderMessages();}
        if(action==='change-context')return showChangeContextV5();
        if(action==='select-facility-context'){state.facility=button.dataset.facilityCode;saveState();closeModal();renderFacilitySelect();toast('Context changed',`Facility context changed to ${button.dataset.facilityCode}.`);return render();}
        if(action==='open-hfr-import')return toast('HFR import endpoint ready','Use POST /api/facilities/import-hfr with the approved current HFR export.');
        if(action==='expire-patient')return showExpirePatientV5();
        if(action==='confirm-expire-patient'){await api(`/patients/${encodeURIComponent(state.selectedPatientId)}/expire`,{method:'POST',body:JSON.stringify({deceased_at:new Date($('#expireAt').value).toISOString(),location:$('#expireLocation').value,cause:$('#expireCause').value,death_certificate_number:$('#expireCertificate').value||null,actor:currentRole().user,notify_mortuary:$('#expireMortuary').checked})});closeModal();toast('Death recorded','The record, encounters and follow-up tasks were updated with event history.');return renderPatientStationV5();}
        if(action==='open-event-history')return navigate('event-management');
        if(action==='undo-event'){openModal('Undo Managed Event',`<label class="field"><span>Reason for correction</span><textarea id="v5UndoReason" required></textarea></label>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button danger" data-v5-action="confirm-undo-event" data-event-id="${esc(button.dataset.eventId)}">Undo Event</button>`,'Authorized Event Correction');return;}
        if(action==='confirm-undo-event'){await api(`/event-management/${button.dataset.eventId}/undo`,{method:'POST',body:JSON.stringify({actor:currentRole().user,reason:$('#v5UndoReason').value})});closeModal();toast('Event reversed','Original event retained and reversal recorded.');return renderEventManagementV5();}
        if(action==='select-specialty'){state.selectedSpecialty=button.dataset.specialtyCode;const route=Object.keys(v5SpecialtyCodes).find(k=>v5SpecialtyCodes[k]===state.selectedSpecialty)||'maternity';return renderSpecialtyV5(route);}
        if(action==='specialty-stage'){$$('.v5-stage-ribbon button').forEach(x=>x.classList.remove('active'));button.classList.add('active');return;}
      }catch(err){console.error(err);toast('Action failed',err.message);}
    },true);
    setInterval(v5RefreshMessageCount,APP_REFRESH_INTERVAL_MS); v5RefreshMessageCount();
  }

  const v5OriginalRender=render;
  render=async function(){
    const route=state.route;
    if(v5NeedsRecord(route)&&!state.selectedPatientId){$('#mainContent').innerHTML=v5EmptyRecordWorkspace(moduleContent[route]?.title||statusLabel(route));return;}
    try{
      if(route==='patient-station')await renderPatientStationV5();
      else if(route==='registration')await renderRegistrationV5();
      else if(route==='orders')await renderOrdersV5();
      else if(route==='flowsheets')await renderFlowsheetsV5();
      else if(route==='bed-board')await renderBedBoardV5();
      else if(route==='admin')await renderSystemAdminV5();
      else if(route==='messages')await renderMessages();
      else if(route==='event-management')await renderEventManagementV5();
      else if(route==='emergency')await renderEmergencyV5();
      else if(v5SpecialtyCodes[route])await renderSpecialtyV5(route);
      else await v5OriginalRender();
      state.v5Patient=await selectedPatient();
      document.body.classList.toggle('patient-context-active',Boolean(state.selectedPatientId));
      $$('[data-route]').forEach(el=>{const locked=v5NeedsRecord(el.dataset.route)&&!state.selectedPatientId;el.classList.toggle('record-locked',locked);if(locked)el.setAttribute('title','Select a patient chart first');});
    }catch(error){console.error(error);$('#mainContent').innerHTML=`${pageHeader('Application Error','Unable to load workspace','The requested workspace could not be retrieved.')}<div class="alert danger"><strong>${esc(error.message)}</strong><br>Verify the backend, migration and seeded data, then retry.</div>`;}
  };


  // ===== v6 front-desk workflow corrections =====
  state.todayDay = state.todayDay || 'today';
  state.todayFilters = state.todayFilters || {search:'',service:'',clinic:'',queue:'',status:''};
  state.walkInDraft = null;

  function v6IsoDay(offset=0){
    const d=new Date(); d.setHours(12,0,0,0); d.setDate(d.getDate()+offset);
    return d.toISOString().slice(0,10);
  }
  function v6DayForTab(tab){return tab==='yesterday'?v6IsoDay(-1):tab==='tomorrow'?v6IsoDay(1):v6IsoDay(0);}
  function v6Unique(values){return [...new Set(values.filter(Boolean))].sort((a,b)=>String(a).localeCompare(String(b)));}
  function v6Option(value,label,selected=''){return `<option value="${esc(value)}" ${String(value)===String(selected)?'selected':''}>${esc(label)}</option>`;}
  function v6TodayRows(rows){
    const f=state.todayFilters||{};
    return rows.filter(r=>{
      const hay=[r.patient?.full_name,r.patient?.mrn,r.patient?.mpi_id,r.patient?.phone,r.service,r.queue,r.status,r.on_duty_team].join(' ').toLowerCase();
      if(f.search && !hay.includes(f.search.toLowerCase())) return false;
      if(f.service && r.service!==f.service) return false;
      if(f.clinic && r.service!==f.clinic) return false;
      if(f.queue && (r.queue||'')!==f.queue) return false;
      if(f.status && String(r.status).toUpperCase()!==f.status.toUpperCase()) return false;
      return true;
    });
  }
  async function v6LoadTodayData(){
    const facility=operationFacility();
    const day=v6DayForTab(state.todayDay);
    if(state.todayDay==='walkins'){
      const [walkins,rosters,points]=await Promise.all([api(`/walk-ins?facility_code=${encodeURIComponent(facility)}&hours=720`),api(`/duty-rosters?facility_code=${encodeURIComponent(facility)}&day=${day}`),api(`/service-points?facility_code=${encodeURIComponent(facility)}`)]);
      const rows=walkins.map(w=>({appointment_id:null,walkin_id:w.walkin_id,patient:w.patient,scheduled_start:w.arrived_at||w.created_at,service:w.service_point||'Walk-In',provider:null,status:w.status,queue:w.queue_name||w.service_point||'Walk-In Registration',on_duty_team:'Duty roster / next available clinician',encounter_id:w.encounter_id,next_step:w.status==='ARRIVED'?'SEND_TO_TRIAGE':w.status==='WAITING_TRIAGE'?'TRIAGE_COMPLETE':w.status==='TRIAGED'?'READY_FOR_PROVIDER':'OPEN_RECORD'}));
      return {data:{rows,total:rows.length,counts:{expected:rows.length,arrived:rows.filter(x=>x.status==='ARRIVED').length,checked_in:0,waiting:rows.filter(x=>x.status==='WAITING_TRIAGE').length,ready_for_provider:rows.filter(x=>x.status==='READY_FOR_PROVIDER').length,completed:rows.filter(x=>x.status==='COMPLETED').length}},rosters,walkins,points};
    }
    const [data,rosters,walkins,points]=await Promise.all([api(`/today-patients?facility_code=${encodeURIComponent(facility)}&day=${day}&limit=500`),api(`/duty-rosters?facility_code=${encodeURIComponent(facility)}&day=${day}`),api(`/walk-ins?facility_code=${encodeURIComponent(facility)}&hours=720`),api(`/service-points?facility_code=${encodeURIComponent(facility)}`)]);
    return {data,rosters,walkins,points};
  }

  renderTodayPatients=async function(){
    renderLoading('Loading patient access operations…');
    const {data,rosters,walkins,points}=await v6LoadTodayData();
    const allRows=data.rows||[]; const rows=v6TodayRows(allRows); const c=data.counts||{};
    const services=v6Unique(allRows.map(r=>r.service)), queues=v6Unique(allRows.map(r=>r.queue)), statuses=v6Unique(allRows.map(r=>String(r.status||'').toUpperCase()));
    const rosterRows=(rosters||[]).slice(0,12);
    const selected=rows.find(r=>r.patient?.mpi_id===state.selectedPatientId)||rows[0]||null;
    const tabCount=(tab)=>tab===state.todayDay?(data.total||0):'';
    $('#mainContent').innerHTML=`<section class="ua-page v6-today-page">
      ${uaPageTitle("Today's Patients & Front Desk Workflow",'Manage scheduled visits, arrivals and walk-ins without leaving this workspace',`<button class="ua-button primary" data-v6-action="open-walkin">Register Walk-In</button>`)}
      <div class="v6-three-pane">
        <section class="v6-pane v6-pane-list">
          <article class="ua-card v6-fill-card">
            <div class="today-tabs v6-tabs">${[['yesterday','Yesterday'],['today','Today'],['tomorrow','Tomorrow'],['walkins','Walk-Ins']].map(([id,label])=>`<button class="${state.todayDay===id?'active':''}" data-v6-action="today-tab" data-tab="${id}">${label}${state.todayDay===id?` (${data.total||0})`:''}</button>`).join('')}</div>
            <div class="today-filterbar v6-filter-grid">
              <div class="ua-search-filter">${v4Icon('search')}<input id="todaySearch" value="${esc(state.todayFilters.search||'')}" placeholder="Search name, MRN, MPI or phone"></div>
              <select id="todayService" class="simple-select">${v6Option('','All Services',state.todayFilters.service)}${services.map(x=>v6Option(x,x,state.todayFilters.service)).join('')}</select>
              <select id="todayQueue" class="simple-select">${v6Option('','All Queues',state.todayFilters.queue)}${queues.map(x=>v6Option(x,x,state.todayFilters.queue)).join('')}</select>
              <select id="todayStatus" class="simple-select">${v6Option('','All Statuses',state.todayFilters.status)}${statuses.map(x=>v6Option(x,statusLabel(x),state.todayFilters.status)).join('')}</select>
              <button class="ua-button compact primary" data-v6-action="apply-today-filter">Apply</button><button class="ua-button compact" data-v6-action="clear-today-filter">Clear</button>
            </div>
            <div class="today-metrics v6-metrics">${[['Expected',c.expected??data.total??0],['Arrived',c.arrived||0],['Checked In',c.checked_in||0],['Waiting',c.waiting||0],['Ready',c.ready_for_provider||0],['Completed',c.completed||0]].map(([l,n])=>`<div class="today-metric"><div><span>${l}</span><strong>${n}</strong></div></div>`).join('')}</div>
            <div class="table-wrap v6-list-scroll"><table class="ua-data-table"><thead><tr><th>Time</th><th>Patient</th><th>MRN</th><th>Service</th><th>Status</th><th>Next</th></tr></thead><tbody>${rows.length?rows.map(row=>`<tr class="${selected?.patient?.mpi_id===row.patient?.mpi_id?'selected-row':''}" data-v6-action="select-today-patient" data-patient-id="${esc(row.patient?.mpi_id)}"><td>${new Date(row.scheduled_start).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</td><td><strong>${esc(row.patient?.full_name||'Unknown')}</strong></td><td>${esc(row.patient?.mrn||'—')}</td><td>${esc(row.service||'—')}</td><td><span class="ua-status ${uaStatusClass(row.status)}">${esc(statusLabel(row.status))}</span></td><td>${nextStepButtonV4(row)}</td></tr>`).join(''):`<tr><td colspan="6" class="v6-empty">No records match this view. Use Clear or change context.</td></tr>`}</tbody></table></div>
            <div class="ua-pagination"><span>${rows.length} visible of ${data.total||0}</span><button class="ua-button compact" data-v6-action="refresh-today">Refresh</button></div>
          </article>
        </section>
        <section class="v6-pane v6-pane-workflow">
          <article class="ua-card"><div class="ua-card-header"><h2>Selected Patient Workflow</h2></div><div class="ua-card-body">${selected?`<div class="v6-selected-patient"><div>${patientAvatar(selected.patient,true)}</div><div><h2>${esc(selected.patient.full_name)}</h2><p>${esc(selected.patient.mrn)} · ${esc(selected.service)} · ${esc(statusLabel(selected.status))}</p></div></div><div class="action-grid v6-action-grid">${[['Arrive','arrive'],['Check In','check-in'],['Send to Triage','triage'],['Assign Queue','assign'],['Open Patient Station','station'],['Print Label','print'],['Benefit Check','benefit'],['Travel Screening','screen']].map(([l,op])=>`<button class="front-action" data-v6-action="front-${op}" data-patient-id="${esc(selected.patient.mpi_id)}" data-appointment="${esc(selected.appointment_id||'')}" data-encounter="${esc(selected.encounter_id||'')}"><strong>${l}</strong></button>`).join('')}</div>`:`<div class="v6-empty">Select a patient from the left pane.</div>`}</div></article>
          <article class="ua-card v6-walkin-card"><div class="ua-card-header"><h2>Walk-In Workflow</h2></div><div class="ua-card-body"><div class="workflow-steps-v4">${['Search/Create','Demographics','Coverage & Consent','Encounter','Arrival & Route'].map((x,i)=>`<div class="workflow-step-v4"><b>${i+1}</b><span>${x}</span></div>`).join('')}</div><button class="ua-button primary full-width" data-v6-action="open-walkin">Start Walk-In Registration</button></div></article>
          <article class="ua-card"><div class="ua-card-header"><h2>Front Desk Queue</h2></div><div class="ua-card-body"><div class="ops-overview-grid">${[['Walk-Ins',walkins.length],['Waiting',c.walking_ins_waiting||c.walk_ins_waiting||0],['Service Points',points.length],['On Duty',rosterRows.length]].map(([l,n])=>`<div><span>${l}</span><strong>${n}</strong></div>`).join('')}</div></div></article>
        </section>
        <aside class="v6-pane v6-pane-context">
          <article class="ua-card v6-fill-card"><div class="ua-card-header"><h2>On-Duty Team & Service Points</h2></div><div class="ua-card-body v6-context-scroll">${rosterRows.length?rosterRows.map(r=>`<button class="v6-roster-row" data-v6-action="choose-service-point" data-service-point="${esc(r.service_point.service_point_id)}"><strong>${esc(r.service_point.name)}</strong><span>${esc(r.service_point.clinic||r.service_point.department)} · ${esc(r.lead_provider||r.team_name)}</span><small>${String(r.shift_start).slice(0,5)}–${String(r.shift_end).slice(0,5)} · ${esc(r.service_point.room||'Room TBD')} · Capacity ${r.service_point.queue_capacity}</small></button>`).join(''):`<div class="v6-empty">No roster loaded for this date.</div>`}</div></article>
          <article class="ua-card"><div class="ua-card-header"><h2>Context & Unit</h2></div><div class="ua-card-body"><p><strong>${esc(data.facility?.name||operationFacility())}</strong></p><button class="ua-button full-width" data-v6-action="change-context">Change Hospital / Unit</button><button class="ua-button full-width" data-route="bed-board">Open Unit Manager</button></div></article>
        </aside>
      </div>
    </section>`;
  };

  function v6WalkinSteps(){return ['Search / Create','Demographics','Coverage & Consent','Encounter','Arrival & Route'];}
  function v6WalkinModal(step=0){
    state.walkInDraft=state.walkInDraft||{step:0,patient:null,existing:false,first_name:'',middle_name:'',last_name:'',date_of_birth:'2000-01-01',sex:'Female',phone:'',nida_number:'',address:'',region:'Dar es Salaam',payer:'Cash',member_number:'',consent_status:'PENDING',proxy_name:'',encounter_type:'OUTPATIENT',service:'General OPD Clinic',reason_for_visit:'Walk-in clinical assessment',service_point_id:'',coverage_route:'Cash',notes:''};
    state.walkInDraft.step=step; const d=state.walkInDraft;
    const steps=v6WalkinSteps();
    let body='';
    if(step===0) body=`<div class="v6-wizard-section"><h3>Find an existing patient</h3><div class="walkin-inline"><input id="v6WalkSearch" placeholder="Name, MRN, MPI, NIDA or phone"><button class="ua-button primary" data-v6-action="walk-search">Search</button></div><div id="v6WalkMatches" class="v5-inline-results"></div><div class="or-divider">OR</div><button class="ua-button" data-v6-action="walk-new">Create a new patient</button></div>`;
    if(step===1) body=`<div class="form-grid"><label class="field"><span>First name</span><input id="wFirst" value="${esc(d.first_name)}" required></label><label class="field"><span>Middle name</span><input id="wMiddle" value="${esc(d.middle_name)}"></label><label class="field"><span>Last name</span><input id="wLast" value="${esc(d.last_name)}" required></label><label class="field"><span>Date of birth</span><input id="wDob" type="date" value="${esc(d.date_of_birth)}"></label><label class="field"><span>Sex</span><select id="wSex">${['Female','Male','Unknown'].map(x=>v6Option(x,x,d.sex)).join('')}</select></label><label class="field"><span>Phone</span><input id="wPhone" value="${esc(d.phone)}"></label><label class="field"><span>NIDA</span><input id="wNida" value="${esc(d.nida_number)}"></label><label class="field full"><span>Address</span><input id="wAddress" value="${esc(d.address)}"></label><label class="field"><span>Region</span><input id="wRegion" value="${esc(d.region)}"></label><label class="field"><span>MRN</span><input value="Auto-assigned on registration" readonly></label></div>`;
    if(step===2) body=`<div class="form-grid"><label class="field"><span>Payment / coverage</span><select id="wPayer">${['Cash','NHIF','Private Insurance','Exempted','Emergency'].map(x=>v6Option(x,x,d.payer)).join('')}</select></label><label class="field"><span>Member number</span><input id="wMember" value="${esc(d.member_number)}"></label><label class="field"><span>Consent status</span><select id="wConsent">${['PENDING','OBTAINED','REFUSED','EMERGENCY_BASIS'].map(x=>v6Option(x,statusLabel(x),d.consent_status)).join('')}</select></label><label class="field"><span>Proxy / guardian</span><input id="wProxy" value="${esc(d.proxy_name)}"></label><label class="field full"><span>Consent notes</span><textarea id="wConsentNotes">${esc(d.consent_notes||'')}</textarea></label></div>`;
    if(step===3) body=`<div class="form-grid"><label class="field"><span>Encounter type</span><select id="wEncounterType">${['OUTPATIENT','EMERGENCY','INPATIENT','DAY_CASE','MATERNITY'].map(x=>v6Option(x,statusLabel(x),d.encounter_type)).join('')}</select></label><label class="field"><span>Service</span><input id="wService" value="${esc(d.service)}"></label><label class="field full"><span>Reason for visit</span><textarea id="wReason">${esc(d.reason_for_visit)}</textarea></label></div>`;
    if(step===4) body=`<div class="form-grid"><label class="field"><span>Service point</span><select id="wServicePoint"><option value="">Duty roster / next available</option></select></label><label class="field"><span>Coverage route</span><select id="wCoverage">${['Cash','NHIF','Private Insurance','Exempted','Emergency'].map(x=>v6Option(x,x,d.coverage_route||d.payer)).join('')}</select></label><label class="field full"><span>Arrival and routing notes</span><textarea id="wNotes">${esc(d.notes||'Registered as walk-in and routed to service point.')}</textarea></label><div class="v6-summary full"><strong>${esc(d.patient?.full_name||`${d.first_name} ${d.last_name}`)}</strong><span>${d.patient?.mrn||'MRN will be auto-assigned'} · ${esc(d.service)} · ${esc(d.payer)}</span></div></div>`;
    openModal('Walk-In Registration',`<div class="v6-wizard-steps">${steps.map((x,i)=>`<button class="${i===step?'active':i<step?'done':''}" data-v6-action="walk-goto" data-step="${i}" ${i>step?'disabled':''}><b>${i+1}</b><span>${x}</span></button>`).join('')}</div><div id="v6WalkBody">${body}</div>`,`<button class="ua-button" data-modal-action="close">Cancel</button>${step>0?`<button class="ua-button" data-v6-action="walk-prev">Back</button>`:''}${step<4?`<button class="ua-button primary" data-v6-action="walk-next">Next</button>`:`<button class="ua-button primary" data-v6-action="walk-finish">Register, Arrive & Route</button>`}`,'Walk-In Workflow');
    $('#modal').classList.add('v6-workflow-modal');
    if(step===4) api(`/service-points?facility_code=${encodeURIComponent(operationFacility())}`).then(points=>{const el=$('#wServicePoint');if(el)el.innerHTML=`<option value="">Duty roster / next available</option>${points.map(p=>v6Option(p.service_point_id,`${p.name} · ${p.clinic} · ${p.room||'Room TBD'}`,d.service_point_id)).join('')}`;}).catch(()=>{});
  }
  function v6SaveWalkStep(){const d=state.walkInDraft;if(!d)return;
    const map={wFirst:'first_name',wMiddle:'middle_name',wLast:'last_name',wDob:'date_of_birth',wSex:'sex',wPhone:'phone',wNida:'nida_number',wAddress:'address',wRegion:'region',wPayer:'payer',wMember:'member_number',wConsent:'consent_status',wProxy:'proxy_name',wConsentNotes:'consent_notes',wEncounterType:'encounter_type',wService:'service',wReason:'reason_for_visit',wServicePoint:'service_point_id',wCoverage:'coverage_route',wNotes:'notes'};
    Object.entries(map).forEach(([id,key])=>{const el=$('#'+id);if(el)d[key]=el.value;});
  }

  async function v6ChangeContextModal(){
    const tree=await api('/facilities/context-tree');
    const facilities=tree.facilities||((tree.groups||[]).flatMap(g=>g.facilities||[]))||[];
    openModal('Change Hospital, Campus and Unit',`<div class="form-grid"><label class="field full"><span>Hospital / facility</span><select id="v6ContextFacility">${facilities.map(f=>v6Option(f.code,f.name,state.facility)).join('')}</select></label><label class="field"><span>Department</span><select id="v6ContextDepartment"><option value="">All departments</option></select></label><label class="field"><span>Unit / ward</span><select id="v6ContextUnit"><option value="">Select unit in Unit Manager</option></select></label></div><p class="muted">Changing context refreshes rosters, patient lists, service points and unit management for the selected facility.</p>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v6-action="save-context">Apply Context</button>`,'Change Context');
  }

  const v6OriginalLoginHtml=$('#loginOverlay')?.innerHTML;
  if($('#loginOverlay') && !$('#loginOverlay .government-login-logo')){
    const card=$('#loginOverlay').querySelector('.login-card');
    if(card)card.insertAdjacentHTML('afterbegin','<div class="government-login-logo"><img src="/assets/tanzania-coat-of-arms.png" alt="Government of Tanzania coat of arms"><div><strong>United Republic of Tanzania</strong><span>National Health Information System</span></div></div>');
  }

  document.addEventListener('click',async e=>{
    const b=e.target.closest('[data-v6-action]'); if(!b)return;
    e.preventDefault(); e.stopImmediatePropagation();
    try{
      const a=b.dataset.v6Action;
      if(a==='today-tab'){state.todayDay=b.dataset.tab;saveState();return renderTodayPatients();}
      if(a==='apply-today-filter'){state.todayFilters={search:$('#todaySearch')?.value.trim()||'',service:$('#todayService')?.value||'',clinic:'',queue:$('#todayQueue')?.value||'',status:$('#todayStatus')?.value||''};saveState();return renderTodayPatients();}
      if(a==='clear-today-filter'){state.todayFilters={search:'',service:'',clinic:'',queue:'',status:''};saveState();return renderTodayPatients();}
      if(a==='refresh-today')return renderTodayPatients();
      if(a==='select-today-patient'){state.selectedPatientId=b.dataset.patientId;saveState();return renderTodayPatients();}
      if(a==='open-walkin'){state.walkInDraft=null;return v6WalkinModal(0);}

      if(a==='front-arrive'){const appt=b.dataset.appointment;if(!appt)throw new Error('This record has no appointment to arrive.');await api(`/appointments/${encodeURIComponent(appt)}`,{method:'PATCH',body:JSON.stringify({status:'ARRIVED',actor:currentRole().user,note:'Patient arrived from front desk workflow.'})});toast('Patient arrived','Arrival was recorded and downstream teams were notified.');return renderTodayPatients();}
      if(a==='front-check-in'||a==='front-triage'||a==='front-assign'){const enc=b.dataset.encounter;if(!enc)throw new Error('Select a patient with an active encounter.');const status=a==='front-check-in'?'REGISTERED':a==='front-triage'?'WAITING_TRIAGE':'READY_FOR_PROVIDER';await api(`/encounters/${encodeURIComponent(enc)}/status`,{method:'PATCH',body:JSON.stringify({status,actor:currentRole().user,note:`${statusLabel(status)} from front desk workflow`})});toast('Workflow updated',statusLabel(status));return renderTodayPatients();}
      if(a==='front-station'){state.selectedPatientId=b.dataset.patientId||state.selectedPatientId;saveState();return navigate('patient-station',{preservePatient:true});}
      if(a==='front-print'){toast('Print labels','Patient label and wristband print job prepared.');return;}
      if(a==='front-benefit'){toast('Benefit check','NHIF / insurance eligibility check submitted.');return;}
      if(a==='front-screen'){toast('Travel screening','Screening form opened for the selected patient.');return;}
      if(a==='walk-search'){const q=$('#v6WalkSearch').value.trim();if(!q)throw new Error('Enter a search value.');const matches=await api(`/patients?search=${encodeURIComponent(q)}&limit=20`);const target=$('#v6WalkMatches');target.innerHTML=matches.length?matches.map(p=>`<button class="v6-patient-match" data-v6-action="walk-select-existing" data-patient="${esc(p.mpi_id)}"><strong>${esc(p.full_name)}</strong><span>${esc(p.mrn)} · ${esc(p.phone||'No phone')} · ${esc(p.date_of_birth||'')}</span></button>`).join(''):'<div class="v6-empty">No match found. Create a new patient.</div>';return;}
      if(a==='walk-select-existing'){const p=await api(`/patients/${encodeURIComponent(b.dataset.patient)}`);state.walkInDraft.patient=p;state.walkInDraft.existing=true;Object.assign(state.walkInDraft,{first_name:p.first_name||'',middle_name:p.middle_name||'',last_name:p.last_name||'',date_of_birth:String(p.date_of_birth||'').slice(0,10)||'2000-01-01',sex:p.sex||'Unknown',phone:p.phone||'',nida_number:p.nida_number||'',address:p.address||'',region:p.region||'',payer:p.payer||'Cash',member_number:p.member_number||'',consent_status:p.consent_status||'PENDING'});state.selectedPatientId=p.mpi_id;saveState();return v6WalkinModal(1);}
      if(a==='walk-new'){state.walkInDraft.existing=false;return v6WalkinModal(1);}
      if(a==='walk-next'){v6SaveWalkStep();const step=state.walkInDraft.step;if(step===1&&(!state.walkInDraft.first_name||!state.walkInDraft.last_name))throw new Error('First and last name are required.');return v6WalkinModal(step+1);}
      if(a==='walk-prev'){v6SaveWalkStep();return v6WalkinModal(Math.max(0,state.walkInDraft.step-1));}
      if(a==='walk-goto'){v6SaveWalkStep();return v6WalkinModal(Number(b.dataset.step));}
      if(a==='walk-finish'){v6SaveWalkStep();const d=state.walkInDraft;let patient=d.patient;if(!d.existing){const reg=await api('/registration',{method:'POST',body:JSON.stringify({facility_code:operationFacility(),registration_mode:'STANDARD',first_name:d.first_name,middle_name:d.middle_name||null,last_name:d.last_name,date_of_birth:d.date_of_birth,sex:d.sex,phone:d.phone||null,nida_number:d.nida_number||null,address:d.address||null,region:d.region||null,district:null,next_of_kin:null,payer:d.payer||'Cash',member_number:d.member_number||null,consent_status:d.consent_status||'PENDING',proxy_name:d.proxy_name||null,encounter_type:d.encounter_type||'OUTPATIENT',service:d.service||'General OPD Clinic',reason_for_visit:d.reason_for_visit||'Walk-in clinical assessment',force_create:false})});patient=reg.patient;}
        state.selectedPatientId=patient.mpi_id;saveState();const result=await api('/walk-ins',{method:'POST',body:JSON.stringify({patient_mpi_id:patient.mpi_id,facility_code:operationFacility(),service_point_id:d.service_point_id||null,reason:d.reason_for_visit||'Walk-in clinical assessment',notes:d.notes||'Registered, arrived and routed from front desk.',coverage_route:d.coverage_route||d.payer||'Cash',created_by:currentRole().user})});closeModal();toast('Walk-In Registered',`${patient.full_name} · ${patient.mrn||'MRN assigned'} · ${result.notification.message_en}`);state.todayDay='walkins';return renderTodayPatients();}
      if(a==='change-context')return v6ChangeContextModal();
      if(a==='save-context'){state.facility=$('#v6ContextFacility').value;state.selectedBedUnit=null;saveState();closeModal();updateChrome();return renderTodayPatients();}
      if(a==='choose-service-point'){state.walkInDraft=state.walkInDraft||{};state.walkInDraft.service_point_id=b.dataset.servicePoint;toast('Service point selected','It will be used in the walk-in workflow.');return;}
    }catch(err){console.error(err);toast('Action failed',err.message||String(err));}
  },true);

  const v6OriginalFrontHandler=nextStepButtonV4;


/* --------------------------------------------------------------------------
   Release 7.0 operational workqueue, state-aware workflow and responsive
   workspace corrections. This layer replaces the affected release 6 views
   while retaining the provider-facing longitudinal record shell.
--------------------------------------------------------------------------- */
state.selectedWorkqueueItemIds=state.selectedWorkqueueItemIds||[];
state.v7WorkqueueFilters=state.v7WorkqueueFilters||{search:'',category:'',status:''};

function v7Status(value){return String(value||'').toUpperCase().replace(/\s+/g,'_');}
function v7VisitContext(row){
  const source=`${row?.visit_type||''} ${row?.encounter_type||''} ${row?.service||''} ${row?.reason_for_visit||''}`.toUpperCase();
  if(/EMERGENCY|CASUALTY|\bED\b/.test(source))return {type:'Emergency',intake:'Emergency Intake',triage:'Emergency Triage',ready:'Ready for Emergency Clinician'};
  if(/INPATIENT|WARD|ADMISSION|MATERNITY/.test(source))return {type:'Inpatient',intake:'Confirm Admission',triage:'Complete Admission Assessment',ready:'Ready for Inpatient Team'};
  if(/TELE|VIRTUAL|REMOTE/.test(source))return {type:'Telehealth',intake:'Confirm Virtual Arrival',triage:'Complete Pre-Visit Review',ready:'Ready for Virtual Clinician'};
  if(row?.walkin_id||/WALK.?IN/.test(source))return {type:'Walk-In',intake:'Register Walk-In',triage:'Send to Triage',ready:'Ready for Provider'};
  return {type:'Outpatient',intake:'Check In',triage:'Send to Triage',ready:'Ready for Provider'};
}
function v7WorkflowAction(row){
  const status=v7Status(row?.status);
  const visit=v7VisitContext(row);
  if(row?.walkin_id){
    const map={ARRIVED:['SEND_TO_TRIAGE','Send to Triage'],SERVICE_ASSIGNED:['SEND_TO_TRIAGE','Send to Triage'],WAITING_TRIAGE:['TRIAGE_COMPLETE','Complete Triage'],TRIAGED:['READY_FOR_PROVIDER','Ready for Provider'],READY_FOR_PROVIDER:['COMPLETE','Complete Walk-In']};
    const next=map[status];
    return next?{kind:'walkin',action:next[0],label:next[1]}:{kind:'open',label:'Open Record'};
  }
  if(['SCHEDULED','CONFIRMED','REINSTATED'].includes(status)&&row?.appointment_id)return {kind:'appointment',action:'ARRIVED',label:visit.type==='Telehealth'?'Start Virtual Arrival':'Arrive Patient',visitType:visit.type};
  const encounterMap={
    ARRIVED:['REGISTERED',visit.intake],WAITING_REGISTRATION:['REGISTERED','Complete Registration'],REGISTERED:['WAITING_TRIAGE',visit.triage],CHECKED_IN:['WAITING_TRIAGE',visit.triage],
    WAITING_TRIAGE:['TRIAGED',visit.type==='Inpatient'?'Complete Admission Assessment':'Complete Triage'],TRIAGED:['READY_FOR_PROVIDER',visit.ready],READY_FOR_PROVIDER:['ROOMED',visit.type==='Telehealth'?'Open Virtual Room':visit.type==='Inpatient'?'Assign Bed / Room':'Room Patient'],ROOMED:['IN_PROGRESS',visit.type==='Inpatient'?'Start Inpatient Care':'Start Visit'],
    IN_PROGRESS:['WAITING_RESULTS','Waiting for Results'],WAITING_RESULTS:['READY_FOR_DISCHARGE','Ready for Discharge']
  };
  if(status==='READY_FOR_DISCHARGE'&&row?.encounter_id)return {kind:'discharge',label:'Discharge Patient'};
  const next=encounterMap[status];
  if(next&&row?.encounter_id)return {kind:'encounter',status:next[0],label:next[1],visitType:visit.type};
  return {kind:'open',label:['DISCHARGED','COMPLETED','CANCELLED'].includes(status)?'Open Completed Record':'Open Record'};
}
function v7WorkflowButton(row,large=false){
  const a=v7WorkflowAction(row); const cls=large?'front-action v7-primary-workflow':'next-step-btn';
  const context=a.visitType||v7VisitContext(row).type;
  return `<button class="${cls}" data-v7-action="workflow-next" data-kind="${a.kind}" data-label="${esc(a.label)}" data-appointment="${esc(row.appointment_id||'')}" data-encounter="${esc(row.encounter_id||'')}" data-walkin="${esc(row.walkin_id||'')}" data-patient-id="${esc(row.patient?.mpi_id||'')}" data-status="${esc(a.status||'')}" data-course="${esc(a.action||'')}"><strong>${esc(a.label)}</strong>${large?`<small>${esc(context)} · ${esc(statusLabel(row.status))} → ${esc(a.label)}</small>`:''}</button>`;
}
function v7SecondaryAction(label,action,row,icon=''){return `<button class="front-action v7-secondary-action" data-v7-action="${action}" data-patient-id="${esc(row.patient?.mpi_id||'')}" data-appointment="${esc(row.appointment_id||'')}" data-encounter="${esc(row.encounter_id||'')}">${icon?`<span>${icon}</span>`:''}<strong>${esc(label)}</strong></button>`;}

function v7LayoutStyle(key,defaults){
  try{const saved=JSON.parse(localStorage.getItem(`umoja-layout-${key}`)||'null');if(saved&&saved.length===2)return `--v7-col1:${saved[0]}px;--v7-col2:${saved[1]}px`; }catch(_){ }
  return `--v7-col1:${defaults[0]}px;--v7-col2:${defaults[1]}px`;
}
function v7EnhancePanels(root=$('#mainContent')){
  if(!root)return;
  root.querySelectorAll('.ua-page > .ua-card,.v7-pane > .ua-card,.v6-pane > .ua-card,.v5-admin-shell > .ua-card,.patient-station-v5 > *').forEach(panel=>{
    panel.classList.add('v7-resizable-panel');
    const header=panel.querySelector(':scope > .ua-card-header');
    if(header&&!header.querySelector('[data-v7-panel-maximize]'))header.insertAdjacentHTML('beforeend','<button class="v7-panel-control" data-v7-panel-maximize title="Maximize or restore panel">⛶</button>');
  });
}
const v7PanelObserver=new MutationObserver(()=>requestAnimationFrame(()=>v7EnhancePanels()));
if($('#mainContent'))v7PanelObserver.observe($('#mainContent'),{childList:true,subtree:true});

renderTodayPatients=async function(){
  renderLoading('Loading patient access operations…');
  const {data,rosters,walkins,points}=await v6LoadTodayData();
  const allRows=data.rows||[]; const rows=v6TodayRows(allRows); const c=data.counts||{};
  const services=v6Unique(allRows.map(r=>r.service)),queues=v6Unique(allRows.map(r=>r.queue)),statuses=v6Unique(allRows.map(r=>v7Status(r.status)));
  const rosterRows=(rosters||[]).slice(0,40);
  const selected=rows.find(r=>r.patient?.mpi_id===state.selectedPatientId)||rows[0]||null;
  if(selected&&state.selectedPatientId!==selected.patient?.mpi_id){state.selectedPatientId=selected.patient?.mpi_id;saveState();}
  $('#mainContent').innerHTML=`<section class="ua-page v7-today-page">
    ${uaPageTitle("Today's Patients & Front Desk Workflow",'State-aware patient flow: completed steps are disabled and the next valid action is presented automatically.',`<button class="ua-button primary" data-v6-action="open-walkin">Register Walk-In</button><button class="ua-button" data-v6-action="change-context">Change Context</button>`)}
    <div class="v7-resizable-workspace v7-today-workspace" data-v7-layout="today" style="${v7LayoutStyle('today',[650,430])}">
      <section class="v7-pane v7-patient-list-pane"><article class="ua-card v7-fill-card">
        <div class="today-tabs v6-tabs">${[['yesterday','Yesterday'],['today','Today'],['tomorrow','Tomorrow'],['walkins','Walk-Ins']].map(([id,label])=>`<button class="${state.todayDay===id?'active':''}" data-v6-action="today-tab" data-tab="${id}">${label}${state.todayDay===id?` (${data.total||0})`:''}</button>`).join('')}</div>
        <div class="today-filterbar v7-filter-grid"><div class="ua-search-filter">${v4Icon('search')}<input id="todaySearch" value="${esc(state.todayFilters.search||'')}" placeholder="Search name, MRN, MPI or phone"></div><select id="todayService" class="simple-select">${v6Option('','All Services',state.todayFilters.service)}${services.map(x=>v6Option(x,x,state.todayFilters.service)).join('')}</select><select id="todayQueue" class="simple-select">${v6Option('','All Queues',state.todayFilters.queue)}${queues.map(x=>v6Option(x,x,state.todayFilters.queue)).join('')}</select><select id="todayStatus" class="simple-select">${v6Option('','All Statuses',state.todayFilters.status)}${statuses.map(x=>v6Option(x,statusLabel(x),state.todayFilters.status)).join('')}</select><button class="ua-button compact primary" data-v6-action="apply-today-filter">Apply</button><button class="ua-button compact" data-v6-action="clear-today-filter">Clear</button></div>
        <div class="today-metrics v7-metrics">${[['Expected',c.expected??data.total??0],['Arrived',c.arrived||0],['Checked In',c.checked_in||0],['Waiting',c.waiting||0],['Ready',c.ready_for_provider||0],['Completed',c.completed||0]].map(([l,n])=>`<div class="today-metric"><div><span>${l}</span><strong>${n}</strong></div></div>`).join('')}</div>
        <div class="table-wrap v7-scroll"><table class="ua-data-table v7-patient-table"><thead><tr><th>Time</th><th>Patient</th><th>MRN</th><th>Service</th><th>Status</th><th>Next Valid Step</th></tr></thead><tbody>${rows.length?rows.map(row=>`<tr class="${selected?.patient?.mpi_id===row.patient?.mpi_id?'selected-row':''}" data-v6-action="select-today-patient" data-patient-id="${esc(row.patient?.mpi_id)}"><td>${new Date(row.scheduled_start).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</td><td><strong>${esc(row.patient?.full_name||'Unknown')}</strong></td><td>${esc(row.patient?.mrn||'—')}</td><td>${esc(row.service||'—')}</td><td><span class="ua-status ${uaStatusClass(row.status)}">${esc(statusLabel(row.status))}</span></td><td>${v7WorkflowButton(row)}</td></tr>`).join(''):`<tr><td colspan="6" class="v6-empty">No records match the selected date and filters.</td></tr>`}</tbody></table></div>
        <div class="ua-pagination"><span>${rows.length} visible of ${data.total||0}</span><button class="ua-button compact" data-v6-action="refresh-today">Refresh</button></div>
      </article></section>
      <div class="v7-splitter" data-v7-splitter="0" title="Drag to resize"></div>
      <section class="v7-pane v7-workflow-pane"><article class="ua-card v7-fill-card"><div class="ua-card-header"><h2>Selected Patient Workflow</h2></div><div class="ua-card-body v7-scroll">${selected?`<div class="v6-selected-patient"><div>${patientAvatar(selected.patient,true)}</div><div><h2>${esc(selected.patient.full_name)}</h2><p>${esc(selected.patient.mrn)} · ${esc(selected.service)} · <b>${esc(statusLabel(selected.status))}</b></p></div></div><div class="v7-next-step-card"><span>Next valid workflow action</span>${v7WorkflowButton(selected,true)}</div><div class="action-grid v7-secondary-grid">${v7SecondaryAction('Open Patient Station','open-station',selected)}${v7SecondaryAction('Print Label','print-label',selected)}${v7SecondaryAction('Benefit Check','benefit-check',selected)}${v7SecondaryAction('Travel Screening','travel-screen',selected)}${v7SecondaryAction('Event History','event-history',selected)}${v7SecondaryAction('Open Chart','open-chart',selected)}</div><div class="v7-workflow-history"><h3>Workflow guardrails</h3><p>Actions already completed are not shown again. Every transition is validated by the backend and written to the audit/event history.</p></div>`:`<div class="v6-empty">Select a patient from the worklist.</div>`}</div></article><article class="ua-card"><div class="ua-card-header"><h2>Walk-In Workflow</h2></div><div class="ua-card-body"><div class="workflow-steps-v4">${['Search/Create','Demographics','Coverage & Consent','Encounter','Arrival & Route'].map((x,i)=>`<div class="workflow-step-v4"><b>${i+1}</b><span>${x}</span></div>`).join('')}</div><button class="ua-button primary full-width" data-v6-action="open-walkin">Start Walk-In Registration</button></div></article></section>
      <div class="v7-splitter" data-v7-splitter="1" title="Drag to resize"></div>
      <aside class="v7-pane v7-context-pane"><article class="ua-card v7-fill-card"><div class="ua-card-header"><h2>On-Duty Team & Service Points</h2></div><div class="ua-card-body v7-scroll">${rosterRows.length?rosterRows.map(r=>`<button class="v6-roster-row" data-v6-action="choose-service-point" data-service-point="${esc(r.service_point.service_point_id)}"><strong>${esc(r.service_point.name)}</strong><span>${esc(r.service_point.clinic||r.service_point.department)} · ${esc(r.lead_provider||r.team_name)}</span><small>${String(r.shift_start).slice(0,5)}–${String(r.shift_end).slice(0,5)} · ${esc(r.service_point.room||'Room TBD')} · Capacity ${r.service_point.queue_capacity}</small></button>`).join(''):`<div class="v6-empty">No roster loaded for this date.</div>`}</div></article><article class="ua-card"><div class="ua-card-header"><h2>Context & Unit</h2></div><div class="ua-card-body"><p><strong>${esc(data.facility?.name||operationFacility())}</strong></p><div class="ops-overview-grid">${[['Walk-Ins',walkins.length],['Waiting',c.walk_ins_waiting||0],['Service Points',points.length],['On Duty',rosterRows.length]].map(([l,n])=>`<div><span>${l}</span><strong>${n}</strong></div>`).join('')}</div><button class="ua-button full-width" data-v6-action="change-context">Change Hospital / Unit</button><button class="ua-button full-width" data-route="bed-board">Open Unit Manager</button></div></article></aside>
    </div></section>`;
  requestAnimationFrame(()=>v7EnhancePanels());
};

function v7SelectedWorkqueueItems(){const ids=new Set(state.selectedWorkqueueItemIds||[]);return (state.v7QueueDetail?.items||[]).filter(item=>ids.has(item.item_id));}
function v7QueueRuleText(queue){
  if(!queue)return 'No queue selected.';
  let rules=queue.routing_rule_json||'';try{rules=rules?JSON.stringify(JSON.parse(rules),null,2):'No explicit JSON rule configured.';}catch(_){ }
  return `${queue.description||'No description configured.'}\n\nOwner: ${queue.owner_team||'Unassigned'}\nService area: ${queue.service_area||'—'}\nSLA: ${queue.sla_hours||24} hours\n\nRouting rule:\n${rules}`;
}
function v7QueueItemRows(items){return items.map(item=>`<tr class="${(state.selectedWorkqueueItemIds||[]).includes(item.item_id)?'selected-row':''}"><td><input type="checkbox" data-v7-wq-item="${esc(item.item_id)}" ${(state.selectedWorkqueueItemIds||[]).includes(item.item_id)?'checked':''}></td><td><strong>${esc(item.title)}</strong><small>${esc(item.item_id)}</small></td><td>${item.patient?`<button class="ua-link" data-patient-id="${esc(item.patient.mpi_id)}" data-open-station="true">${esc(item.patient.full_name)}</button><small>${esc(item.patient.mrn)}</small>`:'No patient context'}</td><td>${esc(item.reason)}</td><td><span class="ua-priority ${String(item.priority).toLowerCase()}">${esc(item.priority)}</span></td><td><span class="ua-status ${item.status==='ACTIVE'?'active':item.status==='DEFERRED'?'checked-in':'scheduled'}">${esc(statusLabel(item.status))}</span></td><td>${esc(item.assigned_to||'Unassigned')}</td><td>${fmtDate(item.due_at)}</td><td><button class="ua-button compact" data-v7-action="item-history" data-item-id="${esc(item.item_id)}">History</button></td></tr>`).join('');}

renderWorkqueues=async function(){
  renderLoading('Loading operational workqueues…');
  const facility=operationFacility();
  const summary=await api(`/workqueues/summary?facility_code=${encodeURIComponent(facility)}`);
  const allQueues=summary.queues||[],totals=summary.totals||{};state.v7Queues=allQueues;
  if(!state.selectedWorkqueueId&&allQueues.length)state.selectedWorkqueueId=allQueues.find(q=>q.name.includes('Walk-In'))?.queue_id||allQueues[0].queue_id;
  const detail=state.selectedWorkqueueId?await api(`/workqueues/${encodeURIComponent(state.selectedWorkqueueId)}/items?limit=500`):null;state.v7QueueDetail=detail;
  const f=state.v7WorkqueueFilters||{};
  const queues=allQueues.filter(q=>(!f.search||[q.name,q.code,q.service_area,q.owner_team].join(' ').toLowerCase().includes(f.search.toLowerCase()))&&(!f.category||q.category===f.category));
  const selected=allQueues.find(q=>q.queue_id===state.selectedWorkqueueId)||allQueues[0];
  const items=(detail?.items||[]).filter(i=>!f.status||i.status===f.status);
  state.selectedWorkqueueItemIds=(state.selectedWorkqueueItemIds||[]).filter(id=>(detail?.items||[]).some(x=>x.item_id===id));
  const selectedItems=v7SelectedWorkqueueItems();
  const avgAge=allQueues.length?(allQueues.reduce((n,q)=>n+Number(q.metrics.avg_age_days||0),0)/allQueues.length).toFixed(1):'0.0';
  $('#mainContent').innerHTML=`<section class="ua-page v7-workqueue-page">${uaPageTitle('Workqueue Management','Every action below is connected to the backend, validated, audited and reversible where applicable.',`<button class="ua-button" data-v7-action="refresh-workqueues">↻ Refresh</button>`)}
    <div class="ua-kpi-grid v7-workqueue-kpis">${uaKpi('Active Queues',totals.active_queues||0,'Configured')}${uaKpi('Active Items',totals.active_items||0,'Needs action')}${uaKpi('Deferred',totals.deferred_items||0,'Scheduled follow-up')}${uaKpi('Overdue',totals.overdue_items||0,'SLA exceeded','danger')}${uaKpi('High Priority',totals.high_priority||0,'Escalate','warning')}${uaKpi('Avg Age',avgAge,'Days')}</div>
    <div class="v7-resizable-workspace v7-workqueue-workspace" data-v7-layout="workqueues" style="${v7LayoutStyle('workqueues',[420,650])}">
      <section class="v7-pane"><article class="ua-card v7-fill-card"><div class="ua-card-header"><div><h2>Queue Directory</h2><p>Select a queue to load its live items.</p></div></div><div class="v7-queue-filter"><input id="v7QueueSearch" value="${esc(f.search||'')}" placeholder="Search queues"><select id="v7QueueCategory">${v6Option('','All categories',f.category)}${v6Unique(allQueues.map(q=>q.category)).map(x=>v6Option(x,statusLabel(x),f.category)).join('')}</select><button class="ua-button compact primary" data-v7-action="apply-queue-filter">Apply</button><button class="ua-button compact" data-v7-action="clear-queue-filter">Clear</button></div><div class="v7-scroll"><table class="ua-data-table"><thead><tr><th>Queue</th><th>Owner</th><th>Active</th><th>Deferred</th><th>Overdue</th></tr></thead><tbody>${queues.map(q=>`<tr class="${q.queue_id===state.selectedWorkqueueId?'selected-row':''}"><td><button class="ua-link" data-v7-action="select-workqueue" data-queue-id="${esc(q.queue_id)}"><strong>${esc(q.name)}</strong><small>${esc(q.service_area)}</small></button></td><td>${esc(q.owner_team)}</td><td>${q.metrics.active}</td><td>${q.metrics.deferred}</td><td>${q.metrics.overdue}</td></tr>`).join('')}</tbody></table></div></article></section>
      <div class="v7-splitter" data-v7-splitter="0" title="Drag to resize"></div>
      <section class="v7-pane"><article class="ua-card v7-fill-card"><div class="ua-card-header"><div><h2>${esc(detail?.queue?.name||'Queue Items')}</h2><p>${items.length} visible items · ${state.selectedWorkqueueItemIds.length} selected</p></div><div><button class="ua-button compact" data-v7-action="select-all-items">Select Visible</button><button class="ua-button compact" data-v7-action="clear-item-selection">Clear</button></div></div><div class="v7-item-filter"><select id="v7QueueItemStatus">${v6Option('','All item statuses',f.status)}${['ACTIVE','DEFERRED','COMPLETED','CANCELLED'].map(x=>v6Option(x,statusLabel(x),f.status)).join('')}</select><button class="ua-button compact" data-v7-action="apply-item-filter">Apply</button></div><div class="v7-scroll"><table class="ua-data-table v7-workqueue-items"><thead><tr><th></th><th>Item</th><th>Patient</th><th>Reason</th><th>Priority</th><th>Status</th><th>Assigned</th><th>Due</th><th></th></tr></thead><tbody>${items.length?v7QueueItemRows(items):'<tr><td colspan="9" class="v6-empty">No items match this filter.</td></tr>'}</tbody></table></div></article></section>
      <div class="v7-splitter" data-v7-splitter="1" title="Drag to resize"></div>
      <aside class="v7-pane"><article class="ua-card v7-fill-card"><div class="ua-card-header"><div><h2>Selected Queue Actions</h2><p>${esc(selected?.name||'Select a queue')}</p></div></div><div class="ua-card-body v7-scroll"><div class="queue-summary-grid">${[['Active',detail?.metrics?.active||0],['Deferred',detail?.metrics?.deferred||0],['Total',detail?.metrics?.total||0],['Overdue',detail?.metrics?.overdue||0],['High Priority',detail?.metrics?.high_priority||0],['Oldest',`${detail?.metrics?.oldest_age_days||0} d`]].map(([l,n])=>`<div class="queue-summary-cell"><span>${l}</span><strong>${n}</strong></div>`).join('')}</div><div class="v7-selection-summary"><strong>${selectedItems.length}</strong><span>workqueue item${selectedItems.length===1?'':'s'} selected</span></div><div class="suggested-actions v7-actions"><h3>Suggested Actions</h3>${[['Open Queue','View and process items','queue','open-queue',false],['Reassign','Assign selected items to a user or team','team','reassign',true],['Route','Move selected items to another queue','transfer','route',true],['Defer','Pause selected items with follow-up time','schedule','defer',true],['Complete','Resolve selected items','orders','complete',true],['Resume / Reopen','Return selected items to active work','patient','resume',true],['Cancel','Cancel selected items with reason','audit','cancel',true],['Create Task','Create a new queue task','document','create-task',false],['View Rules','Review routing and SLA rules','settings','view-rules',false]].map(([a,b,ic,op,needs])=>`<button class="suggested-action" data-v7-action="queue-${op}" ${needs&&!selectedItems.length?'disabled':''}><span class="action-icon">${v4Icon(ic)}</span><span><strong>${a}</strong><small>${b}</small></span><span class="arrow">›</span></button>`).join('')}</div></div></article></aside>
    </div></section>`;
  requestAnimationFrame(()=>v7EnhancePanels());
};

function v7QueueItemsRequired(){const items=v7SelectedWorkqueueItems();if(!items.length)throw new Error('Select at least one workqueue item first.');return items;}
async function v7OpenQueueModal(){const d=state.v7QueueDetail;if(!d)throw new Error('Select a queue.');openModal(`${d.queue.name} — Queue Workbench`,`<div class="v7-modal-toolbar"><span>${d.items.length} items</span><button class="ua-button compact" data-v7-action="modal-select-all">Select All</button><button class="ua-button compact" data-v7-action="clear-item-selection">Clear</button></div><div class="table-wrap v7-modal-table"><table class="ua-data-table"><thead><tr><th></th><th>Item</th><th>Patient</th><th>Priority</th><th>Status</th><th>Assigned</th><th>Due</th></tr></thead><tbody>${v7QueueItemRows(d.items)}</tbody></table></div>`,`<button class="ua-button" data-modal-action="close">Close</button><button class="ua-button primary" data-v7-action="queue-reassign">Reassign Selected</button>`,'Operational Workqueue');$('#modal').classList.add('v7-large-modal');}
async function v7QueueActionDialog(op){
  const items=op==='CREATE'?[]:v7QueueItemsRequired();
  if(op==='ASSIGN'){
    const recipients=await api('/messages/recipients');openModal('Reassign Workqueue Items',`<div class="form-grid"><label class="field full"><span>Assign to user or team</span><select id="v7AssignTo">${recipients.map(u=>v6Option(u.display_name,`${u.display_name} · ${statusLabel(u.role_code)}`)).join('')}<option>Front Desk Team A</option><option>Health Records Team</option><option>NHIF Verification Team</option><option>Care Coordination Team</option></select></label><label class="field full"><span>Reason</span><textarea id="v7QueueNote">Reassigned for workflow ownership and timely completion.</textarea></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v7-action="confirm-queue-action" data-op="ASSIGN">Reassign ${items.length}</button>`,'Workqueue Assignment');return;
  }
  if(op==='ROUTE'){
    const current=state.v7QueueDetail?.queue?.code;openModal('Route Workqueue Items',`<div class="form-grid"><label class="field full"><span>Destination queue</span><select id="v7TargetQueue">${(state.v7Queues||[]).filter(q=>q.code!==current).map(q=>v6Option(q.code,`${q.name} · ${q.owner_team}`)).join('')}</select></label><label class="field full"><span>Routing reason</span><textarea id="v7QueueNote">Routed to the appropriate operational workqueue.</textarea></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v7-action="confirm-queue-action" data-op="ROUTE">Route ${items.length}</button>`,'Workqueue Routing');return;
  }
  if(op==='DEFER'){
    openModal('Defer Workqueue Items',`<div class="form-grid"><label class="field"><span>Follow-up in hours</span><input id="v7DeferHours" type="number" min="1" max="8760" value="24"></label><label class="field full"><span>Reason</span><textarea id="v7QueueNote">Awaiting information or an external dependency.</textarea></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v7-action="confirm-queue-action" data-op="DEFER">Defer ${items.length}</button>`,'Workqueue Deferral');return;
  }
  if(['COMPLETE','RESUME','REOPEN','CANCEL'].includes(op)){
    openModal(`${statusLabel(op)} Workqueue Items`,`<label class="field"><span>Reason / completion note</span><textarea id="v7QueueNote">${op==='COMPLETE'?'Work completed and verified.':op==='CANCEL'?'Cancelled after authorized workflow review.':'Returned to active follow-up.'}</textarea></label>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v7-action="confirm-queue-action" data-op="${op}">${statusLabel(op)} ${items.length}</button>`,'Workqueue Course Change');return;
  }
}
function v7CreateTaskDialog(){const q=state.v7QueueDetail?.queue;if(!q)throw new Error('Select a queue.');const selectedPatient=state.selectedPatientId||'';openModal('Create Workqueue Task',`<div class="form-grid"><label class="field full"><span>Title</span><input id="v7TaskTitle" value="Follow-up task"></label><label class="field full"><span>Reason / instructions</span><textarea id="v7TaskReason">Complete required follow-up and document the outcome.</textarea></label><label class="field"><span>Priority</span><select id="v7TaskPriority">${['ROUTINE','HIGH','URGENT','STAT'].map(x=>`<option>${x}</option>`).join('')}</select></label><label class="field"><span>Due in hours</span><input id="v7TaskDue" type="number" value="24" min="1" max="8760"></label><label class="field"><span>Assigned to</span><input id="v7TaskAssignee" value="${esc(q.owner_team||'')}"></label><label class="field"><span>Patient MPI (optional)</span><input id="v7TaskPatient" value="${esc(selectedPatient)}"></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v7-action="confirm-create-task">Create Task</button>`,'Workqueue Task');}

const v7BaseAdminRender=renderSystemAdminV5;
renderSystemAdminV5=async function(){await v7BaseAdminRender();const shell=$('.v5-admin-shell');if(!shell)return;shell.classList.add('v7-admin-shell','v7-resizable-workspace');shell.dataset.v7Layout='admin';shell.style.cssText+=`;${v7LayoutStyle('admin',[300,900])}`;if(!shell.querySelector('.v7-splitter')){const children=[...shell.children];shell.innerHTML='';children.forEach((child,i)=>{shell.appendChild(child);if(i<2){const split=document.createElement('div');split.className='v7-splitter';split.dataset.v7Splitter=String(i);split.title='Drag to resize';shell.appendChild(split);}});}requestAnimationFrame(()=>v7EnhancePanels());};

document.addEventListener('pointerdown',e=>{
  const splitter=e.target.closest('[data-v7-splitter]');if(!splitter)return;
  const layout=splitter.closest('[data-v7-layout]');if(!layout||innerWidth<1100)return;
  e.preventDefault();const index=Number(splitter.dataset.v7Splitter),rect=layout.getBoundingClientRect();
  const c1=parseFloat(getComputedStyle(layout).getPropertyValue('--v7-col1'))||420,c2=parseFloat(getComputedStyle(layout).getPropertyValue('--v7-col2'))||620;
  const move=ev=>{let n1=c1,n2=c2;if(index===0)n1=Math.max(240,Math.min(ev.clientX-rect.left,rect.width-c2-300));else n2=Math.max(300,Math.min(ev.clientX-rect.left-c1-16,rect.width-c1-300));layout.style.setProperty('--v7-col1',`${n1}px`);layout.style.setProperty('--v7-col2',`${n2}px`);};
  const up=()=>{document.removeEventListener('pointermove',move);document.removeEventListener('pointerup',up);const vals=[parseFloat(getComputedStyle(layout).getPropertyValue('--v7-col1')),parseFloat(getComputedStyle(layout).getPropertyValue('--v7-col2'))];localStorage.setItem(`umoja-layout-${layout.dataset.v7Layout}`,JSON.stringify(vals));document.body.classList.remove('v7-resizing');};
  document.body.classList.add('v7-resizing');document.addEventListener('pointermove',move);document.addEventListener('pointerup',up);
},true);

document.addEventListener('change',e=>{const cb=e.target.closest('[data-v7-wq-item]');if(!cb)return;const ids=new Set(state.selectedWorkqueueItemIds||[]);cb.checked?ids.add(cb.dataset.v7WqItem):ids.delete(cb.dataset.v7WqItem);state.selectedWorkqueueItemIds=[...ids];document.querySelectorAll(`[data-v7-wq-item="${CSS.escape(cb.dataset.v7WqItem)}"]`).forEach(x=>x.checked=cb.checked);},true);

document.addEventListener('click',async e=>{
  const max=e.target.closest('[data-v7-panel-maximize]');if(max){e.preventDefault();e.stopImmediatePropagation();max.closest('.v7-resizable-panel')?.classList.toggle('v7-panel-maximized');return;}
  const b=e.target.closest('[data-v7-action]');if(!b)return;e.preventDefault();e.stopImmediatePropagation();
  try{
    const a=b.dataset.v7Action;
    if(a==='workflow-next'){
      state.selectedPatientId=b.dataset.patientId||state.selectedPatientId;saveState();
      if(b.dataset.kind==='appointment'){const result=await api(`/appointments/${encodeURIComponent(b.dataset.appointment)}`,{method:'PATCH',body:JSON.stringify({status:'ARRIVED',actor:currentRole().user,note:'Patient arrived from the state-aware front desk workflow.'})});toast('Patient arrived',result.notification?.message||'Downstream teams were notified.',1000);}
      else if(b.dataset.kind==='encounter'){await api(`/encounters/${encodeURIComponent(b.dataset.encounter)}/status`,{method:'PATCH',body:JSON.stringify({status:b.dataset.status,actor:currentRole().user,note:`${statusLabel(b.dataset.status)} from state-aware workflow`})});toast('Workflow advanced',statusLabel(b.dataset.status),1000);}
      else if(b.dataset.kind==='walkin'){await api(`/walk-ins/${encodeURIComponent(b.dataset.walkin)}`,{method:'PATCH',body:JSON.stringify({action:b.dataset.course,actor:currentRole().user,note:`${statusLabel(b.dataset.course)} from walk-in workflow`})});toast('Walk-in advanced',statusLabel(b.dataset.course),1000);}
      else if(b.dataset.kind==='discharge'){return showDischargeModal(b.dataset.encounter);}
      else return navigate('patient-station',{preservePatient:true});
      return renderTodayPatients();
    }
    if(a==='open-station'){state.selectedPatientId=b.dataset.patientId;saveState();return navigate('patient-station',{preservePatient:true});}
    if(a==='open-chart'){state.selectedPatientId=b.dataset.patientId;saveState();return navigate('chart');}
    if(a==='event-history'){state.selectedPatientId=b.dataset.patientId;saveState();return navigate('event-management');}
    if(a==='print-label'){toast('Print job prepared','Patient label and wristband are ready for the configured printer.');return;}
    if(a==='benefit-check'){toast('Eligibility submitted','NHIF / payer benefit verification has been queued.');return;}
    if(a==='travel-screen'){toast('Screening opened','Travel and communicable-disease screening started.');return;}
    if(a==='refresh-workqueues')return renderWorkqueues();
    if(a==='select-workqueue'){state.selectedWorkqueueId=b.dataset.queueId;state.selectedWorkqueueItemIds=[];return renderWorkqueues();}
    if(a==='apply-queue-filter'){state.v7WorkqueueFilters.search=$('#v7QueueSearch')?.value.trim()||'';state.v7WorkqueueFilters.category=$('#v7QueueCategory')?.value||'';return renderWorkqueues();}
    if(a==='clear-queue-filter'){state.v7WorkqueueFilters={search:'',category:'',status:''};return renderWorkqueues();}
    if(a==='apply-item-filter'){state.v7WorkqueueFilters.status=$('#v7QueueItemStatus')?.value||'';return renderWorkqueues();}
    if(a==='select-all-items'){state.selectedWorkqueueItemIds=(state.v7QueueDetail?.items||[]).filter(x=>!state.v7WorkqueueFilters.status||x.status===state.v7WorkqueueFilters.status).map(x=>x.item_id);return renderWorkqueues();}
    if(a==='modal-select-all'){state.selectedWorkqueueItemIds=(state.v7QueueDetail?.items||[]).map(x=>x.item_id);document.querySelectorAll('[data-v7-wq-item]').forEach(x=>x.checked=true);return;}
    if(a==='clear-item-selection'){state.selectedWorkqueueItemIds=[];if($('#modal')&&!$('#modal').classList.contains('hidden'))document.querySelectorAll('[data-v7-wq-item]').forEach(x=>x.checked=false);else return renderWorkqueues();return;}
    if(a==='queue-open-queue')return v7OpenQueueModal();
    if(a==='queue-reassign')return v7QueueActionDialog('ASSIGN');
    if(a==='queue-route')return v7QueueActionDialog('ROUTE');
    if(a==='queue-defer')return v7QueueActionDialog('DEFER');
    if(a==='queue-complete')return v7QueueActionDialog('COMPLETE');
    if(a==='queue-resume'){const selected=v7QueueItemsRequired();const op=selected.some(x=>['COMPLETED','CANCELLED'].includes(x.status))?'REOPEN':'RESUME';return v7QueueActionDialog(op);}
    if(a==='queue-cancel')return v7QueueActionDialog('CANCEL');
    if(a==='queue-create-task')return v7CreateTaskDialog();
    if(a==='queue-view-rules'){const q=state.v7QueueDetail?.queue||state.v7Queues?.find(x=>x.queue_id===state.selectedWorkqueueId);return openModal('Workqueue Routing Rules',`<pre class="v7-rule-view">${esc(v7QueueRuleText(q))}</pre>`,`<button class="ua-button primary" data-modal-action="close">Close</button>`,'Rules and SLA');}
    if(a==='confirm-queue-action'){
      const items=v7QueueItemsRequired(),op=b.dataset.op;const payloadBase={action:op,actor:currentRole().user,note:$('#v7QueueNote')?.value||`${statusLabel(op)} from Workqueue Management.`};
      if(op==='ASSIGN')payloadBase.assigned_to=$('#v7AssignTo').value;if(op==='ROUTE')payloadBase.target_queue_code=$('#v7TargetQueue').value;if(op==='DEFER')payloadBase.defer_hours=Number($('#v7DeferHours').value||24);
      for(const item of items)await api(`/workqueue-items/${encodeURIComponent(item.item_id)}`,{method:'PATCH',body:JSON.stringify(payloadBase)});
      closeModal();state.selectedWorkqueueItemIds=[];toast('Workqueue updated',`${items.length} item${items.length===1?'':'s'} ${statusLabel(op).toLowerCase()}.`);return renderWorkqueues();
    }
    if(a==='confirm-create-task'){const q=state.v7QueueDetail?.queue;await api(`/workqueues/${encodeURIComponent(q.queue_id)}/items`,{method:'POST',body:JSON.stringify({patient_mpi_id:$('#v7TaskPatient').value||null,title:$('#v7TaskTitle').value,reason:$('#v7TaskReason').value,priority:$('#v7TaskPriority').value,assigned_to:$('#v7TaskAssignee').value||null,due_hours:Number($('#v7TaskDue').value||24),created_by:currentRole().user})});closeModal();toast('Task created','The task was added to the selected workqueue.');return renderWorkqueues();}
    if(a==='item-history'){const events=await api(`/workqueue-items/${encodeURIComponent(b.dataset.itemId)}/events`);return openModal('Workqueue Item History',`<div class="v7-event-list">${events.map(ev=>`<article><strong>${esc(statusLabel(ev.action))}</strong><span>${esc(ev.actor)} · ${fmtDate(ev.occurred_at)}</span><p>${esc(ev.status_before||'—')} → ${esc(ev.status_after||'—')} · ${esc(ev.note||'')}</p></article>`).join('')||'<p>No history available.</p>'}</div>`,`<button class="ua-button primary" data-modal-action="close">Close</button>`,'Audit History');}
  }catch(err){console.error(err);toast('Action failed',err.message||String(err));}
},true);


/* --------------------------------------------------------------------------
   Release 8.0 results review, automatic chart closure and comprehensive
   facility/unit/bed inventory. Operational navigation does not retain a
   patient chart unless a patient-specific control explicitly requests it.
--------------------------------------------------------------------------- */
state.v8ResultFilters=state.v8ResultFilters||{search:'',flag:'',category:''};
state.v8SelectedResultId=state.v8SelectedResultId||null;
state.v8UnitSearch=state.v8UnitSearch||'';
state.v8BedStatus=state.v8BedStatus||'';

const v8OperationalRoutes=new Set(['dashboard','today-patients','patient-station','workqueues','patient-flow','patient-search','registration','scheduling','bed-board','emergency','recent-discharges','messages','admin','analytics','quality','public-health','supply','revenue']);
const v8BaseNavigate=navigate;
navigate=function(route,options={}){
  const preserve=Boolean(options&&options.preservePatient);
  if(v8OperationalRoutes.has(route)&&!preserve&&state.selectedPatientId){
    state.selectedPatientId=null;
    state.selectedFlowSheetId=null;
    state.chartTab='summary';
    state.v8SelectedResultId=null;
    saveState();
    document.body.classList.remove('patient-context-active');
  }
  return v8BaseNavigate(route);
};

function v8ResultCategory(result){
  const text=`${result.test_name||''} ${result.source||''}`.toLowerCase();
  if(/x-ray|radiograph|ultrasound|ct |mri|imaging|radiology|echo|mammogram/.test(text))return 'IMAGING';
  if(/ecg|ekg|cardiac|troponin|bnp/.test(text))return 'CARDIOLOGY';
  if(/histology|cytology|biopsy|pathology/.test(text))return 'PATHOLOGY';
  if(/culture|malaria|hiv|hepatitis|microbiology|tb |gene xpert|pcr/.test(text))return 'MICROBIOLOGY';
  if(/haemoglobin|white blood|platelet|neutrophil|haematology/.test(text))return 'HAEMATOLOGY';
  if(/creatinine|sodium|potassium|glucose|chemistry|liver|renal/.test(text))return 'CHEMISTRY';
  return 'OTHER';
}
function v8ResultFlagClass(flag){const f=String(flag||'').toUpperCase();return f==='CRITICAL'?'critical':['HIGH','LOW','ABNORMAL','POSITIVE'].includes(f)?'abnormal':'normal';}
function v8FilteredResults(results){
  const f=state.v8ResultFilters||{};const search=String(f.search||'').toLowerCase();
  return results.filter(r=>(!search||`${r.test_name} ${r.value} ${r.source}`.toLowerCase().includes(search))&&(!f.flag||String(r.flag).toUpperCase()===f.flag)&&(!f.category||v8ResultCategory(r)===f.category));
}
function v8ResultDetail(result){
  if(!result)return `<div class="v8-result-empty"><span>◉</span><h3>Select a result</h3><p>Choose a diagnostic result to review its status, provenance and acknowledgement history.</p></div>`;
  const critical=String(result.flag).toUpperCase()==='CRITICAL';
  return `<div class="v8-result-detail-head ${v8ResultFlagClass(result.flag)}"><span>${esc(v8ResultCategory(result))}</span><h2>${esc(result.test_name)}</h2><strong>${esc(result.value)} ${esc(result.unit||'')}</strong><b>${esc(statusLabel(result.flag))}</b></div>
    <dl class="v8-result-facts"><div><dt>Result ID</dt><dd>${esc(result.result_id)}</dd></div><div><dt>Status</dt><dd>${esc(statusLabel(result.status))}</dd></div><div><dt>Source</dt><dd>${esc(result.source)}</dd></div><div><dt>Issued</dt><dd>${fmtDate(result.issued_at)}</dd></div><div><dt>Acknowledgement</dt><dd>${result.acknowledged?`Acknowledged by ${esc(result.acknowledged_by||'clinician')}`:'Pending clinical acknowledgement'}</dd></div><div><dt>Acknowledged at</dt><dd>${result.acknowledged_at?fmtDate(result.acknowledged_at):'—'}</dd></div></dl>
    ${critical&&!result.acknowledged?`<div class="alert danger"><strong>Critical result</strong><br>Document the action taken before acknowledging this result.</div><label class="field"><span>Action taken</span><textarea id="v8ResultAction">Provider notified; patient assessment and treatment plan reviewed.</textarea></label><button class="ua-button danger full-width" data-v8-action="ack-result" data-result-id="${esc(result.result_id)}">Acknowledge Critical Result</button>`:`<div class="alert ${result.acknowledged?'success':'info'}"><strong>${result.acknowledged?'Acknowledgement complete':'Review complete'}</strong><br>${result.acknowledged?'The acknowledgement is retained in the legal audit history.':'No critical acknowledgement is required for this result.'}</div>`}
    <div class="v8-result-actions"><button class="ua-button" data-v8-action="print-result">Print</button><button class="ua-button" data-v8-action="copy-result">Copy Summary</button><button class="ua-button" data-route="orders" data-preserve-patient="true">Related Orders</button></div>`;
}

renderResults=async function(){
  if(!state.selectedPatientId){$('#mainContent').innerHTML=v5EmptyRecordWorkspace('Results Review');return;}
  renderLoading('Loading diagnostic results…');
  const patient=await selectedPatient();if(!patient){$('#mainContent').innerHTML=v5EmptyRecordWorkspace('Results Review');return;}
  const results=await api(`/results?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`);
  state.v8Results=results;
  if(!state.v8SelectedResultId&&results.length)state.v8SelectedResultId=results[0].result_id;
  if(state.v8SelectedResultId&&!results.some(r=>r.result_id===state.v8SelectedResultId))state.v8SelectedResultId=results[0]?.result_id||null;
  const filtered=v8FilteredResults(results);const selected=results.find(r=>r.result_id===state.v8SelectedResultId)||filtered[0]||null;
  const counts={total:results.length,critical:results.filter(r=>String(r.flag).toUpperCase()==='CRITICAL').length,abnormal:results.filter(r=>['HIGH','LOW','ABNORMAL','POSITIVE'].includes(String(r.flag).toUpperCase())).length,pending:results.filter(r=>!r.acknowledged&&String(r.flag).toUpperCase()==='CRITICAL').length};
  const encounter=v5CurrentEncounter(patient);
  $('#mainContent').innerHTML=`${pageHeader('Longitudinal Chart','Results Review','Patient-specific laboratory, imaging and diagnostic results with critical-result acknowledgement and audit history.',`<button class="btn" data-v8-action="refresh-results">Refresh</button><button class="btn" data-route="chart" data-preserve-patient="true">Back to Chart</button>`)}${v5RecordHeader(patient,encounter,true)}
    <section class="v8-results-kpis">${metricCard('All results',counts.total,'Selected record')}${metricCard('Critical',counts.critical,counts.pending+' unacknowledged',counts.pending?'danger':'')}${metricCard('Abnormal',counts.abnormal,'High, low or abnormal')}${metricCard('Final',results.filter(r=>r.status==='FINAL').length,'Released results')}</section>
    <section class="v8-results-shell">
      <article class="ua-card v8-results-list"><div class="ua-card-header"><div><h2>Diagnostic Results</h2><p>${filtered.length} of ${results.length} results</p></div></div><div class="v8-result-filter"><input id="v8ResultSearch" value="${esc(state.v8ResultFilters.search)}" placeholder="Search test, value or source"><select id="v8ResultCategory"><option value="">All categories</option>${['HAEMATOLOGY','CHEMISTRY','MICROBIOLOGY','IMAGING','CARDIOLOGY','PATHOLOGY','OTHER'].map(x=>`<option value="${x}" ${state.v8ResultFilters.category===x?'selected':''}>${statusLabel(x)}</option>`).join('')}</select><select id="v8ResultFlag"><option value="">All flags</option>${['CRITICAL','HIGH','LOW','ABNORMAL','NORMAL'].map(x=>`<option value="${x}" ${state.v8ResultFilters.flag===x?'selected':''}>${statusLabel(x)}</option>`).join('')}</select><button class="ua-button primary" data-v8-action="apply-result-filter">Apply</button><button class="ua-button" data-v8-action="clear-result-filter">Clear</button></div><div class="v8-result-table-wrap"><table class="ua-data-table v8-result-table"><thead><tr><th>Issued</th><th>Test</th><th>Result</th><th>Flag</th><th>Source</th><th>Acknowledgement</th></tr></thead><tbody>${filtered.map(r=>`<tr class="${r.result_id===selected?.result_id?'selected':''}" data-v8-action="select-result" data-result-id="${esc(r.result_id)}"><td>${fmtDate(r.issued_at)}</td><td><strong>${esc(r.test_name)}</strong><small>${esc(v8ResultCategory(r))}</small></td><td><b>${esc(r.value)} ${esc(r.unit||'')}</b></td><td><span class="v8-result-flag ${v8ResultFlagClass(r.flag)}">${esc(statusLabel(r.flag))}</span></td><td>${esc(r.source)}</td><td>${r.acknowledged?`<span class="ua-status arrived">Acknowledged</span>`:`<span class="ua-status waiting">Review</span>`}</td></tr>`).join('')||'<tr><td colspan="6"><div class="v8-result-empty"><h3>No matching results</h3><p>Clear the filters or return to the selected patient chart.</p></div></td></tr>'}</tbody></table></div></article>
      <aside class="ua-card v8-result-detail">${v8ResultDetail(selected)}</aside>
    </section>`;
};

renderBedBoardV5=async function(){
  renderLoading('Loading complete unit inventory…');
  const facility=operationFacility();const units=await api(`/bed-units?facility_code=${encodeURIComponent(facility)}`);
  const unitExists=units.some(u=>u.unit===state.selectedBedUnit);if(!unitExists)state.selectedBedUnit=units[0]?.unit||null;
  const allBeds=state.selectedBedUnit?await api(`/beds?facility_code=${encodeURIComponent(facility)}&unit=${encodeURIComponent(state.selectedBedUnit)}`):[];
  const needle=String(state.v8UnitSearch||'').toLowerCase();const visibleUnits=units.filter(u=>!needle||u.unit.toLowerCase().includes(needle));
  const beds=allBeds.filter(b=>!state.v8BedStatus||String(b.status).toUpperCase()===state.v8BedStatus);
  const totals=units.reduce((a,u)=>({total:a.total+u.total,available:a.available+u.available,occupied:a.occupied+u.occupied,turnover:a.turnover+u.turnover,blocked:a.blocked+u.blocked}),{total:0,available:0,occupied:0,turnover:0,blocked:0});
  $('#mainContent').innerHTML=`${pageHeader('ADT and Capacity','Unit Manager','All configured hospital units are available, while beds and patient details load only after one unit is selected.',`<button class="btn" data-v8-action="refresh-bed-board">Refresh</button><button class="btn" data-v5-action="change-context">Change Context</button>`)}
    <section class="v8-bed-kpis">${metricCard('Configured units',units.length,'Selected hospital')}${metricCard('Configured beds / stations',totals.total,'All units')}${metricCard('Available',totals.available,'Ready for assignment')}${metricCard('Occupied',totals.occupied,'Current census')}${metricCard('Turnover',totals.turnover,'Dirty or cleaning')}${metricCard('Blocked',totals.blocked,'Operational hold')}</section>
    <section class="v8-unit-manager"><aside class="ua-card v8-unit-directory"><div class="ua-card-header"><div><h2>Hospital Units</h2><p>${visibleUnits.length} of ${units.length} units</p></div></div><div class="v8-unit-search"><input id="v8UnitSearch" value="${esc(state.v8UnitSearch)}" placeholder="Search wards, ICU, maternity, theatre…"><button class="ua-button primary" data-v8-action="apply-unit-search">Search</button><button class="ua-button" data-v8-action="clear-unit-search">Clear</button></div><div class="v8-unit-list">${visibleUnits.map(u=>`<button class="${u.unit===state.selectedBedUnit?'active':''}" data-v5-action="select-bed-unit" data-unit="${esc(u.unit)}"><strong>${esc(u.unit)}</strong><span>${u.occupied}/${u.total} occupied</span><div class="v5-capacity-bar"><i style="width:${u.occupancy_percent}%"></i></div><small>${u.available} available · ${u.turnover} turnover · ${u.blocked} blocked</small></button>`).join('')||'<div class="empty-state"><p>No units match the search.</p></div>'}</div></aside>
      <main class="ua-card v8-bed-workspace"><div class="ua-card-header"><div><h2>${esc(state.selectedBedUnit||'Select a unit')}</h2><p>${beds.length} visible of ${allBeds.length} configured beds / stations</p></div><div class="v8-bed-toolbar"><select id="v8BedStatus"><option value="">All statuses</option>${['AVAILABLE','OCCUPIED','ASSIGNED','DIRTY','CLEANING','BLOCKED'].map(x=>`<option value="${x}" ${state.v8BedStatus===x?'selected':''}>${statusLabel(x)}</option>`).join('')}</select><button class="ua-button" data-v8-action="apply-bed-filter">Apply</button></div></div><div class="v5-bed-legend"><span class="available">Available</span><span class="occupied">Occupied</span><span class="turnover">Turnover</span><span class="blocked">Blocked</span></div><div class="v8-bed-grid">${beds.map(b=>`<article class="v5-bed-tile ${String(b.status).toLowerCase()}"><header><strong>${esc(b.room)} · ${esc(b.bed_label)}</strong><span>${esc(statusLabel(b.status))}</span></header>${b.patient?`<button data-patient-id="${esc(b.patient.mpi_id)}"><b>${esc(b.patient.full_name)}</b><small>${esc(b.patient.mrn)} · ${esc(b.encounter?.encounter_id||'')}</small></button>`:'<div class="v5-empty-bed">No patient assigned</div>'}<footer><small>${esc(statusLabel(b.bed_type||'Standard'))}${b.isolation?` · ${esc(b.isolation)}`:''}</small><button class="ua-button compact" data-v5-action="bed-actions" data-bed-id="${esc(b.bed_id)}" data-bed-status="${esc(b.status)}">Actions</button></footer></article>`).join('')||'<div class="empty-state"><p>No beds match the selected status.</p></div>'}</div></main></section>`;
};

document.addEventListener('click',async e=>{
  const b=e.target.closest('[data-v8-action]');if(!b)return;e.preventDefault();e.stopImmediatePropagation();
  try{
    const a=b.dataset.v8Action;
    if(a==='refresh-results')return renderResults();
    if(a==='apply-result-filter'){state.v8ResultFilters={search:$('#v8ResultSearch')?.value.trim()||'',category:$('#v8ResultCategory')?.value||'',flag:$('#v8ResultFlag')?.value||''};return renderResults();}
    if(a==='clear-result-filter'){state.v8ResultFilters={search:'',category:'',flag:''};return renderResults();}
    if(a==='select-result'){state.v8SelectedResultId=b.dataset.resultId;return renderResults();}
    if(a==='ack-result'){await api(`/results/${encodeURIComponent(b.dataset.resultId)}/acknowledge`,{method:'POST',body:JSON.stringify({actor:currentRole().user,action_taken:$('#v8ResultAction')?.value||'Reviewed and acknowledged.'})});toast('Result acknowledged','The clinical action and acknowledgement were recorded.');return renderResults();}
    if(a==='copy-result'){const r=(state.v8Results||[]).find(x=>x.result_id===state.v8SelectedResultId);if(!r)return;await navigator.clipboard?.writeText(`${r.test_name}: ${r.value} ${r.unit||''} (${statusLabel(r.flag)}), ${r.source}, ${fmtDate(r.issued_at)}`);return toast('Result copied','The result summary was copied to the clipboard.');}
    if(a==='print-result'){window.print();return;}
    if(a==='refresh-bed-board')return renderBedBoardV5();
    if(a==='apply-unit-search'){state.v8UnitSearch=$('#v8UnitSearch')?.value.trim()||'';return renderBedBoardV5();}
    if(a==='clear-unit-search'){state.v8UnitSearch='';return renderBedBoardV5();}
    if(a==='apply-bed-filter'){state.v8BedStatus=$('#v8BedStatus')?.value||'';return renderBedBoardV5();}
  }catch(err){console.error(err);toast('Action failed',err.message||String(err));}
},true);


/* --------------------------------------------------------------------------
   Release 8.0 front-desk workflow completion.
   - Filters recalculate both the visible patient rows and KPI counts.
   - Patient workflow actions use record context and backend-validated states.
   - Print forms/labels, benefit verification and travel screening are complete
     audited workflows rather than notification-only placeholders.
--------------------------------------------------------------------------- */
state.v8FrontDeskTabCounts=state.v8FrontDeskTabCounts||{};
state.v8SelectedFrontDeskRow=state.v8SelectedFrontDeskRow||null;
state.v8PrintResult=state.v8PrintResult||null;

function v8FrontDeskCounts(rows){
  const counts={expected:rows.length,arrived:0,checked_in:0,waiting:0,ready_for_provider:0,completed:0};
  rows.forEach(row=>{
    const status=v7Status(row.status);
    if(['ARRIVED','WAITING_REGISTRATION'].includes(status))counts.arrived+=1;
    if(['REGISTERED','CHECKED_IN'].includes(status))counts.checked_in+=1;
    if(['WAITING_TRIAGE','TRIAGED'].includes(status))counts.waiting+=1;
    if(['READY_FOR_PROVIDER','ROOMED','IN_PROGRESS','WAITING_RESULTS','READY_FOR_DISCHARGE','SERVICE_ASSIGNED'].includes(status))counts.ready_for_provider+=1;
    if(['DISCHARGED','COMPLETED','CANCELLED'].includes(status))counts.completed+=1;
  });
  return counts;
}
function v8FrontDeskFilterSummary(){
  const f=state.todayFilters||{};const values=[];
  if(f.search)values.push(`Search: ${f.search}`);if(f.service)values.push(`Service: ${f.service}`);if(f.queue)values.push(`Queue: ${f.queue}`);if(f.status)values.push(`Status: ${statusLabel(f.status)}`);
  return values.length?values.join(' · '):'No filters applied';
}
async function v8FrontDeskTabCounts(currentData){
  const facility=operationFacility();
  const result={};
  const tabs=['yesterday','today','tomorrow'];
  await Promise.all(tabs.map(async tab=>{
    if(tab===state.todayDay&&state.todayDay!=='walkins'){result[tab]=currentData.total||0;return;}
    try{const data=await api(`/today-patients?facility_code=${encodeURIComponent(facility)}&day=${v6DayForTab(tab)}&limit=1`);result[tab]=data.total||0;}catch(_){result[tab]=0;}
  }));
  try{
    if(state.todayDay==='walkins')result.walkins=currentData.total||0;
    else{const walkins=await api(`/walk-ins?facility_code=${encodeURIComponent(facility)}&hours=24`);result.walkins=walkins.length;}
  }catch(_){result.walkins=0;}
  state.v8FrontDeskTabCounts=result;return result;
}
function v8WorkflowButton(row,large=false){
  const a=v7WorkflowAction(row);const cls=large?'front-action v7-primary-workflow':'next-step-btn';
  return `<button class="${cls}" data-v8fd-action="workflow-next" data-kind="${esc(a.kind)}" data-label="${esc(a.label)}" data-appointment="${esc(row.appointment_id||'')}" data-encounter="${esc(row.encounter_id||'')}" data-walkin="${esc(row.walkin_id||'')}" data-patient-id="${esc(row.patient?.mpi_id||'')}" data-status="${esc(a.status||'')}" data-course="${esc(a.action||'')}"><strong>${esc(a.label)}</strong>${large?`<small>${esc(statusLabel(row.status))} → ${esc(a.label)}</small>`:''}</button>`;
}
function v8WorkflowAction(label,action,row){
  return `<button class="front-action v8-functional-action" data-v8fd-action="${action}" data-patient-id="${esc(row.patient?.mpi_id||'')}" data-appointment="${esc(row.appointment_id||'')}" data-encounter="${esc(row.encounter_id||'')}" data-service="${esc(row.service||'')}"><strong>${esc(label)}</strong><small>${action==='print-workflow'?'Labels, wristbands and documents':action==='benefit-workflow'?'NHIF / payer eligibility':action==='travel-workflow'?'Travel and infection risk':'Open selected record workflow'}</small></button>`;
}

renderTodayPatients=async function(){
  renderLoading('Loading patient access operations…');
  const {data,rosters,walkins,points}=await v6LoadTodayData();
  const tabCounts=await v8FrontDeskTabCounts(data);
  const allRows=data.rows||[];const rows=v6TodayRows(allRows);const c=v8FrontDeskCounts(rows);
  const services=v6Unique(allRows.map(r=>r.service)),queues=v6Unique(allRows.map(r=>r.queue)),statuses=v6Unique(allRows.map(r=>v7Status(r.status)));
  const rosterRows=(rosters||[]).slice(0,40);
  let selected=rows.find(r=>r.patient?.mpi_id===state.selectedPatientId)||null;
  if(!selected&&rows.length){selected=rows[0];state.selectedPatientId=selected.patient?.mpi_id;saveState();}
  state.v8SelectedFrontDeskRow=selected;
  $('#mainContent').innerHTML=`<section class="ua-page v8-frontdesk-page">
    ${uaPageTitle("Today's Patients & Front Desk Workflow",'Filters update both patient rows and operational counts. Every selected-patient action opens a complete record-linked workflow.',`<button class="ua-button primary" data-v6-action="open-walkin">Register Walk-In</button><button class="ua-button" data-v6-action="change-context">Change Context</button>`)}
    <div class="v10163-today-workspace">
      <section class="v7-pane v7-patient-list-pane"><article class="ua-card v7-fill-card">
        <div class="today-tabs v6-tabs">${[['yesterday','Yesterday'],['today','Today'],['tomorrow','Tomorrow'],['walkins','Walk-Ins']].map(([id,label])=>`<button class="${state.todayDay===id?'active':''}" data-v8fd-action="today-tab" data-tab="${id}">${label} (${tabCounts[id]??0})</button>`).join('')}</div>
        <div class="today-filterbar v7-filter-grid"><div class="ua-search-filter">${v4Icon('search')}<input id="todaySearch" value="${esc(state.todayFilters.search||'')}" placeholder="Search name, MRN, MPI or phone"></div><select id="todayService" class="simple-select">${v6Option('','All Services',state.todayFilters.service)}${services.map(x=>v6Option(x,x,state.todayFilters.service)).join('')}</select><select id="todayQueue" class="simple-select">${v6Option('','All Queues',state.todayFilters.queue)}${queues.map(x=>v6Option(x,x,state.todayFilters.queue)).join('')}</select><select id="todayStatus" class="simple-select">${v6Option('','All Statuses',state.todayFilters.status)}${statuses.map(x=>v6Option(x,statusLabel(x),state.todayFilters.status)).join('')}</select><button class="ua-button compact primary" data-v8fd-action="apply-filter">Apply</button><button class="ua-button compact" data-v8fd-action="clear-filter">Clear</button></div>
        ${selected?`<section class="v10163-action-dock"><div>${patientAvatar(selected.patient,true)}<span><small>Working patient</small><strong>${esc(selected.patient.full_name)}</strong><em>${esc(selected.patient.mrn)} · ${esc(statusLabel(selected.status))}</em></span></div><div class="v10163-dock-actions">${v8WorkflowButton(selected,true)}<button class="ua-button compact" data-v8fd-action="open-station" data-patient-id="${esc(selected.patient.mpi_id)}">Patient Station</button><button class="ua-button compact" data-v8fd-action="open-chart" data-patient-id="${esc(selected.patient.mpi_id)}">Chart</button></div></section>`:'<section class="v10163-action-dock empty">Select a patient to reveal the next valid action.</section>'}
        <div class="v8-filter-result"><strong>${rows.length}</strong> matching patients of ${data.total||0}<span>${esc(v8FrontDeskFilterSummary())}</span></div>
        <div class="today-metrics v7-metrics">${[['Expected',c.expected],['Arrived',c.arrived],['Checked In',c.checked_in],['Waiting',c.waiting],['Ready',c.ready_for_provider],['Completed',c.completed]].map(([l,n])=>`<div class="today-metric"><div><span>${l}</span><strong>${n}</strong></div></div>`).join('')}</div>
        <div class="table-wrap v7-scroll"><table class="ua-data-table v7-patient-table"><thead><tr><th>Time</th><th>Patient</th><th>MRN</th><th>Service</th><th>Status</th><th class="v10163-action-column">Next Valid Step</th></tr></thead><tbody>${rows.length?rows.map(row=>`<tr class="${selected?.patient?.mpi_id===row.patient?.mpi_id?'selected-row':''}" data-v8fd-action="select-patient" data-patient-id="${esc(row.patient?.mpi_id)}"><td>${new Date(row.scheduled_start).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</td><td><strong>${esc(row.patient?.full_name||'Unknown')}</strong></td><td>${esc(row.patient?.mrn||'—')}</td><td>${esc(row.service||'—')}</td><td><span class="ua-status ${uaStatusClass(row.status)}">${esc(statusLabel(row.status))}</span></td><td class="v10163-action-column">${v8WorkflowButton(row)}</td></tr>`).join(''):`<tr><td colspan="6" class="v6-empty">No records match the selected filters. Clear or adjust the filter criteria.</td></tr>`}</tbody></table></div>
        <div class="ua-pagination"><span>${rows.length} visible of ${data.total||0}</span><button class="ua-button compact" data-v8fd-action="refresh">Refresh</button></div>
      </article></section>
      <section class="v7-pane v7-workflow-pane"><article class="ua-card v7-fill-card"><div class="ua-card-header"><h2>Selected Patient Workflow</h2></div><div class="ua-card-body v10163-workflow-body">${selected?`<div class="v6-selected-patient"><div>${patientAvatar(selected.patient,true)}</div><div><h2>${esc(selected.patient.full_name)}</h2><p>${esc(selected.patient.mrn)} · ${esc(selected.service)} · <b>${esc(statusLabel(selected.status))}</b></p></div></div><div class="v7-next-step-card"><span>Next valid workflow action</span>${v8WorkflowButton(selected,true)}</div><div class="action-grid v7-secondary-grid">${v8WorkflowAction('Open Patient Station','open-station',selected)}${v8WorkflowAction('Print Forms & Labels','print-workflow',selected)}${v8WorkflowAction('Benefit Check','benefit-workflow',selected)}${v8WorkflowAction('Travel Screening','travel-workflow',selected)}${v8WorkflowAction('Event History','event-history',selected)}${v8WorkflowAction('Open Chart','open-chart',selected)}</div><div class="v7-workflow-history"><h3>Workflow guardrails</h3><p>Completed steps are unavailable. The next valid action changes automatically after every saved transition. Printing, eligibility and screening create persistent audit records.</p></div>`:`<div class="v6-empty">No patient is selected in the filtered worklist.</div>`}</div></article><article class="ua-card"><div class="ua-card-header"><h2>Walk-In Workflow</h2></div><div class="ua-card-body"><div class="workflow-steps-v4">${['Search/Create','Demographics','Coverage & Consent','Encounter','Arrival & Route'].map((x,i)=>`<div class="workflow-step-v4"><b>${i+1}</b><span>${x}</span></div>`).join('')}</div><button class="ua-button primary full-width" data-v6-action="open-walkin">Start Walk-In Registration</button></div></article></section>
    </div><details class="v10163-roster-drawer ua-card"><summary><span><strong>On-Duty Teams & Service Points</strong><small>${rosterRows.length} teams · ${points.length} service points · ${esc(data.facility?.name||operationFacility())}</small></span><span>Service coverage & unit context</span></summary><div class="v10163-roster-grid">${rosterRows.length?rosterRows.map(r=>`<button class="v6-roster-row" data-v6-action="choose-service-point" data-service-point="${esc(r.service_point.service_point_id)}"><strong>${esc(r.service_point.name)}</strong><span>${esc(r.service_point.clinic||r.service_point.department)} · ${esc(r.lead_provider||r.team_name)}</span><small>${String(r.shift_start).slice(0,5)}–${String(r.shift_end).slice(0,5)} · ${esc(r.service_point.room||'Room TBD')} · Capacity ${r.service_point.queue_capacity}</small></button>`).join(''):'<div class="v6-empty">No roster loaded for this date.</div>'}</div><footer><div class="ops-overview-grid">${[['Walk-Ins',walkins.length],['Filtered Patients',rows.length],['Service Points',points.length],['On Duty',rosterRows.length]].map(([l,n])=>`<div><span>${l}</span><strong>${n}</strong></div>`).join('')}</div><button class="ua-button" data-v6-action="change-context">Change Hospital / Unit</button><button class="ua-button" data-route="bed-board">Open Unit Manager</button></footer></details></section>`;
};

function v8SelectedRowFromButton(button){
  const selected=state.v8SelectedFrontDeskRow;
  if(selected&&selected.patient?.mpi_id===button.dataset.patientId)return selected;
  return selected||null;
}
async function v8PatientForWorkflow(mpiId){
  if(!mpiId)throw new Error('Select a patient from the worklist.');
  return api(`/patients/${encodeURIComponent(mpiId)}`);
}
async function v8OpenPrintWorkflow(row){
  if(!row?.patient?.mpi_id)throw new Error('Select a patient record before printing.');
  const [templates,history]=await Promise.all([api('/print-templates'),api(`/patients/${encodeURIComponent(row.patient.mpi_id)}/print-jobs?limit=8`)]);
  const groups={LABEL:[],WRISTBAND:[],DOCUMENT:[]};templates.forEach(t=>(groups[t.category]||groups.DOCUMENT).push(t));
  const groupHtml=Object.entries(groups).map(([group,items])=>`<section class="v8-print-group"><h3>${statusLabel(group)}</h3>${items.map((t,i)=>`<label class="v8-print-template"><input type="checkbox" name="v8PrintTemplate" value="${esc(t.code)}" ${['PATIENT_ID_LABEL','ADULT_WRISTBAND','FACESHEET'].includes(t.code)?'checked':''}><span><strong>${esc(t.name)}</strong><small>${esc(t.media)} · ${esc(t.description)}</small></span></label>`).join('')}</section>`).join('');
  openModal('Print Forms, Labels & Wristbands',`<div class="v8-workflow-patient"><strong>${esc(row.patient.full_name)}</strong><span>${esc(row.patient.mrn)} · ${esc(row.service||'Current service')}</span></div><div class="v8-print-options"><label class="field"><span>Printer / output</span><select id="v8PrintPrinter"><option>Browser / PDF</option><option>Front Desk Label Printer</option><option>Wristband Printer</option><option>Health Records A4 Printer</option><option>Laboratory Label Printer</option></select></label><label class="field"><span>Copies</span><input id="v8PrintCopies" type="number" min="1" max="20" value="1"></label><label class="field"><span>Language</span><select id="v8PrintLanguage"><option value="en">English</option><option value="sw">Kiswahili</option></select></label></div><div class="v8-print-catalog">${groupHtml}</div><details class="v8-history"><summary>Recent print history (${history.length})</summary>${history.map(h=>`<p><strong>${esc(h.template_name)}</strong> · ${esc(h.status)} · ${fmtDate(h.created_at)} · ${esc(h.requested_by)}</p>`).join('')||'<p>No previous jobs.</p>'}</details>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v8fd-action="generate-print" data-patient-id="${esc(row.patient.mpi_id)}" data-encounter="${esc(row.encounter_id||'')}">Generate Preview</button>`,'Patient Print Center');
  $('#modal')?.classList.add('v8-large-modal');
}
function v8DocumentHtml(result){
  const context=result.document_context||{};const p=context.patient||{};const e=context.encounter||{};
  const barcode=`<div class="print-barcode"><i></i><span>${esc(p.mrn||p.mpi_id||'')}</span></div>`;
  const header=`<header class="print-header"><div><b>Umoja Afya EHR</b><span>${esc(context.facility_code||'Health Facility')}</span></div><div><strong>${esc(p.full_name||'Patient')}</strong><span>${esc(p.mrn||'')} · ${esc(p.mpi_id||'')}</span></div></header>`;
  return result.jobs.map(job=>{
    const code=job.template.code;let body='';
    if(code.includes('WRISTBAND'))body=`<section class="wristband"><div><strong>${esc(p.full_name)}</strong><span>DOB ${esc(p.date_of_birth||'—')} · ${esc(p.sex||'—')}</span><span>MRN ${esc(p.mrn||'—')}</span><span>Allergies: ${esc(p.allergies||'Not reviewed')}</span></div>${barcode}</section>`;
    else if(code.includes('LABEL'))body=`<section class="patient-label"><strong>${esc(p.full_name)}</strong><span>MRN ${esc(p.mrn||'—')} · DOB ${esc(p.date_of_birth||'—')}</span><span>${esc(e.encounter_id||p.mpi_id||'')}</span>${barcode}</section>`;
    else body=`<section class="print-document">${header}<h1>${esc(job.template.name)}</h1><div class="print-grid"><div><b>Patient</b><span>${esc(p.full_name)}</span></div><div><b>MRN / MPI</b><span>${esc(p.mrn||'—')} / ${esc(p.mpi_id||'—')}</span></div><div><b>DOB / Sex</b><span>${esc(p.date_of_birth||'—')} / ${esc(p.sex||'—')}</span></div><div><b>Contact</b><span>${esc(p.phone||'—')}</span></div><div><b>Address</b><span>${esc(p.address||'—')}</span></div><div><b>Coverage</b><span>${esc(p.payer||'—')} · ${esc(p.member_number||'—')}</span></div><div><b>Visit</b><span>${esc(e.encounter_id||'No active visit')}</span></div><div><b>Service / Location</b><span>${esc(e.service||'—')} · ${esc([e.location,e.room].filter(Boolean).join(' / ')||'—')}</span></div><div><b>Status</b><span>${esc(statusLabel(e.status||'No encounter'))}</span></div><div><b>Provider</b><span>${esc(e.provider||'Duty roster / unassigned')}</span></div><div><b>Reason</b><span>${esc(e.reason_for_visit||'—')}</span></div><div><b>Consent</b><span>${esc(statusLabel(p.consent_status||'Pending'))}</span></div></div>${barcode}<footer>Generated ${esc(context.generated_at||'')} · Job ${esc(job.job_id)}</footer></section>`;
    return Array.from({length:job.copies||1},()=>`<div class="print-page">${body}</div>`).join('');
  }).join('');
}
function v8PrintDocument(result){
  const win=window.open('','_blank','width=1000,height=800');if(!win)throw new Error('The browser blocked the print window. Allow pop-ups and retry.');
  win.document.write(`<!doctype html><html><head><title>Umoja Afya Patient Print</title><style>body{font-family:Arial,sans-serif;color:#102a43;margin:0}.print-page{page-break-after:always;padding:18mm;box-sizing:border-box}.print-header{display:flex;justify-content:space-between;border-bottom:3px solid #008b76;padding-bottom:10px}.print-header div{display:flex;flex-direction:column}.print-document h1{font-size:22px}.print-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:20px 0}.print-grid div{border:1px solid #ccd6df;padding:10px;display:flex;flex-direction:column}.print-grid span{margin-top:5px}.print-barcode{margin-top:14px}.print-barcode i{display:block;height:42px;background:repeating-linear-gradient(90deg,#111 0 2px,#fff 2px 4px,#111 4px 5px,#fff 5px 8px)}.print-barcode span{font-family:monospace;letter-spacing:2px}.patient-label{width:76mm;border:1px dashed #111;padding:4mm;display:flex;flex-direction:column;gap:3px}.wristband{width:250mm;border:1px solid #111;padding:4mm;display:flex;justify-content:space-between;align-items:center}.wristband div{display:flex;flex-direction:column;gap:3px}.wristband .print-barcode{width:70mm}footer{margin-top:30px;font-size:11px}@media print{button{display:none}.print-page:last-child{page-break-after:auto}} </style></head><body>${v8DocumentHtml(result)}<script>window.onload=()=>{window.focus();window.print();}<\/script></body></html>`);win.document.close();
}
async function v8OpenBenefitWorkflow(row){
  const patient=await v8PatientForWorkflow(row.patient.mpi_id);const history=await api(`/patients/${encodeURIComponent(row.patient.mpi_id)}/benefit-checks?limit=5`);
  openModal('Coverage & Benefit Verification',`<div class="v8-workflow-patient"><strong>${esc(patient.full_name)}</strong><span>${esc(patient.mrn)} · ${esc(row.service||'Current service')}</span></div><div class="form-grid"><label class="field"><span>Payer / scheme</span><select id="v8BenefitPayer">${['NHIF','iCHF','Private Insurance','Employer Scheme','Cash / Self-Pay','Exemption'].map(x=>`<option ${String(patient.payer||'')===x?'selected':''}>${x}</option>`).join('')}</select></label><label class="field"><span>Member / policy number</span><input id="v8BenefitMember" value="${esc(patient.member_number||'')}"></label><label class="field full"><span>Requested service</span><input id="v8BenefitService" value="${esc(row.service||'General outpatient care')}"></label></div><details class="v8-history"><summary>Previous checks (${history.length})</summary>${history.map(x=>`<p><strong>${esc(x.payer)} · ${esc(statusLabel(x.status))}</strong><br>${esc(x.response_message||'')} · ${fmtDate(x.requested_at)}</p>`).join('')||'<p>No previous checks.</p>'}</details>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v8fd-action="submit-benefit" data-patient-id="${esc(row.patient.mpi_id)}" data-encounter="${esc(row.encounter_id||'')}">Run Eligibility Check</button>`,'Benefit Check');
}
async function v8OpenTravelWorkflow(row){
  const history=await api(`/patients/${encodeURIComponent(row.patient.mpi_id)}/travel-screenings?limit=5`);
  const q=(id,label)=>`<label class="v8-screen-question"><span>${esc(label)}</span><select id="${id}"><option value="false">No</option><option value="true">Yes</option></select></label>`;
  openModal('Travel & Communicable-Disease Screening',`<div class="v8-workflow-patient"><strong>${esc(row.patient.full_name)}</strong><span>${esc(row.patient.mrn)} · ${esc(row.service||'Current service')}</span></div><div class="v8-screen-grid">${q('v8Travel','Travel outside the home region or country in the last 21 days?')}${q('v8Outbreak','Travel from or residence in a declared outbreak area?')}${q('v8Exposure','Known contact with a person with a communicable disease?')}${q('v8Fever','Fever or chills?')}${q('v8Cough','Cough or sore throat?')}${q('v8Breathing','Difficulty breathing?')}${q('v8Rash','New rash?')}${q('v8Diarrhoea','Diarrhoea or vomiting?')}${q('v8Bleeding','Unexplained bleeding?')}<label class="field full"><span>Travel location / exposure notes</span><textarea id="v8TravelNotes" placeholder="Country, region, dates, exposure details or other relevant information"></textarea></label></div><details class="v8-history"><summary>Previous screenings (${history.length})</summary>${history.map(x=>`<p><strong>${esc(x.risk_level)} risk</strong> · ${esc(x.disposition)} · ${fmtDate(x.completed_at)}</p>`).join('')||'<p>No previous screening.</p>'}</details>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v8fd-action="submit-travel" data-patient-id="${esc(row.patient.mpi_id)}" data-encounter="${esc(row.encounter_id||'')}">Complete Screening</button>`,'Travel Screening');
  $('#modal')?.classList.add('v8-large-modal');
}

function v8ApplyFrontDeskFilters(){state.todayFilters={search:$('#todaySearch')?.value.trim()||'',service:$('#todayService')?.value||'',clinic:'',queue:$('#todayQueue')?.value||'',status:$('#todayStatus')?.value||''};saveState();return renderTodayPatients();}

document.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target?.id==='todaySearch'){e.preventDefault();v8ApplyFrontDeskFilters();}},true);
document.addEventListener('click',async e=>{
  const b=e.target.closest('[data-v8fd-action]');if(!b)return;e.preventDefault();e.stopImmediatePropagation();
  try{
    const action=b.dataset.v8fdAction;
    if(action==='today-tab'){state.todayDay=b.dataset.tab;state.todayFilters={search:'',service:'',clinic:'',queue:'',status:''};saveState();return renderTodayPatients();}
    if(action==='apply-filter')return v8ApplyFrontDeskFilters();
    if(action==='clear-filter'){state.todayFilters={search:'',service:'',clinic:'',queue:'',status:''};saveState();return renderTodayPatients();}
    if(action==='refresh')return renderTodayPatients();
    if(action==='select-patient'){state.selectedPatientId=b.dataset.patientId;saveState();return renderTodayPatients();}
    if(action==='workflow-next'){
      state.selectedPatientId=b.dataset.patientId||state.selectedPatientId;saveState();
      if(b.dataset.kind==='appointment'){const result=await api(`/appointments/${encodeURIComponent(b.dataset.appointment)}`,{method:'PATCH',body:JSON.stringify({status:'ARRIVED',actor:currentRole().user,note:'Patient arrived from Today’s Patients.'})});toast('Patient arrived',result.notification?.message||'Downstream teams were notified.',1000);}
      else if(b.dataset.kind==='encounter'){await api(`/encounters/${encodeURIComponent(b.dataset.encounter)}/status`,{method:'PATCH',body:JSON.stringify({status:b.dataset.status,actor:currentRole().user,note:`${statusLabel(b.dataset.status)} from front desk workflow`})});toast('Workflow advanced',statusLabel(b.dataset.status),1000);}
      else if(b.dataset.kind==='walkin'){await api(`/walk-ins/${encodeURIComponent(b.dataset.walkin)}`,{method:'PATCH',body:JSON.stringify({action:b.dataset.course,actor:currentRole().user,note:`${statusLabel(b.dataset.course)} from walk-in workflow`})});toast('Walk-in advanced',statusLabel(b.dataset.course),1000);}
      else if(b.dataset.kind==='discharge')return showDischargeModal(b.dataset.encounter);
      else return navigate('patient-station',{preservePatient:true});
      return renderTodayPatients();
    }
    const row=v8SelectedRowFromButton(b);
    if(action==='open-station'){state.selectedPatientId=b.dataset.patientId;saveState();return navigate('patient-station',{preservePatient:true});}
    if(action==='open-chart'){state.selectedPatientId=b.dataset.patientId;saveState();return navigate('chart');}
    if(action==='event-history'){state.selectedPatientId=b.dataset.patientId;saveState();return navigate('event-management');}
    if(action==='print-workflow')return v8OpenPrintWorkflow(row);
    if(action==='benefit-workflow')return v8OpenBenefitWorkflow(row);
    if(action==='travel-workflow')return v8OpenTravelWorkflow(row);
    if(action==='generate-print'){
      const codes=[...document.querySelectorAll('input[name="v8PrintTemplate"]:checked')].map(x=>x.value);if(!codes.length)throw new Error('Select at least one form, label or wristband.');
      const result=await api(`/patients/${encodeURIComponent(b.dataset.patientId)}/print-jobs`,{method:'POST',body:JSON.stringify({template_codes:codes,encounter_id:b.dataset.encounter||null,copies:Number($('#v8PrintCopies')?.value||1),language:$('#v8PrintLanguage')?.value||'en',printer_name:$('#v8PrintPrinter')?.value||'Browser / PDF',requested_by:currentRole().user})});state.v8PrintResult=result;
      openModal('Print Preview Ready',`<div class="v8-print-ready"><h2>${result.jobs.length} document type${result.jobs.length===1?'':'s'} prepared</h2><p>${result.jobs.map(j=>`${esc(j.template.name)} × ${j.copies}`).join('<br>')}</p><p>Every print request has been written to the audit trail.</p></div><div class="v8-mini-preview">${v8DocumentHtml({...result,jobs:result.jobs.slice(0,1)})}</div>`,`<button class="ua-button" data-modal-action="close">Close</button><button class="ua-button primary" data-v8fd-action="print-now">Print / Save PDF</button>`,'Patient Print Center');return;
    }
    if(action==='print-now'){if(!state.v8PrintResult)throw new Error('Generate the print preview first.');return v8PrintDocument(state.v8PrintResult);}
    if(action==='submit-benefit'){
      const result=await api(`/patients/${encodeURIComponent(b.dataset.patientId)}/benefit-checks`,{method:'POST',body:JSON.stringify({encounter_id:b.dataset.encounter||null,payer:$('#v8BenefitPayer').value,member_number:$('#v8BenefitMember').value||null,service:$('#v8BenefitService').value||null,requested_by:currentRole().user})});
      openModal('Benefit Verification Result',`<div class="v8-result-banner ${String(result.status).toLowerCase()}"><strong>${esc(statusLabel(result.status))}</strong><p>${esc(result.message)}</p><dl><dt>Payer</dt><dd>${esc(result.payer)}</dd><dt>Member</dt><dd>${esc(result.member_number||'Not supplied')}</dd><dt>Service</dt><dd>${esc(result.service||'—')}</dd><dt>Patient responsibility</dt><dd>${esc(result.copay_amount||'Pending review')}</dd><dt>Verification ID</dt><dd>${esc(result.verification_id)}</dd></dl></div>`,`<button class="ua-button primary" data-modal-action="close">Done</button>`,'Benefit Check');return;
    }
    if(action==='submit-travel'){
      const bool=id=>$('#'+id)?.value==='true';const responses={recent_travel:bool('v8Travel'),outbreak_area:bool('v8Outbreak'),infectious_exposure:bool('v8Exposure'),fever:bool('v8Fever'),cough:bool('v8Cough'),breathing_difficulty:bool('v8Breathing'),rash:bool('v8Rash'),diarrhoea:bool('v8Diarrhoea'),bleeding:bool('v8Bleeding'),notes:$('#v8TravelNotes')?.value||''};
      const result=await api(`/patients/${encodeURIComponent(b.dataset.patientId)}/travel-screenings`,{method:'POST',body:JSON.stringify({encounter_id:b.dataset.encounter||null,responses,completed_by:currentRole().user})});
      openModal('Screening Completed',`<div class="v8-result-banner ${String(result.risk_level).toLowerCase()}"><strong>${esc(result.risk_level)} risk</strong><p>${esc(result.disposition)}</p><dl><dt>Screening ID</dt><dd>${esc(result.screening_id)}</dd><dt>Status</dt><dd>${esc(result.status)}</dd><dt>Completed</dt><dd>${fmtDate(result.completed_at)}</dd></dl></div>`,`<button class="ua-button primary" data-modal-action="close">Done</button>`,'Travel Screening');return;
    }
  }catch(err){console.error(err);toast('Action failed',err.message||String(err));}
},true);



/* --------------------------------------------------------------------------
   Production clinical documentation and unit-manager experience.
   - Notes are a complete three-pane record workspace with templates, draft
     editing, signing, addenda, smart phrases and immutable history.
   - Bed Board is a unit-first command workspace. No beds/patients load until
     the user explicitly chooses a unit such as ED/ER, ICU or a ward.
--------------------------------------------------------------------------- */
state.v9NoteFilters=state.v9NoteFilters||{search:'',status:'',type:''};
state.v9SelectedNoteId=state.v9SelectedNoteId||null;
state.v9NoteMode=state.v9NoteMode||'view';
state.v9NoteResources=state.v9NoteResources||{templates:[],smart_phrases:[]};
state.v9UnitCategory=state.v9UnitCategory||'ALL';
state.v9BedFacility=state.v9BedFacility||null;

function v9NoteStatusClass(status){return String(status||'').toUpperCase()==='SIGNED'?'signed':'draft';}
function v9FilterNotes(notes){
  const f=state.v9NoteFilters||{};const q=String(f.search||'').toLowerCase();
  return notes.filter(n=>(!q||`${n.title} ${n.note_type} ${n.author} ${n.service} ${n.body}`.toLowerCase().includes(q))&&(!f.status||n.status===f.status)&&(!f.type||n.note_type===f.type));
}
function v9NoteEditor(note,patient,encounter){
  const isNew=state.v9NoteMode==='new'||!note;const editable=isNew||note.status==='DRAFT';
  const templates=state.v9NoteResources.templates||[];const phrases=state.v9NoteResources.smart_phrases||[];
  const template=templates.find(t=>t.code===(note?.note_type||'PROGRESS_NOTE'))||templates[0]||{};
  const title=isNew?(template.title||'Progress Note'):(note.title||'');
  const body=isNew?(state.pendingAudioDraft||template.body||''):(note.body||'');
  const service=isNew?(encounter?.service||'General Clinical Service'):(note.service||encounter?.service||'');
  if(!editable){
    const history=Array.isArray(note.edit_history)?note.edit_history:[];
    return `<div class="v9-note-view"><div class="v9-note-view-head"><div><span class="v9-note-status signed">Signed legal note · locked</span><h2>${esc(note.title)}</h2><p>${esc(statusLabel(note.note_type))} · ${esc(note.service)} · ${esc(note.author)}</p></div><div><button class="ua-button" data-v9-action="note-history" data-note-id="${esc(note.note_id)}">Full History</button><button class="ua-button primary" data-v9-action="add-note-addendum" data-note-id="${esc(note.note_id)}">Add Addendum</button></div></div><div class="v9-note-body">${esc(note.body).replace(/\n/g,'<br>')}</div><footer><span>Signed by ${esc(note.signed_by||note.author)} · ${note.signed_at?fmtDate(note.signed_at):'Signature time unavailable'}</span>${note.amended_at?`<b>Last amended ${fmtDate(note.amended_at)}</b>`:''}</footer><section class="v1014-note-audit"><div><h3>Visible edit and signature trail</h3><p>Signed content cannot be overwritten. Corrections appear as attributed addenda.</p></div>${history.length?history.map(event=>`<article><span>${esc(statusLabel(event.action))}</span><strong>${esc(event.actor||'Unknown user')}</strong><time>${fmtDate(event.occurred_at)}</time><p>${esc(event.reason||'Clinical note event')}${event.changed_fields?.length?` · Fields: ${esc(event.changed_fields.map(statusLabel).join(', '))}`:''}</p></article>`).join(''):'<article><strong>No legacy edit events were available for this note.</strong><p>Future saves, signatures and addenda are recorded with user and time.</p></article>'}</section></div>`;
  }
  return `<div class="v9-note-composer"><div class="v9-composer-toolbar"><label><span>Template</span><select id="v9NoteTemplate" data-v9-note-template>${templates.map(t=>`<option value="${esc(t.code)}" ${(note?.note_type||template.code)===t.code?'selected':''}>${esc(t.group)} · ${esc(t.name)}</option>`).join('')}</select></label><label><span>Encounter</span><select id="v9NoteEncounter">${(patient.encounters||[]).map(e=>`<option value="${esc(e.encounter_id)}" ${e.encounter_id===encounter?.encounter_id?'selected':''}>${esc(e.encounter_id)} · ${esc(e.service)} · ${esc(statusLabel(e.status))}</option>`).join('')}</select></label><label><span>Service</span><input id="v9NoteService" value="${esc(service)}"></label></div><div class="v9-note-fields"><label><span>Note title</span><input id="v9NoteTitle" value="${esc(title)}"></label><label><span>Note type</span><input id="v9NoteType" value="${esc(note?.note_type||template.code||'PROGRESS_NOTE')}"></label><label class="v9-cosign"><input id="v9NoteCosign" type="checkbox" ${note?.cosign_required?'checked':''}><span>Supervising clinician cosign required</span></label></div><div class="v9-smart-phrases"><span>Smart phrases</span>${phrases.map(p=>`<button type="button" data-v9-action="insert-smart-phrase" data-code="${esc(p.code)}" title="${esc(p.label)}">${esc(p.code)}</button>`).join('')}</div>${state.v9AudioSessionId?`<div class="v9-audio-link"><strong>Audio-assisted source linked</strong><span>Session ${esc(state.v9AudioSessionId)} · transcript provenance retained · clinician verification required</span></div>`:''}<textarea id="v9NoteBody" class="v9-note-textarea" spellcheck="true">${esc(body)}</textarea><div class="v9-note-footer"><span id="v9AutosaveState">${isNew?'New unsaved note':'Draft loaded · edits are auditable when saved'}</span><div>${!isNew?`<button class="ua-button" data-v9-action="note-history" data-note-id="${esc(note.note_id)}">History</button>`:''}<button class="ua-button" data-action="audio-note">Audio / Dictation</button><button class="ua-button primary" data-v9-action="save-note" data-note-id="${esc(note?.note_id||'')}">Save Draft</button>${isNew?`<button class="ua-button success" data-v9-action="create-and-sign-note">Create & Sign</button>`:`<button class="ua-button success" data-v9-action="save-and-sign-note" data-note-id="${esc(note.note_id)}">Save & Sign</button>`}</div></div></div>`;
}

renderClinicalDocumentation=async function(){
  if(!state.selectedPatientId){$('#mainContent').innerHTML=v5EmptyRecordWorkspace('Clinical Documentation');return;}
  renderLoading('Opening documentation workspace…');
  const patient=await selectedPatient();if(!patient){$('#mainContent').innerHTML=v5EmptyRecordWorkspace('Clinical Documentation');return;}
  const encounter=v5CurrentEncounter(patient)||patient.encounters?.[0]||null;
  if(!encounter){$('#mainContent').innerHTML=`${pageHeader('Clinical Documentation','No Encounter Selected','Create or select an encounter before documenting.')}${v5RecordHeader(patient,null,true)}`;return;}
  const [notes,resources,advisoryResponse]=await Promise.all([api(`/notes?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`),api('/notes/templates'),api(`/practice-advisories?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}&encounter_id=${encodeURIComponent(encounter.encounter_id)}&language=${state.language}`)]);
  state.v9Notes=notes;state.v9NoteResources=resources;
  if(state.v9SelectedNoteId&&!notes.some(n=>n.note_id===state.v9SelectedNoteId))state.v9SelectedNoteId=null;
  if(!state.v9SelectedNoteId&&state.v9NoteMode!=='new'&&notes.length)state.v9SelectedNoteId=notes[0].note_id;
  const filtered=v9FilterNotes(notes);const selected=notes.find(n=>n.note_id===state.v9SelectedNoteId)||null;if(state.v9NoteMode!=='new')state.v9AudioSessionId=selected?.source_audio_session_id||null;const types=[...new Set(notes.map(n=>n.note_type))].sort();const advisories=advisoryResponse.advisories||[];
  $('#mainContent').innerHTML=`<section class="ua-page v9-notes-page">${uaPageTitle('Clinical Documentation','Fast, structured and record-centric notes with templates, smart phrases, audio assistance, signatures, addenda and immutable history.',`<button class="ua-button" data-route="chart" data-preserve-patient="true">Chart</button><button class="ua-button" data-v9-action="refresh-notes">Refresh</button><button class="ua-button primary" data-v9-action="new-note">New Note</button>`)}${v5RecordHeader(patient,encounter,true)}<div class="v7-resizable-workspace v9-notes-workspace" data-v7-layout="notes" style="${v7LayoutStyle('notes',[330,780])}">
    <aside class="v9-pane ua-card"><div class="ua-card-header"><div><h2>Notes</h2><p>${filtered.length} of ${notes.length}</p></div></div><div class="v9-note-filters"><input id="v9NoteSearch" value="${esc(state.v9NoteFilters.search)}" placeholder="Search notes"><select id="v9NoteStatus"><option value="">All statuses</option>${['DRAFT','SIGNED'].map(x=>`<option value="${x}" ${state.v9NoteFilters.status===x?'selected':''}>${statusLabel(x)}</option>`).join('')}</select><select id="v9NoteTypeFilter"><option value="">All note types</option>${types.map(x=>`<option value="${esc(x)}" ${state.v9NoteFilters.type===x?'selected':''}>${esc(statusLabel(x))}</option>`).join('')}</select><button class="ua-button primary" data-v9-action="apply-note-filter">Apply</button><button class="ua-button" data-v9-action="clear-note-filter">Clear</button></div><div class="v9-note-list">${filtered.map(n=>`<button class="${n.note_id===selected?.note_id&&state.v9NoteMode!=='new'?'active':''}" data-v9-action="select-note" data-note-id="${esc(n.note_id)}"><span class="v9-note-status ${v9NoteStatusClass(n.status)}">${esc(statusLabel(n.status))}</span><strong>${esc(n.title)}</strong><small>${esc(statusLabel(n.note_type))} · ${esc(n.author)}</small><time>${fmtDate(n.created_at)}</time></button>`).join('')||'<div class="v9-empty"><b>No matching notes</b><span>Create a note or clear the filters.</span></div>'}</div></aside>
    <div class="v7-splitter" data-v7-splitter="0" title="Drag to resize"></div>
    <main class="v9-pane ua-card v9-editor-pane"><div class="ua-card-header"><div><h2>${state.v9NoteMode==='new'?'New Clinical Note':selected?'Note Composer':'Documentation Workspace'}</h2><p>${selected?.note_id||encounter.encounter_id}</p></div></div>${v9NoteEditor(selected,patient,encounter)}</main>
    <div class="v7-splitter" data-v7-splitter="1" title="Drag to resize"></div>
    <aside class="v9-pane ua-card v9-note-insights"><div class="ua-card-header"><h2>Clinical Guardrails</h2></div><div class="v9-note-health">${[['Drafts',notes.filter(n=>n.status==='DRAFT').length],['Signed',notes.filter(n=>n.status==='SIGNED').length],['Cosign needed',notes.filter(n=>n.cosign_required&&n.status!=='SIGNED').length],['Advisories',advisories.length]].map(([l,n])=>`<div><span>${l}</span><strong>${n}</strong></div>`).join('')}</div><h3>Practice Advisories</h3><div class="v9-advisories">${advisories.map(a=>`<article class="${String(a.severity||'').toLowerCase()}"><b>${esc(a.title)}</b><p>${esc(a.message)}</p><button class="ua-button compact" data-action="advisory-action" data-key="${esc(a.key)}" data-op="ACKNOWLEDGE" data-encounter="${esc(encounter.encounter_id)}">Acknowledge</button></article>`).join('')||'<div class="v9-empty"><b>No active advisories</b><span>Continue clinical judgment and standard workflows.</span></div>'}</div><div class="v9-integrity-card"><b>Legal record integrity</b><p>Draft edits are versioned in event history. Signed notes are locked; corrections use an addendum. No note is silently overwritten or deleted.</p></div></aside>
  </div></section>`;
  requestAnimationFrame(()=>v7EnhancePanels());
};

function v9UnitCategoryLabel(code){return ({ALL:'All Units',EMERGENCY:'ED / Emergency',CRITICAL_CARE:'Critical Care',INPATIENT:'Inpatient Wards',WOMEN_CHILDREN:'Women & Children',SURGICAL:'Surgical / Procedural',AMBULATORY_PROCEDURAL:'Day Care / Treatment',ISOLATION:'Isolation',MENTAL_HEALTH:'Mental Health'})[code]||statusLabel(code);}
function v9UnitGlyph(code){return ({EMERGENCY:'⚡',CRITICAL_CARE:'✚',INPATIENT:'▦',WOMEN_CHILDREN:'♡',SURGICAL:'✦',AMBULATORY_PROCEDURAL:'◉',ISOLATION:'⬡',MENTAL_HEALTH:'☼'})[code]||'▦';}
function v9GroupBedsByRoom(beds){return beds.reduce((acc,b)=>{(acc[b.room]||(acc[b.room]=[])).push(b);return acc;},{});}
function v9UnitCard(u){return `<button class="v9-unit-card ${u.unit===state.selectedBedUnit?'active':''}" data-v9-action="select-unit" data-unit="${esc(u.unit)}"><span class="v9-unit-glyph">${v9UnitGlyph(u.care_setting)}</span><span><strong>${esc(u.unit)}</strong><small>${esc(u.care_setting_label)} · ${u.total} ${esc(u.station_term)}</small><i><b style="width:${Math.min(100,u.occupancy_percent||0)}%"></b></i><em>${u.occupied} occupied · ${u.available} available · ${u.turnover} turnover</em></span></button>`;}

renderBedBoardV5=async function(){
  renderLoading('Loading unit directory…');
  const facility=operationFacility();
  if(state.v9BedFacility!==facility){state.v9BedFacility=facility;state.selectedBedUnit=null;state.v8BedStatus='';}
  const units=await api(`/bed-units?facility_code=${encodeURIComponent(facility)}`);state.v9Units=units;
  const needle=String(state.v8UnitSearch||'').toLowerCase();const category=state.v9UnitCategory||'ALL';
  const visibleUnits=units.filter(u=>(category==='ALL'||u.care_setting===category)&&(!needle||`${u.unit} ${u.care_setting_label}`.toLowerCase().includes(needle)));
  if(state.selectedBedUnit&&!units.some(u=>u.unit===state.selectedBedUnit))state.selectedBedUnit=null;
  const overview=state.selectedBedUnit?await api(`/unit-manager/overview?facility_code=${encodeURIComponent(facility)}&unit=${encodeURIComponent(state.selectedBedUnit)}`):null;
  const allBeds=overview?.beds||[];const beds=allBeds.filter(b=>!state.v8BedStatus||String(b.status).toUpperCase()===state.v8BedStatus);const roomGroups=v9GroupBedsByRoom(beds);const summary=overview?.summary||{};
  const categories=['ALL',...new Set(units.map(u=>u.care_setting))];
  $('#mainContent').innerHTML=`<section class="ua-page v9-unit-page">${uaPageTitle('Unit Manager','Choose a hospital unit first. The bed, bay or treatment-station layout then loads with patient movement, turnover and capacity controls.',`<button class="ua-button" data-v9-action="reset-unit">Unit Lookup</button><button class="ua-button" data-v5-action="change-context">Change Hospital</button><button class="ua-button primary" data-v9-action="refresh-unit-manager">Refresh</button>`)}<div class="v7-resizable-workspace v9-unit-workspace" data-v7-layout="unit-manager" style="${v7LayoutStyle('unit-manager',[360,860])}">
    <aside class="v9-pane ua-card"><div class="ua-card-header"><div><h2>Unit Lookup</h2><p>${visibleUnits.length} of ${units.length} configured units</p></div></div><div class="v9-unit-search"><input id="v9UnitSearch" value="${esc(state.v8UnitSearch||'')}" placeholder="Search ED, ICU, ward, theatre…"><button class="ua-button primary" data-v9-action="apply-unit-search">Search</button></div><div class="v9-unit-categories">${categories.map(c=>`<button class="${category===c?'active':''}" data-v9-action="unit-category" data-category="${esc(c)}">${v9UnitGlyph(c)} ${esc(v9UnitCategoryLabel(c))}</button>`).join('')}</div><div class="v9-unit-list">${visibleUnits.map(v9UnitCard).join('')||'<div class="v9-empty"><b>No units match</b><span>Clear the search or select another unit category.</span></div>'}</div></aside>
    <div class="v7-splitter" data-v7-splitter="0" title="Drag to resize"></div>
    <main class="v9-pane ua-card v9-unit-layout"><div class="ua-card-header"><div><h2>${esc(overview?.unit?.name||'Select a unit')}</h2><p>${overview?`${esc(overview.unit.care_setting_label)} · ${beds.length} visible ${esc(overview.unit.station_term)}`:'Beds and patient details stay hidden until a unit is selected.'}</p></div>${overview?`<div class="v9-bed-filter"><select id="v9BedStatus"><option value="">All statuses</option>${['AVAILABLE','ASSIGNED','OCCUPIED','DIRTY','CLEANING','BLOCKED'].map(x=>`<option value="${x}" ${state.v8BedStatus===x?'selected':''}>${statusLabel(x)}</option>`).join('')}</select><button class="ua-button" data-v9-action="apply-bed-status">Apply</button></div>`:''}</div>${overview?`<div class="v9-unit-kpis">${[['Capacity',summary.total||0],['Available',summary.AVAILABLE||0],['Occupied',summary.OCCUPIED||0],['Assigned',summary.ASSIGNED||0],['Turnover',(summary.DIRTY||0)+(summary.CLEANING||0)],['Blocked',summary.BLOCKED||0]].map(([l,n])=>`<div><span>${l}</span><strong>${n}</strong></div>`).join('')}</div><div class="v9-room-layout">${Object.entries(roomGroups).map(([room,items])=>`<section class="v9-room"><header><h3>${esc(room)}</h3><span>${items.length} space${items.length===1?'':'s'}</span></header><div>${items.map(b=>`<article class="v9-bed ${String(b.status).toLowerCase()}"><header><b>${esc(b.bed_label)}</b><span>${esc(statusLabel(b.status))}</span></header>${b.patient?`<button data-patient-id="${esc(b.patient.mpi_id)}"><strong>${esc(b.patient.full_name)}</strong><small>${esc(b.patient.mrn)} · ${esc(b.encounter?.service||'')}</small></button>`:'<div class="v9-empty-bed">Ready for assignment</div>'}<footer><small>${esc(statusLabel(b.bed_type||'STANDARD'))}${b.isolation?` · ${esc(b.isolation)}`:''}</small><button class="ua-button compact" data-v5-action="bed-actions" data-bed-id="${esc(b.bed_id)}" data-bed-status="${esc(b.status)}">Manage</button></footer></article>`).join('')}</div></section>`).join('')||'<div class="v9-empty"><b>No spaces match the filter</b><span>Choose another bed status.</span></div>'}</div>`:`<div class="v9-unit-launch"><span>▦</span><h2>Choose a unit to begin</h2><p>Select <b>ED / Emergency</b>, an ICU, inpatient ward, maternity, theatre, dialysis or another unit from the lookup. The layout and operational workflow will populate here without exposing the rest of the hospital.</p><button class="ua-button primary" data-v9-action="unit-category" data-category="EMERGENCY">Show ED / Emergency Units</button></div>`}</main>
    <div class="v7-splitter" data-v7-splitter="1" title="Drag to resize"></div>
    <aside class="v9-pane ua-card v9-unit-command"><div class="ua-card-header"><h2>Unit Command</h2></div>${overview?`<div class="v9-unit-identity"><span>${v9UnitGlyph(overview.unit.care_setting)}</span><div><strong>${esc(overview.unit.name)}</strong><small>${esc(overview.facility.name)}</small></div></div>${overview.unit.care_setting==='EMERGENCY'?`<button class="ua-button danger full-width" data-route="emergency">Open ED / ER Tracking Board</button>`:''}<h3>Pending Placement / Movement</h3><div class="v9-pending-list">${(overview.pending_assignments||[]).map(e=>`<article><button data-patient-id="${esc(e.patient?.mpi_id||'')}"><strong>${esc(e.patient?.full_name||'Unknown patient')}</strong><small>${esc(e.patient?.mrn||'')} · ${esc(e.service||'')}</small></button><span class="ua-status ${uaStatusClass(e.status)}">${esc(statusLabel(e.status))}</span><small>${esc(e.location||'Location pending')} · ${esc(e.acuity||'Acuity pending')}</small></article>`).join('')||'<div class="v9-empty"><b>No pending placement</b><span>The unit has no unassigned encounters in the current view.</span></div>'}</div><h3>Seamless unit workflow</h3><ol class="v9-unit-steps"><li>Review capacity and pending placement</li><li>Assign or occupy an available space</li><li>Move or transfer the patient with encounter context</li><li>Discharge / vacate and trigger turnover</li><li>EVS cleans and returns the space to available</li></ol>`:`<div class="v9-empty command"><b>Unit context required</b><span>Operational summaries, patient movement and bed actions appear only after a unit is selected.</span></div>`}</aside>
  </div></section>`;
  requestAnimationFrame(()=>v7EnhancePanels());
};

function v9CollectNotePayload(){return {encounter_id:$('#v9NoteEncounter')?.value,title:$('#v9NoteTitle')?.value.trim(),note_type:$('#v9NoteType')?.value.trim(),service:$('#v9NoteService')?.value.trim(),body:$('#v9NoteBody')?.value,cosign_required:Boolean($('#v9NoteCosign')?.checked),source_audio_session_id:state.v9AudioSessionId||null};}
function v9InsertAtCursor(textarea,text){if(!textarea)return;const start=textarea.selectionStart??textarea.value.length,end=textarea.selectionEnd??start;textarea.value=textarea.value.slice(0,start)+text+textarea.value.slice(end);textarea.focus();textarea.selectionStart=textarea.selectionEnd=start+text.length;$('#v9AutosaveState').textContent='Unsaved changes';}

document.addEventListener('change',e=>{
  if(e.target.id==='audioFileInput'&&e.target.files?.[0]){const file=e.target.files[0];updateAudioPreview(file,file.name);}
  if(e.target.matches('[data-v9-note-template]')){const t=(state.v9NoteResources.templates||[]).find(x=>x.code===e.target.value);if(!t)return;$('#v9NoteType').value=t.code;$('#v9NoteTitle').value=t.title;$('#v9NoteBody').value=t.body;$('#v9AutosaveState').textContent='Template loaded · unsaved';}
},true);
document.addEventListener('input',e=>{if(e.target.closest('.v9-note-composer')&&$('#v9AutosaveState'))$('#v9AutosaveState').textContent='Unsaved changes';},true);
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'&&e.target.closest('.v9-note-composer')){e.preventDefault();document.querySelector('[data-v9-action="save-note"]')?.click();}},true);

document.addEventListener('click',async e=>{
  const b=e.target.closest('[data-v9-action]');if(!b)return;e.preventDefault();e.stopImmediatePropagation();
  try{
    const action=b.dataset.v9Action;
    if(action==='refresh-notes')return renderClinicalDocumentation();
    if(action==='new-note'){state.v9NoteMode='new';state.v9SelectedNoteId=null;state.pendingAudioDraft='';state.v9AudioSessionId=null;if(state.route!=='clinical-documentation')return navigate('clinical-documentation');return renderClinicalDocumentation();}
    if(action==='select-note'){state.v9NoteMode='view';state.v9SelectedNoteId=b.dataset.noteId;return renderClinicalDocumentation();}
    if(action==='apply-note-filter'){state.v9NoteFilters={search:$('#v9NoteSearch')?.value.trim()||'',status:$('#v9NoteStatus')?.value||'',type:$('#v9NoteTypeFilter')?.value||''};return renderClinicalDocumentation();}
    if(action==='clear-note-filter'){state.v9NoteFilters={search:'',status:'',type:''};return renderClinicalDocumentation();}
    if(action==='insert-smart-phrase'){const phrase=(state.v9NoteResources.smart_phrases||[]).find(x=>x.code===b.dataset.code);return v9InsertAtCursor($('#v9NoteBody'),phrase?.text||'');}
    if(action==='save-note'){
      const payload=v9CollectNotePayload();if(!payload.encounter_id||!payload.title||!payload.body)throw new Error('Encounter, title and note body are required.');
      if(b.dataset.noteId){await api(`/notes/${encodeURIComponent(b.dataset.noteId)}`,{method:'PATCH',body:JSON.stringify({...payload,actor:currentRole().user})});toast('Draft saved','The note draft and edit history were recorded.');}
      else{const created=await api('/notes',{method:'POST',body:JSON.stringify({...payload,patient_mpi_id:state.selectedPatientId,author:currentRole().user})});state.v9SelectedNoteId=created.note_id;state.v9NoteMode='view';state.pendingAudioDraft='';toast('Draft created','The note is linked to the selected record and encounter.');}
      return renderClinicalDocumentation();
    }
    if(action==='create-and-sign-note'){
      const payload=v9CollectNotePayload();if(!payload.encounter_id||!payload.title||!payload.body)throw new Error('Encounter, title and note body are required.');
      const created=await api('/notes',{method:'POST',body:JSON.stringify({...payload,patient_mpi_id:state.selectedPatientId,author:currentRole().user})});await api(`/notes/${encodeURIComponent(created.note_id)}/sign`,{method:'POST',body:JSON.stringify({signer:currentRole().user,attestation:'Reviewed for accuracy and electronically signed in Umoja Afya EHR.'})});state.v9SelectedNoteId=created.note_id;state.v9NoteMode='view';state.pendingAudioDraft='';toast('Note created and signed','The note is locked in the legal health record.');return renderClinicalDocumentation();
    }
    if(action==='save-and-sign-note'){
      const payload=v9CollectNotePayload();await api(`/notes/${encodeURIComponent(b.dataset.noteId)}`,{method:'PATCH',body:JSON.stringify({...payload,actor:currentRole().user})});await api(`/notes/${encodeURIComponent(b.dataset.noteId)}/sign`,{method:'POST',body:JSON.stringify({signer:currentRole().user,attestation:'Reviewed for accuracy and electronically signed in Umoja Afya EHR.'})});toast('Note signed','The note is locked in the legal health record. Future corrections require an addendum.');return renderClinicalDocumentation();
    }
    if(action==='add-note-addendum'){openModal('Add Clinical Note Addendum',`<div class="alert info"><strong>Original note remains unchanged in history.</strong><br>The addendum will be appended with author and timestamp.</div><label class="field"><span>Reason</span><input id="v9AddendumReason" value="Clarification or additional clinical information"></label><label class="field"><span>Addendum</span><textarea id="v9AddendumText" rows="10" placeholder="Document the additional information or correction."></textarea></label>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v9-action="confirm-addendum" data-note-id="${esc(b.dataset.noteId)}">Append Addendum</button>`,'Legal Clinical Documentation');return;}
    if(action==='confirm-addendum'){await api(`/notes/${encodeURIComponent(b.dataset.noteId)}/addendum`,{method:'POST',body:JSON.stringify({text:$('#v9AddendumText').value,author:currentRole().user,reason:$('#v9AddendumReason').value})});closeModal();toast('Addendum appended','The original signed note and addendum are both preserved.');return renderClinicalDocumentation();}
    if(action==='note-history'){const events=await api(`/notes/${encodeURIComponent(b.dataset.noteId)}/history`);openModal('Clinical Note History',`<div class="v7-event-list">${events.map(ev=>`<article><strong>${esc(statusLabel(ev.action))}</strong><span>${esc(ev.actor)} · ${fmtDate(ev.occurred_at)}</span><p>${esc(ev.status_before||'—')} → ${esc(ev.status_after||'—')} · ${esc(ev.reason||'')}</p></article>`).join('')||'<p>No note history has been recorded.</p>'}</div>`,`<button class="ua-button primary" data-modal-action="close">Close</button>`,'Immutable Documentation History');return;}
    if(action==='reset-unit'){state.selectedBedUnit=null;state.v8BedStatus='';return renderBedBoardV5();}
    if(action==='refresh-unit-manager')return renderBedBoardV5();
    if(action==='apply-unit-search'){state.v8UnitSearch=$('#v9UnitSearch')?.value.trim()||'';return renderBedBoardV5();}
    if(action==='unit-category'){state.v9UnitCategory=b.dataset.category;state.selectedBedUnit=null;state.v8BedStatus='';return renderBedBoardV5();}
    if(action==='select-unit'){state.selectedBedUnit=b.dataset.unit;state.v8BedStatus='';saveState();return renderBedBoardV5();}
    if(action==='apply-bed-status'){state.v8BedStatus=$('#v9BedStatus')?.value||'';return renderBedBoardV5();}
  }catch(err){console.error(err);toast('Action failed',err.message||String(err));}
},true);


  /* v10.4: personalized activity memory, recent-patient memory, favorites and
     a Patient Station-style lookup workspace. Patient memory is scoped to the
     authenticated username and cleared on sign-out; it never changes the legal
     health record. Every chart open continues through the existing audited API. */
  const v104MaxRecentActivities=10, v104MaxRecentPatients=20;
  function v104UserKey(){return String(state.account?.username||state.account?.user_id||'anonymous').replace(/[^a-zA-Z0-9_.-]/g,'_');}
  function v104StoreKey(name){const scope=`${state.countryCode||'country'}.${state.facility||'facility'}`.replace(/[^a-zA-Z0-9_.-]/g,'_');return `umoja.v11.0.0.${v104UserKey()}.${scope}.${name}`;}
  function v104Read(name,fallback=[]){try{const v=JSON.parse(localStorage.getItem(v104StoreKey(name))||'null');return v??fallback;}catch{return fallback;}}
  function v104Write(name,value){localStorage.setItem(v104StoreKey(name),JSON.stringify(value));}
  function v104ActivityMeta(route){for(const [category,items] of Object.entries(v4LauncherMap)){const item=items.find(x=>x[1]===route);if(item)return {category,label:item[0],route:item[1],icon:item[2],detail:item[3]};}const item=navGroups.flatMap(g=>g.items).find(x=>x[0]===route);return item?{category:'Workspace',label:item[1],route:item[0],icon:item[2],detail:'Open workspace'}:{category:'Workspace',label:statusLabel(route),route,icon:'tools',detail:'Open workspace'};}
  function v104RememberActivity(route){if(!route||route==='login')return;const meta=v104ActivityMeta(route),list=v104Read('recentActivities',[]).filter(x=>x.route!==route);list.unshift({...meta,at:new Date().toISOString()});v104Write('recentActivities',list.slice(0,v104MaxRecentActivities));}
  function v104TogglePin(route){const pins=v104Read('pinnedActivities',[]);const exists=pins.some(x=>x.route===route);v104Write('pinnedActivities',exists?pins.filter(x=>x.route!==route):[...pins,v104ActivityMeta(route)]);renderLauncherCategories(state.v104LauncherCategory||'Patient Care');}
  function v104PatientSummary(p){return {mpi_id:p.mpi_id,full_name:p.full_name,mrn:p.mrn||'',date_of_birth:p.date_of_birth||'',sex:p.sex||'',phone:p.phone||'',nida_number:p.nida_number||'',payer:p.payer||'',at:new Date().toISOString()};}
  function v104RememberPatient(p){if(!p?.mpi_id)return;const list=v104Read('recentPatients',[]).filter(x=>x.mpi_id!==p.mpi_id);list.unshift(v104PatientSummary(p));v104Write('recentPatients',list.slice(0,v104MaxRecentPatients));}
  function v104TogglePatientFavorite(p){if(!p?.mpi_id)return;const list=v104Read('favoritePatients',[]);const exists=list.some(x=>x.mpi_id===p.mpi_id);v104Write('favoritePatients',exists?list.filter(x=>x.mpi_id!==p.mpi_id):[...list,v104PatientSummary(p)]);if(state.route==='patient-search')renderPatientSearch();else renderLauncherCategories(state.v104LauncherCategory||'Patient Care');}
  function v104IsPatientFavorite(id){return v104Read('favoritePatients',[]).some(x=>x.mpi_id===id);}
  function v104RenderLauncherMemory(){
    const host=$('#launcherMemory');if(!host)return;
    const pins=v104Read('pinnedActivities',[]),recent=v104Read('recentActivities',[]);
    const item=(x,type)=>`<article class="launcher-memory-card" data-v104-route="${esc(x.route)}" tabindex="0" role="button" aria-label="Open ${esc(x.label)}">
      <span class="launcher-memory-icon">${v4Icon(x.icon||'tools')}</span>
      <span class="launcher-memory-copy"><strong>${esc(x.label)}</strong><small>${esc(type==='recent'?(x.category||'Workspace'):(x.detail||'Pinned activity'))}</small></span>
      <button class="launcher-memory-pin ${type==='pinned'?'active':''}" data-v104-action="${type==='pinned'?'unpin-activity':'pin-activity'}" data-route="${esc(x.route)}" aria-label="${type==='pinned'?'Unpin':'Pin'} ${esc(x.label)}" data-tooltip="${type==='pinned'?'Remove from pinned activities':'Pin for quick access'}">${type==='pinned'?'★':'☆'}</button>
      <span class="launcher-memory-chevron" aria-hidden="true">›</span>
    </article>`;
    const section=(title,items,type)=>`<section class="launcher-memory-section launcher-memory-${type}">
      <header><h3>${esc(title)}</h3>${items.length?`<button class="clear-memory" data-v104-action="clear-${type}">Clear</button>`:`<span class="section-symbol" aria-hidden="true">${type==='pinned'?'◆':'↺'}</span>`}</header>
      ${items.length?`<div class="launcher-memory-list">${items.map(x=>item(x,type)).join('')}</div>`:(type==='pinned'?`<div class="launcher-memory-empty"><span class="empty-pin">◆</span><strong>Pin activities for quick access</strong><small>Pinned activities will appear here for easy access.</small></div>`:`<div class="launcher-memory-empty compact"><strong>No recent activities</strong><small>Workspaces you open will appear here.</small></div>`)}
    </section>`;
    host.innerHTML=section('Pinned',pins,'pinned')+section('Recent',recent,'recent');
  }

  const v104OriginalRenderLauncherCategories=renderLauncherCategories;
  renderLauncherCategories=function(active='Patient Care'){
    state.v104LauncherCategory=active;
    const cats=$('#launcherCategories'),acts=$('#launcherActivities');if(!cats||!acts)return;
    const pins=new Set(v104Read('pinnedActivities',[]).map(x=>x.route));
    cats.innerHTML=Object.keys(v4LauncherMap).map(name=>`<button class="launcher-category ${name===active?'active':''}" data-launcher-category="${esc(name)}"><span class="cat-icon">${v4Icon(v4ModuleTabs.find(x=>x.label===name)?.icon||'tools')}</span>${esc(name)}<span class="cat-chevron">›</span></button>`).join('');
    acts.innerHTML=(v4LauncherMap[active]||[]).filter(([,route])=>canOpenRoute(route)).map(([label,route,icon,detail])=>`<button class="launcher-activity" data-route="${esc(route)}"><span class="activity-icon">${v4Icon(icon)}</span><span><strong>${esc(label)}</strong><small>${esc(detail)}</small></span><span class="launcher-pin ${pins.has(route)?'pinned':''}" data-v104-action="pin-activity" data-route="${esc(route)}" title="${pins.has(route)?'Unpin':'Pin'} activity">${pins.has(route)?'★':'☆'}</span></button>`).join('');
    v104RenderLauncherMemory();
  };

  const v104PreviousNavigate=navigate;
  navigate=function(route,options){v104RememberActivity(route);return v104PreviousNavigate(route,options);};

  function v104PatientMemoryCard(p,kind){return `<button class="patient-memory-card" data-v104-action="preview-memory-patient" data-patient-id="${esc(p.mpi_id)}"><span class="patient-memory-avatar">${esc(initials(p.full_name))}</span><span><strong>${esc(p.full_name)}</strong><small>${esc(p.mrn||p.mpi_id)} · ${esc(p.phone||'No phone')}</small></span><span class="favorite-star ${v104IsPatientFavorite(p.mpi_id)?'active':''}" data-v104-action="toggle-patient-favorite" data-patient-id="${esc(p.mpi_id)}" title="Favorite">★</span></button>`;}
  function v104PatientPreview(p){if(!p)return `<div class="patient-preview-empty"><div><span class="patient-memory-avatar">⌕</span><h3>Select a patient</h3><p>Review identity and encounter context before opening the Patient Station or chart.</p></div></div>`;const active=(p.encounters||[]).find(e=>!['DISCHARGED','CANCELLED','COMPLETED'].includes(String(e.status)))||(p.encounters||[])[0];return `<div class="patient-preview-card"><div class="patient-preview-header"><span class="patient-memory-avatar">${esc(initials(p.full_name))}</span><div><h2>${esc(p.full_name)}</h2><p>${esc(p.mrn)} · ${esc(p.mpi_id)}</p><p>${esc(p.sex||'—')} · ${esc(p.date_of_birth||'DOB unknown')}</p></div><button class="favorite-star ${v104IsPatientFavorite(p.mpi_id)?'active':''}" data-v104-action="toggle-patient-favorite" data-patient-id="${esc(p.mpi_id)}">★</button></div><div class="patient-preview-grid"><div><span>Phone</span><strong>${esc(p.phone||'Not recorded')}</strong></div><div><span>NIDA</span><strong>${esc(p.nida_number||'Not recorded')}</strong></div><div><span>Coverage</span><strong>${esc(p.payer||'Not verified')}</strong></div><div><span>Current encounter</span><strong>${esc(active?`${statusLabel(active.status)} · ${active.service||'Service pending'}`:'None')}</strong></div></div><div class="patient-preview-actions"><button class="btn btn-primary" data-v104-action="open-patient-station" data-patient-id="${esc(p.mpi_id)}">Open Patient Station</button><button class="btn" data-v104-action="open-patient-chart" data-patient-id="${esc(p.mpi_id)}">Open Chart</button><button class="btn" data-route="registration">New Encounter</button><button class="btn" data-v104-action="patient-event-history" data-patient-id="${esc(p.mpi_id)}">Event History</button></div></div>`;}

  renderPatientSearch=async function(){
    const favorites=v104Read('favoritePatients',[]),recent=v104Read('recentPatients',[]);state.v104SearchResults=state.v104SearchResults||[];
    $('#mainContent').innerHTML=`${pageHeader('Patient Access','Patient Station & Record Search','Search the enterprise MPI, reopen recent records, or pin frequently accessed patients. Selecting a patient establishes the record context before any chart-driven workflow.',`<button class="btn btn-primary" data-route="registration">+ New Registration</button>`)}<section class="patient-lookup-station"><aside class="card"><div class="card-header"><h2>Recents & Favorites</h2></div><div class="card-body patient-memory-list"><p class="eyebrow">Favorites (${favorites.length})</p>${favorites.map(p=>v104PatientMemoryCard(p,'favorite')).join('')||'<p class="muted">No favorite patients.</p>'}<p class="eyebrow" style="margin-top:18px">Recent records (${recent.length})</p>${recent.map(p=>v104PatientMemoryCard(p,'recent')).join('')||'<p class="muted">No recently opened records.</p>'}</div></aside><section class="card"><div class="card-header"><div><h2>Enterprise Patient Lookup</h2><p>Name, MRN, MPI, NIDA, phone or visit ID</p></div></div><div class="card-body"><div class="search-bar"><input id="patientSearchInput" autofocus value="${esc(state.v104PatientQuery||'')}" placeholder="Search name, MPI, MRN, phone or NIDA…"><button class="btn btn-primary" data-v104-action="run-station-search">Search</button><button class="btn" data-v104-action="clear-station-search">Clear</button></div><div id="patientSearchResults"><div class="empty-state"><p>Enter at least one search term, or choose a recent patient.</p></div></div></div></section><aside class="card patient-preview-pane"><div class="card-header"><h2>Patient Preview</h2></div><div class="card-body" id="patientPreview">${v104PatientPreview(state.v104PreviewPatient||null)}</div></aside></section>`;
    if(state.v104PatientQuery)await performPatientSearch(state.v104PatientQuery);
  };
  performPatientSearch=async function(value){const q=String(value||'').trim();state.v104PatientQuery=q;const target=$('#patientSearchResults');if(!target)return;target.innerHTML='<div class="empty-state"><p>Searching enterprise MPI…</p></div>';const patients=await api(`/patients${q?`?search=${encodeURIComponent(q)}`:'?limit=25'}`);state.v104SearchResults=patients;target.innerHTML=patients.length?`<div class="table-wrap"><table><thead><tr><th>Patient</th><th>Identifiers</th><th>Demographics</th><th>Coverage</th><th>Action</th></tr></thead><tbody>${patients.map(p=>`<tr><td><button class="link-button" data-v104-action="preview-search-patient" data-patient-id="${esc(p.mpi_id)}"><strong>${esc(p.full_name)}</strong></button><br><small>${esc(p.phone||'No phone')}</small></td><td>${esc(p.mrn)}<br><small>${esc(p.nida_number||p.mpi_id)}</small></td><td>${esc(p.sex||'—')} · ${esc(p.date_of_birth||'DOB unknown')}<br><small>${esc(p.region||'Tanzania')}</small></td><td>${esc(p.payer||'Not verified')}<br><small>${esc(p.consent_status||'Consent pending')}</small></td><td><button class="btn btn-sm btn-primary" data-v104-action="open-patient-station" data-patient-id="${esc(p.mpi_id)}">Patient Station</button></td></tr>`).join('')}</tbody></table></div>`:'<div class="empty-state"><p>No matching patients.</p></div>';};

  document.addEventListener('click',async e=>{
    const el=e.target.closest('[data-v104-action],[data-v104-route]');if(!el)return;
    const action=el.dataset.v104Action;
    if(el.dataset.v104Route){e.preventDefault();e.stopImmediatePropagation();return navigate(el.dataset.v104Route);}
    if(!action)return;
    e.preventDefault();e.stopImmediatePropagation();
    try{
      if(action==='pin-activity')return v104TogglePin(el.dataset.route);
      if(action==='unpin-activity')return v104TogglePin(el.dataset.route);
      if(action==='clear-pinned'){v104Write('pinnedActivities',[]);return renderLauncherCategories(state.v104LauncherCategory||'Patient Care');}
      if(action==='clear-recent'){v104Write('recentActivities',[]);return renderLauncherCategories(state.v104LauncherCategory||'Patient Care');}
      if(action==='run-station-search')return performPatientSearch($('#patientSearchInput')?.value||'');
      if(action==='clear-station-search'){state.v104PatientQuery='';state.v104SearchResults=[];return renderPatientSearch();}
      if(action==='preview-search-patient'){const p=(state.v104SearchResults||[]).find(x=>x.mpi_id===el.dataset.patientId)||await api(`/patients/${encodeURIComponent(el.dataset.patientId)}`);state.v104PreviewPatient=p;v104RememberPatient(p);$('#patientPreview').innerHTML=v104PatientPreview(p);return;}
      if(action==='preview-memory-patient'){const p=await api(`/patients/${encodeURIComponent(el.dataset.patientId)}`);state.v104PreviewPatient=p;v104RememberPatient(p);$('#patientPreview').innerHTML=v104PatientPreview(p);return;}
      if(action==='toggle-patient-favorite'){let p=(state.v104SearchResults||[]).find(x=>x.mpi_id===el.dataset.patientId)||state.v104PreviewPatient;if(!p||p.mpi_id!==el.dataset.patientId)p=await api(`/patients/${encodeURIComponent(el.dataset.patientId)}`);return v104TogglePatientFavorite(p);}
      if(action==='open-patient-station'||action==='open-patient-chart'){const p=await api(`/patients/${encodeURIComponent(el.dataset.patientId)}`);state.selectedPatientId=p.mpi_id;state.v104PreviewPatient=p;v104RememberPatient(p);saveState();return navigate(action==='open-patient-station'?'patient-station':'chart',{preservePatient:true});}
      if(action==='patient-event-history'){state.selectedPatientId=el.dataset.patientId;saveState();return navigate('event-management');}
    }catch(err){console.error(err);toast('Patient Station action failed',err.message||String(err));}
  },true);
  document.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.id==='patientSearchInput'){e.preventDefault();performPatientSearch(e.target.value);}},true);

  installV4ChromeHandlers();
  installV5EnhancementHandlers();

  const COUNTRY_META={
    TZ:{name:'Tanzania',formal:'United Republic of Tanzania',ministry:'Ministry of Health',logo:'/assets/tanzania-coat-of-arms.png'},
    KE:{name:'Kenya',formal:'Republic of Kenya',ministry:'Ministry of Health',logo:'/assets/kenya-ministry-health.png'},
    NG:{name:'Nigeria',formal:'Federal Republic of Nigeria',ministry:'Federal Ministry of Health and Social Welfare',logo:'/assets/nigeria-ministry-health.png'},
    PK:{name:'Pakistan',formal:'Islamic Republic of Pakistan',ministry:'Ministry of National Health Services, Regulations and Coordination',logo:'/assets/pakistan-flag.svg'},
    RW:{name:'Rwanda',formal:'Republic of Rwanda',ministry:'Ministry of Health',logo:'/assets/rwanda-flag.svg'}
  };
  function applyCountryBranding(){const meta=COUNTRY_META[state.countryCode]||COUNTRY_META.TZ;const logo=$('#ministryLogo');if(logo){logo.src=meta.logo;logo.alt=meta.formal;}$('#ministryCountryName')&&($('#ministryCountryName').textContent=meta.formal);$('#ministryName')&&($('#ministryName').textContent=meta.ministry+' · National Electronic Health Record');$('#loginCountryEyebrow')&&($('#loginCountryEyebrow').textContent=meta.formal);$('#loginFooterCountry')&&($('#loginFooterCountry').textContent=meta.formal+' · '+meta.ministry);document.documentElement.dataset.country=state.countryCode||'TZ';}
  async function selectCountryContext(code){state.countryCode=code;state.countrySelected=true;localStorage.setItem('umojaCountry',code);applyCountryBranding();$$('[data-country-select]').forEach(x=>x.classList.toggle('selected',x.dataset.countrySelect===code));try{state.facilities=await api(`/facilities?country_code=${encodeURIComponent(code)}`);renderFacilitySelect();}catch(error){toast('Country context unavailable',error.message);return;}$('#countryLanding').classList.add('hidden');$('#loginOverlay').classList.remove('hidden');}
  function renderCountryLanding(){applyCountryBranding();if(state.account)return;$('#countryLanding')?.classList.remove('hidden');$('#loginOverlay')?.classList.add('hidden');}
  document.addEventListener('click',event=>{const button=event.target.closest('[data-country-select]');if(button){event.preventDefault();selectCountryContext(button.dataset.countrySelect);}});


  /* --------------------------------------------------------------------------
     v10.6 real-time collaboration, idempotent workflow and discoverability.
  --------------------------------------------------------------------------- */
  const V106_LOCKED_ROUTES=new Set(['patient-station','chart','clinical-documentation','orders','results','flowsheets','nursing','pharmacy','telehealth','maternity','cardiology','orthopaedics','oncology','critical-care','rehab','anesthesia','theatre']);
  const V106_ACTIVITY_LABELS={
    'patient-station':'Patient Station','chart':'Longitudinal Chart','clinical-documentation':'Clinical Documentation',orders:'Orders',results:'Results Review',flowsheets:'Flowsheets & eMAR',nursing:'Nursing Workspace',pharmacy:'Medication Management',telehealth:'Telehealth',maternity:'Maternity',cardiology:'Cardiology',orthopaedics:'Orthopaedics and Trauma',oncology:'Oncology','critical-care':'Critical Care',rehab:'Rehabilitation',anesthesia:'Anesthesia',theatre:'Theatre'
  };
  state.v106Lock=null;state.v106LockRoute=null;state.v106Heartbeat=null;state.v106Refresh=null;state.v106IncomingSeen=new Set();
  function v106ActiveEncounterId(patient){const e=(patient?.encounters||[]).find(x=>!['DISCHARGED','TRANSFERRED','LEFT_WITHOUT_BEING_SEEN','COMPLETED','CANCELLED'].includes(String(x.status)))||patient?.encounters?.[0];return e?.encounter_id||null;}
  async function v106ReleaseCurrentLock(){const lock=state.v106Lock;if(!lock?.owned_by_me||!lock.lock_id)return;state.v106Lock=null;state.v106LockRoute=null;clearInterval(state.v106Heartbeat);state.v106Heartbeat=null;try{await api(`/collaboration/locks/${encodeURIComponent(lock.lock_id)}/release`,{method:'POST',keepalive:true});}catch(err){console.warn('Lock release deferred to expiry',err);}}
  async function v106AcquireForRoute(route){
    if(!state.selectedPatientId||!V106_LOCKED_ROUTES.has(route))return {status:'NOT_REQUIRED'};
    if(state.v106Lock?.owned_by_me&&state.v106LockRoute===route)return state.v106Lock;
    if(state.v106Lock?.owned_by_me&&state.v106LockRoute!==route)await v106ReleaseCurrentLock();
    const patient=await api(`/patients/${encodeURIComponent(state.selectedPatientId)}`);
    const result=await api('/collaboration/locks/acquire',{method:'POST',body:JSON.stringify({patient_mpi_id:patient.mpi_id,encounter_id:v106ActiveEncounterId(patient),activity_code:route})});
    state.v106Lock=result;state.v106LockRoute=route;
    clearInterval(state.v106Heartbeat);
    if(result.owned_by_me&&result.lock_id){state.v106Heartbeat=setInterval(async()=>{try{await api(`/collaboration/locks/${encodeURIComponent(result.lock_id)}/heartbeat`,{method:'POST'});}catch(err){clearInterval(state.v106Heartbeat);state.v106Heartbeat=null;state.v106Lock=null;toast('Record activity released',err.message||'The collaboration lock is no longer active.');}},60000);}
    return result;
  }
  function v106LockBlockedView(lock){
    const req=lock.request||{};const retry=req.retry_after?new Date(req.retry_after).toLocaleTimeString():'';
    $('#mainContent').innerHTML=`${pageHeader('Collaborative record safety',V106_ACTIVITY_LABELS[state.route]||'Patient Activity','Only one user may edit the same patient activity at a time. Other users can request a controlled handoff.')}
    <section class="v106-lock-panel"><div class="v106-lock-icon">🔒</div><div><p class="eyebrow">Activity currently in use</p><h2>${esc(lock.holder?.display_name||lock.holder?.username||'Another user')} is working in this activity</h2><p>Their lock remains active while they are working and expires after five minutes without a heartbeat.</p>${req.status==='PENDING'?`<div class="alert info"><strong>Permission requested.</strong> Waiting for the current user to respond. Automatic handoff is scheduled if the lock expires.</div>`:''}${req.status==='DENIED'?`<div class="alert warning"><strong>Request declined.</strong> ${esc(req.denial_reason||'No reason supplied.')} ${retry?`Try again after ${esc(retry)}.`:''}</div>`:''}</div><div class="page-actions"><button class="btn" data-route="patient-search">Choose another patient</button><button class="btn btn-primary" data-v106-action="request-lock" data-lock-id="${esc(lock.lock_id)}" ${req.status==='PENDING'?'disabled':''}>${req.status==='PENDING'?'Request pending':'Ask for permission'}</button><button class="btn" data-v106-action="retry-lock">Retry</button></div></section>`;
  }
  const v106OriginalRender=render;
  render=async function(){
    if(state.account&&state.selectedPatientId&&V106_LOCKED_ROUTES.has(state.route)){
      try{const lock=await v106AcquireForRoute(state.route);if(lock.status==='LOCKED'&&!lock.owned_by_me){v106LockBlockedView(lock);return;}}catch(err){console.error(err);$('#mainContent').innerHTML=`${pageHeader('Collaboration service','Unable to secure patient activity','The record was not opened because an exclusive activity lock could not be confirmed.')}<div class="alert danger">${esc(err.message||String(err))}</div>`;return;}
    }else if(state.v106Lock?.owned_by_me){await v106ReleaseCurrentLock();}
    await v106OriginalRender();v106DecorateTooltips();
  };
  async function v106PollIncoming(){if(!state.account)return;try{const data=await api('/collaboration/locks/requests/incoming');for(const item of data.items||[]){if(state.v106IncomingSeen.has(item.request_id))continue;state.v106IncomingSeen.add(item.request_id);v106ShowIncomingRequest(item);}}catch(err){console.debug('Incoming lock poll',err.message);}}
  function v106ShowIncomingRequest(item){openModal('Patient activity handoff request',`<div class="alert info"><strong>${esc(item.requester)}</strong> is asking to open <strong>${esc(V106_ACTIVITY_LABELS[item.activity_code]||item.activity_code)}</strong> for <strong>${esc(item.patient_name)}</strong>.</div><div class="form-grid" style="margin-top:12px"><label class="field full"><span>Requester reason</span><textarea readonly>${esc(item.reason||'No reason supplied')}</textarea></label><label class="field full"><span>Reason if declining</span><textarea id="v106DenyReason" placeholder="Explain why the record cannot be released yet"></textarea></label><label class="field"><span>Time needed if declining</span><select id="v106DenyMinutes"><option value="5">5 minutes</option><option value="10">10 minutes</option><option value="15">15 minutes</option><option value="30">30 minutes</option><option value="60">1 hour</option></select></label></div><p class="muted">Selecting Yes closes your current patient activity and transfers it to the requester. Without a response, the lock releases after five minutes without a heartbeat.</p>`,`<button class="btn" data-v106-action="deny-lock-request" data-request-id="${esc(item.request_id)}">No — keep activity</button><button class="btn btn-primary" data-v106-action="grant-lock-request" data-request-id="${esc(item.request_id)}">Yes — release and transfer</button>`,'Controlled record handoff');}
  function v106RefreshSafe(){if(!state.account||document.hidden||$('#modalBackdrop')?.classList.contains('visible'))return;const active=document.activeElement;if(active&&['INPUT','TEXTAREA','SELECT'].includes(active.tagName))return;if(state.route==='clinical-documentation'&&$('#v9NoteBody')?.value?.trim())return;render().catch(console.error);v106PollIncoming();}
  function v106StartRealtime(){clearInterval(state.v106Refresh);state.v106Refresh=setInterval(v106RefreshSafe,APP_REFRESH_INTERVAL_MS);v106PollIncoming();}
  const v106OpenAuthenticatedApp=openAuthenticatedApp;
  openAuthenticatedApp=function(){v106OpenAuthenticatedApp();v106StartRealtime();};
  const v106EnterApp=enterApp;
  enterApp=async function(){return v106EnterApp();};

  const V106_TOOLTIPS={
    'Open Patient Station':'Open registration, encounter, coverage and patient-flow tools for the selected record.',
    'Open Chart':'Open the longitudinal clinical record for the selected patient.',
    'Print Label':'Choose patient labels, wristbands, facesheets and chart documents.',
    'Benefit Check':'Verify coverage eligibility and route exceptions to follow-up.',
    'Travel Screening':'Document travel, exposure and symptom screening.',
    'Event History':'Review every recorded action, reversal and correction.',
    'Arrive':'Mark the patient present and notify downstream registration and triage workspaces.',
    'Check In':'Complete front-desk arrival and advance the patient to the next valid step.',
    'Send to Triage':'Route the patient into the clinical triage queue.',
    'New Note':'Create a patient-linked clinical note; signed notes remain immutable.',
    'Orders':'Search and place patient-linked clinical or operational orders.',
    'Change Context':'Select the authorized country, facility, department and unit.'
  };
  function v106DecorateTooltips(root=document){root.querySelectorAll('button,a,[role="button"],.nav-item,.top-action').forEach(el=>{if(el.dataset.tooltip)return;const label=(el.getAttribute('aria-label')||el.title||el.textContent||'').replace(/\s+/g,' ').trim();const key=Object.keys(V106_TOOLTIPS).find(k=>label.toLowerCase().includes(k.toLowerCase()));const detail=key?V106_TOOLTIPS[key]:(el.title&&el.title!==label?el.title:'');if(detail){el.dataset.tooltip=detail;el.removeAttribute('title');}});}
  new MutationObserver(m=>{for(const x of m)for(const node of x.addedNodes)if(node.nodeType===1)v106DecorateTooltips(node);}).observe(document.body,{childList:true,subtree:true});

  const V106_NON_REPEATABLE={
    'today-arrive':'PATIENT_ARRIVAL','submit-registration':'PATIENT_REGISTRATION','discharge':'PATIENT_DISCHARGE',
    'confirm-expire-patient':'PATIENT_EXPIRY','walk-finish':'WALKIN_REGISTRATION_COMPLETE'
  };
  document.addEventListener('click',async event=>{
    const el=event.target.closest('[data-action],[data-v5-action],[data-v6-action]');if(!el||el.dataset.v106Guarded==='1'||!state.selectedPatientId)return;
    const action=el.dataset.action||el.dataset.v5Action||el.dataset.v6Action;const code=V106_NON_REPEATABLE[action];if(!code)return;
    event.preventDefault();event.stopImmediatePropagation();
    try{const patient=await api(`/patients/${encodeURIComponent(state.selectedPatientId)}`);await api('/collaboration/workflows/start',{method:'POST',body:JSON.stringify({patient_mpi_id:patient.mpi_id,encounter_id:v106ActiveEncounterId(patient),workflow_code:code,metadata:{route:state.route,action}})});el.dataset.v106Guarded='1';el.click();delete el.dataset.v106Guarded;}catch(err){toast('Workflow already initiated',err.message||'This workflow cannot be repeated. Open Event History to review the original action.');}
  },true);

  document.addEventListener('click',async event=>{const el=event.target.closest('[data-v106-action]');if(!el)return;event.preventDefault();event.stopImmediatePropagation();try{
    if(el.dataset.v106Action==='request-lock'){const reason=prompt('Briefly explain why you need this patient activity:','I need to continue the patient workflow.');if(!reason)return;const r=await api(`/collaboration/locks/${encodeURIComponent(el.dataset.lockId)}/request`,{method:'POST',body:JSON.stringify({reason})});toast('Permission requested',r.status==='RETRY_ACQUIRE'?'The lock expired. Retry opening the activity.':'The current user has been notified.');return render();}
    if(el.dataset.v106Action==='retry-lock'){state.v106Lock=null;return render();}
    if(el.dataset.v106Action==='grant-lock-request'){await api(`/collaboration/requests/${encodeURIComponent(el.dataset.requestId)}/respond`,{method:'POST',body:JSON.stringify({decision:'YES'})});closeModal();state.v106Lock=null;toast('Activity transferred','Your patient activity was closed and released to the requester.');return navigate('patient-search');}
    if(el.dataset.v106Action==='deny-lock-request'){const reason=$('#v106DenyReason')?.value.trim();const timeframe=Number($('#v106DenyMinutes')?.value||5);if(!reason)throw new Error('Enter a reason before declining.');await api(`/collaboration/requests/${encodeURIComponent(el.dataset.requestId)}/respond`,{method:'POST',body:JSON.stringify({decision:'NO',reason,timeframe_minutes:timeframe})});closeModal();toast('Request declined',`The requester was given your reason and a ${timeframe}-minute timeframe.`);}
  }catch(err){toast('Collaboration action failed',err.message||String(err));}},true);
  window.addEventListener('beforeunload',()=>{if(state.v106Lock?.owned_by_me&&state.v106Lock.lock_id&&state.token)fetch(`${API}/collaboration/locks/${encodeURIComponent(state.v106Lock.lock_id)}/release`,{method:'POST',headers:{Authorization:`Bearer ${state.token}`},keepalive:true}).catch(()=>{});});
  v106DecorateTooltips();

  /* v10.12: reactive facility context, personalization, country ambience and
     compact activity memory. Preferences contain no patient information. */
  const V1012_PREF_KEY='umoja.v10.12.preferences';
  function v1012Preferences(){try{return {...{theme:'light',density:'comfortable',accent:'teal',flagBackground:true},...JSON.parse(localStorage.getItem(V1012_PREF_KEY)||'{}')}}catch{return {theme:'light',density:'comfortable',accent:'teal',flagBackground:true};}}
  function v1012ApplyPreferences(){
    const p=v1012Preferences(),root=document.documentElement;
    root.dataset.theme=p.theme;root.dataset.density=p.density;root.dataset.accent=p.accent;
    root.classList.toggle('country-ambience',p.flagBackground!==false);
    const themeMeta=$('meta[name="theme-color"]');if(themeMeta)themeMeta.content=p.theme==='dark'?'#071d28':'#008c76';
  }
  function v1012UpdateFacilityContext(){
    const facility=currentFacility();
    $('#statusFacilityName')&&($('#statusFacilityName').textContent=facility.name||facility.code||'Selected facility');
    $('#statusFacilityCode')&&($('#statusFacilityCode').textContent=facility.code||'Facility context');
    document.documentElement.dataset.facility=facility.code||'';
  }
  function v1012OpenPreferences(){
    const p=v1012Preferences();
    openModal('Personalize Umoja Afya',`<div class="v1012-preferences">
      <p class="muted">These display preferences stay on this device and never include patient information.</p>
      <label class="field"><span>Appearance</span><select id="v1012Theme"><option value="light" ${p.theme==='light'?'selected':''}>Light</option><option value="dark" ${p.theme==='dark'?'selected':''}>Dark</option><option value="system" ${p.theme==='system'?'selected':''}>Use device setting</option></select></label>
      <label class="field"><span>Display density</span><select id="v1012Density"><option value="comfortable" ${p.density==='comfortable'?'selected':''}>Comfortable</option><option value="compact" ${p.density==='compact'?'selected':''}>Compact</option></select></label>
      <label class="field"><span>Accent</span><select id="v1012Accent"><option value="teal" ${p.accent==='teal'?'selected':''}>Clinical teal</option><option value="blue" ${p.accent==='blue'?'selected':''}>Ocean blue</option><option value="violet" ${p.accent==='violet'?'selected':''}>Violet</option></select></label>
      <label class="v1012-check"><input id="v1012FlagBackground" type="checkbox" ${p.flagBackground!==false?'checked':''}><span>Use subtle selected-country flag background</span></label>
    </div>`,`<button class="btn" data-v1012-action="sign-out">Sign out</button><button class="btn" data-modal-action="close">Cancel</button><button class="btn btn-primary" data-v1012-action="save-preferences">Save preferences</button>`,'Display and account');
  }
  document.addEventListener('click',event=>{
    const profile=event.target.closest('#userMenuButton');
    if(profile){event.preventDefault();event.stopImmediatePropagation();v1012OpenPreferences();return;}
    const action=event.target.closest('[data-v1012-action]')?.dataset.v1012Action;if(!action)return;
    event.preventDefault();event.stopImmediatePropagation();
    if(action==='save-preferences'){
      localStorage.setItem(V1012_PREF_KEY,JSON.stringify({theme:$('#v1012Theme').value,density:$('#v1012Density').value,accent:$('#v1012Accent').value,flagBackground:$('#v1012FlagBackground').checked}));
      v1012ApplyPreferences();closeModal();toast('Preferences saved','Your workspace appearance has been updated.');return;
    }
    if(action==='sign-out'){state.token='';state.account=null;state.offlineSession=false;sessionStorage.removeItem('umojaAfyaToken');window.UmojaOffline?.lock();closeModal();$('#app').setAttribute('aria-hidden','true');$('#loginOverlay').classList.add('hidden');$('#countryLanding').classList.remove('hidden');}
  },true);
  document.addEventListener('change',event=>{if(event.target.id==='facilitySelect')queueMicrotask(v1012UpdateFacilityContext);},true);
  const v1012Render=render;
  render=async function(){v1012UpdateFacilityContext();await v1012Render();v1012UpdateFacilityContext();};
  const v1012FacilitySelect=renderFacilitySelect;
  renderFacilitySelect=function(){v1012FacilitySelect();v1012UpdateFacilityContext();};
  const v1012CountryBranding=applyCountryBranding;
  applyCountryBranding=function(){v1012CountryBranding();v1012ApplyPreferences();};
  v1012ApplyPreferences();

  /* ------------------------------------------------------------------------
     Release 10.14 record-centred Patient Station and financial workflow.
     The Patient Station is a longitudinal-record launcher, not a second copy
     of Today's Patients or the operational workqueue dashboard. Activities
     that do not represent a visit remain patient-linked without fabricating
     an encounter. Scheduled arrival, walk-in and triage retain encounter
     guardrails. Billing follows the selected record and local currency.
  ------------------------------------------------------------------------- */
  state.v1014StationTab=state.v1014StationTab||'actions';
  state.v1014StationSearchResults=state.v1014StationSearchResults||[];
  state.v1014StationQuery=state.v1014StationQuery||'';
  operationFacility=function(){
    if(state.facility&&state.facility!=='ALL')return state.facility;
    return state.facilities.find(f=>!state.countryCode||f.country_code===state.countryCode)?.code||state.facilities[0]?.code||'MNH-UPANGA';
  };

  function v1014Currency(){
    return ({
      TZ:{code:'TZS',symbol:'TSh',locale:'en-TZ',methods:['Cash','Card','Bank transfer','GePG','M-Pesa','Airtel Money','Tigo Pesa','HaloPesa','USDT','Bitcoin','Ethereum']},
      KE:{code:'KES',symbol:'KSh',locale:'en-KE',methods:['Cash','Card','Bank transfer','M-Pesa','Airtel Money','PesaLink','eCitizen','USDT','Bitcoin','Ethereum']},
      NG:{code:'NGN',symbol:'₦',locale:'en-NG',methods:['Cash','Card','Bank transfer','USSD','OPay','PalmPay','Paga','Remita','USDT','Bitcoin','Ethereum']},
      PK:{code:'PKR',symbol:'Rs',locale:'en-PK',methods:['Cash','Card','Bank transfer','Raast','Easypaisa','JazzCash','1LINK','USDT','Bitcoin','Ethereum']},
      RW:{code:'RWF',symbol:'FRw',locale:'en-RW',methods:['Cash','Card','Bank transfer','MTN MoMo','Airtel Money','IremboPay','USDT','Bitcoin','Ethereum']}
    })[state.countryCode]||{code:'USD',symbol:'$',locale:'en-US',methods:['Cash','Card','Bank transfer','USDT','Bitcoin','Ethereum']};
  }
  function v1014Money(value,currencyCode){const active=v1014Currency(),code=currencyCode||active.code,locale=({TZS:'en-TZ',KES:'en-KE',NGN:'en-NG',PKR:'en-PK',RWF:'en-RW',USD:'en-US'})[code]||active.locale;try{return new Intl.NumberFormat(locale,{style:'currency',currency:code,maximumFractionDigits:2}).format(Number(value)||0);}catch(_){return `${code} ${(Number(value)||0).toLocaleString(locale)}`;}}
  function v1014Can(capability){return !state.account||(state.account.functions||[]).includes(capability);}
  function v1014OpenEncounter(patient){return (patient?.encounters||[]).find(item=>item.encounter_id===state.selectedEncounterId)||v5CurrentEncounter(patient)||null;}
  function v1014ScheduledAppointment(items){return (items||[]).find(x=>['SCHEDULED','CONFIRMED'].includes(String(x.status).toUpperCase()))||null;}
  function v1014PatientRow(patient,encounter){return {patient:{mpi_id:patient.mpi_id,mrn:patient.mrn,full_name:patient.full_name},encounter_id:encounter?.encounter_id||'',service:encounter?.service||'Longitudinal record'};}
  function v1014Storyboard(patient,encounter,activity){
    return `<section class="v1014-storyboard" aria-label="Current patient record storyboard"><div class="complete"><span>1</span><small>Record</small><strong>${esc(patient.full_name)}</strong><em>${esc(patient.mrn)} · ${esc(patient.mpi_id)}</em></div><i></i><div class="${activity?'complete':'current'}"><span>2</span><small>Activity</small><strong>${esc(activity?statusLabel(activity.activity_type):'Choose next action')}</strong><em>${esc(activity?.title||'Registration, chart, call, refill or finance')}</em></div><i></i><div class="${encounter?'complete':'optional'}"><span>3</span><small>Encounter (when needed)</small><strong>${esc(encounter?encounter.service:'Not required')}</strong><em>${esc(encounter?`${encounter.encounter_id} · ${statusLabel(encounter.status)}`:'Phone calls, refills and counseling can stay record-only')}</em></div></section>`;
  }
  function v10163RecentPatientLookup(patient){
    const recent=v104Read('recentPatients',[]).filter(item=>item.mpi_id!==patient?.mpi_id).slice(0,6);
    if(!recent.length)return '';
    return `<section class="v10163-recent-patients"><header><strong>Recently viewed</strong><small>${esc(currentFacility()?.name||operationFacility())}</small></header><div>${recent.map(item=>`<button data-v1014-action="select-record" data-patient-id="${esc(item.mpi_id)}"><strong>${esc(item.full_name)}</strong><span>${esc(item.mrn||item.mpi_id)}</span></button>`).join('')}</div></section>`;
  }
  function v1014RecordFinder(patient){
    const results=state.v1014StationSearchResults||[],canSearch=v1014Can('patient.search'),canRegister=v1014Can('registration.manage');
    return `<aside class="v1014-record-finder ua-card"><div class="ua-card-header"><div><h2>Record Finder</h2><p>${canSearch?'Type any part of a name, MRN, MPI, phone or national ID':'Patient search is not assigned to this account'}</p></div></div><div class="v1014-record-search"><input id="v1014RecordQuery" value="${esc(state.v1014StationQuery)}" autocomplete="off" autocapitalize="words" placeholder="Start typing a patient name or identifier" aria-controls="v1014RecordResults" ${canSearch?'':'disabled'}><button class="ua-button primary" data-v1014-action="record-search" ${canSearch?'':'disabled'}>Search</button></div><div class="v1016-search-status" id="v1014SearchStatus" aria-live="polite">${state.v1014StationQuery?`${results.length} closest match${results.length===1?'':'es'} — results narrow as you type`:'Type 2 or more characters for live matches'}</div>${!state.v1014StationQuery?v10163RecentPatientLookup(patient):''}<div id="v1014RecordResults" class="v1014-record-results">${results.map((p,index)=>`<button class="${p.mpi_id===patient?.mpi_id?'active':''}" data-v1014-action="select-record" data-patient-id="${esc(p.mpi_id)}" data-result-index="${index}"><strong>${esc(p.full_name)}</strong><span>${esc(p.mrn)} · ${esc(p.mpi_id)}</span><small>${esc(p.phone||'No phone')} · ${esc(p.payer||'Coverage not recorded')}</small></button>`).join('')||`<div class="v1014-finder-hint">${patient?`<strong>Working record</strong><span>${esc(patient.full_name)}</span><small>${esc(patient.mrn)} · ${esc(patient.mpi_id)}</small>`:canSearch?'Search and select a longitudinal record to begin.':'Open a patient from an assigned workqueue or request patient.search access.'}</div>`}</div><button class="ua-button full-width" data-v1016-action="new-registration" ${canRegister?'':'disabled'}>Register a new patient</button></aside>`;
  }

  let v1016StationSearchTimer=0,v1016StationSearchSerial=0;
  function v1016PatientSearchUrl(query){const country=state.countryCode?`&country_code=${encodeURIComponent(state.countryCode)}`:'';return `/patients?search=${encodeURIComponent(query)}&limit=30${country}`;}
  function v1016RecordResultsHtml(results,patient){return results.map((p,index)=>`<button class="${p.mpi_id===patient?.mpi_id?'active':''}" data-v1014-action="select-record" data-patient-id="${esc(p.mpi_id)}" data-result-index="${index}"><strong>${esc(p.full_name)}</strong><span>${esc(p.mrn)} · ${esc(p.mpi_id)}</span><small>${esc(p.phone||'No phone')} · ${esc(p.payer||'Coverage not recorded')}</small></button>`).join('')||'<div class="v1014-finder-hint"><strong>No matching record</strong><span>Check spelling or search by MRN, MPI, phone or national ID.</span></div>';}
  function v1016LiveRecordSearch(value){
    clearTimeout(v1016StationSearchTimer);const query=String(value||'').trim().replace(/\s+/g,' ');state.v1014StationQuery=query;
    const target=$('#v1014RecordResults'),status=$('#v1014SearchStatus');if(!target)return;
    if(query.length<2){state.v1014StationSearchResults=[];status&&(status.textContent='Type 2 or more characters for live matches');return;}
    status&&(status.textContent='Finding closest patient records…');const serial=++v1016StationSearchSerial;
    v1016StationSearchTimer=setTimeout(async()=>{try{const results=await api(v1016PatientSearchUrl(query));if(serial!==v1016StationSearchSerial)return;state.v1014StationSearchResults=results;target.innerHTML=v1016RecordResultsHtml(results,state.v5Patient);status&&(status.textContent=`${results.length} closest match${results.length===1?'':'es'} — continue typing to narrow`);}catch(error){status&&(status.textContent=error.message||'Search unavailable');}},220);
  }
  function v1014Action(code,label,description,icon='chart',disabled=false){return `<button class="v1014-action" data-v1014-action="${code}" ${disabled?'disabled':''}><span>${v4Icon(icon)}</span><strong>${esc(label)}</strong><small>${esc(description)}</small></button>`;}
  function v1014RecordRequired(title,tracker=[]){
    $('#mainContent').innerHTML=`<section class="ua-page v1014-station-page">${uaPageTitle('Patient Station',title,'<span class="v1014-page-promise">Search the longitudinal MPI by name, MRN, MPI, phone or national ID.</span>')}${v10163CareReadyBoard(tracker,true)}<div class="v1014-no-record">${v1014RecordFinder(null)}<article class="ua-card"><div class="empty-state"><h2>No patient record selected</h2><p>Every registration, chart, clinical, financial and communication workflow begins with one selected longitudinal record.</p></div></article></div></section>`;
  }

  renderPatientStationV5=async function(){
    if(!state.selectedPatientId){renderLoading('Loading patient care readiness…');const tracker=await api(`/tracker?facility_code=${encodeURIComponent(operationFacility())}`);v1014RecordRequired('Longitudinal Record Workspace',tracker);return;}
    renderLoading('Opening the longitudinal patient station…');
    const patient=await selectedPatient();if(!patient){state.selectedPatientId=null;v1014RecordRequired('Longitudinal Record Workspace');return;}
    const encoded=encodeURIComponent(patient.mpi_id);v104RememberPatient(patient);
    const canSchedule=v1014Can('scheduling.manage'),canNotes=v1014Can('notes.manage'),canRevenue=v1014Can('revenue.manage'),canRegister=v1014Can('registration.manage'),canWalkIn=v1014Can('walkins.manage'),canTriage=v1014Can('patient_flow.manage'),canFlowsheets=v1014Can('flowsheets.manage');
    const [appointments,activities,notes,charges,payments,tracker]=await Promise.all([
      canSchedule?api(`/appointments?patient_mpi_id=${encoded}&from_hours=-720&to_hours=2160`):Promise.resolve([]),
      api(`/module-activities?patient_mpi_id=${encoded}`),
      canNotes?api(`/notes?patient_mpi_id=${encoded}`):Promise.resolve([]),
      canRevenue?api(`/charges?patient_mpi_id=${encoded}`):Promise.resolve([]),
      canRevenue?api(`/payments?patient_mpi_id=${encoded}`):Promise.resolve([]),
      api(`/tracker?facility_code=${encodeURIComponent(operationFacility())}`)
    ]);
    const encounter=v1014OpenEncounter(patient),scheduled=v1014ScheduledAppointment(appointments),recent=activities[0]||null;
    const billed=charges.filter(x=>x.status==='POSTED').reduce((n,x)=>n+Number(x.total||0),0),paid=payments.reduce((n,x)=>n+Number(x.amount||0),0);
    const actions=`<div class="v1014-action-grid">
      ${v1014Action('open-chart','Open Chart','Review the complete longitudinal clinical record','chart')}
      ${v1014Action('open-registration','Registration Record',canRegister?'Identity, demographics, contacts and coverage':'Not assigned: registration.manage','registration',!canRegister)}
      ${scheduled?v1014Action('arrive-scheduled','Arrive Scheduled Patient',`${scheduled.service} · ${fmtDate(scheduled.scheduled_start)}`,'scheduling',!canSchedule):v1014Action('walk-in','Start Walk-In',canWalkIn?'Create an arrival only when care is being initiated':'Not assigned: walkins.manage','registration',!canWalkIn)}
      ${v1014Action('triage','Triage',!canTriage?'Not assigned: patient_flow.manage':encounter?'Record acuity, complaint and route to triage':'Requires an active arrival','patient',!encounter||!canTriage)}
      ${v1014Action('provider-workflow','Provider Visit',encounter?`ROS, examination, assessment and plan · ${statusLabel(encounter.status)}`:'Requires a selected visit','chart',!encounter||!canNotes)}
      ${v1014Action('phone-call','Phone Call','Record communication without creating an encounter','messages')}
      ${v1014Action('refill','Refill Request','Route a medication refill without creating a visit','orders')}
      ${v1014Action('print-forms','Print Forms','Labels, wristbands, facesheet and visit documents','documents')}
      ${v1014Action('consents','Consents & Signatures','Search approved consent forms and capture an electronic signature','documents',!canRegister)}
      ${v1014Action('open-billing','Billing & Account',canRevenue?'Charges, billed-to, claims and payments':'Not assigned: revenue.manage','billing',!canRevenue)}
      ${v1014Action('financial-counseling','Financial Counseling',canRevenue?'Record advice, estimates and assistance':'Not assigned: revenue.manage','patient',!canRevenue)}
      ${v1014Action('payment-plan','Payment Plan',canRevenue?'Create a record-linked installment plan':'Not assigned: revenue.manage','billing',!canRevenue)}
      ${v1014Action('collect-payment','Collect Payment',canRevenue?`${v1014Currency().code} cash, card, mobile money or crypto`:'Not assigned: revenue.manage','billing',!canRevenue)}
      ${v1014Action('open-flowsheets','Flowsheets',canFlowsheets?'Open editable longitudinal observations':'Not assigned: flowsheets.manage','reports',!canFlowsheets)}
    </div>`;
    const registration=`<article class="ua-card v1014-detail-card"><div class="ua-card-header"><div><h2>Registration side of record</h2><p>Demographics, identity, contact, coverage and consent</p></div><button class="ua-button primary" data-v1014-action="open-registration" ${canRegister?'':'disabled'}>Open Registration</button></div><div class="v1014-detail-grid">${[['MRN',patient.mrn],['MPI',patient.mpi_id],['National ID',patient.nida_number||'Not recorded'],['Phone',patient.phone||'Not recorded'],['Sex',patient.sex||'Not recorded'],['Date of birth',patient.date_of_birth||'Not recorded'],['Address',patient.address||'Not recorded'],['Coverage',patient.payer||'Not recorded'],['Member number',patient.member_number||'Not recorded'],['Consent',statusLabel(patient.consent_status||'Pending')]].map(([k,v])=>`<div><span>${k}</span><strong>${esc(v)}</strong></div>`).join('')}</div>${canRegister?'':'<div class="alert info"><strong>Read-only record context.</strong> This account is not assigned registration.manage.</div>'}</article>`;
    const encounters=`<article class="ua-card v1014-detail-card"><div class="ua-card-header"><div><h2>Encounters and scheduled care</h2><p>Choose the exact visit before reviewing or documenting. Historical visits remain available but closed.</p></div></div><div class="table-wrap"><table class="ua-data-table"><thead><tr><th>Date</th><th>Visit / appointment</th><th>Service</th><th>Status</th><th>Record action</th></tr></thead><tbody>${appointments.map(a=>`<tr><td>${fmtDate(a.scheduled_start)}</td><td>${esc(a.appointment_id)}</td><td>${esc(a.service)}</td><td><span class="ua-status ${uaStatusClass(a.status)}">${esc(statusLabel(a.status))}</span></td><td>${['SCHEDULED','CONFIRMED'].includes(a.status)?`<button class="ua-button compact" data-v1014-action="arrive-appointment" data-appointment-id="${esc(a.appointment_id)}">Arrive</button>`:'—'}</td></tr>`).join('')}${(patient.encounters||[]).map(e=>`<tr class="${e.encounter_id===encounter?.encounter_id?'selected-row':''}"><td>${fmtDate(e.arrival_at)}</td><td>${esc(e.encounter_id)}</td><td>${esc(e.service)} · ${esc(e.encounter_type)}</td><td><span class="ua-status ${uaStatusClass(e.status)}">${esc(statusLabel(e.status))}</span></td><td><button class="ua-button compact" data-v1014-action="open-chart" data-encounter-id="${esc(e.encounter_id)}">${['DISCHARGED','TRANSFERRED','LEFT_WITHOUT_BEING_SEEN'].includes(e.status)?'Review visit':'Work in visit'}</button></td></tr>`).join('')||'<tr><td colspan="5">No visits recorded.</td></tr>'}</tbody></table></div></article>`;
    const documents=`<article class="ua-card v1014-detail-card"><div class="ua-card-header"><div><h2>Documents, consents and printing</h2><p>Generated documents and electronic signatures retain patient, encounter, signer, time and evidence context.</p></div><div class="v5-action-row"><button class="ua-button" data-v1014-action="consents" ${canRegister?'':'disabled'}>Consent Forms</button><button class="ua-button primary" data-v1014-action="print-forms">Print Center</button></div></div>${canNotes?`<div class="v1014-document-summary"><div><strong>${notes.length}</strong><span>clinical notes</span></div><div><strong>${notes.filter(n=>n.status==='SIGNED').length}</strong><span>signed legal notes</span></div><div><strong>${notes.reduce((n,x)=>n+Number(x.amendment_count||0),0)}</strong><span>signed-note addenda</span></div></div><p class="muted">Signed notes remain immutable. Corrections are addenda and show the author and time in the visible note history.</p>`:'<div class="alert info"><strong>Clinical-note counts are restricted.</strong><br>This account can still use the patient print center but is not assigned notes.manage.</div>'}</article>`;
    const financial=canRevenue?`<article class="ua-card v1014-detail-card"><div class="ua-card-header"><div><h2>Patient account</h2><p>${v1014Currency().code} · country-sensitive financial context</p></div><button class="ua-button primary" data-v1014-action="open-billing">Open Billing</button></div><div class="v1014-money-grid"><div><span>Billed</span><strong>${v1014Money(billed)}</strong></div><div><span>Collected</span><strong>${v1014Money(paid)}</strong></div><div><span>Balance</span><strong>${v1014Money(Math.max(0,billed-paid))}</strong></div></div><div class="v5-action-row"><button class="ua-button" data-v1014-action="financial-counseling">Financial counseling</button><button class="ua-button" data-v1014-action="payment-plan">Payment plan</button><button class="ua-button primary" data-v1014-action="collect-payment">Collect payment</button></div></article>`:`<article class="ua-card v1014-detail-card"><div class="empty-state"><h2>Financial account restricted</h2><p>This account is not assigned revenue.manage. Patient Station remains available for its authorized record workflows.</p></div></article>`;
    const pane={actions,registration,encounters,documents,financial}[state.v1014StationTab]||actions;
    $('#mainContent').innerHTML=`<section class="ua-page v1014-station-page">${uaPageTitle('Patient Station','Longitudinal Record Workspace','<span class="v1014-page-promise">Find one patient record, know exactly what you are working on, then launch the right record-linked action.</span>')}${v10163CareReadyBoard(tracker,true)}<div class="v1014-station-layout">${v1014RecordFinder(patient)}<main class="v1014-station-main">${v5RecordHeader(patient,encounter,true)}${v1014Storyboard(patient,encounter,recent)}<nav class="v1014-tabs">${[['actions','Record Actions'],['registration','Registration'],['encounters','Visits & Arrivals'],['documents','Documents & Print'],['financial','Financial']].map(([id,label])=>`<button class="${state.v1014StationTab===id?'active':''}" data-v1014-action="station-tab" data-tab="${id}">${label}</button>`).join('')}</nav><div class="v1014-pane">${pane}</div></main><aside class="v1014-context ua-card"><div class="ua-card-header"><h2>Record Context</h2></div><div class="v1014-context-patient">${patientAvatar(patient,true)}<strong>${esc(patient.full_name)}</strong><span>${esc(patient.mrn)}</span></div><h3>Current workflow</h3>${encounter?`<div class="v1014-context-block"><small>Encounter</small><strong>${esc(encounter.service)}</strong><span>${esc(encounter.encounter_id)}</span><b class="ua-status ${uaStatusClass(encounter.status)}">${esc(statusLabel(encounter.status))}</b></div>`:'<div class="v1014-context-block"><strong>No active encounter</strong><span>Record-only actions remain available.</span></div>'}${scheduled?`<div class="v1014-context-block"><small>Scheduled</small><strong>${esc(scheduled.service)}</strong><span>${fmtDate(scheduled.scheduled_start)}</span><button class="ua-button compact primary" data-v1014-action="arrive-appointment" data-appointment-id="${esc(scheduled.appointment_id)}">Arrive patient</button></div>`:''}<h3>Recent record activity</h3><div class="v1014-activity-list">${activities.slice(0,8).map(a=>`<div><span class="ua-status ${uaStatusClass(a.status)}">${esc(statusLabel(a.status))}</span><strong>${esc(a.title)}</strong><small>${esc(a.created_by)} · ${fmtDate(a.created_at)}${a.encounter?` · ${esc(a.encounter.encounter_id)}`:' · record only'}</small></div>`).join('')||'<p>No recent activities.</p>'}</div></aside></div></section>`;
  };

  function v1014ActivityModal(kind,patient,encounter){
    const specs={
      'phone-call':['Record Phone Call','PHONE_CALL','Phone call','Communication Pool','ROUTINE','Call outcome, advice given and follow-up'],
      refill:['Refill Request','REFILL_REQUEST','Medication refill request','Pharmacy Pool','ROUTINE','Medication, strength, supply and request details'],
      'financial-counseling':['Financial Counseling','FINANCIAL_COUNSELING','Financial counseling session','Financial Counseling Pool','ROUTINE','Estimate, assistance, coverage and agreed next steps']
    };const s=specs[kind];
    openModal(s[0],`<div class="v1014-modal-record"><strong>${esc(patient.full_name)}</strong><span>${esc(patient.mrn)} · ${esc(patient.mpi_id)}</span><small>${encounter?`Optional visit link: ${esc(encounter.encounter_id)}`:'This action will not create an encounter.'}</small></div><div class="form-grid"><label class="field"><span>Priority</span><select id="v1014ActivityPriority"><option>ROUTINE</option><option>HIGH</option><option>URGENT</option></select></label><label class="field"><span>Assign to</span><input id="v1014ActivityAssignee" value="${esc(s[3])}"></label><label class="field full"><span>${esc(s[5])}</span><textarea id="v1014ActivityDetails" required></textarea></label><label class="field full v1014-encounter-choice"><input id="v1014LinkEncounter" type="checkbox" ${encounter?'':'disabled'}><span>Link to current encounter${encounter?` (${esc(encounter.encounter_id)})`:' — no active encounter'}</span></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v1014-action="save-activity" data-kind="${kind}" data-activity-type="${s[1]}" data-title="${esc(s[2])}">Save to Record</button>`,'Longitudinal Record Activity');
  }
  function v1014WalkInModal(patient){
    openModal('Start Walk-In for Selected Record',`<div class="v1014-modal-record"><strong>${esc(patient.full_name)}</strong><span>${esc(patient.mrn)} · ${esc(patient.mpi_id)}</span><small>A new visit is appropriate because the patient is arriving for care.</small></div><div class="form-grid"><label class="field"><span>Service</span><input id="v1014WalkService" value="General OPD Clinic"></label><label class="field"><span>Reason for visit</span><input id="v1014WalkReason" required></label><label class="field"><span>Coverage route</span><select id="v1014WalkCoverage">${['NHIF','Cash','Private Insurance','Exempted','Emergency'].map(x=>`<option ${patient.payer===x?'selected':''}>${x}</option>`).join('')}</select></label><label class="field full"><span>Arrival notes</span><textarea id="v1014WalkNotes">Arrived at Patient Station and routed using the facility workflow.</textarea></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v1014-action="confirm-walk-in">Create Arrival</button>`,'Encounter Workflow');
  }
  function v1014TriageModal(patient,encounter){
    openModal('Triage Selected Patient',`<div class="v1014-modal-record"><strong>${esc(patient.full_name)}</strong><span>${esc(encounter.encounter_id)} · ${esc(encounter.service)} · ${esc(statusLabel(encounter.status))}</span></div><div class="form-grid"><label class="field"><span>Acuity</span><select id="v1014TriageAcuity"><option>Low</option><option>Medium</option><option>High</option><option>Critical</option></select></label><label class="field"><span>Triage location</span><input id="v1014TriageLocation" value="Triage"></label><label class="field full"><span>Chief complaint / assessment</span><textarea id="v1014TriageDetails" required></textarea></label><label class="field"><span>Temperature °C</span><input id="v1014Temp" type="number" step="0.1"></label><label class="field"><span>Heart rate bpm</span><input id="v1014Hr" type="number"></label><label class="field"><span>Blood pressure</span><input id="v1014Bp" placeholder="120/80"></label><label class="field"><span>SpO₂ %</span><input id="v1014Spo2" type="number"></label><label class="field"><span>After triage</span><select id="v10163TriageDisposition"><option value="ROOMED" selected>Room patient for provider</option><option value="TRIAGED">Keep in completed-triage queue</option></select></label><label class="field"><span>Room / care space</span><input id="v10163TriageRoom" value="General Practice Room"></label></div><div class="alert info"><strong>Rooming is not provider start.</strong> The patient remains ready for the clinician until the provider explicitly begins the visit.</div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v1014-action="confirm-triage">Complete Triage</button>`,'Encounter Workflow');
  }
  function v10163RoomingModal(patient,encounter){
    openModal('Room Patient',`<div class="v1014-modal-record"><strong>${esc(patient.full_name)}</strong><span>${esc(encounter.encounter_id)} · ${esc(encounter.service)} · ${esc(statusLabel(encounter.status))}</span></div><div class="form-grid"><label class="field full"><span>Room / care space</span><input id="v10163RoomName" value="${esc(encounter.room||'General Practice Room')}" required></label><label class="field full"><span>Rooming note</span><textarea id="v10163RoomNote">Patient placed and ready for the provider.</textarea></label></div><div class="alert info">Rooming writes a placement event to this encounter. It does not start provider time or create another visit.</div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v1016-action="confirm-rooming">Confirm Rooming</button>`,'Encounter-Controlled Rooming');
  }
  function v1014PaymentModal(patient,encounter){const c=v1014Currency();state.v1016PaymentContext={patient,encounter};openModal('Collect Payment',`<div class="v1014-modal-record"><strong>${esc(patient.full_name)}</strong><span>${esc(patient.mrn)} · ${esc(c.code)} account</span><small>${encounter?`Apply to selected visit ${esc(encounter.encounter_id)} or keep as account-level credit.`:'Account-level payment; no active visit selected.'}</small></div><div class="form-grid v1016-payment-grid"><label class="field"><span>Amount (${esc(c.code)})</span><input id="v1014PaymentAmount" type="number" min="0.01" step="0.01" required></label><label class="field"><span>Payment method</span><select id="v1014PaymentMethod">${c.methods.map(x=>`<option>${esc(x)}</option>`).join('')}</select></label><label class="field v1016-cash-only"><span>Cash tendered (${esc(c.code)})</span><input id="v1016TenderedAmount" type="number" min="0" step="0.01"></label><div class="v1016-cash-only v1016-change"><span>Change due</span><strong id="v1016ChangeDue">${v1014Money(0,c.code)}</strong></div><label class="field full"><span id="v1016PaymentReferenceLabel">Receipt / transaction reference</span><input id="v1014PaymentReference" autocomplete="off"></label><label class="field full v1014-encounter-choice"><input id="v1014PaymentEncounter" type="checkbox" ${encounter?'checked':'disabled'}><span>${encounter?`Apply to encounter ${esc(encounter.encounter_id)}`:'Record-level payment'}</span></label><label class="field full v1016-confirm"><input id="v1016PaymentConfirmed" type="checkbox"><span>I verified that funds were received through the selected channel and the reference is correct.</span></label></div><section id="v1016PaymentInstructions" class="v1016-payment-instructions"><div><strong>Loading facility payment instructions…</strong></div></section><div class="alert warning"><strong>PCI and reconciliation:</strong> never enter or store a full card number, CVV, mobile PIN or private crypto key. Only post a provider authorization/confirmation reference.</div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v1014-action="confirm-payment">Confirm & Post Payment</button>`,'Cashiering and Reconciliation');queueMicrotask(v1016RefreshPaymentInstructions);}

  async function v1016RefreshPaymentInstructions(){
    const method=$('#v1014PaymentMethod')?.value;if(!method)return;const c=v1014Currency(),amount=Number($('#v1014PaymentAmount')?.value)||0;
    const target=$('#v1016PaymentInstructions');try{const info=await api(`/payment-instructions?method=${encodeURIComponent(method)}&facility_code=${encodeURIComponent(operationFacility())}&amount=${amount}&currency_code=${c.code}`);state.v1016PaymentChannel=info;$('#v1016PaymentReferenceLabel')&&($('#v1016PaymentReferenceLabel').textContent=info.reference_label);const isCash=/cash/i.test(method);$$('.v1016-cash-only').forEach(x=>x.classList.toggle('hidden',!isCash));if(target)target.innerHTML=`${info.qr_data_uri?`<img src="${info.qr_data_uri}" alt="${esc(method)} payment QR code">`:''}<div><span class="ua-status ${info.configured?'success':'warning'}">${info.configured?'Configured':'Configuration required'}</span><strong>${esc(info.destination||method)}</strong><p>${esc(info.instructions)}</p><small>${esc(info.facility_code)} · ${esc(c.code)} ${amount.toLocaleString()}</small></div>`;}catch(error){if(target)target.innerHTML=`<div class="alert danger"><strong>Payment channel unavailable:</strong> ${esc(error.message)}</div>`;}
  }
  function v1016UpdateChange(){const c=v1014Currency(),amount=Number($('#v1014PaymentAmount')?.value)||0,tendered=Number($('#v1016TenderedAmount')?.value)||0;$('#v1016ChangeDue')&&($('#v1016ChangeDue').textContent=v1014Money(Math.max(0,tendered-amount),c.code));}

  async function v1016ConsentCenter(patient,encounter){
    const [catalog,history]=await Promise.all([api('/consent-templates'),api(`/patients/${encodeURIComponent(patient.mpi_id)}/consents`)]);state.v1016ConsentContext={patient,encounter,catalog};
    openModal('Consent Forms & Electronic Signature',`<div class="v1014-modal-record"><strong>${esc(patient.full_name)}</strong><span>${esc(patient.mrn)} · ${esc(patient.mpi_id)}</span><small>${encounter?`Selected visit: ${esc(encounter.encounter_id)} · ${esc(encounter.service)}`:'No active visit selected; visit-required forms are unavailable.'}</small></div><section class="v1016-consent-layout"><div class="v1016-consent-form"><label class="field"><span>Consent form</span><select id="v1016ConsentTemplate">${catalog.templates.map(item=>`<option value="${esc(item.code)}" data-encounter-required="${item.encounter_required?'1':'0'}" ${item.encounter_required&&!encounter?'disabled':''}>${esc(item.category)} · ${esc(item.name)}</option>`).join('')}</select></label><div id="v1016ConsentSummary" class="v1016-consent-summary"></div><div class="form-grid"><label class="field"><span>Decision</span><select id="v1016ConsentDecision"><option value="SIGNED">Consent signed</option><option value="DECLINED">Declined</option></select></label><label class="field"><span>Signer relationship</span><select id="v1016ConsentRelationship"><option value="SELF">Patient / self</option><option value="PARENT">Parent</option><option value="GUARDIAN">Legal guardian</option><option value="PROXY">Authorized proxy</option><option value="CLINICIAN_EMERGENCY_BASIS">Clinician — emergency basis</option></select></label><label class="field"><span>Signer full name</span><input id="v1016ConsentSigner" value="${esc(patient.full_name)}"></label><label class="field"><span>Witness (optional)</span><input id="v1016ConsentWitness"></label><label class="field full"><span>Electronic signature</span><input id="v1016ConsentSignature" autocomplete="off" placeholder="Signer types their full legal name"><small>Typing the legal name and confirming below creates a time-stamped SHA-256 evidence record; it does not replace jurisdiction-specific witness requirements.</small></label><label class="field full v1016-confirm"><input id="v1016ConsentAttest" type="checkbox"><span>The form was presented in a language the signer understands, questions were answered, identity/authority was checked, and the signer intentionally made this decision.</span></label></div></div><aside class="v1016-consent-history"><h3>Consent history</h3>${history.map(item=>`<article><span class="ua-status ${uaStatusClass(item.decision)}">${esc(statusLabel(item.decision))}</span><strong>${esc(item.title)}</strong><small>${fmtDate(item.signed_at)} · ${esc(item.evidence?.signer_name||item.signed_by)}${item.encounter?` · ${esc(item.encounter.encounter_id)}`:' · record level'}</small></article>`).join('')||'<p>No electronic consent decisions recorded.</p>'}</aside></section>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v1016-action="sign-consent">Record Consent Decision</button>`,'Registration, Consent and Legal Basis');queueMicrotask(v1016UpdateConsentSummary);
  }
  function v1016UpdateConsentSummary(){const context=state.v1016ConsentContext,item=context?.catalog?.templates.find(x=>x.code===$('#v1016ConsentTemplate')?.value),target=$('#v1016ConsentSummary');if(target&&item)target.innerHTML=`<span>${esc(item.category)}</span><strong>${esc(item.name)}</strong><p>${esc(item.summary)}</p><small>${item.encounter_required?'Must be linked to the selected visit.':'May be recorded at longitudinal-record level.'}</small>`;}

  const V1016_ROS=[
    {label:'Constitutional',region:'whole'}, {label:'Eyes',region:'head'},
    {label:'Ear, nose & throat',region:'head'}, {label:'Cardiovascular',region:'chest'},
    {label:'Respiratory',region:'chest'}, {label:'Gastrointestinal',region:'abdomen'},
    {label:'Genitourinary',region:'pelvis'}, {label:'Musculoskeletal',region:'limbs'},
    {label:'Skin / breast',region:'skin'}, {label:'Neurologic',region:'head'},
    {label:'Psychiatric',region:'head'}, {label:'Endocrine',region:'whole'},
    {label:'Hematologic / lymphatic',region:'whole'}, {label:'Allergy / immunology',region:'skin'}
  ];
  function v1016RosBodyMap(){
    return `<div class="v1016-ros-body" aria-label="Body-system review map">
      <svg viewBox="0 0 240 430" role="img" aria-label="Front body-system review guide">
        <g class="ros-silhouette"><circle cx="120" cy="40" r="28"></circle><path d="M91 82Q120 66 149 82L162 178L146 266L144 394M96 394L94 266L78 178Z"></path><path d="M84 98L38 220M156 98L202 220"></path></g>
        <g class="ros-region" data-ros-region="head"><circle cx="120" cy="40" r="22"></circle></g>
        <g class="ros-region" data-ros-region="chest"><path d="M91 84Q120 72 149 84L154 174H86Z"></path></g>
        <g class="ros-region" data-ros-region="abdomen"><path d="M86 177H154L146 256H94Z"></path></g>
        <g class="ros-region" data-ros-region="pelvis"><path d="M94 258H146L137 298H103Z"></path></g>
        <g class="ros-region ros-limbs" data-ros-region="limbs"><path d="M83 103L42 220M157 103L198 220M103 294L96 394M137 294L144 394"></path></g>
        <g class="ros-anatomy"><path d="M120 82V275M102 123H138M104 150H136M108 181H132M112 211H128"></path><circle cx="120" cy="122" r="16"></circle><path d="M104 122Q88 142 101 166M136 122Q152 142 139 166"></path><path d="M120 182Q94 192 104 229Q120 244 136 229Q146 192 120 182Z"></path></g>
      </svg>
      <div class="v1016-ros-legend"><strong>Review by exception</strong><span>1. Confirm all systems negative.</span><span>2. Tap only exceptions.</span><span>3. Document each positive finding.</span></div>
    </div>`;
  }
  function v1016RosCards(){
    return V1016_ROS.map((item,index)=>`<article class="v1016-ros-system" data-ros-system data-ros-region-name="${esc(item.region)}">
      <button type="button" data-v1016-action="ros-cycle" data-ros-index="${index}" aria-label="Change ${esc(item.label)} review status">
        <span class="v1016-ros-dot"></span><strong>${esc(item.label)}</strong><small data-ros-status-label>Not reviewed</small>
      </button>
      <select class="hidden" data-provider-ros data-ros-label="${esc(item.label)}" aria-label="${esc(item.label)} status"><option value="NOT_REVIEWED">Not reviewed</option><option value="NEGATIVE">Reviewed — negative</option><option value="POSITIVE">Positive / pertinent</option><option value="UNABLE_TO_ASSESS">Unable to assess</option></select>
      <label class="v1016-ros-finding hidden"><span>Pertinent finding</span><input data-ros-note="${index}" placeholder="Describe symptom, timing and severity"></label>
    </article>`).join('');
  }
  function v1016UpdateRosUi(){
    const systems=$$('[data-ros-system]');let reviewed=0,positive=0,unable=0;
    systems.forEach((card,index)=>{const select=card.querySelector('[data-provider-ros]'),value=select?.value||'NOT_REVIEWED';reviewed+=value!=='NOT_REVIEWED'?1:0;positive+=value==='POSITIVE'?1:0;unable+=value==='UNABLE_TO_ASSESS'?1:0;card.dataset.status=value;const label=card.querySelector('[data-ros-status-label]');if(label)label.textContent=value==='NEGATIVE'?'Negative':value==='POSITIVE'?'Positive':'Unable to assess';card.querySelector('.v1016-ros-finding')?.classList.toggle('hidden',value!=='POSITIVE');if(value!=='POSITIVE'){const note=$(`[data-ros-note="${index}"]`);if(note)note.value='';}});
    if($('#v1016RosReviewed'))$('#v1016RosReviewed').textContent=reviewed;if($('#v1016RosPositive'))$('#v1016RosPositive').textContent=positive;if($('#v1016RosPending'))$('#v1016RosPending').textContent=V1016_ROS.length-reviewed;
    $$('[data-ros-region]').forEach(region=>{const name=region.dataset.rosRegion;region.classList.toggle('positive',systems.some(card=>card.dataset.rosRegionName===name&&card.dataset.status==='POSITIVE'));region.classList.toggle('reviewed',systems.some(card=>card.dataset.rosRegionName===name&&card.dataset.status==='NEGATIVE'));});
  }
  async function v1016ProviderWorkflow(patient,encounter){
    if(['DISCHARGED','TRANSFERRED','LEFT_WITHOUT_BEING_SEEN'].includes(encounter.status))throw new Error('This encounter is closed and available for historical review only. Start a new visit for new physical care.');
    const [activities,notes,orders,results]=await Promise.all([api(`/module-activities?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`),api(`/notes?encounter_id=${encodeURIComponent(encounter.encounter_id)}`),api(`/orders?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`),api(`/results?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}`)]);const triage=activities.find(item=>item.activity_type==='TRIAGE_ASSESSMENT'&&item.encounter?.encounter_id===encounter.encounter_id);state.v1016ProviderContext={patient,encounter};
    openModal('Provider Visit Workspace',`<div class="v1016-provider-banner"><div><span>Working patient & visit</span><strong>${esc(patient.full_name)}</strong><small>${esc(patient.mrn)} · ${esc(encounter.encounter_id)} · ${esc(encounter.service)}</small></div><span class="ua-status ${uaStatusClass(encounter.status)}">${esc(statusLabel(encounter.status))}</span></div>
      <div class="v1016-provider-progress"><span class="done">Arrival</span><span class="done">Registration</span><span class="${triage?'done':'current'}">Triage</span><span class="current">Provider assessment</span><span>Orders / results</span><span>Disposition</span></div>
      <section class="v1016-provider-layout"><main>
        <article class="v1016-provider-section"><h3>Post-triage handoff</h3>${triage?`<div class="v1016-triage-summary"><strong>${esc(triage.details)}</strong><span>Acuity ${esc(triage.priority)} · ${esc(triage.created_by)} · ${fmtDate(triage.created_at)}</span><small>${Object.entries(triage.payload||{}).filter(([,v])=>v).map(([k,v])=>`${statusLabel(k)} ${v}`).join(' · ')||'No numeric observations recorded'}</small></div>`:'<div class="alert warning"><strong>Triage has not been documented for this encounter.</strong> Emergency clinical judgment may proceed, but the missing triage step remains visible.</div>'}</article>
        <article class="v1016-provider-section"><h3>History of present illness</h3><textarea id="v1016Hpi" class="editor" placeholder="Onset, location, duration, character, aggravating/relieving factors, associated symptoms and relevant context…"></textarea></article>
        <article class="v1016-provider-section v1016-ros-workspace"><div class="v1016-section-heading"><div><h3>Review of systems</h3><p>One-click normal review; document only exceptions.</p></div><div class="v1016-ros-actions"><button class="ua-button compact primary" data-v1016-action="ros-all-negative">All reviewed — negative</button><button class="ua-button compact" data-v1016-action="ros-clear">Clear</button></div></div><div class="v1016-ros-summary"><span><strong id="v1016RosReviewed">0</strong> reviewed</span><span class="positive"><strong id="v1016RosPositive">0</strong> positive</span><span><strong id="v1016RosPending">${V1016_ROS.length}</strong> pending</span></div><div class="v1016-ros-review">${v1016RosBodyMap()}<div class="v1016-ros-grid">${v1016RosCards()}</div></div></article>
        <article class="v1016-provider-section"><h3>Physical examination</h3><textarea id="v1016Exam" class="editor" placeholder="General appearance and focused examination findings…"></textarea></article>
        <article class="v1016-provider-section"><h3>Assessment & diagnoses</h3><textarea id="v1016Assessment" class="editor" placeholder="Problem-oriented assessment, differentials and diagnosis codes when known…"></textarea></article>
        <article class="v1016-provider-section"><h3>Plan, treatment and follow-up</h3><textarea id="v1016Plan" class="editor" placeholder="Investigations, medication, procedures, counselling, referrals, precautions and follow-up…"></textarea></article>
      </main><aside><article class="v1016-provider-section"><h3>Visit safety context</h3><p><strong>Allergies</strong><br>${esc(patient.allergies)}</p><p><strong>Active problems</strong><br>${esc(patient.problems)}</p><p><strong>Medication list</strong><br>${esc(patient.medications)}</p></article><article class="v1016-provider-section"><h3>Encounter activity</h3><p><strong>${orders.filter(x=>x.encounter?.encounter_id===encounter.encounter_id).length}</strong> orders in this visit</p><p><strong>${results.filter(x=>x.encounter?.encounter_id===encounter.encounter_id).length}</strong> results in this visit</p><p><strong>${notes.length}</strong> clinical notes in this visit</p><div class="v1016-provider-actions"><button class="ua-button" data-v1016-action="provider-orders">Orders</button><button class="ua-button" data-v1016-action="provider-results">Results</button><button class="ua-button" data-v1016-action="provider-flowsheets">Flowsheets</button></div></article><article class="v1016-provider-section"><h3>Documentation</h3><label class="field"><span>Note title</span><input id="v1016ProviderTitle" value="Provider encounter note"></label><label class="field"><span><input id="v1016ProviderCosign" type="checkbox"> Supervising clinician cosign required</span></label><p class="muted">A saved draft is encounter-linked. Signing makes the note immutable; later corrections are visible addenda showing who changed what and when.</p></article></aside></section>`,`<button class="ua-button" data-modal-action="close">Close</button><button class="ua-button" data-v1016-action="save-provider-note" data-sign="false">Save Draft</button><button class="ua-button primary" data-v1016-action="save-provider-note" data-sign="true">Create & Sign</button>`,'Encounter-Controlled Provider Workflow');
    queueMicrotask(v1016UpdateRosUi);
  }
  async function v1016AdvanceProviderEncounter(encounter){let status=String(encounter.status);const move=async next=>{await api(`/encounters/${encodeURIComponent(encounter.encounter_id)}/status`,{method:'PATCH',body:JSON.stringify({status:next,location:next==='ROOMED'?'Examination Room':'With Provider',provider:currentRole().user,actor:currentRole().user,note:'Provider workflow progression'})});status=next;};if(status==='TRIAGED')await move('READY_FOR_PROVIDER');if(status==='READY_FOR_PROVIDER')await move('ROOMED');if(status==='ROOMED')await move('IN_PROGRESS');return status;}
  function v1014PlanModal(patient,encounter){const c=v1014Currency();openModal('Create Payment Plan',`<div class="v1014-modal-record"><strong>${esc(patient.full_name)}</strong><span>${esc(patient.mrn)} · ${esc(c.code)} account</span></div><div class="form-grid"><label class="field"><span>Total plan amount (${esc(c.code)})</span><input id="v1014PlanAmount" type="number" min="0.01"></label><label class="field"><span>Deposit (${esc(c.code)})</span><input id="v1014PlanDeposit" type="number" min="0" value="0"></label><label class="field"><span>Number of installments</span><input id="v1014PlanInstallments" type="number" min="1" value="3"></label><label class="field"><span>Frequency</span><select id="v1014PlanFrequency"><option>Monthly</option><option>Fortnightly</option><option>Weekly</option></select></label><label class="field full"><span>Counseling notes and agreement</span><textarea id="v1014PlanNotes" required></textarea></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v1014-action="confirm-payment-plan">Create Plan</button>`,'Patient Financial Services');}
  function v1014ChargeModal(patient,encounter,status='POSTED'){const c=v1014Currency(),estimate=status==='DRAFT';openModal(estimate?'Create Visit Estimate':'Post Patient Charge',`<div class="v1014-modal-record"><strong>${esc(patient.full_name)}</strong><span>${esc(encounter.encounter_id)} · ${esc(encounter.service)}</span><small>${estimate?'Draft estimates remain editable and do not become a balance until finalized.':'This charge posts to the selected encounter ledger.'}</small></div><input id="v1014ChargeStatus" type="hidden" value="${status}"><div class="form-grid"><label class="field"><span>Service code</span><input id="v1014ChargeCode" value="CONS-001"></label><label class="field"><span>Billed to</span><select id="v1014BilledTo">${[patient.payer,'Patient / Self-pay','NHIF','Private Insurance','Employer','Exemption'].filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i).map(x=>`<option>${esc(x)}</option>`).join('')}</select></label><label class="field full"><span>Description</span><input id="v1014ChargeDescription" value="Clinical service"></label><label class="field"><span>Quantity</span><input id="v1014ChargeQty" type="number" min="1" value="1"></label><label class="field"><span>Unit price (${esc(c.code)})</span><input id="v1014ChargePrice" type="number" min="0" value="0"></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v1014-action="confirm-charge">${estimate?'Save Draft Estimate':'Post Charge'}</button>`,'Billing Workflow');}
  function v1014ClaimModal(patient,encounter){const c=v1014Currency();openModal('Create Patient Claim',`<div class="v1014-modal-record"><strong>${esc(patient.full_name)}</strong><span>${esc(encounter.encounter_id)} · ${esc(encounter.service)}</span></div><div class="form-grid"><label class="field"><span>Billed to / payer</span><select id="v1014ClaimPayer">${[patient.payer,'NHIF','Private Insurance','Employer Scheme','UHI','iCHF'].filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i).map(x=>`<option>${esc(x)}</option>`).join('')}</select></label><label class="field"><span>Member / policy number</span><input id="v1014ClaimMember" value="${esc(patient.member_number||'')}"></label><label class="field"><span>Claim amount (${esc(c.code)})</span><input id="v1014ClaimAmount" type="number" min="0" value="0"></label><label class="field"><span>Authorization</span><input id="v1014ClaimAuthorization"></label></div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-v1014-action="confirm-claim">Create Draft Claim</button>`,'Claims Workflow');}

  renderRevenueCycle=async function(){
    if(!state.selectedPatientId){$('#mainContent').innerHTML=`<section class="ua-page v1014-revenue-page">${uaPageTitle('Financial Operations','Record-Linked Billing & Payments','Search and select a patient before creating charges, claims, counseling, plans or payments.')}<div class="v1014-no-record">${v1014RecordFinder(null)}<article class="ua-card"><div class="empty-state"><h2>Choose a patient account</h2><p>Billing actions cannot be posted to an unidentified record.</p></div></article></div></section>`;return;}
    renderLoading('Opening the selected patient account…');const patient=await selectedPatient();if(!patient){state.selectedPatientId=null;return renderRevenueCycle();}
    const encounter=v1014OpenEncounter(patient),encoded=encodeURIComponent(patient.mpi_id);
    const [charges,claims,payments,activities]=await Promise.all([api(`/charges?patient_mpi_id=${encoded}`),api(`/claims?patient_mpi_id=${encoded}`),api(`/payments?patient_mpi_id=${encoded}`),api(`/module-activities?patient_mpi_id=${encoded}`)]);
    const billed=charges.filter(x=>x.status==='POSTED').reduce((n,x)=>n+Number(x.total||0),0),estimated=charges.filter(x=>x.status==='DRAFT').reduce((n,x)=>n+Number(x.total||0),0),paid=payments.reduce((n,x)=>n+Number(x.amount||0),0),balance=billed-paid;
    $('#mainContent').innerHTML=`<section class="ua-page v1014-revenue-page">${uaPageTitle('Financial Operations','Patient Billing, Claims & Payments','Charges, estimates, billed-to responsibility, claims and collections remain connected to the selected record and encounter.',`<button class="ua-button" data-v1014-action="record-search-focus">Change Patient</button><button class="ua-button" data-v1014-action="new-estimate" ${encounter?'':'disabled'}>+ Estimate</button><button class="ua-button" data-v1014-action="new-charge" ${encounter?'':'disabled'}>+ Charge</button><button class="ua-button" data-v1014-action="new-claim" ${encounter?'':'disabled'}>+ Claim</button><button class="ua-button primary" data-v1014-action="collect-payment">Collect Payment</button>`)}${v5RecordHeader(patient,encounter,true)}${v1014Storyboard(patient,encounter,activities.find(a=>a.module_code==='REVENUE'))}<div class="v1014-finance-actions"><button class="ua-button" data-v1014-action="financial-counseling">Financial Counseling</button><button class="ua-button" data-v1014-action="payment-plan">Payment Plan</button><span>Account currency: <strong>${esc(v1014Currency().code)}</strong></span></div><div class="v1014-money-grid v1014-revenue-metrics"><div><span>Draft estimates</span><strong>${v1014Money(estimated)}</strong><small>${charges.filter(x=>x.status==='DRAFT').length} awaiting finalization</small></div><div><span>Billed</span><strong>${v1014Money(billed)}</strong><small>${charges.filter(x=>x.status==='POSTED').length} posted charge(s)</small></div><div><span>Collected</span><strong>${v1014Money(paid)}</strong><small>${payments.length} confirmed payment(s)</small></div><div><span>Balance</span><strong>${v1014Money(balance)}</strong><small>${balance>0?'Patient / payer balance due':'Account settled or in credit'}</small></div></div><section class="v1014-finance-grid"><article class="ua-card"><div class="ua-card-header"><div><h2>Estimates, charges and billed-to responsibility</h2><p>Draft estimates become balances only after an authorized user finalizes them.</p></div></div><div class="table-wrap"><table class="ua-data-table"><thead><tr><th>Date</th><th>Service</th><th>Billed to</th><th>Amount</th><th>Status / action</th></tr></thead><tbody>${charges.map(x=>`<tr><td>${fmtDate(x.posted_at)}</td><td><strong>${esc(x.description)}</strong><small>${esc(x.service_code)} · ${esc(x.encounter?.encounter_id||'')}</small></td><td>${esc(x.payer||'Patient / Self-pay')}</td><td>${v1014Money(x.total,x.currency_code)}</td><td><span class="ua-status ${uaStatusClass(x.status)}">${esc(statusLabel(x.status))}</span>${x.status==='DRAFT'?` <button class="ua-button compact primary" data-v1016-action="finalize-estimate" data-charge-id="${esc(x.charge_id)}">Finalize</button>`:''}</td></tr>`).join('')||'<tr><td colspan="5">No estimates or charges for this record.</td></tr>'}</tbody></table></div></article><article class="ua-card"><div class="ua-card-header"><div><h2>Confirmed payments</h2><p>Cash, card, bank, local mobile money and crypto references.</p></div><button class="ua-button primary compact" data-v1014-action="collect-payment">Collect</button></div><div class="v1014-payment-list">${payments.map(x=>`<div><span>${fmtDate(x.received_at)}</span><strong>${v1014Money(x.amount,x.currency_code)}</strong><b>${esc(x.method)}</b><small>${esc(x.reference||'Cash receipt')} · ${esc(x.received_by)}</small></div>`).join('')||'<p>No payments collected.</p>'}</div></article><article class="ua-card v1014-claims"><div class="ua-card-header"><h2>Claims</h2></div><div class="table-wrap"><table class="ua-data-table"><thead><tr><th>Claim</th><th>Payer</th><th>Amount</th><th>Status</th><th>Next action</th></tr></thead><tbody>${claims.map(x=>`<tr><td>${esc(x.claim_id)}<small>${esc(x.encounter?.encounter_id||'')}</small></td><td>${esc(x.payer)}</td><td>${v1014Money(x.amount,x.currency_code)}</td><td><span class="ua-status ${uaStatusClass(x.status)}">${esc(statusLabel(x.status))}</span></td><td>${x.status==='DRAFT'?`<button class="ua-button compact" data-action="claim-status" data-id="${esc(x.claim_id)}" data-status="READY">Ready</button>`:x.status==='READY'?`<button class="ua-button compact primary" data-action="claim-status" data-id="${esc(x.claim_id)}" data-status="SUBMITTED">Submit</button>`:'—'}</td></tr>`).join('')||'<tr><td colspan="5">No claims for this record.</td></tr>'}</tbody></table></div></article><article class="ua-card"><div class="ua-card-header"><h2>Financial support activity</h2></div><div class="v1014-activity-list">${activities.filter(a=>a.module_code==='REVENUE').map(a=>`<div><span class="ua-status ${uaStatusClass(a.status)}">${esc(statusLabel(a.status))}</span><strong>${esc(a.title)}</strong><small>${esc(a.details||'')} · ${esc(a.created_by)} · ${fmtDate(a.created_at)}</small></div>`).join('')||'<p>No counseling or payment-plan activity.</p>'}</div></article></section></section>`;
  };

  async function v1014Context(){const patient=await selectedPatient();if(!patient)throw new Error('Select a patient record first.');return {patient,encounter:v1014OpenEncounter(patient)};}
  async function v1014SaveActivity(button){const {patient,encounter}=await v1014Context();const link=$('#v1014LinkEncounter')?.checked;const details=$('#v1014ActivityDetails')?.value.trim();if(!details)throw new Error('Enter the activity details.');await api('/module-activities',{method:'POST',body:JSON.stringify({module_code:button.dataset.kind==='financial-counseling'?'REVENUE':'PATIENT_CARE',activity_type:button.dataset.activityType,title:button.dataset.title,patient_mpi_id:patient.mpi_id,encounter_id:link&&encounter?encounter.encounter_id:null,priority:$('#v1014ActivityPriority').value,assigned_to:$('#v1014ActivityAssignee').value,details,payload:{record_only:!(link&&encounter)},created_by:currentRole().user})});closeModal();toast('Activity saved',`${button.dataset.title} was added to ${patient.full_name}'s record.`);return state.route==='revenue'?renderRevenueCycle():renderPatientStationV5();}

  document.addEventListener('input',e=>{if(e.target?.id==='v1014RecordQuery')v1016LiveRecordSearch(e.target.value);},true);
  document.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target?.id==='v1014RecordQuery'){e.preventDefault();const first=document.querySelector('#v1014RecordResults [data-v1014-action="select-record"]');if(first)first.click();else document.querySelector('[data-v1014-action="record-search"]')?.click();}},true);
  document.addEventListener('click',async e=>{
    const b=e.target.closest('[data-v1014-action]');if(!b)return;e.preventDefault();e.stopImmediatePropagation();
    try{
      const action=b.dataset.v1014Action;
      if(action==='station-tab'){state.v1014StationTab=b.dataset.tab;return renderPatientStationV5();}
      if(action==='record-search'){const q=$('#v1014RecordQuery')?.value.trim()||'';if(q.length<2)throw new Error('Enter at least two characters of a patient name or identifier.');state.v1014StationQuery=q;state.v1014StationSearchResults=await api(v1016PatientSearchUrl(q));if(state.route==='revenue')return renderRevenueCycle();return state.selectedPatientId?renderPatientStationV5():v1014RecordRequired('Longitudinal Record Workspace');}
      if(action==='select-record'){const chosen=(state.v1014StationSearchResults||[]).find(item=>item.mpi_id===b.dataset.patientId)||await api(`/patients/${encodeURIComponent(b.dataset.patientId)}`);v104RememberPatient(chosen);state.selectedPatientId=chosen.mpi_id;state.selectedEncounterId=null;state.v1014StationSearchResults=[];state.v1014StationQuery='';return state.route==='revenue'?renderRevenueCycle():renderPatientStationV5();}
      if(action==='record-search-focus'){state.selectedPatientId=null;state.v1014StationSearchResults=[];return renderRevenueCycle();}
      if(action==='open-chart'){if(b.dataset.encounterId)state.selectedEncounterId=b.dataset.encounterId;navigate('chart');return;}
      if(action==='open-registration'){state.registrationWorkspace='identity';state.registrationEditExisting=true;navigate('registration');return;}
      if(action==='open-billing'){navigate('revenue');return;}
      if(action==='open-flowsheets'){navigate('flowsheets');return;}
      const {patient,encounter}=await v1014Context();
      if(action==='print-forms')return v8OpenPrintWorkflow(v1014PatientRow(patient,encounter));
      if(action==='walk-in')return v1014WalkInModal(patient);
      if(action==='triage'){if(!encounter)throw new Error('Start or arrive a visit before triage.');return v1014TriageModal(patient,encounter);}
      if(['phone-call','refill','financial-counseling'].includes(action))return v1014ActivityModal(action,patient,encounter);
      if(action==='payment-plan')return v1014PlanModal(patient,encounter);
      if(action==='collect-payment')return v1014PaymentModal(patient,encounter);
      if(action==='consents')return v1016ConsentCenter(patient,encounter);
      if(action==='provider-workflow'){if(!encounter)throw new Error('Select or create an encounter before starting a provider visit.');return v1016ProviderWorkflow(patient,encounter);}
      if(action==='new-estimate'){if(!encounter)throw new Error('An estimate requires a selected encounter.');return v1014ChargeModal(patient,encounter,'DRAFT');}
      if(action==='new-charge'){if(!encounter)throw new Error('A charge requires an encounter.');return v1014ChargeModal(patient,encounter);}
      if(action==='new-claim'){if(!encounter)throw new Error('A claim requires an encounter.');return v1014ClaimModal(patient,encounter);}
      if(action==='arrive-scheduled'){const appointments=await api(`/appointments?patient_mpi_id=${encodeURIComponent(patient.mpi_id)}&from_hours=-720&to_hours=2160`);const item=v1014ScheduledAppointment(appointments);if(!item)throw new Error('No scheduled or confirmed appointment is available to arrive.');await api(`/appointments/${item.appointment_id}`,{method:'PATCH',body:JSON.stringify({status:'ARRIVED',actor:currentRole().user,note:'Arrived from record-centred Patient Station'})});toast('Scheduled patient arrived',`${item.service} workflow has started.`);return renderPatientStationV5();}
      if(action==='arrive-appointment'){await api(`/appointments/${b.dataset.appointmentId}`,{method:'PATCH',body:JSON.stringify({status:'ARRIVED',actor:currentRole().user,note:'Arrived from record-centred Patient Station'})});toast('Scheduled patient arrived','The appointment is linked to an active encounter.');return renderPatientStationV5();}
      if(action==='save-activity')return v1014SaveActivity(b);
      if(action==='confirm-walk-in'){const result=await api('/walk-ins',{method:'POST',body:JSON.stringify({patient_mpi_id:patient.mpi_id,facility_code:operationFacility(),service_point_id:null,service:$('#v1014WalkService').value,reason:$('#v1014WalkReason').value||$('#v1014WalkService').value,notes:$('#v1014WalkNotes').value,coverage_route:$('#v1014WalkCoverage').value,created_by:currentRole().user})});closeModal();toast('Walk-in arrived',result.notification?.message_en||'The visit was created and routed.');return renderPatientStationV5();}
      if(action==='confirm-triage'){const details=$('#v1014TriageDetails').value.trim();if(!details)throw new Error('Enter a triage assessment.');let status=String(encounter.status),room=$('#v10163TriageRoom').value.trim()||'General Practice Room',disposition=$('#v10163TriageDisposition').value;const update=async(next,extra={})=>{await api(`/encounters/${encounter.encounter_id}/status`,{method:'PATCH',body:JSON.stringify({status:next,location:extra.location||$('#v1014TriageLocation').value,room:extra.room??null,acuity:$('#v1014TriageAcuity').value,actor:currentRole().user,note:extra.note||details})});status=next;};if(status==='WAITING_REGISTRATION')await update('REGISTERED');if(['ARRIVED','REGISTERED'].includes(status))await update('WAITING_TRIAGE');if(status==='WAITING_TRIAGE')await update('TRIAGED');if(disposition==='ROOMED'){if(status==='TRIAGED')await update('READY_FOR_PROVIDER',{location:'Provider Queue',note:'Triage complete; awaiting room placement'});if(status==='READY_FOR_PROVIDER')await update('ROOMED',{location:'Outpatient Rooming',room,note:`Roomed in ${room} after completed triage`});}await api('/module-activities',{method:'POST',body:JSON.stringify({module_code:'PATIENT_CARE',activity_type:'TRIAGE_ASSESSMENT',title:'Triage assessment and disposition',patient_mpi_id:patient.mpi_id,encounter_id:encounter.encounter_id,priority:$('#v1014TriageAcuity').value.toUpperCase(),assigned_to:'Clinical Care Team',details,payload:{temperature:$('#v1014Temp').value||null,heart_rate:$('#v1014Hr').value||null,blood_pressure:$('#v1014Bp').value||null,spo2:$('#v1014Spo2').value||null,disposition,room:disposition==='ROOMED'?room:null},created_by:currentRole().user})});closeModal();toast('Triage completed',disposition==='ROOMED'?`${patient.full_name} is roomed in ${room} and ready for the provider.`:`${patient.full_name} is in the completed-triage queue.`);return state.route==='patient-flow'?renderPatientFlow():renderPatientStationV5();}
      if(action==='confirm-payment'){const amount=Number($('#v1014PaymentAmount').value);if(!(amount>0))throw new Error('Enter a payment amount greater than zero.');if(!$('#v1016PaymentConfirmed')?.checked)throw new Error('Verify receipt of funds before posting the payment.');const c=v1014Currency(),method=$('#v1014PaymentMethod').value,reference=$('#v1014PaymentReference').value.trim(),tendered=Number($('#v1016TenderedAmount')?.value)||null;const result=await api('/payments',{method:'POST',body:JSON.stringify({patient_mpi_id:patient.mpi_id,encounter_id:$('#v1014PaymentEncounter')?.checked&&encounter?encounter.encounter_id:null,amount,currency_code:c.code,method,reference:reference||null,confirmation_code:reference||null,tendered_amount:tendered,facility_code:operationFacility(),confirmed:true,channel_metadata:{configured_destination:state.v1016PaymentChannel?.destination||null},received_by:currentRole().user})});closeModal();toast('Payment confirmed',`${v1014Money(amount,c.code)} by ${method} · receipt ${result.payment_id}${result.change_due?` · change ${v1014Money(result.change_due,c.code)}`:''}.`);return state.route==='revenue'?renderRevenueCycle():renderPatientStationV5();}
      if(action==='confirm-payment-plan'){const amount=Number($('#v1014PlanAmount').value),installments=Number($('#v1014PlanInstallments').value);if(!(amount>0)||!(installments>0))throw new Error('Enter a valid plan amount and installment count.');const c=v1014Currency();await api('/module-activities',{method:'POST',body:JSON.stringify({module_code:'REVENUE',activity_type:'PAYMENT_PLAN',title:'Patient payment plan',patient_mpi_id:patient.mpi_id,encounter_id:encounter?.encounter_id||null,priority:'ROUTINE',assigned_to:'Patient Financial Services',details:$('#v1014PlanNotes').value||`${installments} ${$('#v1014PlanFrequency').value} installments`,payload:{currency:c.code,total_amount:amount,deposit:Number($('#v1014PlanDeposit').value)||0,installments,frequency:$('#v1014PlanFrequency').value},created_by:currentRole().user})});closeModal();toast('Payment plan created',`${v1014Money(amount)} across ${installments} installments.`);return state.route==='revenue'?renderRevenueCycle():renderPatientStationV5();}
      if(action==='confirm-charge'){const qty=Number($('#v1014ChargeQty').value),price=Number($('#v1014ChargePrice').value),billedTo=$('#v1014BilledTo').value,c=v1014Currency(),status=$('#v1014ChargeStatus')?.value||'POSTED';if(!(qty>0)||price<0)throw new Error('Enter a valid quantity and unit price.');await api('/charges',{method:'POST',body:JSON.stringify({patient_mpi_id:patient.mpi_id,encounter_id:encounter.encounter_id,service_code:$('#v1014ChargeCode').value,description:$('#v1014ChargeDescription').value,quantity:qty,unit_price:price,currency_code:c.code,payer:billedTo,posted_by:currentRole().user,status})});closeModal();toast(status==='DRAFT'?'Estimate saved':'Charge posted',`${v1014Money(qty*price,c.code)} ${status==='DRAFT'?'awaits review and finalization':`billed to ${billedTo}`}.`);return renderRevenueCycle();}
      if(action==='confirm-claim'){const amount=Number($('#v1014ClaimAmount').value);if(!(amount>0))throw new Error('Enter a claim amount greater than zero.');const payer=$('#v1014ClaimPayer').value,c=v1014Currency();await api('/claims',{method:'POST',body:JSON.stringify({patient_mpi_id:patient.mpi_id,encounter_id:encounter.encounter_id,payer,member_number:$('#v1014ClaimMember').value||null,amount,currency_code:c.code,authorization_number:$('#v1014ClaimAuthorization').value||null})});closeModal();toast('Draft claim created',`${v1014Money(amount,c.code)} billed to ${payer}.`);return renderRevenueCycle();}
    }catch(err){console.error(err);toast('Action failed',err.message||String(err));}
  },true);

  /* ------------------------------------------------------------------------
     Release 10.15 installable, encrypted offline workspace.

     The service worker caches only the application shell. Patient responses
     and the mutation outbox live in an AES-GCM encrypted IndexedDB vault that
     is unlocked with a separate device PIN. The server password and bearer
     token are never placed in offline storage. Reconnect replay is sequential
     and idempotent; rejected transactions remain visible for reconciliation.
  ------------------------------------------------------------------------- */
  function offlineDeviceId(){
    let id=localStorage.getItem('umojaOfflineDeviceId');
    if(!id){id=`device-${crypto.randomUUID?crypto.randomUUID():`${Date.now()}-${Math.random().toString(16).slice(2)}`}`;localStorage.setItem('umojaOfflineDeviceId',id);}
    return id;
  }

  function offlineProfile(){
    return {account:state.account,facilities:state.facilities,modules:state.modules,countryCode:state.countryCode,facility:state.facility,deviceId:offlineDeviceId(),release:'11.0.0'};
  }

  async function updateOfflineUi(snapshot=null){
    const offline=window.UmojaOffline;if(!offline)return;
    const current=snapshot||await offline.stats().catch(()=>null);if(!current)return;
    const pending=Number(current.pending||0)+Number(current.needs_review||0);
    const label=current.syncing?'Syncing':!current.online?'Offline':current.needs_review?'Review':current.pending?'Pending':current.enrolled&&!current.unlocked?'Locked':'Online';
    $('#syncStatusLabel')&&($('#syncStatusLabel').textContent=label);
    $('#syncStatusButton')?.classList.toggle('offline',!current.online);
    $('#syncStatusButton')?.classList.toggle('attention',Boolean(current.needs_review));
    $('#syncStatusButton')?.classList.toggle('syncing',Boolean(current.syncing));
    $('#syncPendingCount')&&($('#syncPendingCount').textContent=String(pending));
    $('#syncPendingCount')?.classList.toggle('hidden',pending===0);
    $('#syncStatusDot')?.setAttribute('data-state',current.needs_review?'review':current.syncing?'syncing':!current.online?'offline':current.pending?'pending':current.unlocked?'ready':'locked');
    $('#syncConnectionLabel')&&($('#syncConnectionLabel').textContent=current.online?(current.pending?`${current.pending} pending sync`:'Online'):'Offline');
    $('#footerConnectionDot')?.classList.toggle('offline-dot',!current.online);
    $('#installAppButton')?.classList.toggle('hidden',current.installed||!current.install_available);
    $('#offlineUnlockPanel')?.classList.toggle('hidden',!current.enrolled||current.unlocked||current.expired);
  }

  async function showOfflineCenter(){
    const offline=window.UmojaOffline;if(!offline)return toast('Offline unavailable','This browser does not support the protected device vault.');
    const current=await offline.stats(),rows=current.unlocked?await offline.operations():[];
    let serverDevices=[];if(state.token&&navigator.onLine){try{serverDevices=await api('/offline/devices');}catch(_){serverDevices=[];}}
    const connection=current.online?'Connected to Umoja Afya':'No network connection';
    const vault=!current.enrolled?'Not enabled':current.expired?'Lease expired':current.unlocked?'Unlocked':'Locked';
    const operationRows=rows.slice().reverse().slice(0,100).map(row=>`<tr><td><strong>${esc(statusLabel(row.status))}</strong><small>${esc(row.id)}</small></td><td>${esc(row.protected?.path||'Protected transaction')}<small>${esc(row.protected?.patient_mpi_id||'No patient identifier')}</small></td><td>${fmtDate(row.created_at)}</td><td>${row.error_message?`<span class="offline-error">${esc(row.error_message)}</span>`:'—'}</td><td>${['NEEDS_REVIEW','BLOCKED_AUTH','RETRY'].includes(row.status)?`<button class="ua-button compact" data-offline-action="retry" data-operation-id="${esc(row.id)}">Retry</button>`:'—'}</td></tr>`).join('');
    const vaultAction=!current.enrolled?'<button class="ua-button primary" data-offline-action="enable">Enable protected offline access</button>':!current.unlocked&&!current.expired?'<label class="field"><span>Offline PIN</span><input id="offlineCenterPin" type="password" inputmode="numeric" maxlength="12"></label><button class="ua-button primary" data-offline-action="unlock">Unlock vault</button>':current.expired?'<label class="field"><span>Offline PIN</span><input id="offlineRenewPin" type="password" inputmode="numeric" maxlength="12"></label><button class="ua-button primary" data-offline-action="renew">Renew after online sign-in</button>':'<button class="ua-button" data-offline-action="lock">Lock offline vault</button>';
    openModal('Install & Offline Sync',`<section class="offline-center">
      <div class="offline-status-grid"><div><span>Connection</span><strong>${esc(connection)}</strong></div><div><span>Device vault</span><strong>${esc(vault)}</strong></div><div><span>Pending</span><strong>${current.pending}</strong></div><div><span>Needs review</span><strong>${current.needs_review}</strong></div></div>
      <div class="offline-assurance"><strong>Protected offline operation</strong><p>Cached records and queued transactions are encrypted on this device. The server account password and session token are not retained. Reauthentication is required before synchronization.</p><p><b>Online-only safeguards:</b> note signatures/addenda, clinical orders, medication administration, result acknowledgement, discharge, death recording, claim submission, break-glass access and administration.</p></div>
      <div class="offline-center-actions">${current.installed?'<span class="ua-status success">Installed</span>':'<button class="ua-button" data-offline-action="install">Install App</button>'}${vaultAction}${current.unlocked?'<button class="ua-button primary" data-offline-action="sync">Sync now</button>':''}</div>
      ${current.enrolled?`<p class="offline-lease">Offline access expires: <strong>${current.expires_at?fmtDate(current.expires_at):'—'}</strong></p>`:''}
      ${current.unlocked?`<div class="table-wrap offline-outbox"><table class="ua-data-table"><thead><tr><th>Status</th><th>Workflow</th><th>Saved</th><th>Reconciliation</th><th>Action</th></tr></thead><tbody>${operationRows||'<tr><td colspan="5">No offline transactions have been recorded on this device.</td></tr>'}</tbody></table></div>`:''}
      ${serverDevices.length?`<section class="offline-devices"><h3>Authorized offline devices</h3>${serverDevices.map(device=>`<div><span class="sync-dot" data-state="${device.active?'ready':'locked'}"></span><p><strong>${esc(device.device_name)}</strong><small>${esc(device.device_id)} · Last sync ${device.last_sync_at?fmtDate(device.last_sync_at):'Never'}</small></p>${device.active?`<button class="ua-button compact danger" data-offline-action="revoke-device" data-device-id="${esc(device.device_id)}">Revoke</button>`:'<span class="ua-status">Revoked</span>'}</div>`).join('')}</section>`:''}
      ${current.enrolled?'<details class="offline-danger"><summary>Remove offline data from this device</summary><p>This permanently removes the encrypted cache and outbox from this browser. Synchronize and reconcile all pending work first.</p><button class="ua-button danger" data-offline-action="request-wipe">Remove local offline data</button></details>':''}
    </section>`,`<button class="ua-button" data-modal-action="close">Close</button>`,'Secure Device Workspace');
  }

  function showEnableOffline(){
    if(!state.token||!state.account)return toast('Online sign-in required','Sign in before authorizing this browser for offline use.');
    openModal('Enable Protected Offline Access',`<div class="offline-enroll">
      <div class="alert info"><strong>Institutional device only.</strong> Enable this on a managed device with screen lock, full-device encryption and an approved remote-wipe process.</div>
      <label class="field"><span>Device name</span><input id="offlineDeviceName" value="${esc(`${navigator.platform||'Clinical'} device`)}" maxlength="160"></label>
      <label class="field"><span>Create offline PIN (6–12 digits)</span><input id="offlinePin" type="password" inputmode="numeric" minlength="6" maxlength="12" autocomplete="new-password"></label>
      <label class="field"><span>Confirm offline PIN</span><input id="offlinePinConfirm" type="password" inputmode="numeric" minlength="6" maxlength="12" autocomplete="new-password"></label>
      <label class="v1012-check"><input id="offlineDeviceApproval" type="checkbox"><span>I confirm this is an authorized clinical device and understand that unsynchronized work must be reviewed before this device is removed.</span></label>
    </div>`,`<button class="ua-button" data-modal-action="close">Cancel</button><button class="ua-button primary" data-offline-action="confirm-enable">Encrypt & Enable</button>`,'Offline Security');
  }

  async function unlockOfflineFromLogin(){
    try{
      const profile=await window.UmojaOffline.unlock($('#offlineUnlockPin')?.value||'');
      state.account=profile.account;state.facilities=profile.facilities||[];state.modules=profile.modules||[];state.countryCode=profile.countryCode||state.countryCode;state.facility=profile.facility||profile.account?.facility_code||state.facility;state.token='';state.offlineSession=true;
      $('#offlineUnlockPin').value='';openAuthenticatedApp();toast('Offline workspace unlocked','Cached records are available. Reconnect and sign in before synchronization.');
    }catch(error){toast('Offline unlock failed',error.message);}
  }

  async function syncOfflineOutbox(){
    const offline=window.UmojaOffline;if(!offline||!state.token||!navigator.onLine)return;
    const current=await offline.stats();if(!current.unlocked||(!current.pending&&!current.needs_review))return updateOfflineUi(current);
    try{const result=await offline.sync({token:state.token,countryCode:state.countryCode});updateOfflineUi(result);if(!result.pending&&!result.needs_review){toast('Offline work synchronized','All protected transactions were reconciled with the central record.');render();}else if(result.needs_review){toast('Reconciliation required','One or more offline transactions need authorized review.');}}
    catch(error){updateOfflineUi();if(!/sign in|connection/i.test(error.message))toast('Sync paused',error.message);}
  }

  async function handleOfflineAction(action,button){
    const offline=window.UmojaOffline;
    try{
      if(action==='install'){await offline.install();return updateOfflineUi();}
      if(action==='enable')return showEnableOffline();
      if(action==='confirm-enable'){
        const pin=$('#offlinePin').value,confirm=$('#offlinePinConfirm').value,approved=$('#offlineDeviceApproval').checked,deviceName=$('#offlineDeviceName').value.trim();
        if(pin!==confirm)throw new Error('Offline PIN entries do not match.');if(!approved)throw new Error('Confirm that this is an authorized clinical device.');if(!deviceName)throw new Error('Enter a recognizable device name.');
        const policy=await api('/offline/policy');const deviceId=offlineDeviceId();await api('/offline/devices',{method:'POST',body:JSON.stringify({device_id:deviceId,device_name:deviceName,platform:navigator.userAgent.slice(0,160),app_version:'11.0.0'})});await offline.enroll(pin,{...offlineProfile(),deviceId},policy);closeModal();toast('Offline access enabled','Install the app if prompted, then open records online once to make them available offline.');updateOfflineUi();return;
      }
      if(action==='unlock'){await offline.unlock($('#offlineCenterPin')?.value||'');closeModal();toast('Offline vault unlocked','Protected records and outbox transactions are available.');updateOfflineUi();return showOfflineCenter();}
      if(action==='renew'){if(!state.token||!navigator.onLine)throw new Error('Reconnect and sign in online before renewing the offline lease.');const policy=await api('/offline/policy');await offline.renew($('#offlineRenewPin')?.value||'',offlineProfile(),policy);closeModal();toast('Offline lease renewed',`Protected access is renewed for ${policy.lease_hours} hours.`);updateOfflineUi();return showOfflineCenter();}
      if(action==='sync'){closeModal();await syncOfflineOutbox();return showOfflineCenter();}
      if(action==='lock'){offline.lock();closeModal();toast('Offline vault locked','Protected records are no longer accessible until the offline PIN is entered.');return updateOfflineUi();}
      if(action==='retry'){await offline.retry(button.dataset.operationId);closeModal();await syncOfflineOutbox();return showOfflineCenter();}
      if(action==='revoke-device'){const current=await offline.stats(),deviceId=button.dataset.deviceId;if(deviceId===current.device_id&&(current.pending||current.needs_review))throw new Error('Synchronize and reconcile this device before revoking it.');await api(`/offline/devices/${encodeURIComponent(deviceId)}`,{method:'DELETE'});if(deviceId===current.device_id)await offline.wipe();closeModal();toast('Offline device revoked','The selected browser can no longer submit offline transactions.');updateOfflineUi();return showOfflineCenter();}
      if(action==='request-wipe'){
        const current=await offline.stats();if(current.pending||current.needs_review)throw new Error('Synchronize and reconcile all offline transactions before removing local data.');
        openModal('Remove Offline Data',`<div class="alert danger"><strong>This cannot be undone.</strong> The encrypted record cache and synchronized outbox history will be removed from this browser.</div><label class="field"><span>Type REMOVE to confirm</span><input id="offlineWipeConfirm" autocomplete="off"></label>`,`<button class="ua-button" data-offline-action="cancel-wipe">Cancel</button><button class="ua-button danger" data-offline-action="confirm-wipe">Remove Data</button>`,'Device Security');return;
      }
      if(action==='cancel-wipe')return showOfflineCenter();
      if(action==='confirm-wipe'){if($('#offlineWipeConfirm').value!=='REMOVE')throw new Error('Type REMOVE exactly to confirm.');if(!state.token||!navigator.onLine)throw new Error('Online sign-in is required to revoke this device before local data is removed.');const current=await offline.stats();if(current.device_id)await api(`/offline/devices/${encodeURIComponent(current.device_id)}`,{method:'DELETE'});await offline.wipe();closeModal();toast('Offline data removed','The server authorization was revoked and the encrypted local cache was removed.');return updateOfflineUi();}
    }catch(error){toast('Offline action failed',error.message||String(error));}
  }

  $('#offlineUnlockSubmit')?.addEventListener('click',unlockOfflineFromLogin);
  $('#offlineUnlockPin')?.addEventListener('keydown',event=>{if(event.key==='Enter')unlockOfflineFromLogin();});
  $('#syncStatusButton')?.addEventListener('click',showOfflineCenter);
  $('#installAppButton')?.addEventListener('click',()=>handleOfflineAction('install',$('#installAppButton')));
  document.addEventListener('click',event=>{const button=event.target.closest('[data-offline-action]');if(!button)return;event.preventDefault();event.stopImmediatePropagation();handleOfflineAction(button.dataset.offlineAction,button);},true);

  /* v10.16 encounter-controlled search, provider, consent and payment workflows */
  document.addEventListener('input',event=>{
    if(['v1014PaymentAmount','v1016TenderedAmount'].includes(event.target.id)){v1016UpdateChange();clearTimeout(state.v1016PaymentTimer);state.v1016PaymentTimer=setTimeout(v1016RefreshPaymentInstructions,280);}
  },true);
  document.addEventListener('change',event=>{
    if(event.target.id==='v1014PaymentMethod'){v1016RefreshPaymentInstructions();v1016UpdateChange();}
    if(event.target.id==='v1016ConsentTemplate')v1016UpdateConsentSummary();
    if(event.target.id==='chartEncounterSelect'){state.selectedEncounterId=event.target.value||null;renderChart();}
  },true);
  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-v1016-action]');if(!button)return;event.preventDefault();event.stopImmediatePropagation();
    try{
      const action=button.dataset.v1016Action;
      if(action==='new-registration'){state.selectedPatientId=null;state.selectedEncounterId=null;state.registrationEditExisting=false;state.registrationWorkspace='identity';return navigate('registration');}
      if(action==='select-chart-encounter'){state.selectedEncounterId=button.dataset.encounterId;state.chartTab='summary';return renderChart();}
      if(action==='tracker-triage'){state.selectedPatientId=button.dataset.patientId;state.selectedEncounterId=button.dataset.encounterId;const patient=await api(`/patients/${encodeURIComponent(state.selectedPatientId)}`),encounter=patient.encounters.find(x=>x.encounter_id===state.selectedEncounterId);return v1014TriageModal(patient,encounter);}
      if(action==='tracker-room'){state.selectedPatientId=button.dataset.patientId;state.selectedEncounterId=button.dataset.encounterId;const patient=await api(`/patients/${encodeURIComponent(state.selectedPatientId)}`),encounter=patient.encounters.find(x=>x.encounter_id===state.selectedEncounterId);if(!encounter)throw new Error('The selected encounter was not found.');return v10163RoomingModal(patient,encounter);}
      if(action==='confirm-rooming'){const patient=state.selectedPatientId?await api(`/patients/${encodeURIComponent(state.selectedPatientId)}`):null,encounter=patient?.encounters?.find(item=>item.encounter_id===state.selectedEncounterId),room=$('#v10163RoomName')?.value.trim(),note=$('#v10163RoomNote')?.value.trim()||'Patient placed and ready for the provider.';if(!encounter)throw new Error('The selected encounter was not found.');if(!room)throw new Error('Enter the room or care space.');let status=String(encounter.status);const move=async next=>{await api(`/encounters/${encodeURIComponent(encounter.encounter_id)}/status`,{method:'PATCH',body:JSON.stringify({status:next,location:next==='ROOMED'?'Outpatient Rooming':'Provider Queue',room:next==='ROOMED'?room:null,actor:currentRole().user,note})});status=next;};if(status==='TRIAGED')await move('READY_FOR_PROVIDER');if(status==='READY_FOR_PROVIDER')await move('ROOMED');if(status==='ROOMED')await move('ROOMED');if(status!=='ROOMED')throw new Error(`Rooming is not valid while the encounter is ${statusLabel(status)}.`);await api('/module-activities',{method:'POST',body:JSON.stringify({module_code:'PATIENT_CARE',activity_type:'ROOMING',title:'Patient roomed',patient_mpi_id:patient.mpi_id,encounter_id:encounter.encounter_id,priority:'ROUTINE',assigned_to:'Clinical Care Team',details:note,payload:{room,location:'Outpatient Rooming'},created_by:currentRole().user})});closeModal();toast('Patient roomed',`${patient.full_name} is in ${room} and ready for the provider.`);return state.route==='patient-flow'?renderPatientFlow():renderPatientStationV5();}
      if(action==='tracker-ready-provider'){await updateTrackerStatus(button.dataset.encounterId,'READY_FOR_PROVIDER');return;}
      if(action==='provider-workflow'){state.selectedPatientId=button.dataset.patientId||state.selectedPatientId;state.selectedEncounterId=button.dataset.encounterId||state.selectedEncounterId;const patient=await api(`/patients/${encodeURIComponent(state.selectedPatientId)}`),encounter=patient.encounters.find(x=>x.encounter_id===state.selectedEncounterId);if(!encounter)throw new Error('The selected encounter was not found for this patient.');return v1016ProviderWorkflow(patient,encounter);}
      if(action==='ros-all-negative'){$$('[data-provider-ros]').forEach(select=>select.value='NEGATIVE');v1016UpdateRosUi();return;}
      if(action==='ros-clear'){$$('[data-provider-ros]').forEach(select=>select.value='NOT_REVIEWED');v1016UpdateRosUi();return;}
      if(action==='ros-cycle'){const select=$(`[data-provider-ros]`,button.closest('[data-ros-system]'));if(!select)return;select.value=select.value==='NOT_REVIEWED'?'NEGATIVE':select.value==='NEGATIVE'?'POSITIVE':select.value==='POSITIVE'?'UNABLE_TO_ASSESS':'NOT_REVIEWED';v1016UpdateRosUi();return;}
      if(action==='provider-orders'){closeModal();return navigate('orders');}
      if(action==='provider-results'){closeModal();return navigate('results');}
      if(action==='provider-flowsheets'){closeModal();return navigate('flowsheets');}
      if(action==='save-provider-note'){
        const context=state.v1016ProviderContext;if(!context)throw new Error('Provider encounter context expired. Reopen the visit.');const hpi=$('#v1016Hpi')?.value.trim(),exam=$('#v1016Exam')?.value.trim(),assessment=$('#v1016Assessment')?.value.trim(),plan=$('#v1016Plan')?.value.trim();if(!hpi&&!assessment&&!plan)throw new Error('Document the history, assessment or plan before saving.');
        const undocumentedPositive=$$('[data-provider-ros]').find((select,index)=>select.value==='POSITIVE'&&!$(`[data-ros-note="${index}"]`)?.value.trim());if(undocumentedPositive)throw new Error(`Document the pertinent ${undocumentedPositive.dataset.rosLabel} finding before saving.`);
        const ros=$$('[data-provider-ros]').map((select,index)=>`${select.dataset.rosLabel}: ${statusLabel(select.value)}${$(`[data-ros-note="${index}"]`)?.value.trim()?` — ${$(`[data-ros-note="${index}"]`).value.trim()}`:''}`).join('\n');const status=await v1016AdvanceProviderEncounter(context.encounter);
        const body=`ENCOUNTER: ${context.encounter.encounter_id}\nSERVICE: ${context.encounter.service}\n\nHISTORY OF PRESENT ILLNESS\n${hpi||'Not documented'}\n\nREVIEW OF SYSTEMS\n${ros}\n\nPHYSICAL EXAMINATION\n${exam||'Not documented'}\n\nASSESSMENT / DIAGNOSES\n${assessment||'Not documented'}\n\nPLAN / TREATMENT / FOLLOW-UP\n${plan||'Not documented'}`;
        const created=await api('/notes',{method:'POST',body:JSON.stringify({patient_mpi_id:context.patient.mpi_id,encounter_id:context.encounter.encounter_id,note_type:'PROVIDER_ENCOUNTER_NOTE',title:$('#v1016ProviderTitle')?.value.trim()||'Provider encounter note',body,author:currentRole().user,service:context.encounter.service,cosign_required:Boolean($('#v1016ProviderCosign')?.checked)})});if(button.dataset.sign==='true')await api(`/notes/${encodeURIComponent(created.note_id)}/sign`,{method:'POST',body:JSON.stringify({signer:currentRole().user,attestation:'Electronically signed after review of the encounter, triage, ROS, examination, assessment and plan.'})});await api('/module-activities',{method:'POST',body:JSON.stringify({module_code:'PATIENT_CARE',activity_type:'PROVIDER_VISIT',title:'Provider assessment',patient_mpi_id:context.patient.mpi_id,encounter_id:context.encounter.encounter_id,priority:'ROUTINE',assigned_to:currentRole().user,details:`Provider assessment ${button.dataset.sign==='true'?'signed':'saved as draft'}; encounter ${statusLabel(status)}`,payload:{note_id:created.note_id,encounter_status:status},created_by:currentRole().user})});closeModal();toast(button.dataset.sign==='true'?'Provider note signed':'Provider draft saved',`${created.note_id} is linked to ${context.encounter.encounter_id}.`);return renderPatientFlow();
      }
      if(action==='sign-consent'){
        const context=state.v1016ConsentContext;if(!context)throw new Error('Consent context expired.');if(!$('#v1016ConsentAttest')?.checked)throw new Error('Complete the signer attestation before recording consent.');const signature=$('#v1016ConsentSignature')?.value.trim(),signer=$('#v1016ConsentSigner')?.value.trim();if(!signature||!signer)throw new Error('Enter the signer name and electronic signature.');const template=context.catalog.templates.find(item=>item.code===$('#v1016ConsentTemplate').value);const result=await api(`/patients/${encodeURIComponent(context.patient.mpi_id)}/consents`,{method:'POST',body:JSON.stringify({template_code:template.code,encounter_id:template.encounter_required?context.encounter?.encounter_id||null:null,decision:$('#v1016ConsentDecision').value,signer_name:signer,signer_relationship:$('#v1016ConsentRelationship').value,signature,witness_name:$('#v1016ConsentWitness').value.trim()||null,language:state.language,actor:currentRole().user})});closeModal();toast('Consent decision recorded',`${template.name} · ${result.consent_id} · evidence ${result.signature_sha256.slice(0,12)}…`);return renderPatientStationV5();
      }
      if(action==='finalize-estimate'){await api(`/charges/${encodeURIComponent(button.dataset.chargeId)}`,{method:'PATCH',body:JSON.stringify({status:'POSTED',actor:currentRole().user,reason:'Estimate reviewed with patient and finalized for charge capture'})});toast('Estimate finalized','The approved estimate is now a posted encounter charge.');return renderRevenueCycle();}
    }catch(error){console.error(error);toast('Action failed',error.message||String(error));}
  },true);

  init();
})();
