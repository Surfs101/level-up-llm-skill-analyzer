"""Observability — the no-op config, PII redaction, and health check wiring."""

from app.observability import configure_observability, redact_email, scrub_emails


def test_configure_is_a_safe_noop_without_secrets() -> None:
    # No LOGFIRE_TOKEN / SENTRY_DSN in the test env — this must not raise.
    configure_observability("skillbridge-test")

    import logfire

    logfire.info("noop", run_id="abc")  # a no-op, must not raise


def test_redact_email_masks_the_local_part() -> None:
    assert redact_email("jane.doe@example.com") == "j***@example.com"
    assert redact_email("a@b.co") == "a***@b.co"
    assert redact_email("not-an-email") == "[redacted]"


def test_scrub_emails_replaces_addresses_in_free_text() -> None:
    text = "Reach me at bob@corp.io or alice@example.org, thanks!"
    scrubbed = scrub_emails(text)
    assert "bob@corp.io" not in scrubbed
    assert "alice@example.org" not in scrubbed
    assert scrubbed.count("[redacted-email]") == 2


def test_pii_keys_are_registered_for_logfire_scrubbing() -> None:
    from app.observability import _PII_KEY_PATTERNS

    # The resume/JD text and email keys are scrubbed from any span/log (§11).
    assert "email" in _PII_KEY_PATTERNS
    assert "jd_text" in _PII_KEY_PATTERNS
    assert "resume_text_snapshot" in _PII_KEY_PATTERNS
