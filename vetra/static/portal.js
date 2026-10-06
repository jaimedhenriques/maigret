'use strict';
const root=document.getElementById('portal-content');
const token=document.body.dataset.token;
const base='/api/portal/' + encodeURIComponent(token);
const csrf=document.querySelector('meta[name="csrf-token"]').content;
const e=value=>String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const descriptions={identity:'Complete a hosted identity check when the employer activates its provider.',employment:'Share employment details for review against a documented source.',education:'Share qualification details for review against a documented source.',professional_profile:'Share a professional profile you choose to provide.'};
const labels={pending:'Not started',in_progress:'In progress',needs_review:'Ready for review',reviewed:'Manually reviewed',verified:'Provider verified'};
let toastTimer, dirty=false;
async function api(path='',body) {
  let response;
  try { response=await fetch(base + path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body===undefined?undefined:JSON.stringify(body)}); }
  catch { throw new Error('The connection was interrupted. Check your connection and try again.'); }
  const result=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(result.error || 'The request could not be completed. Try again.');return result;
}
function toast(message) { const el=document.getElementById('toast');el.textContent=message;el.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.hidden=true,6000); }
function privacy() {
  return '<div class="portal-privacy"><h3>How your information is used</h3><ul><li>The employer sees your submitted statements, evidence sources, and check outcomes for the scope shown here.</li><li>Any identity documents are collected on the identity provider’s hosted pages. This portal does not collect identity documents or biometrics.</li><li>Verisento does not infer sensitive traits or recommend whether you should be hired.</li><li>You can request a correction or withdraw. Withdrawal removes your details from this workspace, revokes this invitation, and requests provider cleanup where a session exists.</li></ul><p>Ask the employer about its legal basis, retention policy, and any separate record-keeping obligations. Your approval records your choice to participate; it does not establish every legal basis for employment processing.</p><a href="/privacy" class="text-link">Read the candidate privacy notice</a></div>';
}
function progressMarkup(approved, submitted, completed) {
  const current=!approved?0:!submitted && !completed?1:2;
  return '<ol class="portal-step" aria-label="Verification steps">' + ['Review & approve','Share information','Human review'].map((label,index)=>'<li class="' + (index===current?'current':index<current?'complete':'') + '"' + (index===current?' aria-current="step"':'') + '><span class="step-number" aria-hidden="true">' + (index+1) + '</span><span>' + label + '</span></li>').join('') + '</ol>';
}
function scopeMarkup(checks) {
  return '<ul class="scope-list">' + checks.map(check=>'<li><div><strong>' + e(check.label) + '</strong><small>' + e(descriptions[check.kind] || 'Review the information you share against a documented source.') + '</small></div><span class="status ' + e(check.status) + '">' + e(labels[check.status] || check.status) + '</span></li>').join('') + '</ul>';
}
function safeProviderURL(value) { try { const u=new URL(value);return u.protocol==='https:' && (u.hostname==='verify.stripe.com' || u.hostname.endsWith('.stripe.com'))?u.href:null; } catch { return null; } }
function claimField(check, statement) {
  const id='claim-' + e(check.kind), hint=id+'-hint';
  return '<div class="field"><label for="' + id + '">' + e(check.label) + '</label>' + (check.kind==='professional_profile'?'<input id="' + id + '" name="' + e(check.kind) + '" type="url" autocomplete="url" spellcheck="false" placeholder="https://your-professional-profile.example…" maxlength="500" aria-describedby="' + hint + '" value="' + e(statement || '') + '">':'<textarea id="' + id + '" name="' + e(check.kind) + '" maxlength="2500" aria-describedby="' + hint + '" placeholder="' + (check.kind==='employment'?'Employer, role, dates, and a source the reviewer can confirm…':'Institution, qualification, dates, and a source the reviewer can confirm…') + '">' + e(statement || '') + '</textarea>') + '<small id="' + hint + '">Include only details needed for this check. Your statement becomes evidence only after a source review.</small></div>';
}
function focusTitle() { const title=root.querySelector('h1');if(title){title.tabIndex=-1;title.focus({preventScroll:true});} }
async function render(focus=false) {
  root.setAttribute('aria-busy','true');
  try {
    const data=await api(), c=data.candidate, checks=data.checks || [], statements=data.statements || {}, corrections=data.corrections || [];
    const approved=data.consent, submitted=Object.keys(statements).length>0, completed=data.status==='completed', credentialChecks=checks.filter(check=>check.kind!=='identity');
    const expires=new Date(data.expires_at), expiration=Number.isNaN(expires.valueOf())?'':new Intl.DateTimeFormat('en',{day:'numeric',month:'short',year:'numeric'}).format(expires);
    const identitySessions=checks.filter(check=>check.kind==='identity' && check.verification_url).map(check=>{
      const url=safeProviderURL(check.verification_url);
      return '<div class="identity-session"><h3>' + (url?'Your identity session is ready':'Ask your employer for an updated identity link') + '</h3><p>' + (url?'Continue on the provider’s website to complete the check. Documents are collected there. Return here and refresh your status after you finish.':'This identity link could not be opened safely. Your employer can arrange a new hosted session.') + '</p>' + (url?'<a class="button primary" target="_blank" rel="noopener noreferrer" href="' + e(url) + '">Continue identity verification<span class="sr-only"> (opens provider in a new tab)</span></a>':'') + '</div>';
    }).join('');
    root.innerHTML=(data.sample?'<div class="sample-banner">Fictional demonstration. Please use sample information only.</div>':'') + progressMarkup(approved,submitted,completed) +
      '<h1>' + (!approved?'Review your verification request':completed?'Your evidence review is complete':submitted?'Your information is with the reviewer':'Share your verification information') + '</h1><p class="intro">Hello ' + e(c.name) + '. <strong>' + e(c.organization) + '</strong> has requested verification for the <strong>' + e(c.role) + '</strong> role. You control your participation and can request a correction.</p>' +
      '<div class="portal-case"><div><strong>' + e(c.organization) + '</strong><span>' + e(c.role) + '</span></div>' + (expiration?'<p>Invitation access expires<br><strong>' + e(expiration) + '</strong></p>':'') + '</div>' +
      '<section class="portal-card"><h2>' + (approved?'Your checks':'What you are being asked to approve') + '</h2>' + scopeMarkup(checks) +
      (!approved?'<form id="consent-form"><div class="portal-privacy"><h3>Before you approve</h3><p>Your employer will see the information you submit and the recorded outcomes. Any identity documents stay in the identity provider’s hosted flow. You can request a correction or withdraw.</p></div><details class="privacy-disclosure"><summary>How your information is used</summary>' + privacy() + '</details><label class="consent-box"><input type="checkbox" id="approve" name="approved" required><span>I have read the requested scope and agree to participate. I understand how to request a correction or withdraw.</span></label><div class="form-actions"><button class="button primary" type="submit">Approve and continue</button></div><div class="form-error" role="alert"></div></form>':'<div class="portal-status-summary"><strong>' + (completed?'All requested checks have a recorded outcome.':'Your approval is recorded.') + '</strong><p>' + (completed?'A completed review records the workflow. The employer makes the hiring decision.':'Manual evidence review and provider verification are labeled separately.') + '</p><div class="form-actions"><button class="button small" id="portal-refresh">Refresh check status</button></div></div>') + '</section>' +
      (approved && (credentialChecks.length || identitySessions)?'<section class="portal-card" id="information-section"><h2>' + (submitted?'Your submitted information':'Information for the reviewer') + '</h2><p>Your statements remain unverified until a source review or provider check is complete.</p>' + identitySessions +
      (credentialChecks.length?(submitted?'<div class="saved-notice" role="status">Your information is saved. Changes will send the affected statements back for review.</div>':'') + '<form id="claims-form">' + credentialChecks.map(check=>claimField(check,statements[check.kind])).join('') + '<div class="form-actions"><button class="button primary" type="submit">' + (submitted?'Save changes for review':'Submit information for review') + '</button></div><div class="form-error" role="alert"></div></form>':'') + '</section>':'') +
      (approved?'<section class="portal-card"><h2>Corrections & your choices</h2><p>Tell the reviewer what is wrong and what should change.</p><details class="privacy-disclosure"' + (corrections.some(cr=>cr.status!=='resolved')?' open':'') + '><summary>Request a correction</summary><form id="correction-form"><div class="field"><label for="correction-message">What needs correcting?</label><textarea id="correction-message" name="message" required maxlength="4000" placeholder="Explain which information needs updating…"></textarea></div><div class="form-actions"><button class="button" type="submit">Send correction request</button></div><div class="form-error" role="alert"></div></form></details>' +
      (corrections.length?'<div class="full-panel"><h3>Your correction requests</h3>' + corrections.map(cr=>'<div class="correction"><strong>' + (cr.status==='resolved'?'Resolved':'Awaiting reviewer response') + '</strong><p>' + e(cr.message) + '</p>' + (cr.resolution_notes?'<p><strong>Reviewer response:</strong> ' + e(cr.resolution_notes) + '</p>':'') + '</div>').join('') + '</div>':'') + '<details class="privacy-disclosure"><summary>Privacy & use of your information</summary>' + privacy() + '</details></section>':'') +
      '<section class="withdraw-block"><div><h2>' + (approved?'Withdraw from this verification':'Prefer not to participate?') + '</h2><p>Withdrawing removes your workspace details and revokes this invitation. Discuss any hiring-process implications with the employer.</p></div><button class="button danger" id="withdraw">' + (approved?'Withdraw from verification':'Decline and withdraw') + '</button></section>';
    if(focus)focusTitle();
    document.getElementById('consent-form')?.addEventListener('submit',event=>submit(event,'/consent',{approved:document.getElementById('approve').checked},'Your approval has been recorded.','Recording approval…'));
    document.getElementById('claims-form')?.addEventListener('submit',event=>submit(event,'/submit',Object.fromEntries(new FormData(event.target)),'Your information is saved for human review.','Saving information…'));
    document.getElementById('correction-form')?.addEventListener('submit',event=>submit(event,'/correction',Object.fromEntries(new FormData(event.target)),'Your correction request has been recorded.','Sending correction…'));
    document.getElementById('portal-refresh')?.addEventListener('click',async event=>{if(dirty && !window.confirm('Refresh check status? Your unsaved information will be discarded.'))return;dirty=false;const button=event.currentTarget;button.disabled=true;button.textContent='Refreshing…';await render(true);toast('Showing the latest recorded check status.');});
    root.querySelectorAll('form input,form textarea').forEach(field=>field.addEventListener('input',()=>dirty=true));
    document.getElementById('withdraw').addEventListener('click',async event=>{
      if(!window.confirm('Withdraw from verification? Your workspace details will be removed and this invitation will stop working.'))return;
      const button=event.currentTarget;button.disabled=true;button.textContent='Withdrawing…';
      try {
        const result=await api('/withdraw',{});dirty=false;
        root.innerHTML='<section class="portal-card"><h1>Your withdrawal is recorded</h1><p>Your details have been removed from this workspace and invitation access has been revoked.</p><p>' + e(result.provider_cleanup==='follow_up_required'?'Provider cleanup needs follow-up from the employer.':result.provider_cleanup==='requested'?'Provider cleanup has been requested. The employer must confirm its completion.':'There was no external identity session requiring cleanup.') + '</p><a href="/about" class="button">About Verisento</a></section>';focusTitle();
      } catch(error) { toast(error.message);button.disabled=false;button.textContent=approved?'Withdraw from verification':'Decline and withdraw'; }
    });
  } catch(error) {
    root.innerHTML='<section class="portal-card" role="alert"><h1>This invitation could not load</h1><p>' + e(error.message) + '</p><p>Check your connection and try again. If this invitation has expired or been replaced, ask the employer for a new link.</p><div class="form-actions"><button class="button" id="retry-portal">Try again</button><a class="text-link" href="/about">About Verisento</a></div></section>';document.getElementById('retry-portal').onclick=()=>render(true);if(focus)focusTitle();
  } finally {root.setAttribute('aria-busy','false');}
}
async function submit(event,path,body,message,busyLabel) {
  event.preventDefault();const form=event.target, button=form.querySelector('button[type="submit"]'), label=button.textContent;button.disabled=true;button.setAttribute('aria-busy','true');button.textContent=busyLabel;form.querySelector('.form-error').textContent='';
  try { await api(path,body);dirty=false;toast(message);await render(true); }
  catch(error) { const errorEl=form.querySelector('.form-error');errorEl.textContent=error.message;errorEl.tabIndex=-1;errorEl.focus();button.disabled=false;button.removeAttribute('aria-busy');button.textContent=label; }
}
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
render();
