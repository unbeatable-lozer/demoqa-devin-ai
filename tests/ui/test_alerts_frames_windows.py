import pytest
from healing import expect

from pages.alerts_frames_windows import (
    AlertsPage, BrowserWindowsPage, FramesPage, ModalDialogsPage, NestedFramesPage,
)

pytestmark = pytest.mark.ui


class TestBrowserWindows:
    @pytest.mark.parametrize("button_id", ["tabButton", "windowButton"])
    def test_new_tab_and_window(self, page, button_id):
        popup = BrowserWindowsPage(page).open().open_popup(button_id)
        assert popup.url.endswith("/sample")
        expect(popup.locator("#sampleHeading")).to_have_text("This is a sample page")
        popup.close()


class TestAlerts:
    def test_simple_alert(self, page):
        d = AlertsPage(page).open().trigger("alertButton")
        assert d["type"] == "alert"
        assert d["message"] == "You clicked a button"

    def test_timed_alert(self, page):
        d = AlertsPage(page).open().trigger("timerAlertButton")
        assert d["message"] == "This alert appeared after 5 seconds"

    @pytest.mark.parametrize("accept, result", [(True, "Ok"), (False, "Cancel")])
    def test_confirm(self, page, accept, result):
        ap = AlertsPage(page).open()
        d = ap.trigger("confirmButton", accept=accept)
        assert d["type"] == "confirm"
        expect(ap.confirm_result).to_have_text(f"You selected {result}")

    def test_prompt(self, page):
        ap = AlertsPage(page).open()
        d = ap.trigger("promtButton", prompt_text="Playwright")
        assert d["type"] == "prompt"
        expect(ap.prompt_result).to_have_text("You entered Playwright")

    def test_prompt_dismissed_shows_no_result(self, page):
        ap = AlertsPage(page).open()
        ap.trigger("promtButton", accept=False)
        expect(ap.prompt_result).to_have_count(0)


class TestFrames:
    @pytest.mark.parametrize("frame_id", ["frame1", "frame2"])
    def test_frame_content(self, page, frame_id):
        expect(FramesPage(page).open().heading(frame_id)).to_have_text("This is a sample page")

    def test_nested_frames(self, page):
        nf = NestedFramesPage(page).open()
        expect(nf.parent_body).to_contain_text("Parent frame")
        expect(nf.child_body).to_contain_text("Child Iframe")


class TestModalDialogs:
    @pytest.mark.parametrize("size, text", [("Small", "small modal"), ("Large", "Lorem Ipsum")])
    def test_open_and_close_modal(self, page, size, text):
        md = ModalDialogsPage(page).open()
        md.open_modal(size)
        expect(md.dialog).to_be_visible()
        expect(md.dialog).to_contain_text(text)
        md.close_modal(size)
        expect(md.dialog).to_be_hidden()
