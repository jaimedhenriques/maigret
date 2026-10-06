'use strict';
async function post(path, body) {
  let response;
  try {
    response = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content}, body: JSON.stringify(body)});
  } catch {
    throw new Error('Connection interrupted. Check your connection and try again.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'We could not save this request. Please try again.');
  return data;
}
const pay = document.getElementById('pay');
if (pay) pay.addEventListener('click', async () => {
  const status = document.getElementById('payment-status');
  pay.disabled = true;
  status.textContent = 'Opening secure checkout…';
  delete status.dataset.error;
  try {
    const data = await post('/api/billing/checkout', {});
    const url = new URL(data.url);
    if (url.protocol !== 'https:' || url.hostname !== 'checkout.stripe.com') throw new Error('Checkout is unavailable. Please contact your workspace owner.');
    location.assign(url.href);
  } catch (error) {
    status.textContent = error.message;
    status.dataset.error = 'true';
    pay.disabled = false;
  }
});
const form = document.getElementById('time-form');
if (form) form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button[type="submit"]');
  if (button.disabled) return;
  const status = document.getElementById('time-status');
  const candidate = form.elements.candidate_id;
  const minutes = form.elements.minutes;
  const baseline = form.elements.baseline_minutes;
  button.disabled = true;
  button.textContent = 'Saving…';
  status.textContent = '';
  delete status.dataset.error;
  form.setAttribute('aria-busy', 'true');
  try {
    const data = await post('/api/pilot/time', {candidate_id: candidate.value, minutes: Number(minutes.value), baseline_minutes: Number(baseline.value)});
    document.getElementById('saved-minutes').textContent = String(data.saved_minutes);
    document.getElementById('measurement-count').textContent = String(data.measurements);
    minutes.value = '';
    baseline.value = '';
    status.textContent = 'Measurement saved. Your performance totals are updated.';
  } catch (error) {
    status.textContent = error.message;
    status.dataset.error = 'true';
  } finally {
    button.disabled = false;
    button.textContent = 'Save measurement';
    form.removeAttribute('aria-busy');
  }
});
