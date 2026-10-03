'use strict';
const root=document.getElementById('portal-content');
const token=document.body.dataset.token;
const base='/api/portal/' + encodeURIComponent(token);
const csrf=document.querySelector('meta[name="csrf-token"]').content;
const e=value=>String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const descriptions={identity:'A hosted identity check when the employer enables its provider.',employment:'Employment details reviewed against a documented source.',education:'Education or qualification details reviewed against a documented source.',professional_profile:'Only a professional profile you choose to share.'};
const labels={pending:'Not started',in_progress:'In progress',needs_review:'Ready for review',reviewed:'Manually reviewed',verified:'Provider verified'};
async function api(path='',body) {
  const response=await fetch(base + path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body===undefined?undefined:JSON.stringify(body)});
  const result=await response.json();if(!response.ok)throw new Error(result.error || 'The request could not be completed. Try again.');return result;
}
function toast(message){const el=document.getElementById('toast');el.textContent=message;el.hidden=false;setTimeout(()=>el.hidden=true,6000);}
function privacy() {
  return '<div class="portal-privacy"><h3>What you are approving</h3><ul><li>The employer sees your submitted statements, evidence sources, and check outcomes for the scope shown above.</li><li>If identity verification is enabled, the identity provider collects your documents in its hosted experience. This portal does not collect identity documents or biometrics.</li><li>Vetra does not infer sensitive traits or recommend whether you should be hired.</li><li>You can request a correction or withdraw. Withdrawal removes your details from this workspace, revokes the invitation link, and requests provider cleanup where a session exists. Ask the employer about its separate legal record-keeping obligations.</li></ul><p>Participation approval is recorded. The employer must establish the appropriate legal basis, notices, and retention policy for your region.</p></div>';
}
async function render(focus=false){
  try{
    const data=await api(), c=data.candidate;
    const checks=data.checks || [];
    const statements=data.statements || {};
    const corrections=data.corrections || [];
    const isApproved=data.consent;
    root.innerHTML=(data.sample?'<div class="sample-banner">This is a fictional demonstration. Please use sample information only.</div>':'') +
      '<div class="portal-step"><strong>Invitation</strong><span>→</span><strong>' + (isApproved?'Approved':'Your approval') + '</strong><span>→</span><span>Share information</span><span>→</span><span>Human review</span></div><h1>A clear start, on your terms.</h1><p class="intro">Hello ' + e(c.name) + '. <strong>' + e(c.organization) + '</strong> has invited you to complete verification for the <strong>' + e(c.role) + '</strong> role. Here is exactly what they have requested.</p>' +
      '<section class="portal-card"><h2>Your verification scope</h2><ul class="scope-list">' + checks.map(check=>'<li><div><strong>' + e(check.label) + '</strong><small>' + e(descriptions[check.kind] || 'A source-based review of the information you share.') + '</small></div><span class="status ' + e(check.status) + '">' + e(labels[check.status] || check.status) + '</span></li>').join('') + '</ul>' +
      (!isApproved?'<form id="consent-form">' + privacy() + '<label class="consent-box"><input type="checkbox" id="approve" required><span>I have read the scope and agree to participate in the requested verification. I understand how to request a correction or withdraw.</span></label><div class="form-actions"><button class="button primary" type="submit">Approve and continue</button></div><div class="form-error" role="alert"></div></form>':'<div class="info-note">Your approval is recorded. You can share your statements below or ask the employer to correct information.</div>') + '</section>' +
      (isApproved?'<section class="portal-card"><h2>Share the information you want reviewed.</h2><p>These are your statements. They remain unverified until evidence is reviewed or the configured identity provider completes its check.</p>' +
      checks.filter(check=>check.kind==='identity' && check.verification_url).map(check=>'<div class="info-note">Your hosted identity session is ready. <a class="button primary small" target="_blank" rel="noopener noreferrer" href="' + e(safeProviderURL(check.verification_url)) + '">Continue identity verification</a><p class="sample-note">You will continue on the identity provider’s website. Return here after completion.</p></div>').join('') +
      (Object.keys(statements).length?'<div class="info-note"><strong>Your submitted information is saved.</strong> The statements below are your current record. Updating them sends them back for review.</div>':'') + '<form id="claims-form">' + checks.filter(check=>check.kind!=='identity').map(check=>'<div class="field"><label for="claim-' + e(check.kind) + '">' + e(check.label) + '</label>' + (check.kind==='professional_profile'?'<input id="claim-' + e(check.kind) + '" name="' + e(check.kind) + '" type="url" placeholder="https://your-professional-profile.example" maxlength="500" value="' + e(statements[check.kind] || '') + '">':'<textarea id="claim-' + e(check.kind) + '" name="' + e(check.kind) + '" maxlength="2500" placeholder="' + (check.kind==='employment'?'Employer, role, dates, and a source the reviewer can confirm.':'Institution, qualification, dates, and a source the reviewer can confirm.') + '">' + e(statements[check.kind] || '') + '</textarea>') + '<small>Include only the details needed for this check.</small></div>').join('') + '<div class="form-actions"><button class="button primary" type="submit">Submit for review</button></div><div class="form-error" role="alert"></div></form></section><section class="portal-card"><h2>Something needs correcting?</h2><p>Tell the reviewer what is wrong and what should change.</p><form id="correction-form"><div class="field"><label for="correction-message">Your correction request</label><textarea id="correction-message" name="message" required maxlength="4000" placeholder="Explain which information needs updating."></textarea></div><div class="form-actions"><button class="button" type="submit">Request a correction</button></div><div class="form-error" role="alert"></div></form>' + (corrections.length?'<div class="full-panel"><h3>Your correction requests</h3>' + corrections.map(cr=>'<div class="correction"><strong>' + (cr.status==='resolved'?'Resolved':'Awaiting reviewer response') + '</strong><p>' + e(cr.message) + '</p>' + (cr.resolution_notes?'<p><strong>Reviewer response:</strong> ' + e(cr.resolution_notes) + '</p>':'') + '</div>').join('') + '</div>':'') + privacy() + '</section>':'') +
      '<section class="withdraw-block"><div><h3>You can withdraw.</h3><p>Your workspace details will be removed and this invitation will stop working. Contact the employer to discuss any hiring-process implications.</p></div><button class="button danger" id="withdraw">Withdraw from verification</button></section>';
    if(focus){const title=root.querySelector('h1');title.tabIndex=-1;title.focus({preventScroll:true});}
    document.getElementById('consent-form')?.addEventListener('submit',event=>submit(event,'/consent',{approved:document.getElementById('approve').checked},'Your approval has been recorded.',true));
    document.getElementById('claims-form')?.addEventListener('submit',event=>submit(event,'/submit',Object.fromEntries(new FormData(event.target)),'Your statements have been submitted for human review.',true));
    document.getElementById('correction-form')?.addEventListener('submit',event=>submit(event,'/correction',Object.fromEntries(new FormData(event.target)),'Your correction request has been recorded.',true));
    document.getElementById('withdraw').addEventListener('click',async event=>{
      if(!window.confirm('Withdraw from verification? Your workspace details will be removed and this invitation will stop working.'))return;
      event.target.disabled=true;
      try{const result=await api('/withdraw',{});root.innerHTML='<section class="portal-card"><h1>Your withdrawal is recorded.</h1><p>Your details have been removed from this workspace and invitation access has been revoked.</p><p>' + e(result.provider_cleanup==='follow_up_required'?'Provider cleanup needs follow-up from the employer.':result.provider_cleanup==='requested'?'Provider cleanup has been requested. The employer must confirm its completion.':'There was no external identity session requiring cleanup.') + '</p><a href="/about" class="button">About Vetra</a></section>';const title=root.querySelector('h1');title.tabIndex=-1;title.focus({preventScroll:true});}
      catch(error){toast(error.message);event.target.disabled=false;}
    });
  }catch(error){root.innerHTML='<section class="portal-card" role="alert"><h1>This invitation is unavailable.</h1><p>' + e(error.message) + '</p><p>Ask the employer for a new invitation if yours has expired or been replaced.</p><a class="button" href="/about">About Vetra</a></section>';}
}
function safeProviderURL(value){try{const u=new URL(value);return u.protocol==='https:' && (u.hostname==='verify.stripe.com' || u.hostname.endsWith('.stripe.com'))?u.href:'#';}catch{return '#';}}
async function submit(event,path,body,message,rerender){
  event.preventDefault();const form=event.target,button=form.querySelector('button');button.disabled=true;form.querySelector('.form-error').textContent='';
  try{await api(path,body);toast(message);if(rerender)await render(true);else{form.reset();button.disabled=false;}}
  catch(error){form.querySelector('.form-error').textContent=error.message;button.disabled=false;}
}
render();
