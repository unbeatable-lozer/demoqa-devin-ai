import pytest
from playwright.sync_api import expect

from pages.book_store import BooksPage, LoginPage, ProfilePage

pytestmark = pytest.mark.ui


def test_invalid_login_shows_error(page):
    lp = LoginPage(page).open()
    lp.login("nobody_does_not_exist_42", "Wrong@1234")
    expect(lp.error).to_have_text("Invalid username or password!")


@pytest.mark.smoke
def test_login_with_api_created_user(page, new_user):
    LoginPage(page).open().login(new_user["username"], new_user["password"])
    expect(page).to_have_url("/profile")
    expect(ProfilePage(page).username).to_have_text(new_user["username"])


def test_search_books(page):
    bp = BooksPage(page).open()
    expect(bp.book_links).to_have_count(8)
    bp.search("JavaScript")
    for title in bp.book_links.all_inner_texts():
        assert "javascript" in title.lower()
    bp.search("no-such-book-xyz")
    expect(bp.book_links).to_have_count(0)


def test_book_details(page):
    bp = BooksPage(page).open()
    bp.open_book("Git Pocket Guide")
    expect(bp.detail("ISBN")).to_have_text("9781449325862")
    expect(bp.detail("title")).to_have_text("Git Pocket Guide")
    expect(bp.detail("author")).to_have_text("Richard E. Silverman")
