from playwright.sync_api import Page


class BasePage:
    path = "/"

    def __init__(self, page: Page):
        self.page = page

    def open(self):
        self.page.goto(self.path, wait_until="load")
        return self
