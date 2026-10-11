from playwright.sync_api import Page

from healing import HealingPage


class BasePage:
    path = "/"

    def __init__(self, page: Page):
        self.page = page if isinstance(page, HealingPage) else HealingPage(page)

    def open(self):
        self.page.goto(self.path, wait_until="load")
        return self
