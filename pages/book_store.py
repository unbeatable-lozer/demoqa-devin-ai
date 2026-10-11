from playwright.sync_api import Locator

from pages.base_page import BasePage


class LoginPage(BasePage):
    path = "/login"

    def login(self, username: str, password: str):
        self.page.fill("#userName", username)
        self.page.fill("#password", password)
        self.page.click("#login")

    @property
    def error(self) -> Locator:
        return self.page.locator("#output #name")


class BooksPage(BasePage):
    path = "/books"

    def search(self, text: str):
        self.page.fill("#searchBox", text)

    @property
    def book_links(self) -> Locator:
        return self.page.locator("[id^='see-book-']")

    def open_book(self, title: str):
        self.page.locator(f"[id='see-book-{title}'] a").click()

    def detail(self, field: str) -> Locator:
        return self.page.locator(f"#{field}-wrapper #userName-value")


class ProfilePage(BasePage):
    path = "/profile"

    @property
    def username(self) -> Locator:
        return self.page.locator("#userName-value")
