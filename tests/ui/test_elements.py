import re

import pytest
from playwright.sync_api import expect

from pages.elements import (
    ButtonsPage, CheckBoxPage, DynamicPropertiesPage, RadioButtonPage,
    TextBoxPage, UploadDownloadPage, WebTablesPage,
)

pytestmark = pytest.mark.ui


class TestTextBox:
    @pytest.mark.smoke
    def test_submit_shows_entered_data(self, page):
        tb = TextBoxPage(page).open()
        tb.submit("Jane Doe", "jane@example.com", "1 Main St", "2 Side Ave")
        expect(tb.output("name")).to_have_text("Name:Jane Doe")
        expect(tb.output("email")).to_have_text("Email:jane@example.com")
        expect(tb.output("currentAddress")).to_contain_text("1 Main St")
        expect(tb.output("permanentAddress")).to_contain_text("2 Side Ave")

    @pytest.mark.parametrize("email", ["plainaddress", "user@", "@domain.com"])
    def test_invalid_email_is_flagged(self, page, email):
        tb = TextBoxPage(page).open()
        tb.submit("Jane", email, "", "")
        expect(tb.email_input).to_have_class(re.compile(r"field-error"))
        expect(tb.output("email")).to_have_count(0)


class TestCheckBox:
    def test_checking_child_marks_parent_partial(self, page):
        cb = CheckBoxPage(page).open()
        cb.expand("Home")
        cb.toggle("Desktop")
        expect(cb.checkbox("Desktop")).to_have_attribute("aria-checked", "true")
        expect(cb.checkbox("Home")).to_have_attribute("aria-checked", "mixed")
        expect(page.locator("#result .text-success")).to_have_text(["desktop", "notes", "commands"])

    def test_checking_root_selects_everything(self, page):
        cb = CheckBoxPage(page).open()
        cb.toggle("Home")
        expect(cb.checkbox("Home")).to_have_attribute("aria-checked", "true")
        expect(page.locator("#result")).to_contain_text("home")
        expect(page.locator("#result")).to_contain_text("downloads")

    def test_uncheck_clears_result(self, page):
        cb = CheckBoxPage(page).open()
        cb.toggle("Home")
        cb.toggle("Home")
        expect(cb.checkbox("Home")).to_have_attribute("aria-checked", "false")
        expect(page.locator("#result")).to_have_count(0)


class TestRadioButton:
    @pytest.mark.parametrize("option_id, label", [("yesRadio", "Yes"), ("impressiveRadio", "Impressive")])
    def test_select_option(self, page, option_id, label):
        rb = RadioButtonPage(page).open()
        rb.select(option_id)
        expect(rb.radio(option_id)).to_be_checked()
        expect(rb.result).to_have_text(label)

    def test_no_option_is_disabled(self, page):
        rb = RadioButtonPage(page).open()
        expect(rb.radio("noRadio")).to_be_disabled()


class TestWebTables:
    def test_default_rows(self, page):
        wt = WebTablesPage(page).open()
        expect(wt.rows).to_have_count(3)
        expect(wt.row_with("cierra@example.com")).to_contain_text("Cierra")

    @pytest.mark.smoke
    def test_add_record(self, page):
        wt = WebTablesPage(page).open()
        wt.add_record("Ada", "Lovelace", "ada@example.com", 36, 9000, "Engineering")
        expect(wt.modal).to_be_hidden()
        row = wt.row_with("ada@example.com")
        expect(row).to_have_count(1)
        expect(row.locator("td")).to_contain_text(["Ada", "Lovelace", "36", "ada@example.com", "9000", "Engineering"])

    def test_add_record_requires_fields(self, page):
        wt = WebTablesPage(page).open()
        page.get_by_role("button", name="Add").click()
        page.click("#submit")
        expect(wt.modal).to_be_visible()
        expect(page.locator("#userForm")).to_have_class(re.compile("was-validated"))

    def test_edit_record(self, page):
        wt = WebTablesPage(page).open()
        wt.edit_record(1, salary=55555, department="QA")
        row = wt.row_with("cierra@example.com")
        expect(row).to_contain_text("55555")
        expect(row).to_contain_text("QA")

    def test_delete_record(self, page):
        wt = WebTablesPage(page).open()
        wt.delete_record(2)
        expect(wt.rows).to_have_count(2)
        expect(wt.row_with("alden@example.com")).to_have_count(0)

    @pytest.mark.parametrize("term, expected", [("Compliance", "Alden"), ("kierra", "Kierra"), ("29", "Kierra")])
    def test_search(self, page, term, expected):
        wt = WebTablesPage(page).open()
        wt.search(term)
        expect(wt.rows).to_have_count(1)
        expect(wt.rows.first).to_contain_text(expected)


class TestButtons:
    @pytest.mark.parametrize("action, kind, text", [
        ("double_click", "double", "You have done a double click"),
        ("right_click", "right", "You have done a right click"),
        ("dynamic_click", "dynamic", "You have done a dynamic click"),
    ])
    def test_click_types(self, page, action, kind, text):
        bp = ButtonsPage(page).open()
        getattr(bp, action)()
        expect(bp.message(kind)).to_have_text(text)

    def test_single_click_does_not_trigger_double_click(self, page):
        bp = ButtonsPage(page).open()
        page.click("#doubleClickBtn")
        expect(bp.message("double")).to_have_count(0)


class TestDynamicProperties:
    def test_button_enables_after_5_seconds(self, page):
        dp = DynamicPropertiesPage(page).open()
        expect(dp.enable_after).to_be_disabled()
        expect(dp.enable_after).to_be_enabled(timeout=8_000)

    def test_button_becomes_visible_after_5_seconds(self, page):
        dp = DynamicPropertiesPage(page).open()
        expect(dp.visible_after).to_have_count(0)
        expect(dp.visible_after).to_be_visible(timeout=8_000)

    def test_button_changes_color(self, page):
        dp = DynamicPropertiesPage(page).open()
        expect(dp.color_change).to_have_class(re.compile("text-danger"), timeout=8_000)


class TestUploadDownload:
    def test_upload_file(self, page, tmp_path):
        f = tmp_path / "resume.txt"
        f.write_text("hello demoqa")
        ud = UploadDownloadPage(page).open()
        ud.upload(f)
        expect(ud.uploaded_path).to_have_text(r"C:\fakepath\resume.txt")

    def test_download_file(self, page, tmp_path):
        ud = UploadDownloadPage(page).open()
        download = ud.download()
        assert download.suggested_filename == "sampleFile.jpeg"
        target = tmp_path / download.suggested_filename
        download.save_as(target)
        assert target.stat().st_size > 0
