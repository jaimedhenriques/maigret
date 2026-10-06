'use strict';
const root = document.getElementById('view-content');
const csrf = document.querySelector('meta[name="csrf-token"]').content;
const canEdit = ['owner', 'reviewer'].includes(document.body.dataset.role);
const state = {overview: null, filter: 'all', search: '', candidates: [], request: 0, route: 0, view: 'overview', tableController: null, sort: 'newest'};
const labels = {invited:'Awaiting approval', pending:'Not started', in_progress:'In progress', needs_review:'Needs review', completed:'Review complete', withdrawn:'Withdrawn', reviewed:'Manually reviewed', verified:'Provider verified'};
const e = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon = name => '<svg class="icon" aria-hidden="true"><use href="#i-' + name + '"/></svg>';
const status = value => '<span class="status ' + e(value) + '">' + e(labels[value] || value) + '</span>';
const date = value => value ? new Intl.DateTimeFormat('en', {day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}).format(new Date(value)) : '—';
const initials = name => (name || '?').split(' ').slice(0,2).map(x=>x[0]).join('').toUpperCase();
let toastTimer;
function toast(message) { const el=document.getElementById('toast'); el.textContent=message; el.hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.hidden=true,5500); }
async function api(url, method='GET', data, signal) {
  let res;
  try { res=await fetch(url,{method,signal,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:data===undefined ? undefined : JSON.stringify(data)}); }
  catch(error) { if(error.name==='AbortError')throw error;throw new Error('The connection was interrupted. Check your connection and try again.'); }
  const body=await res.json().catch(()=>({}));
  if(res.status===401)throw new Error('Your session has ended. Sign in again to continue.');
  if(!res.ok)throw new Error(body.error || 'Unable to complete the request. Try again.');
  return body;
}
function formError(form, message) {
  const error=form.querySelector('.form-error');error.textContent=message;error.tabIndex=-1;error.focus({preventScroll:false});
}
function loadingMarkup(message='Loading your workspace…') { return '<div class="loading-state" role="status"><span class="loading-line"></span><span class="loading-line short"></span><p>' + e(message) + '</p></div>'; }
function setBusy(button, message) { button.dataset.original=button.innerHTML;button.disabled=true;button.setAttribute('aria-busy','true');button.textContent=message; }
function clearBusy(button) { button.disabled=false;button.removeAttribute('aria-busy');if(button.dataset.original)button.innerHTML=button.dataset.original; }

