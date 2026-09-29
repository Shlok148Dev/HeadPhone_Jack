import pytest

from accounts.models import User
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "url",
    ["/admin/accounts/user/", "/admin/accounts/consent/", "/admin/core_api/featureflag/",
     "/admin/accounts/user/add/"],
)
def test_admin_pages_render(client, url):
    admin = User.objects.create_superuser(username="Root_Admin", email="Root@Example.test",
                                          password="x-very-long-pass-1")
    assert admin.username == "root_admin" and admin.email == "root@example.test"
    client.force_login(admin)
    assert client.get(url).status_code == 200


def test_admin_user_change_page(client):
    admin = User.objects.create_superuser(username="boss", email="boss@example.test",
                                          password="x-very-long-pass-1")
    other = UserFactory()
    client.force_login(admin)
    assert client.get(f"/admin/accounts/user/{other.pk}/change/").status_code == 200
