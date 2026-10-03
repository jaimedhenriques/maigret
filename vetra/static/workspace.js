'use strict';
const root = document.getElementById('view-content');
const csrf = document.querySelector('meta[name="csrf-token"]').content;
const canEdit = ['owner', 'reviewer'].includes(document.body.dataset.role);
const state = {overview: null, filter: 'all', search: '', candidates: [], request: 0};
const labels = {invited:'Awaiting approval', pending:'Not started', in_progress:'In progress', needs_review:'Needs review', completed:'Review complete', withdrawn:'Withdrawn', reviewed:'Manually reviewed', verified:'Provider verified'};
const e = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon = name => '<svg class="icon" aria-hidden="true"><use href="#i-' + name + '"/></svg>';
const status = value => '<span class="status ' + e(value) + '">' + e(labels[value] || value) + '</span>';
const date = value => value ? new Intl.DateTimeFormat('en', {day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}).format(new Date(value)) : '—';
const initials = name => (name || '?').split(' ').slice(0,2).map(x=>x[0]).join('').toUpperCase();
let toastTimer;
function toast(message) { const el=document.getElementById('toast'); el.textContent=message; el.hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.hidden=true,5500); }
async function api(url, method='GET', data) {
  const res=await fetch(url,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:data===undefined ? undefined : JSON.stringify(data)});
  const body=await res.json();
  if(!res.ok) throw new Error(body.error || 'Unable to complete the request. Try again.');
  return body;
}
async function copyLink(link) {
  const value=new URL(link,location.origin).href;
  try { await navigator.clipboard.writeText(value); toast('Candidate link copied. Share it through your approved channel.'); }
  catch { const field=document.querySelector('.invitation-url'); if(field){field.focus();field.select();toast('Select and copy the invitation link.');} else { toast('Clipboard unavailable. The invitation link is shown below.'); } }
}
function invitationMarkup(link) {
  const full=new URL(link,location.origin).href;
  return '<div class="invitation-result"><h3>The invitation is ready.</h3><p>No email has been sent. Share this private link with the candidate through your approved channel. It expires in seven days.</p><div class="copy-row"><input class="invitation-url" readonly aria-label="Private candidate invitation link" value="' + e(full) + '"><button class="button" id="copy-link">Copy link</button></div><a class="text-link" href="' + e(link) + '" target="_blank" rel="noopener noreferrer">Preview the candidate experience ' + icon('arrow') + '</a></div>';
}
function heading(title, description, actions='') { return '<div class="page-heading"><div><h1>' + e(title) + '</h1><p>' + e(description) + '</p></div><div class="actions">' + actions + '</div></div>'; }
function focusHeading() { const heading=root.querySelector('h1'); if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});} }
function primaryInvite() { return canEdit ? '<a class="button primary" href="#new">' + icon('plus') + 'Invite candidate</a>' : ''; }
function activityMarkup(items) { return items.length ? '<ol class="activity-list">' + items.map(item=>'<li class="activity-item">' + e(item.message) + '<time datetime="' + e(item.created_at) + '">' + e(date(item.created_at)) + '</time></li>').join('') + '</ol>' : '<p class="sample-note">Your workspace activity will appear here.</p>'; }
async function overviewData() {
  state.overview=await api('/api/overview');
  document.getElementById('candidate-count').textContent=state.overview.metrics.total;
  document.getElementById('review-count').textContent=state.overview.metrics.needs_review;
  return state.overview;
}
function tablePanel(title) {
  return '<section class="panel"><div class="panel-heading"><div><h2>' + e(title) + '</h2><p>Every candidate, with a clear next step.</p></div><a class="text-link" href="#candidates">View all ' + icon('arrow') + '</a></div><div class="table-toolbar"><div class="tabs" aria-label="Filter candidates">' +
  [['all','All candidates'],['in_progress','In progress'],['needs_review','Needs review'],['completed','Complete']].map(([key,label])=>'<button class="tab ' + (state.filter===key?'active':'') + '" data-filter="' + key + '" aria-pressed="' + (state.filter===key) + '">' + label + '</button>').join('') +
  '</div><label class="search-field">' + icon('search') + '<input id="candidate-search" aria-label="Search candidates" placeholder="Search candidates…" value="' + e(state.search) + '"></label></div><div class="table-scroll"><table><thead><tr><th scope="col">Candidate</th><th scope="col" class="optional-column">Role</th><th scope="col">Status</th><th scope="col">Checks</th><th scope="col" class="optional-column">Updated</th><th scope="col"><span class="muted">Open</span></th></tr></thead><tbody id="candidate-rows"><tr><td colspan="6" class="loading-state">Loading candidates…</td></tr></tbody></table></div><div class="table-foot"><span id="table-count">Loading…</span><span>Evidence reviewed by people</span></div></section>';
}
function candidateRows(candidates) {
  if(!candidates.length) return '<tr><td colspan="6"><div class="empty-state"><h3>No candidates found</h3><p>Try another search or invite your first candidate.</p></div></td></tr>';
  return candidates.map((c,index)=>'<tr><td><div class="person"><span class="avatar tone-' + index%4 + '">' + e(initials(c.name)) + '</span><div><a class="candidate-link" href="#candidate/' + e(c.id) + '"><strong>' + e(c.name) + '</strong></a><span class="email">' + e(c.email) + '</span></div></div></td><td class="optional-column">' + e(c.role) + '</td><td>' + status(c.status) + '</td><td><div class="progress"><div class="progress-track" aria-hidden="true"><span style="width:' + (c.checks_total ? Math.round(c.checks_completed/c.checks_total*100) : 0) + '%"></span></div><span>' + e(c.checks_completed) + '/' + e(c.checks_total) + '</span></div></td><td class="optional-column muted">' + e(date(c.updated_at)) + '</td><td><a class="row-arrow" href="#candidate/' + e(c.id) + '" aria-label="View ' + e(c.name) + '">' + icon('arrow') + '</a></td></tr>').join('');
}
async function updateTable() {
  const request=++state.request;
  try {
    const data=await api('/api/candidates?search=' + encodeURIComponent(state.search) + '&status=' + encodeURIComponent(state.filter));
    if(request!==state.request || !document.getElementById('candidate-rows')) return;
    state.candidates=data.candidates;
    document.getElementById('candidate-rows').innerHTML=candidateRows(data.candidates);
    document.getElementById('table-count').textContent=data.candidates.length + (data.candidates.length===1?' candidate':' candidates') + (state.overview?.demo ? ' · fictional demo records are labeled in each report' : '');
  } catch(error) { if(document.getElementById('candidate-rows'))document.getElementById('candidate-rows').innerHTML='<tr><td colspan="6" class="empty-state">' + e(error.message) + '</td></tr>'; }
}
function bindTable() {
  root.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{
    state.filter=button.dataset.filter;
    root.querySelectorAll('[data-filter]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});
    updateTable();
  }));
  let timer;
  document.getElementById('candidate-search').addEventListener('input',event=>{state.search=event.target.value;clearTimeout(timer);timer=setTimeout(updateTable,180);});
  updateTable();
}
async function renderOverview(view) {
  const data=await overviewData();
  state.filter=view==='review'?'needs_review':'all';state.search='';
  const invite=primaryInvite();
  if(view==='overview') {
    const metrics=[['total','All candidates','Your hiring workspace',''],['in_progress','In progress','Candidate checks underway',''],['needs_review','Needs review','Ready for a human review','amber'],['completed','Review complete','Evidence review finished','teal']];
    root.innerHTML=heading('A clearer path to your next hire.','Keep verification moving. Give every candidate a fair beginning.','<a class="button" href="/api/export.csv">' + icon('down') + 'Export cases</a>' + invite) +
      '<div class="summary-strip">' + metrics.map(([key,label,foot,tone])=>'<div class="summary-item"><div class="summary-label"><span class="tiny-dot ' + tone + '"></span>' + label + '</div><div class="summary-value">' + e(data.metrics[key]) + '</div><div class="summary-foot">' + foot + '</div></div>').join('') + '</div>' +
      '<div class="welcome-band"><div><h2>Good verification starts with transparency.</h2><p>Candidates approve the scope, share their information, and can request a correction. You review the evidence with context.</p></div><div class="welcome-symbol" aria-hidden="true">' + icon('shield') + '</div></div>' +
      '<div class="content-grid">' + tablePanel('Your candidate pipeline') + '<aside class="right-column"><section class="panel activity-panel"><h2>Recent activity</h2><p class="muted" style="font-size:11px">A record of what happened, and when.</p>' + activityMarkup(data.activity.slice(0,5)) + '<p class="sample-note">' + (data.demo?'Demo events describe fictional candidates. Real invitations and reviews are recorded when you create them.':'Activity is scoped to your organization.') + '</p></section><section class="process-note"><h3>Reviewed is a useful distinction.</h3><p>A manual evidence review is labeled separately from provider-verified identity. A completed case records the review workflow; it is not a recommendation to hire.</p></section></aside></div>';
  } else {
    root.innerHTML=heading(view==='review'?'Ready for your review.':'People, not just a pipeline.',view==='review'?'Review candidate statements and record the evidence behind each check.':'Invite candidates and follow every verification from beginning to review.','<a class="button" href="/api/export.csv">' + icon('down') + 'Export cases</a>' + invite) + tablePanel(view==='review'?'Review queue':'Candidates');
  }
  bindTable();
}
function renderNew() {
  if(!canEdit){root.innerHTML=heading('You have read-only access.','An owner or reviewer can invite candidates.');return;}
  root.innerHTML=heading('Start with a simple invitation.','The candidate stays informed and in control.','<a class="button" href="#candidates">Back to candidates</a>') +
    '<section class="panel form-panel"><form id="invite-form"><div class="form-grid"><div class="field"><label for="candidate-name">Full name</label><input id="candidate-name" name="name" autocomplete="name" placeholder="e.g. Alex Morgan" required maxlength="120"></div><div class="field"><label for="candidate-email">Email address</label><input id="candidate-email" name="email" type="email" autocomplete="email" placeholder="alex@example.com" required maxlength="254"></div><div class="field full"><label for="candidate-role">Hiring role</label><input id="candidate-role" name="role" placeholder="e.g. Product designer" required maxlength="160"></div><div class="field full"><label for="candidate-package">Verification scope</label><select id="candidate-package" name="package"><option value="Essential">Essential · Identity & employment</option><option value="Professional">Professional · Identity, employment, education & professional profile</option></select><small>Identity requires a configured provider. Credential checks use source-based manual review in this pilot.</small></div></div><div class="info-note">A private invitation link will be created. No checks begin until the candidate approves the scope. This workspace does not send invitation emails.</div><div class="form-actions"><button class="button primary" type="submit">' + icon('plus') + 'Create invitation</button><a class="button" href="#candidates">Cancel</a></div><div class="form-error" id="invite-error" role="alert"></div></form><div id="invitation-result"></div></section>';
  document.getElementById('invite-form').addEventListener('submit',async event=>{
    event.preventDefault();const form=event.target;const button=form.querySelector('button[type="submit"]');button.disabled=true;button.textContent='Creating invitation…';
    document.getElementById('invite-error').textContent='';
    try {
      const data=await api('/api/candidates','POST',Object.fromEntries(new FormData(form)));
      document.getElementById('invitation-result').innerHTML=invitationMarkup(data.invitation_url) + '<div class="form-actions"><a class="button primary" href="#candidate/' + e(data.candidate.id) + '">Open candidate case ' + icon('arrow') + '</a></div>';
      document.getElementById('copy-link').onclick=()=>copyLink(data.invitation_url);
      button.textContent='Invitation created';form.querySelectorAll('input,select').forEach(input=>input.disabled=true);
      toast('Invitation created. Candidate approval is the next step.');await overviewData();
    } catch(error){document.getElementById('invite-error').textContent=error.message;button.disabled=false;button.textContent='Create invitation';}
  });
}
async function renderCandidate(id) {
  const data=await api('/api/candidates/' + encodeURIComponent(id)), c=data.candidate;
  const consent=c.consent && c.status!=='withdrawn';
  const checkHTML=data.checks.map(check=>'<section class="check-row"><div class="check-title"><h3>' + e(check.label) + '</h3>' + status(check.status) + '</div><div class="check-meta">' + e(check.provider || 'Source-based manual review') + (check.sample?' · illustrative evidence':'') + '</div>' +
    (check.source?'<p class="check-notes"><strong>Source:</strong> ' + e(check.source) + '</p>':'') +
    (check.notes?'<p class="check-notes">' + e(check.notes) + '</p>':'<p class="check-notes">No evidence has been submitted for this check.</p>') +
    (canEdit && consent && !['verified','reviewed'].includes(check.status)?'<div class="actions"><button class="button small" data-review="' + e(check.id) + '" aria-expanded="false">Record manual review</button>' + (check.kind==='identity' && !c.sample?'<button class="button small primary" data-start="' + e(check.id) + '">Start identity verification</button>':'') + '</div><form class="review-form" id="review-' + e(check.id) + '" data-check="' + e(check.id) + '" hidden><div class="field"><label for="source-' + e(check.id) + '">Evidence source</label><input id="source-' + e(check.id) + '" name="source" placeholder="Official issuer, reference contact, or source URL" required maxlength="500"></div><div class="field"><label for="notes-' + e(check.id) + '">Review notes</label><textarea id="notes-' + e(check.id) + '" name="notes" required placeholder="What did you review? Record the evidence and any limitations." maxlength="4000"></textarea></div><div><button class="button primary small" type="submit">Save manual review</button></div><div class="form-error" role="alert"></div></form>':'') + '</section>').join('');
  root.innerHTML='<div class="page-heading"><div class="detail-person"><span class="avatar">' + e(initials(c.name)) + '</span><div><h1>' + e(c.name) + '</h1><p>' + e(c.role) + ' · ' + e(c.email) + '</p></div></div><a class="button" href="#candidates">Back to candidates</a></div>' +
    (c.sample?'<div class="sample-banner">Fictional demo candidate. Sample evidence is illustrative and cannot be submitted to a real identity provider.</div>':'') +
    '<div class="detail-layout"><div><section class="panel"><div class="panel-heading"><div><h2>Verification evidence</h2><p>Review the source. Keep the limitations visible.</p></div>' + status(c.status) + '</div>' +
    (!consent?'<div class="info-note" style="margin:0 24px 24px">' + (c.status==='withdrawn'?'This candidate withdrew. Their information has been removed and access is revoked.':'Waiting for candidate approval. Evidence review and provider checks are locked until the candidate approves.') + '</div>':'') +
    (checkHTML || '<div class="empty-state">No active checks.</div>') + '</section>' +
    (data.corrections?.length?'<section class="panel full-panel"><div class="panel-heading"><h2>Candidate corrections</h2></div>' + data.corrections.map(cr=>'<div class="correction"><h3>' + (cr.status==='resolved'?'Resolved correction':'Correction requested') + '</h3><p>' + e(cr.message) + '</p>' + (cr.resolution_notes?'<p><strong>Resolution:</strong> ' + e(cr.resolution_notes) + '</p>':'') + (canEdit && cr.status!=='resolved'?'<form data-correction="' + e(cr.id) + '" class="review-form"><div class="field"><label for="correction-' + e(cr.id) + '">Response to the candidate</label><textarea id="correction-' + e(cr.id) + '" name="notes" required maxlength="4000"></textarea><small>This response is visible to the candidate.</small></div><div><button class="button small primary" type="submit">Record resolution</button></div><div class="form-error" role="alert"></div></form>':'') + '</div>').join('') + '</section>':'') +
    '<div id="detail-invitation"></div></div><aside><section class="panel detail-info"><h2>Case details</h2><dl><dt>Scope</dt><dd>' + e(c.package) + '</dd><dt>Candidate approval</dt><dd>' + (consent?'Approved':'Not active') + '</dd><dt>Evidence review</dt><dd>' + e(c.checks_completed) + ' of ' + e(c.checks_total) + ' checks complete</dd><dt>Created</dt><dd>' + e(date(c.created_at)) + '</dd></dl>' +
    (canEdit && c.status!=='withdrawn'?'<div class="form-actions"><button class="button" id="reissue-link">' + icon('link') + 'Create new invitation link</button></div><p class="sample-note">A new link revokes earlier invitation links. It does not send an email.</p>':'') + '</section><section class="panel activity-panel full-panel"><h2>Case activity</h2>' + activityMarkup(data.activity) + '</section></aside></div>';
  root.querySelectorAll('[data-review]').forEach(button=>button.addEventListener('click',()=>{const form=document.getElementById('review-' + button.dataset.review);form.hidden=!form.hidden;button.setAttribute('aria-expanded',String(!form.hidden));if(!form.hidden)form.querySelector('input').focus();}));
  root.querySelectorAll('form[data-check]').forEach(form=>form.addEventListener('submit',async event=>{
    event.preventDefault();const button=form.querySelector('button');button.disabled=true;
    try{await api('/api/candidates/' + encodeURIComponent(id) + '/checks/' + encodeURIComponent(form.dataset.check) + '/review','POST',Object.fromEntries(new FormData(form)));toast('Manual review recorded with its evidence source.');await renderCandidate(id);await overviewData();}
    catch(error){form.querySelector('.form-error').textContent=error.message;button.disabled=false;}
  }));
  root.querySelectorAll('[data-start]').forEach(button=>button.addEventListener('click',async()=>{
    button.disabled=true;
    try{await api('/api/candidates/' + encodeURIComponent(id) + '/checks/' + encodeURIComponent(button.dataset.start) + '/start','POST',{provider:'stripe_identity'});toast('Identity session created. The candidate can continue from their portal.');await renderCandidate(id);}
    catch(error){toast(error.message);button.disabled=false;}
  }));
  root.querySelectorAll('form[data-correction]').forEach(form=>form.addEventListener('submit',async event=>{
    event.preventDefault();const button=form.querySelector('button');button.disabled=true;
    try{await api('/api/candidates/' + encodeURIComponent(id) + '/corrections/' + encodeURIComponent(form.dataset.correction) + '/resolve','POST',{notes:new FormData(form).get('notes')});toast('Correction resolution recorded.');await renderCandidate(id);}
    catch(error){form.querySelector('.form-error').textContent=error.message;button.disabled=false;}
  }));
  document.getElementById('reissue-link')?.addEventListener('click',async event=>{
    event.target.disabled=true;
    try{const result=await api('/api/candidates/' + encodeURIComponent(id) + '/invite','POST',{});document.getElementById('detail-invitation').innerHTML=invitationMarkup(result.invitation_url);document.getElementById('copy-link').onclick=()=>copyLink(result.invitation_url);toast('New invitation link created. Older links have been revoked.');}
    catch(error){toast(error.message);event.target.disabled=false;}
  });
  focusHeading();
}
async function renderAudit() {
  const data=await api('/api/audit');
  root.innerHTML=heading('A record you can follow.','Candidate and staff events, scoped to your organization.') +
    '<section class="panel"><div class="panel-heading"><h2>Audit trail</h2><span class="muted" style="font-size:11px">Latest ' + data.entries.length + ' events</span></div><div class="table-scroll"><table class="audit-table"><thead><tr><th scope="col">Time</th><th scope="col">Event</th><th scope="col">Action</th></tr></thead><tbody>' + (data.entries.length?data.entries.map(item=>'<tr><td class="muted">' + e(date(item.created_at)) + '</td><td>' + e(item.message) + '</td><td>' + e(item.action || '') + '</td></tr>').join(''):'<tr><td colspan="3" class="empty-state">Events will appear as your workspace is used.</td></tr>') + '</tbody></table></div></section><p class="sample-note">Events cannot be edited through the app. This pilot uses SQLite; production tamper-evident storage and external log retention are launch requirements.</p>';
}
async function renderSettings() {
  const data=await api('/api/settings');
  root.innerHTML=heading('A workspace built on clear boundaries.','See what is connected, who has access, and what is required before launch.') +
    '<div class="settings-grid"><section class="panel"><div class="panel-heading"><div><h2>Verification providers</h2><p>Real checks require a configured provider.</p></div></div><div class="capability-list" id="capability-list"></div></section><section class="panel detail-info"><h2>Current pilot scope</h2><p style="font-size:12px">Tenant-scoped cases, staff roles, approval, candidate claims, source-based review, and signed identity webhooks.</p><ul class="readiness-list"><li>Connect and validate an identity provider</li><li>Contract credential and screening data providers</li><li>Validate privacy, retention, and legal basis</li><li>Add SSO, managed storage, queues, and monitoring</li><li>Run independent security and operational reviews</li></ul><p class="sample-note">No certification or enterprise compliance claim is made.</p></section></div><div id="team-panel"></div>';
  const host=document.getElementById('capability-list');
  // The settings API deliberately exposes capabilities rather than pretending toggles configure providers.
  const identityProvider=(data.providers || []).find(provider=>provider.id==='stripe_identity');
  const known=[
    ['Identity verification',identityProvider?.configured || data.capabilities?.identity_provider ? 'Configured · verify provider account readiness' : 'Stripe Identity · not connected'],
    ['Employment & education','Source-based manual review'],
    ['Criminal records & right to work','Provider not connected'],
    ['Invitation email','Manual link delivery'],
    ['Suitability scoring','Not part of the product']
  ];
  host.innerHTML=known.map(([name,value])=>'<div class="capability-row"><strong>' + e(name) + '</strong><span>' + e(value) + '</span></div>').join('');
  if(document.body.dataset.role==='owner') {
    const result=await api('/api/users');
    document.getElementById('team-panel').innerHTML='<section class="panel full-panel"><div class="panel-heading"><div><h2>Team access</h2><p>Owners manage accounts. Reviewers work on checks. Viewers have read-only access.</p></div></div><div class="table-scroll"><table><thead><tr><th scope="col">Name</th><th scope="col">Email</th><th scope="col">Role</th></tr></thead><tbody>' + result.users.map(user=>'<tr><td>' + e(user.name) + '</td><td>' + e(user.email) + '</td><td>' + e(user.role) + '</td></tr>').join('') + '</tbody></table></div><form id="team-form" class="team-form"><h3>Add a team member</h3><div class="form-grid"><div class="field"><label for="team-name">Full name</label><input id="team-name" name="name" required maxlength="120"></div><div class="field"><label for="team-email">Email</label><input id="team-email" type="email" name="email" required></div><div class="field"><label for="team-password">Initial password</label><input id="team-password" type="password" name="password" required minlength="12" autocomplete="new-password"><small>At least 12 characters. Deliver through an approved secure channel.</small></div><div class="field"><label for="team-role">Access role</label><select id="team-role" name="role"><option value="viewer">Viewer</option><option value="reviewer">Reviewer</option><option value="owner">Owner</option></select></div></div><div class="form-actions"><button class="button primary" type="submit">Add team member</button></div><div class="form-error" role="alert"></div></form></section>';
    document.getElementById('team-form').addEventListener('submit',async event=>{
      event.preventDefault();const form=event.target;const button=form.querySelector('button');button.disabled=true;
      try{await api('/api/users','POST',Object.fromEntries(new FormData(form)));toast('Team member added with the selected access role.');await renderSettings();}
      catch(error){form.querySelector('.form-error').textContent=error.message;button.disabled=false;}
    });
  }
}
async function route() {
  const hash=location.hash.slice(1) || 'overview';
  const [view,id]=hash.split('/');
  const titles={overview:'Overview',candidates:'Candidates',review:'Review queue',audit:'Audit trail',settings:'Workspace settings',new:'Invite candidate',candidate:'Candidate case'};
  document.getElementById('breadcrumb').textContent=titles[view] || 'Overview';
  document.title=(titles[view] || 'Overview') + ' · Vetra';
  root.setAttribute('aria-busy','true');
  document.querySelectorAll('.nav-link').forEach(link=>{const active=link.dataset.view===(['new','candidate'].includes(view)?'candidates':view);link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
  root.innerHTML='<div class="loading-state" role="status">Loading…</div>';
  try {
    if(['overview','candidates','review'].includes(view))await renderOverview(view);
    else if(view==='new')renderNew();
    else if(view==='candidate' && id)await renderCandidate(id);
    else if(view==='audit')await renderAudit();
    else if(view==='settings')await renderSettings();
    else {location.hash='overview';}
    focusHeading();
  } catch(error) {root.innerHTML='<div class="error-state" role="alert"><h2>This page could not load.</h2><p>' + e(error.message) + '</p><button class="button" id="retry">Try again</button></div>';document.getElementById('retry').onclick=route;}
  finally {root.setAttribute('aria-busy','false');}
}
document.querySelectorAll('#logout,#logout-mobile').forEach(button=>button.addEventListener('click',async()=>{try{await api('/api/logout','POST',{});location.href='/login';}catch(error){toast(error.message);}}));
window.addEventListener('hashchange',route);
route();
