"""DPDP erasure reaches ingest-ml (S1-INGEST-security M5, NFR-PRIV-03)."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from accounts.models import ConsentPurpose
from accounts.services import give_consent, purge_account, soft_delete_account, withdraw_consent

pytestmark = pytest.mark.django_db(transaction=True)


def test_withdrawing_activity_sharing_erases_ingest_data(user, ingest_deletions):
    give_consent(user, ConsentPurpose.ACTIVITY_SHARING)
    withdraw_consent(user, ConsentPurpose.ACTIVITY_SHARING)
    assert ingest_deletions == [str(user.pk)]


def test_withdrawing_other_purpose_does_not_erase(user, ingest_deletions):
    give_consent(user, ConsentPurpose.EMAIL_DIGEST)
    withdraw_consent(user, ConsentPurpose.EMAIL_DIGEST)
    assert ingest_deletions == []


def test_account_deletion_erases_ingest_data(user, ingest_deletions):
    soft_delete_account(user)
    assert ingest_deletions == [str(user.pk)]


def test_purge_retries_when_ingest_unreachable(user, monkeypatch):
    soft_delete_account(user)
    monkeypatch.setattr("sources.views.delete_ingest_data", lambda uid: False)
    with pytest.raises(RuntimeError):
        purge_account(user.pk)


def test_weak_secrets_refused_outside_local(monkeypatch):
    import core_api.settings as s

    monkeypatch.setattr(s, "JINGLE_ENV", "prod")
    with pytest.raises(ImproperlyConfigured):
        s._check_secrets()
    monkeypatch.setattr(s, "SECRET_KEY", "k" * 40)
    monkeypatch.setattr(s, "SERVICE_TOKEN", "t" * 40)
    monkeypatch.setitem(s.SIMPLE_JWT, "SIGNING_KEY", "j" * 40)
    s._check_secrets()
