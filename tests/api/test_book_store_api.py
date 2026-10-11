import pytest

pytestmark = pytest.mark.api

GIT_POCKET_GUIDE = "9781449325862"
SPEAKING_JS = "9781449365035"


@pytest.mark.smoke
def test_get_all_books(api):
    resp = api.get_books()
    assert resp.ok
    books = resp.json()["books"]
    assert len(books) >= 8
    for book in books:
        assert {"isbn", "title", "author", "publisher", "pages"} <= book.keys()


def test_get_book_by_isbn(api):
    resp = api.get_book(GIT_POCKET_GUIDE)
    assert resp.ok
    body = resp.json()
    assert body["title"] == "Git Pocket Guide"
    assert body["author"] == "Richard E. Silverman"


def test_get_book_with_unknown_isbn_returns_400(api):
    resp = api.get_book("0000000000000")
    assert resp.status == 400
    assert resp.json()["code"] == "1205"


def test_authorized_with_unknown_user(api):
    resp = api.authorized("nobody_does_not_exist_42", "Wrong@123")
    assert resp.status == 404
    assert resp.json()["message"] == "User not found!"


def test_create_user_with_weak_password_rejected(api):
    username, _ = api.random_credentials()
    resp = api.create_user(username, "weak")
    assert resp.status == 400
    assert "Passwords must have" in resp.json()["message"]


def test_create_duplicate_user_rejected(api, new_user):
    resp = api.create_user(new_user["username"], new_user["password"])
    assert resp.status == 406
    assert resp.json()["message"] == "User exists!"


def test_generate_token_and_authorize(api, new_user):
    resp = api.generate_token(new_user["username"], new_user["password"])
    assert resp.ok
    assert resp.json()["status"] == "Success"
    assert api.authorized(new_user["username"], new_user["password"]).json() is True


def test_get_user_requires_auth(api, new_user):
    resp = api.get_user(new_user["user_id"], "invalid-token")
    assert resp.status == 401


def test_add_and_remove_books_from_collection(api, new_user):
    uid, token = new_user["user_id"], new_user["token"]

    resp = api.add_books(uid, [GIT_POCKET_GUIDE, SPEAKING_JS], token)
    assert resp.status == 201, resp.text()

    isbns = {b["isbn"] for b in api.get_user(uid, token).json()["books"]}
    assert isbns == {GIT_POCKET_GUIDE, SPEAKING_JS}

    assert api.delete_book(uid, GIT_POCKET_GUIDE, token).status == 204
    isbns = {b["isbn"] for b in api.get_user(uid, token).json()["books"]}
    assert isbns == {SPEAKING_JS}
