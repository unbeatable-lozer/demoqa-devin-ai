from playwright.sync_api import Locator

from pages.base_page import BasePage


class AccordionPage(BasePage):
    path = "/accordian"

    def header(self, title: str) -> Locator:
        return self.page.locator(".accordion-button", has_text=title)

    def body(self, title: str) -> Locator:
        return self.page.locator(".accordion-item", has=self.header(title)).locator(".accordion-collapse")


class ProgressBarPage(BasePage):
    path = "/progress-bar"

    @property
    def bar(self) -> Locator:
        return self.page.locator("#progressBar [role=progressbar]")

    @property
    def start_stop(self) -> Locator:
        return self.page.locator("#start-stop-btn")


class SliderPage(BasePage):
    path = "/slider"

    def set_value(self, value: int):
        slider = self.page.locator("#slider")
        slider.focus()
        current = int(slider.input_value())
        key = "ArrowRight" if value > current else "ArrowLeft"
        for _ in range(abs(value - current)):
            self.page.keyboard.press(key)

    @property
    def value_box(self) -> Locator:
        return self.page.locator("#slider-value-input")


class TabsPage(BasePage):
    path = "/tabs"

    def tab(self, name: str) -> Locator:
        return self.page.locator(f"#demo-tab-{name}")

    def pane(self, name: str) -> Locator:
        return self.page.locator(f"#demo-tabpane-{name}")


class ToolTipsPage(BasePage):
    path = "/tool-tips"

    def hover_button(self, attempts: int = 5):
        # The tooltip handler attaches after hydration, so re-hover until it shows.
        for _ in range(attempts):
            self.page.mouse.move(0, 0)
            self.page.hover("#toolTipButton")
            try:
                self.tooltip.wait_for(state="visible", timeout=2_000)
                return
            except Exception:
                continue

    @property
    def tooltip(self) -> Locator:
        return self.page.locator("#buttonToolTip")


class SelectMenuPage(BasePage):
    path = "/select-menu"

    @property
    def old_select(self) -> Locator:
        return self.page.locator("#oldSelectMenu")

    @property
    def cars(self) -> Locator:
        return self.page.locator("#cars")
