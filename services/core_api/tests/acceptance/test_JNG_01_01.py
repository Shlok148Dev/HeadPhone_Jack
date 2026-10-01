"""JNG-01-01 sign-up age gate (NFR-PRIV-02) and refresh rotation (ADR-0011)."""

from datetime import date

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from rest_framework.test import APIClient

from accounts.models import User
from tests.factories import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

scenarios("../features/ep01/JNG-01-01_sign_up.feature")

COOKIE = "jingle_refresh"


@given(parsers.parse("a visitor born {years:d} years ago"), target_fixture="birth_year")
def visitor(years):
    return date.today().year - years


@when("they sign up with email")
def sign_up(birth_year, ctx):
    ctx["resp"] = APIClient().post(
        "/api/v1/auth/register",
        {
            "email": "teen@example.test",
            "password": "a-long-unique-passphrase-7",
            "username": "teen_listener",
            "birth_year": birth_year,
        },
        format="json",
    )


@then(parsers.parse('the sign-up is rejected with code "{code}"'))
def rejected(ctx, code):
    assert ctx["resp"].status_code == 403
    assert ctx["resp"].json()["error"]["code"] == code


@then("no account is created")
def no_account():
    assert not User.objects.filter(email="teen@example.test").exists()


@given("a signed-in member with a refresh cookie", target_fixture="client")
def signed_in(ctx):
    UserFactory(email="member@example.test")
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login", {"email": "member@example.test", "password": PASSWORD}, format="json"
    )
    assert r.status_code == 200
    ctx["old_refresh"] = r.cookies[COOKIE].value
    ctx["old_access"] = r.json()["access"]
    return client


@when("the web app refreshes the session")
def refresh(client, ctx):
    ctx["resp"] = client.post("/api/v1/auth/refresh")


@then("it receives a new access token and a new refresh cookie")
def new_tokens(ctx):
    resp = ctx["resp"]
    assert resp.status_code == 200
    assert resp.json()["access"] != ctx["old_access"]
    assert resp.cookies[COOKIE].value not in ("", ctx["old_refresh"])
    assert resp.cookies[COOKIE]["httponly"]


@then("the old refresh cookie is rejected")
def old_rejected(ctx):
    client = APIClient()
    client.cookies[COOKIE] = ctx["old_refresh"]
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "REFRESH_INVALID"
