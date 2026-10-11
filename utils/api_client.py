import uuid

from playwright.sync_api import APIRequestContext, APIResponse


class BookStoreApi:
    """Thin wrapper around the demoqa Book Store REST API."""

    def __init__(self, request: APIRequestContext):
        self.request = request

    # Books
    def get_books(self) -> APIResponse:
        return self.request.get("/BookStore/v1/Books")

    def get_book(self, isbn: str) -> APIResponse:
        return self.request.get("/BookStore/v1/Book", params={"ISBN": isbn})

    def add_books(self, user_id: str, isbns: list[str], token: str) -> APIResponse:
        return self.request.post(
            "/BookStore/v1/Books",
            data={"userId": user_id, "collectionOfIsbns": [{"isbn": i} for i in isbns]},
            headers=self._auth(token),
        )

    def delete_book(self, user_id: str, isbn: str, token: str) -> APIResponse:
        return self.request.delete(
            "/BookStore/v1/Book", data={"userId": user_id, "isbn": isbn}, headers=self._auth(token)
        )

    # Account
    def create_user(self, username: str, password: str) -> APIResponse:
        return self.request.post("/Account/v1/User", data={"userName": username, "password": password})

    def generate_token(self, username: str, password: str) -> APIResponse:
        return self.request.post("/Account/v1/GenerateToken", data={"userName": username, "password": password})

    def authorized(self, username: str, password: str) -> APIResponse:
        return self.request.post("/Account/v1/Authorized", data={"userName": username, "password": password})

    def get_user(self, user_id: str, token: str) -> APIResponse:
        return self.request.get(f"/Account/v1/User/{user_id}", headers=self._auth(token))

    def delete_user(self, user_id: str, token: str) -> APIResponse:
        return self.request.delete(f"/Account/v1/User/{user_id}", headers=self._auth(token))

    @staticmethod
    def _auth(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def random_credentials() -> tuple[str, str]:
        return f"qa_{uuid.uuid4().hex[:10]}", f"Qa!{uuid.uuid4().hex[:8]}A1"
