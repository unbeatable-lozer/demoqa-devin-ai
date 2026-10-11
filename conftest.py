import re

import pytest
from playwright.sync_api import Page, expect

from healing import HealingPage

pytest_plugins = ["healing.plugin"]

AD_HOSTS = re.compile(
    r"(googlesyndication|doubleclick|googletagservices|adservice\.google|"
    r"google-analytics|googletagmanager|adsrvr|pubmatic|rubiconproject|"
    r"amazon-adsystem|criteo|taboola|outbrain|moatads|ezoic|adnxs)"
)

expect.set_options(timeout=10_000)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1920, "height": 1080}}


@pytest.fixture
def page(page: Page) -> HealingPage:
    """Every selector used through this page heals itself when it stops matching."""
    return HealingPage(page)


@pytest.fixture(autouse=True)
def block_ads(page: HealingPage):
    """demoqa.com serves heavy ads that slow pages and overlay buttons."""
    page.route(AD_HOSTS, lambda route: route.abort())
    page.set_default_timeout(15_000)
    yield


@pytest.fixture(scope="session")
def api(playwright, base_url):
    from utils.api_client import BookStoreApi

    ctx = playwright.request.new_context(base_url=base_url)
    yield BookStoreApi(ctx)
    ctx.dispose()


@pytest.fixture
def new_user(api):
    """Registers a throwaway account and deletes it after the test."""
    username, password = api.random_credentials()
    resp = api.create_user(username, password)
    assert resp.status == 201, resp.text()
    user_id = resp.json()["userID"]
    token = api.generate_token(username, password).json()["token"]
    yield {"username": username, "password": password, "user_id": user_id, "token": token}
    api.delete_user(user_id, token)
