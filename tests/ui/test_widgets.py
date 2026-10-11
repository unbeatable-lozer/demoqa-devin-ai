import re

import pytest
from healing import expect

from pages.widgets import AccordionPage, ProgressBarPage, SelectMenuPage, SliderPage, TabsPage, ToolTipsPage

pytestmark = pytest.mark.ui


class TestAccordion:
    def test_first_section_open_by_default(self, page):
        acc = AccordionPage(page).open()
        expect(acc.body("What is Lorem Ipsum?")).to_be_visible()
        expect(acc.body("Where does it come from?")).to_be_hidden()

    def test_expand_another_section(self, page):
        acc = AccordionPage(page).open()
        acc.header("Where does it come from?").click()
        expect(acc.body("Where does it come from?")).to_be_visible()
        expect(acc.header("Where does it come from?")).to_have_attribute("aria-expanded", "true")


class TestProgressBar:
    def test_progress_reaches_100_and_resets(self, page):
        pb = ProgressBarPage(page).open()
        expect(pb.bar).to_have_attribute("aria-valuenow", "0")
        pb.start_stop.click()
        expect(pb.bar).to_have_attribute("aria-valuenow", "100", timeout=20_000)
        expect(pb.bar).to_have_class(re.compile("bg-success"))
        page.click("#resetButton")
        expect(pb.bar).to_have_attribute("aria-valuenow", "0")

    def test_stop_pauses_progress(self, page):
        pb = ProgressBarPage(page).open()
        pb.start_stop.click()
        expect(pb.bar).not_to_have_attribute("aria-valuenow", "0")
        pb.start_stop.click()
        expect(pb.start_stop).to_have_text("Start")
        paused = pb.bar.get_attribute("aria-valuenow")
        page.wait_for_timeout(1000)
        expect(pb.bar).to_have_attribute("aria-valuenow", paused)
        assert int(paused) < 100


class TestSlider:
    @pytest.mark.parametrize("value", [0, 60, 100])
    def test_set_slider_value(self, page, value):
        sl = SliderPage(page).open()
        sl.set_value(value)
        expect(sl.value_box).to_have_value(str(value))


class TestTabs:
    def test_switch_tabs(self, page):
        tabs = TabsPage(page).open()
        expect(tabs.pane("what")).to_be_visible()
        tabs.tab("origin").click()
        expect(tabs.tab("origin")).to_have_attribute("aria-selected", "true")
        expect(tabs.pane("origin")).to_be_visible()
        expect(tabs.pane("what")).to_be_hidden()

    def test_more_tab_disabled(self, page):
        expect(TabsPage(page).open().tab("more")).to_be_disabled()


class TestToolTips:
    def test_button_tooltip(self, page):
        tt = ToolTipsPage(page).open()
        tt.hover_button()
        expect(tt.tooltip).to_have_text("You hovered over the Button")


class TestSelectMenu:
    def test_old_style_select(self, page):
        sm = SelectMenuPage(page).open()
        sm.old_select.select_option(label="Purple")
        expect(sm.old_select.locator("option:checked")).to_have_text("Purple")

    def test_multi_select(self, page):
        sm = SelectMenuPage(page).open()
        sm.cars.select_option(["volvo", "audi"])
        expect(sm.cars).to_have_values(["volvo", "audi"])
