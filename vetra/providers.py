"""Identity provider adapters; no OSINT or demo result is an identity attestation.

Stripe protocol references: https://docs.stripe.com/api/identity/verification_sessions
and https://docs.stripe.com/webhooks/signature. No third-party code is vendored here.
"""

import hashlib
import hmac
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ProviderError(RuntimeError):
    """Sanitized provider failure, safe to expose without credentials or documents."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward provider credentials through an API redirect.
        return None


class StripeIdentityProvider:
    """Hosted document verification with signed webhook verification.

    ``verify_webhook`` authenticates the raw bytes before decoding JSON. The caller
    must persist event IDs for replay deduplication and match the session ID and
    metadata to its tenant, candidate and check before accepting any result.
    """

    API_URL = "https://api.stripe.com/v1/identity/verification_sessions"
    MAX_RESPONSE_BYTES = 1024 * 1024
    WEBHOOK_TOLERANCE_SECONDS = 300

    def __init__(self, secret_key="", webhook_secret="", *, timeout=15, opener=None):
        self._secret_key = secret_key.strip()
        self._webhook_secret = webhook_secret.strip()
        self._timeout = timeout
        self._opener = opener or build_opener(_NoRedirect())

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("STRIPE_SECRET_KEY", ""), os.environ.get("STRIPE_WEBHOOK_SECRET", ""))

    @property
    def is_configured(self):
        return bool(
            re.fullmatch(r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]+", self._secret_key)
            and re.fullmatch(r"whsec_[A-Za-z0-9]+", self._webhook_secret)
        )

    @property
    def is_live(self):
        return self.is_configured and self._secret_key.startswith(("sk_live_", "rk_live_"))

    def _require_configured(self):
        if not self.is_configured:
            raise ProviderError("Stripe Identity is not configured.")

    @staticmethod
    def _valid_https_url(value, *, hosted=False):
        if not isinstance(value, str) or any(ord(c) < 32 or c.isspace() for c in value):
            return False
        try:
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                return False
            if parsed.port not in (None, 443) or parsed.fragment:
                return False
            return not hosted or parsed.hostname == "verify.stripe.com"
        except ValueError:
            return False

    def _post(self, url, fields, *, idempotency_key):
        self._require_configured()
        if not isinstance(idempotency_key, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,255}", idempotency_key):
            raise ProviderError("A valid idempotency key is required.")
        request = Request(
            url,
            data=urlencode(fields).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + self._secret_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "Idempotency-Key": idempotency_key,
                "User-Agent": "Vetra-Identity/0.1",
            },
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                if response.status != 200:
                    raise ProviderError("Stripe Identity request failed.")
                raw = response.read(self.MAX_RESPONSE_BYTES + 1)
        except (HTTPError, URLError, OSError, TimeoutError):
            raise ProviderError("Stripe Identity request failed.") from None
        if len(raw) > self.MAX_RESPONSE_BYTES:
            raise ProviderError("Stripe Identity returned an invalid response.")
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise ProviderError("Stripe Identity returned an invalid response.") from None
        if not isinstance(result, dict) or result.get("object") != "identity.verification_session":
            raise ProviderError("Stripe Identity returned an invalid session.")
        return result

    def create_verification_session(self, *, tenant_id, candidate_id, check_id, return_url, idempotency_key):
        self._require_configured()
        metadata = {"tenant_id": str(tenant_id), "candidate_id": str(candidate_id), "check_id": str(check_id)}
        if any(not value or len(value) > 500 for value in metadata.values()):
            raise ProviderError("Verification metadata is required.")
        if not self._valid_https_url(return_url):
            raise ProviderError("An HTTPS return URL is required.")
        fields = {
            "type": "document",
            "return_url": return_url,
            "options[document][require_matching_selfie]": "true",
            **{f"metadata[{key}]": value for key, value in metadata.items()},
        }
        result = self._post(self.API_URL, fields, idempotency_key=idempotency_key)
        if (
            not self._valid_session_id(result.get("id"))
            or not self._valid_https_url(result.get("url"), hosted=True)
            or result.get("status") != "requires_input"
            or result.get("livemode") is not self.is_live
            or result.get("metadata") != metadata
        ):
            raise ProviderError("Stripe Identity returned an invalid session.")
        # Do not retain document images, extracted identity attributes or secrets.
        return {key: result[key] for key in ("id", "url", "status", "livemode")}

    @staticmethod
    def _valid_session_id(value):
        return isinstance(value, str) and re.fullmatch(r"vs_[A-Za-z0-9]+", value) is not None

    def _session_action(self, session_id, action):
        if not self._valid_session_id(session_id):
            raise ProviderError("A valid Stripe session ID is required.")
        result = self._post(
            f"{self.API_URL}/{session_id}/{action}", {},
            idempotency_key=f"vetra-{action}-{session_id}",
        )
        if result.get("id") != session_id or result.get("livemode") is not self.is_live:
            raise ProviderError("Stripe Identity returned an invalid session.")
        if action == "cancel" and result.get("status") != "canceled":
            raise ProviderError("Stripe Identity could not cancel the session.")
        if action == "redact" and result.get("redaction", {}).get("status") not in ("processing", "redacted"):
            raise ProviderError("Stripe Identity could not request redaction.")
        return {"id": result["id"], "status": result.get("status"), "redaction": result.get("redaction")}

    def cancel_verification_session(self, session_id):
        return self._session_action(session_id, "cancel")

    def redact_verification_session(self, session_id):
        return self._session_action(session_id, "redact")

    def verify_webhook(self, raw_body, signature_header, *, now=None):
        self._require_configured()
        if not isinstance(raw_body, bytes) or len(raw_body) > self.MAX_RESPONSE_BYTES:
            raise ProviderError("Invalid Stripe webhook body.")
        if not isinstance(signature_header, str) or len(signature_header) > 4096:
            raise ProviderError("Invalid Stripe webhook signature.")
        timestamps, signatures = [], []
        for part in signature_header.split(","):
            key, separator, value = part.strip().partition("=")
            if not separator:
                raise ProviderError("Invalid Stripe webhook signature.")
            if key == "t":
                timestamps.append(value)
            elif key == "v1":
                signatures.append(value)
        if len(timestamps) != 1 or not re.fullmatch(r"[0-9]{1,12}", timestamps[0]) or not signatures:
            raise ProviderError("Invalid Stripe webhook signature.")
        timestamp = int(timestamps[0])
        current_time = time.time() if now is None else now
        if abs(current_time - timestamp) > self.WEBHOOK_TOLERANCE_SECONDS:
            raise ProviderError("Stripe webhook timestamp is outside the permitted window.")
        signed_payload = timestamps[0].encode("ascii") + b"." + raw_body
        expected = hmac.new(self._webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        if not any(re.fullmatch(r"[a-fA-F0-9]{64}", supplied) and hmac.compare_digest(expected, supplied.lower())
                   for supplied in signatures):
            raise ProviderError("Invalid Stripe webhook signature.")
        # Parse only after authenticity and freshness have been checked.
        try:
            event = json.loads(raw_body)
        except (ValueError, UnicodeDecodeError):
            raise ProviderError("Invalid Stripe webhook event.") from None
        if (
            not isinstance(event, dict)
            or not isinstance(event.get("id"), str)
            or not re.fullmatch(r"evt_[A-Za-z0-9]+", event["id"])
            or not isinstance(event.get("type"), str)
            or not isinstance(event.get("data"), dict)
            or event.get("livemode") is not self.is_live
        ):
            raise ProviderError("Invalid Stripe webhook event.")
        return event


class DemoProvider:
    """Explicit fictional fixture provider; never produces a verified check."""

    is_configured = False
    is_live = False

    def create_verification_session(self, **kwargs):
        raise ProviderError("Demo data cannot start or attest a real verification.")

    @staticmethod
    def sample_result():
        return {"sample": True, "provider": "Demo only", "status": "not_connected", "attestation": False}


BACKGROUND_CHECK_CAPABILITIES = {
    "employment": {"connected": False, "status": "not_connected"},
    "education": {"connected": False, "status": "not_connected"},
    "criminal_records": {"connected": False, "status": "not_connected"},
    "sanctions": {"connected": False, "status": "not_connected"},
    "right_to_work": {"connected": False, "status": "not_connected"},
}
