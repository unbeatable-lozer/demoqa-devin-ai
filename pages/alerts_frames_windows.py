from playwright.sync_api import Dialog, Locator, Page

from pages.base_page import BasePage


class BrowserWindowsPage(BasePage):
    path = "/browser-windows"

    def open_popup(self, button_id: str) -> Page:
        with self.page.context.expect_page() as info:
            self.page.click(f"#{button_id}")
        popup = info.value
        popup.wait_for_load_state()
        return popup


class AlertsPage(BasePage):
    path = "/alerts"

    def trigger(self, button_id: str, accept: bool = True, prompt_text: str | None = None) -> Dialog:
        captured = {}

        def handle(dialog: Dialog):
            captured["dialog"] = dialog
            captured["message"] = dialog.message
            captured["type"] = dialog.type
            if accept:
                dialog.accept(prompt_text) if prompt_text is not None else dialog.accept()
            else:
                dialog.dismiss()

        with self.page.expect_event("dialog", timeout=10_000):
            self.page.once("dialog", handle)
            self.page.click(f"#{button_id}")
        return captured

    @property
    def confirm_result(self) -> Locator:
        return self.page.locator("#confirm-result-text")

    @property
    def prompt_result(self) -> Locator:
        return self.page.locator("#promptResult")


class FramesPage(BasePage):
    path = "/frames"

    def heading(self, frame_id: str) -> Locator:
        return self.page.frame_locator(f"#{frame_id}").locator("#sampleHeading")


class NestedFramesPage(BasePage):
    path = "/nestedframes"

    @property
    def parent_body(self) -> Locator:
        return self.page.frame_locator("#frame1").locator("body")

    @property
    def child_body(self) -> Locator:
        return self.page.frame_locator("#frame1").frame_locator("iframe").locator("body")


class ModalDialogsPage(BasePage):
    path = "/modal-dialogs"

    def open_modal(self, size: str):
        self.page.click(f"#show{size}Modal")

    @property
    def dialog(self) -> Locator:
        return self.page.get_by_role("dialog")

    def close_modal(self, size: str):
        self.page.click(f"#close{size}Modal")