async function copyLink(link) {
  const value=new URL(link,location.origin).href;
  try { await navigator.clipboard.writeText(value); toast('Candidate link copied. Share it through your approved channel.'); }
  catch { const field=document.querySelector('.invitation-url'); if(field){field.focus();field.select();toast('Select and copy the invitation link.');} else { toast('Clipboard unavailable. The invitation link is shown below.'); } }
}
function invitationMarkup(link, delivery="manual") {
  const full=new URL(link,location.origin).href;
  return '<div class="invitation-result"><h3>The invitation is ready.</h3><p>' + (delivery==='email' ? 'Invitation accepted by the mail server. Confirm receipt with the candidate.' : 'Email was not sent. Share this private link through your approved channel.') + ' It expires in seven days.</p><div class="copy-row"><input class="invitation-url" readonly aria-label="Private candidate invitation link" value="' + e(full) + '"><button class="button" id="copy-link">Copy link</button></div><a class="text-link" href="' + e(link) + '" target="_blank" rel="noopener noreferrer">Preview the candidate experience ' + icon('arrow') + '</a></div>';
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
const filters=[['all','All statuses'],['invited','Awaiting approval'],['in_progress','In progress'],['needs_review','Needs review'],['completed','Review complete'],['withdrawn','Withdrawn']];
function tablePanel(title) {
  return '<section class="panel candidate-panel" aria-labelledby="candidate-table-title"><div class="panel-heading"><div><h2 id="candidate-table-title">' + e(title) + '</h2><p>Open a case to see its scope, evidence, and next step.</p></div>' + (state.view==='overview'?'<a class="text-link" href="#candidates">View all ' + icon('arrow') + '</a>':'') + '</div><div class="table-toolbar"><label class="search-field">' + icon('search') + '<span class="sr-only">Search candidate name, email, or hiring role</span><input id="candidate-search" name="search" type="search" autocomplete="off" placeholder="Search name, email, or role…" value="' + e(state.search) + '"></label><label class="filter-field" for="candidate-filter"><span>Status</span><select id="candidate-filter" name="status">' + filters.map(([key,label])=>'<option value="' + key + '"' + (state.filter===key?' selected':'') + '>' + label + '</option>').join('') + '</select></label><label class="sort-field" for="candidate-sort"><span>Sort</span><select id="candidate-sort" name="sort"><option value="newest">Newest first</option><option value="name_asc">Name: A to Z</option><option value="name_desc">Name: Z to A</option></select></label></div><div class="table-scroll"><table aria-describedby="table-count"><thead><tr><th scope="col" id="name-sort-heading" aria-label="Candidate" aria-sort="none"><button class="table-sort" id="sort-name" aria-label="Sort candidates by name">Candidate <span class="sort-indicator" aria-hidden="true">' + icon('sort') + '</span></button></th><th scope="col" class="optional-column">Hiring role</th><th scope="col">Next step</th><th scope="col">Checks</th><th scope="col" class="optional-column">Updated</th><th scope="col"><span class="sr-only">Open case</span></th></tr></thead><tbody id="candidate-rows"><tr><td colspan="6">' + loadingMarkup('Loading candidates…') + '</td></tr></tbody></table></div><div class="table-foot"><span id="table-count" role="status" aria-live="polite">Loading candidates…</span><span>Manual review and provider results stay distinct</span></div></section>';
}
function sortedCandidates(candidates) { return state.sort==='newest'?candidates:[...candidates].sort((a,b)=>(state.sort==='name_desc'?-1:1)*a.name.localeCompare(b.name,undefined,{sensitivity:'base'})); }
function candidateRows(candidates) {
  if(!candidates.length) {
    const filtered=state.search || state.filter!=='all';
    return '<tr><td colspan="6"><div class="empty-state">' + icon(filtered?'search':'users') + '<h3>' + (filtered?'No matching candidates':'Invite your first candidate') + '</h3><p>' + (filtered?'Try a different name, email, or role, or clear the status filter.':'Create a private invitation. The candidate approves the scope before any review begins.') + '</p><div class="actions">' + (filtered?'<button class="button" id="clear-filters">Clear search & filters</button>':primaryInvite()) + '</div></div></td></tr>';
  }
  return sortedCandidates(candidates).map(c=>'<tr><td><div class="person"><span class="avatar" aria-hidden="true">' + e(initials(c.name)) + '</span><div><a class="candidate-link" href="#candidate/' + e(c.id) + '"><strong>' + e(c.name) + '</strong></a><span class="email">' + e(c.email) + '</span><span class="mobile-role">' + e(c.role) + '</span></div></div></td><td class="optional-column">' + e(c.role) + '</td><td data-label="Next step">' + status(c.status) + '</td><td data-label="Checks"><div class="progress"><div class="progress-track" aria-hidden="true"><span style="width:' + (c.checks_total ? Math.round(c.checks_completed/c.checks_total*100) : 0) + '%"></span></div><span>' + e(c.checks_completed) + ' of ' + e(c.checks_total) + '<span class="sr-only"> checks complete</span></span></div></td><td class="optional-column muted">' + e(date(c.updated_at)) + '</td><td><a class="row-arrow" href="#candidate/' + e(c.id) + '" aria-label="Open case for ' + e(c.name) + '">' + icon('arrow') + '</a></td></tr>').join('');
}
root.addEventListener('click',event=>{if(event.target.closest('#clear-filters')){state.search='';state.filter='all';document.getElementById('candidate-search').value='';document.getElementById('candidate-filter').value='all';persistTableState();updateTable();document.getElementById('candidate-search').focus();}});
function persistTableState() {
  const params=new URLSearchParams();if(state.search)params.set('search',state.search);if(state.filter!=='all')params.set('status',state.filter);if(state.sort!=='newest')params.set('sort',state.sort);
  const hash=state.view + (params.size?'?'+params.toString():'');history.replaceState(null,'','#'+hash);
}
async function updateTable() {
  const request=++state.request;
  state.tableController?.abort();state.tableController=new AbortController();
  const rows=document.getElementById('candidate-rows');if(!rows)return;rows.setAttribute('aria-busy','true');
  document.getElementById('table-count').textContent='Updating candidates…';
  try {
    const data=await api('/api/candidates?search=' + encodeURIComponent(state.search) + '&status=' + encodeURIComponent(state.filter),'GET',undefined,state.tableController.signal);
    if(request!==state.request || !rows.isConnected)return;
    state.candidates=data.candidates;rows.innerHTML=candidateRows(data.candidates);
    document.getElementById('table-count').textContent=data.candidates.length + (data.candidates.length===1?' candidate':' candidates') + (state.overview?.demo?' · fictional demo data':'');
  } catch(error) {
    if(error.name==='AbortError' || request!==state.request || !rows.isConnected)return;
    rows.innerHTML='<tr><td colspan="6"><div class="empty-state" role="alert"><h3>Candidates could not load</h3><p>' + e(error.message) + '</p><button class="button" id="retry-candidates">Try again</button></div></td></tr>';
    document.getElementById('table-count').textContent='Candidate list unavailable';document.getElementById('retry-candidates').onclick=updateTable;
  } finally { if(request===state.request && rows.isConnected)rows.setAttribute('aria-busy','false'); }
}
function bindTable() {
  let timer;
  function syncSort() { document.getElementById('candidate-sort').value=state.sort;const heading=document.getElementById('name-sort-heading');heading.setAttribute('aria-sort',state.sort==='name_asc'?'ascending':state.sort==='name_desc'?'descending':'none');document.getElementById('sort-name').setAttribute('aria-label',state.sort==='name_asc'?'Candidate names ascending. Sort descending':state.sort==='name_desc'?'Candidate names descending. Restore newest first':'Sort candidates by name, ascending'); }
  syncSort();document.getElementById('sort-name').addEventListener('click',()=>{state.sort=state.sort==='newest'?'name_asc':state.sort==='name_asc'?'name_desc':'newest';persistTableState();syncSort();document.getElementById('candidate-rows').innerHTML=candidateRows(state.candidates);});
  document.getElementById('candidate-sort').addEventListener('change',event=>{state.sort=event.target.value;persistTableState();syncSort();document.getElementById('candidate-rows').innerHTML=candidateRows(state.candidates);});
  document.getElementById('candidate-filter').addEventListener('change',event=>{clearTimeout(timer);state.filter=event.target.value;persistTableState();updateTable();});
  document.getElementById('candidate-search').addEventListener('input',event=>{state.search=event.target.value;persistTableState();clearTimeout(timer);timer=setTimeout(updateTable,160);});
  document.getElementById('candidate-search').addEventListener('search',event=>{state.search=event.target.value;persistTableState();clearTimeout(timer);updateTable();});
  updateTable();
}
function onboardingMarkup() {
  return '<section class="getting-started"><div><h2>Start with one candidate.</h2><p>Your workspace is ready to organize approvals and source-based reviews. Identity checks need an activated provider before they can run.</p><div class="actions">' + primaryInvite() + '<a class="text-link" href="#settings">Review service setup ' + icon('arrow') + '</a></div></div><ol class="onboarding-steps"><li><div><strong>Check the requested scope</strong><span>Choose only the checks relevant to the role.</span></div></li><li><div><strong>Send a private invitation</strong><span>The candidate approves and shares their information.</span></div></li><li><div><strong>Review and record the source</strong><span>Keep manual evidence separate from provider verification.</span></div></li></ol></section>';
}
async function renderOverview(view, params=new URLSearchParams(), routeRequest=state.route) {
  const data=await overviewData();if(routeRequest!==state.route)return;
  state.view=view;state.sort=['name_asc','name_desc'].includes(params.get('sort'))?params.get('sort'):'newest';state.filter=params.get('status') || (view==='review'?'needs_review':'all');if(!filters.some(([key])=>key===state.filter))state.filter='all';state.search=params.get('search') || '';
  const actions=(canEdit?'<a class="button" href="/api/export.csv">' + icon('down') + 'Export cases</a>':'') + primaryInvite();
  if(view==='overview') {
    const queue=[['total','All candidates','candidates'],['in_progress','In progress','candidates?status=in_progress'],['needs_review','Needs review','review'],['completed','Review complete','candidates?status=completed']];
    root.innerHTML=heading('Your verification workspace','Invite candidates, follow approvals, and review evidence in one place.',actions) +
      '<nav class="queue-summary" aria-label="Candidate counts">' + queue.map(([key,label,path])=>'<a href="#' + path + '"' + (key==='needs_review'?' class="queue-warning"':'') + '><span>' + label + '</span><strong>' + e(data.metrics[key]) + '</strong></a>').join('') + '</nav>' +
      (data.metrics.total===0?onboardingMarkup():data.metrics.needs_review?'<section class="next-action"><div><h2>' + e(data.metrics.needs_review) + (data.metrics.needs_review===1?' case needs your review':' cases need your review') + '</h2><p>Check candidate statements, record sources, and respond to corrections.</p></div><a class="button" href="#review">Open review queue ' + icon('arrow') + '</a></section>':'') +
      '<div class="content-grid">' + tablePanel('Candidate queue') + '<aside class="right-column"><section class="panel activity-panel"><h2>Recent activity</h2>' + activityMarkup(data.activity.slice(0,5)) + '<a class="text-link full-panel" href="#audit">Open audit trail ' + icon('arrow') + '</a><p class="sample-note">' + (data.demo?'These demo events describe fictional candidates.':'Events are scoped to your organization.') + '</p></section><section class="process-note"><h3>A completed review is not a hiring decision.</h3><p>Manual reviews record evidence and its source. Only a configured identity provider can return a provider verification.</p></section></aside></div>';
  } else {
    root.innerHTML=heading(view==='review'?'Review queue':'Candidates',view==='review'?'Review submitted statements and respond to candidate corrections.':'Follow approvals, check progress, and open each candidate case.',actions) + tablePanel(view==='review'?'Cases to review':'Candidate directory');
  }
  bindTable();
}
function renderNew() {
  if(!canEdit){root.innerHTML=heading('You have read-only access.','An owner or reviewer can invite candidates.');return;}
  root.innerHTML=heading('Invite a candidate','Choose the scope. The candidate approves before checks begin.','<a class="button" href="#candidates">Back to candidates</a>') +
    '<div class="form-layout"><section class="panel form-panel"><form id="invite-form"><div class="form-grid"><div class="field"><label for="candidate-name">Full name</label><input id="candidate-name" name="name" autocomplete="name" placeholder="e.g. Alex Morgan…" required maxlength="120"></div><div class="field"><label for="candidate-email">Email address</label><input id="candidate-email" name="email" type="email" autocomplete="email" spellcheck="false" placeholder="alex@example.com…" required maxlength="254"></div><div class="field full"><label for="candidate-role">Hiring role</label><input id="candidate-role" name="role" placeholder="e.g. Product designer…" required maxlength="160"></div><div class="field full"><label for="candidate-package">Verification scope</label><select id="candidate-package" name="package"><option value="Essential">Essential · Identity & employment</option><option value="Professional">Professional · Identity, employment, education & professional profile</option></select><small>Identity requires a configured provider. Credential checks use source-based manual review in this pilot.</small></div></div><div class="info-note">A private invitation link will be created. No checks begin until the candidate approves the scope. Email delivery is attempted when a sender is configured; otherwise copy the link.</div><div class="form-actions"><button class="button primary" type="submit">' + icon('plus') + 'Create invitation</button><a class="button" href="#candidates">Cancel</a></div><div class="form-error" id="invite-error" role="alert"></div></form><div id="invitation-result"></div></section><aside class="form-explainer"><h2>What happens next</h2><ol><li>Share the private invitation.</li><li>The candidate reviews the scope and approves participation.</li><li>They submit statements and complete any hosted identity session.</li><li>You review the evidence and record its source.</li></ol><p>You can change a candidate’s invitation link later. Previous links will stop working.</p></aside></div>';
  document.getElementById('invite-form').addEventListener('submit',async event=>{
    event.preventDefault();const form=event.target;const button=form.querySelector('button[type="submit"]');button.disabled=true;button.textContent='Creating invitation…';
    document.getElementById('invite-error').textContent='';
    try {
      const data=await api('/api/candidates','POST',Object.fromEntries(new FormData(form)));
      document.getElementById('invitation-result').innerHTML=invitationMarkup(data.invitation_url,data.delivery) + '<div class="form-actions"><a class="button primary" href="#candidate/' + e(data.candidate.id) + '">Open candidate case ' + icon('arrow') + '</a></div>';
      document.getElementById('copy-link').onclick=()=>copyLink(data.invitation_url);
      button.textContent='Invitation created';form.querySelectorAll('input,select').forEach(input=>input.disabled=true);document.getElementById('invitation-result').scrollIntoView({block:'nearest'});
      toast('Invitation created. Candidate approval is the next step.');await overviewData();
    } catch(error){formError(form,error.message);button.disabled=false;button.textContent='Create invitation';}
  });
}
function identityActionMarkup(check, candidate, providerReady) {
  if(check.kind!=='identity' || check.status==='verified')return '';
  if(candidate.sample)return '<p class="check-guidance">Fictional samples cannot start a real provider check.</p>';
  const sessionExists=typeof check.has_provider_session==='boolean'?check.has_provider_session:check.provider==='Stripe Identity';
  if(sessionExists)return '<div class="identity-guidance"><strong>An identity session already exists.</strong><p>The candidate can continue from their private portal. If they cannot open the session, follow up with the provider rather than creating another session.</p><p>The recorded outcome updates when the provider sends its result.</p></div>';
  if(check.status==='reviewed')return '';
  if(!providerReady)return '<div class="identity-guidance"><strong>Identity provider activation is required.</strong><p>A live provider and a valid public return address must be configured before hosted identity checks can start. Manual evidence review remains separate.</p><a class="text-link" href="#settings">Review provider setup ' + icon('arrow') + '</a></div>';
  return '<button class="button small primary" data-start="' + e(check.id) + '">Start identity verification</button>';
}
async function renderCandidate(id) {
  const routeRequest=state.route;
  const [data, settings]=await Promise.all([api('/api/candidates/' + encodeURIComponent(id)),api('/api/settings').catch(()=>null)]);
  const c=data.candidate, providerReady=settings?.capabilities?.identity_provider===true;if(routeRequest!==state.route)return;
  const consent=c.consent && c.status!=='withdrawn';
  const checkHTML=data.checks.map(check=>'<section class="check-row"><div class="check-title"><h3>' + e(check.label) + '</h3>' + status(check.status) + '</div><div class="check-meta">' + e(check.provider || 'Awaiting a recorded source') + (check.sample?' · illustrative evidence':'') + '</div>' +
    (check.source?'<p class="check-notes"><strong>Source:</strong> ' + e(check.source) + '</p>':'') +
    (check.notes?'<p class="check-notes">' + e(check.notes) + '</p>':'<p class="check-empty">No evidence source has been recorded yet.</p>') +
    (canEdit && consent && !['verified','reviewed'].includes(check.status)?'<div class="actions"><button class="button small" data-review="' + e(check.id) + '" aria-expanded="false">Record manual review</button>' + identityActionMarkup(check,c,providerReady) + '</div><form class="review-form" id="review-' + e(check.id) + '" data-check="' + e(check.id) + '" hidden><div class="field"><label for="source-' + e(check.id) + '">Evidence source</label><input id="source-' + e(check.id) + '" name="source" placeholder="Official issuer, reference contact, or source URL" required maxlength="500"></div><div class="field"><label for="notes-' + e(check.id) + '">Review notes</label><textarea id="notes-' + e(check.id) + '" name="notes" required placeholder="What did you review? Record the evidence and any limitations." maxlength="4000"></textarea></div><div><button class="button primary small" type="submit">Save manual review</button></div><div class="form-error" role="alert"></div></form>':'') + (check.kind==='identity' && consent && check.status==='reviewed'?identityActionMarkup(check,c,providerReady):'') + '</section>').join('');
  root.innerHTML='<div class="page-heading"><div class="detail-person"><span class="avatar">' + e(initials(c.name)) + '</span><div><h1>' + e(c.name) + '</h1><p>' + e(c.role) + ' · ' + e(c.email) + '</p></div></div><a class="button" href="#candidates">Back to candidates</a></div>' +
    (c.sample?'<div class="sample-banner">Fictional demo candidate. Sample evidence is illustrative and cannot be submitted to a real identity provider.</div>':'') +
    '<div class="detail-layout"><div><section class="panel"><div class="panel-heading"><div><h2>Checks & evidence</h2><p>Candidate statements need an independent source review.</p></div>' + status(c.status) + '</div>' +
    (!consent?'<div class="info-note" style="margin:0 24px 24px">' + (c.status==='withdrawn'?'This candidate withdrew. Their information has been removed and access is revoked.':'Waiting for candidate approval. Evidence review and provider checks are locked until the candidate approves.') + '</div>':'') +
    (checkHTML || '<div class="empty-state">No active checks.</div>') + '</section>' +
    (data.corrections?.length?'<section class="panel full-panel"><div class="panel-heading"><h2>Candidate corrections</h2></div>' + data.corrections.map(cr=>'<div class="correction"><h3>' + (cr.status==='resolved'?'Resolved correction':'Correction requested') + '</h3><p>' + e(cr.message) + '</p>' + (cr.resolution_notes?'<p><strong>Resolution:</strong> ' + e(cr.resolution_notes) + '</p>':'') + (canEdit && cr.status!=='resolved'?'<form data-correction="' + e(cr.id) + '" class="review-form"><div class="field"><label for="correction-' + e(cr.id) + '">Response to the candidate</label><textarea id="correction-' + e(cr.id) + '" name="notes" required maxlength="4000"></textarea><small>This response is visible to the candidate.</small></div><div><button class="button small primary" type="submit">Record resolution</button></div><div class="form-error" role="alert"></div></form>':'') + '</div>').join('') + '</section>':'') +
    '<div id="detail-invitation"></div></div><aside><section class="panel detail-info"><h2>Case details</h2><dl><dt>Scope</dt><dd>' + e(c.package) + '</dd><dt>Candidate approval</dt><dd>' + (consent?'Approved':'Not active') + '</dd><dt>Evidence review</dt><dd>' + e(c.checks_completed) + ' of ' + e(c.checks_total) + ' checks complete</dd><dt>Created</dt><dd>' + e(date(c.created_at)) + '</dd></dl>' +
    (canEdit && c.status!=='withdrawn'?'<div class="form-actions"><button class="button" id="reissue-link">' + icon('link') + 'Create new invitation link</button></div><p class="sample-note">A new link revokes earlier links. Email delivery is attempted when a sender is configured; otherwise share the link.</p>':'') + '</section><section class="panel activity-panel full-panel"><h2>Case activity</h2>' + activityMarkup(data.activity) + '</section></aside></div>';
  root.querySelectorAll('[data-review]').forEach(button=>button.addEventListener('click',()=>{const form=document.getElementById('review-' + button.dataset.review);form.hidden=!form.hidden;button.setAttribute('aria-expanded',String(!form.hidden));if(!form.hidden)form.querySelector('input').focus();}));
  root.querySelectorAll('form[data-check]').forEach(form=>form.addEventListener('submit',async event=>{
    event.preventDefault();const button=form.querySelector('button');setBusy(button,'Saving review…');form.querySelector('.form-error').textContent='';
    try{await api('/api/candidates/' + encodeURIComponent(id) + '/checks/' + encodeURIComponent(form.dataset.check) + '/review','POST',Object.fromEntries(new FormData(form)));toast('Manual review recorded with its evidence source.');await renderCandidate(id);await overviewData();}
    catch(error){formError(form,error.message);clearBusy(button);}
  }));
  root.querySelectorAll('[data-start]').forEach(button=>button.addEventListener('click',async()=>{
    setBusy(button,'Creating session…');
    try{await api('/api/candidates/' + encodeURIComponent(id) + '/checks/' + encodeURIComponent(button.dataset.start) + '/start','POST',{provider:'stripe_identity'});toast('Identity session created. The candidate can continue from their portal.');await renderCandidate(id);}
    catch(error){toast(error.message);clearBusy(button);}
  }));
  root.querySelectorAll('form[data-correction]').forEach(form=>form.addEventListener('submit',async event=>{
    event.preventDefault();const button=form.querySelector('button');setBusy(button,'Saving review…');form.querySelector('.form-error').textContent='';
    try{await api('/api/candidates/' + encodeURIComponent(id) + '/corrections/' + encodeURIComponent(form.dataset.correction) + '/resolve','POST',{notes:new FormData(form).get('notes')});toast('Correction resolution recorded.');await renderCandidate(id);}
    catch(error){formError(form,error.message);clearBusy(button);}
  }));
  document.getElementById('reissue-link')?.addEventListener('click',async event=>{
    if(!window.confirm('Create a new invitation? Previous invitation links will stop working.'))return;
    const button=event.currentTarget;setBusy(button,'Creating invitation…');
    try{const result=await api('/api/candidates/' + encodeURIComponent(id) + '/invite','POST',{});document.getElementById('detail-invitation').innerHTML=invitationMarkup(result.invitation_url,result.delivery);document.getElementById('copy-link').onclick=()=>copyLink(result.invitation_url);toast('New invitation link created. Older links have been revoked.');clearBusy(button);}
    catch(error){toast(error.message);clearBusy(button);}
  });
  focusHeading();
}
async function renderAudit() {
  const routeRequest=state.route;const data=await api('/api/audit');if(routeRequest!==state.route)return;
  root.innerHTML=heading('Audit trail','Candidate and staff events, with their time and recorded action.') +
    '<section class="panel"><div class="panel-heading"><h2>Audit trail</h2><span class="muted" style="font-size:12px">Latest ' + data.entries.length + ' events</span></div><div class="table-scroll"><table class="audit-table"><thead><tr><th scope="col">Time</th><th scope="col">Event</th><th scope="col">Action</th></tr></thead><tbody>' + (data.entries.length?data.entries.map(item=>'<tr><td class="muted">' + e(date(item.created_at)) + '</td><td>' + e(item.message) + '</td><td>' + e(item.action || '') + '</td></tr>').join(''):'<tr><td colspan="3" class="empty-state">Events will appear as your workspace is used.</td></tr>') + '</tbody></table></div></section><p class="sample-note">Events cannot be edited through the app. This pilot uses SQLite; production tamper-evident storage and external log retention are launch requirements.</p>';
}
async function renderSettings() {
  const routeRequest=state.route;const data=await api('/api/settings');if(routeRequest!==state.route)return;
  root.innerHTML=heading('Workspace settings','Review provider availability and manage team access.') +
    '<div class="settings-grid"><section class="panel"><div class="panel-heading"><div><h2>Verification providers</h2><p>Real checks require a configured provider.</p></div></div><div class="capability-list" id="capability-list"></div></section><section class="panel detail-info"><h2>Current pilot scope</h2><p style="font-size:12px">Tenant-scoped cases, staff roles, approval, candidate claims, source-based review, and signed identity webhooks.</p><ul class="readiness-list"><li>Connect and validate an identity provider</li><li>Contract credential and screening data providers</li><li>Validate privacy, retention, and legal basis</li><li>Add SSO, managed storage, queues, and monitoring</li><li>Run independent security and operational reviews</li></ul><p class="sample-note">No certification or enterprise compliance claim is made.</p></section></div><div id="team-panel"></div>';
  const host=document.getElementById('capability-list');
  // The settings API deliberately exposes capabilities rather than pretending toggles configure providers.
  const identityProvider=(data.providers || []).find(provider=>provider.id==='stripe_identity');
  const known=[
    ['Identity verification',identityProvider?.configured || data.capabilities?.identity_provider ? 'Configured · verify provider account readiness' : 'Stripe Identity · not connected'],
    ['Employment & education','Source-based manual review'],
    ['Criminal records & right to work','Provider not connected'],
    ['Invitation email',data.capabilities?.email_delivery ? 'SMTP configured' : 'Manual link delivery'],
    ['Pilot billing',data.capabilities?.billing ? 'Checkout configured · no payment required during open access' : 'Open access · no payment required'],
    ['Suitability scoring','Not part of the product']
  ];
  host.innerHTML=known.map(([name,value])=>'<div class="capability-row"><strong>' + e(name) + '</strong><span>' + e(value) + '</span></div>').join('');
  if(document.body.dataset.role==='owner') {
    const result=await api('/api/users');if(routeRequest!==state.route)return;
    document.getElementById('team-panel').innerHTML='<section class="panel full-panel"><div class="panel-heading"><div><h2>Team access</h2><p>Owners manage accounts. Reviewers work on checks. Viewers have read-only access.</p></div></div><div class="table-scroll"><table><thead><tr><th scope="col">Name</th><th scope="col">Email</th><th scope="col">Role</th></tr></thead><tbody>' + result.users.map(user=>'<tr><td>' + e(user.name) + '</td><td>' + e(user.email) + '</td><td>' + e(user.role) + '</td></tr>').join('') + '</tbody></table></div><form id="team-form" class="team-form"><h3>Add a team member</h3><div class="form-grid"><div class="field"><label for="team-name">Full name</label><input id="team-name" name="name" autocomplete="name" required maxlength="120"></div><div class="field"><label for="team-email">Email</label><input id="team-email" type="email" name="email" autocomplete="email" spellcheck="false" required></div><div class="field"><label for="team-password">Initial password</label><input id="team-password" type="password" name="password" required minlength="12" autocomplete="new-password"><small>At least 12 characters. Deliver through an approved secure channel.</small></div><div class="field"><label for="team-role">Access role</label><select id="team-role" name="role"><option value="viewer">Viewer</option><option value="reviewer">Reviewer</option><option value="owner">Owner</option></select></div></div><div class="form-actions"><button class="button primary" type="submit">Add team member</button></div><div class="form-error" role="alert"></div></form></section>';
    document.getElementById('team-form').addEventListener('submit',async event=>{
      event.preventDefault();const form=event.target;const button=form.querySelector('button');setBusy(button,'Adding team member…');form.querySelector('.form-error').textContent='';
      try{await api('/api/users','POST',Object.fromEntries(new FormData(form)));toast('Team member added with the selected access role.');await renderSettings();}
      catch(error){formError(form,error.message);clearBusy(button);}
    });
  }
}
async function route() {
  const routeRequest=++state.route;state.tableController?.abort();++state.request;
  const hash=location.hash.slice(1) || 'overview', [path,query='']=hash.split('?'), [view,id]=path.split('/');
  state.view=view;
  const titles={overview:'Overview',candidates:'Candidates',review:'Review queue',audit:'Audit trail',settings:'Workspace settings',new:'Invite candidate',candidate:'Candidate case'};
  document.getElementById('breadcrumb').textContent=titles[view] || 'Overview';document.title=(titles[view] || 'Overview') + ' · Verisento';
  root.setAttribute('aria-busy','true');
  document.querySelectorAll('.nav-link[data-view]').forEach(link=>{const active=link.dataset.view===(['new','candidate'].includes(view)?'candidates':view);link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
  closeNavigation();root.innerHTML=loadingMarkup();
  try {
    if(['overview','candidates','review'].includes(view))await renderOverview(view,new URLSearchParams(query),routeRequest);
    else if(view==='new')renderNew();
    else if(view==='candidate' && id)await renderCandidate(id);
    else if(view==='audit')await renderAudit();
    else if(view==='settings')await renderSettings();
    else {location.hash='overview';}
    if(routeRequest===state.route)focusHeading();
  } catch(error) {
    if(routeRequest!==state.route)return;
    root.innerHTML='<div class="error-state" role="alert"><h1>This page could not load</h1><p>' + e(error.message) + '</p><div class="actions"><button class="button" id="retry">Try again</button>' + (error.message.includes('session has ended')?'<a class="button primary" href="/login">Sign in again</a>':'') + '</div></div>';document.getElementById('retry').onclick=route;focusHeading();
  } finally {if(routeRequest===state.route)root.setAttribute('aria-busy','false');}
}
function closeNavigation() {
  document.getElementById('workspace-sidebar').dataset.expanded='false';const button=document.getElementById('nav-toggle');button.setAttribute('aria-expanded','false');button.setAttribute('aria-label','Open workspace navigation');button.querySelector('use').setAttribute('href','#i-menu');
}
document.getElementById('nav-toggle').addEventListener('click',event=>{const button=event.currentTarget, expanded=button.getAttribute('aria-expanded')!=='true';document.getElementById('workspace-sidebar').dataset.expanded=String(expanded);button.setAttribute('aria-expanded',String(expanded));button.setAttribute('aria-label',expanded?'Close workspace navigation':'Open workspace navigation');button.querySelector('use').setAttribute('href',expanded?'#i-close':'#i-menu');});
document.querySelectorAll('#workspace-navigation a').forEach(link=>link.addEventListener('click',closeNavigation));
document.addEventListener('keydown',event=>{if(event.key==='Escape' && document.getElementById('nav-toggle').getAttribute('aria-expanded')==='true'){closeNavigation();document.getElementById('nav-toggle').focus();}});
document.querySelectorAll('#logout,#logout-mobile').forEach(button=>button.addEventListener('click',async()=>{setBusy(button,'Signing out…');try{await api('/api/logout','POST',{});location.href='/login';}catch(error){toast(error.message);clearBusy(button);}}));
window.addEventListener('hashchange',route);
route();
