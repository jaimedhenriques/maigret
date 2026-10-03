"""Protocol and trust-boundary checks without an external provider account."""

import hashlib
import hmac
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs

import pytest

from vetra.providers import BACKGROUND_CHECK_CAPABILITIES, DemoProvider, ProviderError, StripeIdentityProvider


NOW = 1_790_000_000
WEBHOOK_SECRET = "whsec_example"


def provider(**kwargs):
    return StripeIdentityProvider("sk_live_example", WEBHOOK_SECRET, **kwargs)


def event(status="verified", *, livemode=True):
    return {
        "id": "evt_example", "type": f"identity.verification_session.{status}", "livemode": livemode,
        "data": {"object": {"id": "vs_example", "object": "identity.verification_session",
                            "status": status, "metadata": {"tenant_id": "1", "candidate_id": "2", "check_id": "3"}}},
    }


def signed(body, timestamp=NOW):
    digest = hmac.new(WEBHOOK_SECRET.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_unconfigured_provider_fails_closed(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    empty = StripeIdentityProvider.from_env()
    assert not empty.is_configured
    with pytest.raises(ProviderError, match="not configured"):
        empty.create_verification_session(tenant_id="1", candidate_id="2", check_id="3",
                                          return_url="https://vetra.example/return", idempotency_key="check-3")
    with pytest.raises(ProviderError, match="not configured"):
        empty.verify_webhook(b"{}", "")
    assert not StripeIdentityProvider("sk_live_example", "").is_configured
    assert not StripeIdentityProvider("pk_live_example", WEBHOOK_SECRET).is_configured


@pytest.mark.parametrize("status", ["verified", "requires_input", "processing", "canceled"])
def test_valid_signed_status_event_preserves_provider_payload(status):
    payload = event(status)
    body = json.dumps(payload).encode()
    assert provider().verify_webhook(body, signed(body), now=NOW) == payload


@pytest.mark.parametrize("header", ["", "t=abc,v1=nope", "t=1,t=2,v1=nope", "v1=abc", "t=1", "t=1,bad"])
def test_malformed_signature_rejected(header):
    with pytest.raises(ProviderError):
        provider().verify_webhook(b"{}", header, now=NOW)


def test_tampered_event_rejected_before_parsing(monkeypatch):
    body = json.dumps(event()).encode()
    def unexpected_parse(*args, **kwargs):
        raise AssertionError("Unauthenticated JSON must never be parsed")
    monkeypatch.setattr("vetra.providers.json.loads", unexpected_parse)
    with pytest.raises(ProviderError, match="signature"):
        provider().verify_webhook(body + b"tampered", signed(body), now=NOW)


@pytest.mark.parametrize("offset", [-301, 301])
def test_expired_and_future_signed_events_rejected(offset):
    body = json.dumps(event()).encode()
    with pytest.raises(ProviderError, match="window"):
        provider().verify_webhook(body, signed(body, NOW + offset), now=NOW)


def test_signature_rotation_accepts_any_v1_signature():
    body = json.dumps(event()).encode()
    header = signed(body) + ",v1=" + "0" * 64
    assert provider().verify_webhook(body, header, now=NOW)["id"] == "evt_example"


@pytest.mark.parametrize("body", [b"not JSON", b"[]", b'{}', b'{"id":"evt_example","type":"unknown","data":{}}'])
def test_signed_malformed_body_rejected(body):
    with pytest.raises(ProviderError, match="event"):
        provider().verify_webhook(body, signed(body), now=NOW)


def test_test_events_cannot_be_accepted_by_live_provider():
    body = json.dumps(event(livemode=False)).encode()
    with pytest.raises(ProviderError, match="event"):
        provider().verify_webhook(body, signed(body), now=NOW)
    sandbox = StripeIdentityProvider("sk_test_example", WEBHOOK_SECRET)
    assert sandbox.is_configured and not sandbox.is_live
    assert sandbox.verify_webhook(body, signed(body), now=NOW)["livemode"] is False


class Response:
    status = 200

    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return json.dumps(self.data).encode()[:size]


class Opener:
    def __init__(self, data):
        self.data = data
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        return Response(self.data)


def session(**overrides):
    return {
        "id": "vs_example", "object": "identity.verification_session", "status": "requires_input",
        "url": "https://verify.stripe.com/start/example", "livemode": True,
        "metadata": {"tenant_id": "1", "candidate_id": "2", "check_id": "3"}, **overrides,
    }


def create(adapter, **overrides):
    return adapter.create_verification_session(**{
        "tenant_id": "1", "candidate_id": "2", "check_id": "3",
        "return_url": "https://vetra.example/return", "idempotency_key": "vetra-check-3", **overrides,
    })


def test_create_sends_document_selfie_and_bound_metadata():
    transport = Opener(session())
    result = create(provider(opener=transport))
    request = transport.requests[0]
    fields = parse_qs(request.data.decode())
    assert request.full_url == StripeIdentityProvider.API_URL
    assert fields["type"] == ["document"]
    assert fields["options[document][require_matching_selfie]"] == ["true"]
    assert fields["metadata[tenant_id]"] == ["1"]
    assert fields["metadata[candidate_id]"] == ["2"]
    assert fields["metadata[check_id]"] == ["3"]
    assert request.get_header("Idempotency-key") == "vetra-check-3"
    assert result == {"id": "vs_example", "url": "https://verify.stripe.com/start/example",
                      "status": "requires_input", "livemode": True}


@pytest.mark.parametrize("url", ["http://vetra.example", "https://user:secret@vetra.example", "https://", "https://vetra.example:444/", "https://vetra.example/\n"])
def test_unsafe_return_urls_rejected_without_network(url):
    transport = Opener(session())
    with pytest.raises(ProviderError, match="HTTPS"):
        create(provider(opener=transport), return_url=url)
    assert transport.requests == []


@pytest.mark.parametrize("overrides", [
    {"url": "https://evil.example/start"}, {"url": "http://verify.stripe.com/start"},
    {"url": "https://verify.stripe.com.evil.example/start"}, {"status": "verified"},
    {"metadata": {"tenant_id": "other"}}, {"id": "../secrets"}, {"livemode": False},
])
def test_invalid_provider_response_is_rejected(overrides):
    with pytest.raises(ProviderError, match="invalid session"):
        create(provider(opener=Opener(session(**overrides))))


def test_http_failure_does_not_expose_secrets():
    class Failure:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, 401, "sk_live_sensitivesecret", {}, None)
    with pytest.raises(ProviderError, match="request failed") as error:
        create(provider(opener=Failure()))
    assert "sensitivesecret" not in str(error.value)


def test_cancellation_and_redaction_are_idempotent_requests():
    cancel_transport = Opener(session(status="canceled"))
    adapter = provider(opener=cancel_transport)
    assert adapter.cancel_verification_session("vs_example")["status"] == "canceled"
    assert cancel_transport.requests[0].full_url.endswith("/vs_example/cancel")
    redact_transport = Opener(session(redaction={"status": "processing"}))
    assert provider(opener=redact_transport).redact_verification_session("vs_example")["redaction"] == {"status": "processing"}
    assert redact_transport.requests[0].full_url.endswith("/vs_example/redact")


def test_demo_and_disconnected_background_capabilities_never_attest():
    result = DemoProvider.sample_result()
    assert result["sample"] and not result["attestation"] and result["status"] != "verified"
    assert not DemoProvider.is_configured
    with pytest.raises(ProviderError):
        DemoProvider().create_verification_session()
    assert all(not entry["connected"] for entry in BACKGROUND_CHECK_CAPABILITIES.values())
