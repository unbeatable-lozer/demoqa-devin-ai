from playwright.sync_api import Locator

from pages.base_page import BasePage


class TextBoxPage(BasePage):
    path = "/text-box"

    def submit(self, name: str, email: str, current_address: str, permanent_address: str):
        self.page.fill("#userName", name)
        self.page.fill("#userEmail", email)
        self.page.fill("#currentAddress", current_address)
        self.page.fill("#permanentAddress", permanent_address)
        self.page.click("#submit")

    @property
    def email_input(self) -> Locator:
        return self.page.locator("#userEmail")

    def output(self, field: str) -> Locator:
        return self.page.locator(f"#output #{field}")


class CheckBoxPage(BasePage):
    path = "/checkbox"

    def expand(self, node: str):
        self.page.locator(f"[role=treeitem]:has([title='{node}']) .rc-tree-switcher").click()

    def toggle(self, node: str):
        self.checkbox(node).click()

    def checkbox(self, node: str) -> Locator:
        return self.page.locator(f"[aria-label='Select {node}']")

    def node(self, node: str) -> Locator:
        return self.page.locator(f".rc-tree-title:text-is('{node}')")


class RadioButtonPage(BasePage):
    path = "/radio-button"

    def select(self, option_id: str):
        self.page.click(f"label[for={option_id}]")

    def radio(self, option_id: str) -> Locator:
        return self.page.locator(f"#{option_id}")

    @property
    def result(self) -> Locator:
        return self.page.locator("p .text-success")


class WebTablesPage(BasePage):
    path = "/webtables"

    @property
    def rows(self) -> Locator:
        return self.page.locator("table tbody tr")

    def row_with(self, text: str) -> Locator:
        return self.rows.filter(has_text=text)

    def add_record(self, first, last, email, age, salary, department):
        self.page.get_by_role("button", name="Add").click()
        self.fill_form(first, last, email, age, salary, department)

    def fill_form(self, first=None, last=None, email=None, age=None, salary=None, department=None):
        for field, value in {
            "firstName": first, "lastName": last, "userEmail": email,
            "age": age, "salary": salary, "department": department,
        }.items():
            if value is not None:
                self.page.fill(f"#{field}", str(value))
        self.page.click("#submit")

    def edit_record(self, record_id: int, **fields):
        self.page.click(f"#edit-record-{record_id}")
        self.fill_form(**fields)

    def delete_record(self, record_id: int):
        self.page.click(f"#delete-record-{record_id}")

    def search(self, text: str):
        self.page.fill("#searchBox", text)

    @property
    def modal(self) -> Locator:
        return self.page.locator("#registration-form-modal")


class ButtonsPage(BasePage):
    path = "/buttons"

    def double_click(self):
        self.page.dblclick("#doubleClickBtn")

    def right_click(self):
        self.page.click("#rightClickBtn", button="right")

    def dynamic_click(self):
        self.page.get_by_role("button", name="Click Me", exact=True).click()

    def message(self, kind: str) -> Locator:
        return self.page.locator(f"#{kind}ClickMessage")


class DynamicPropertiesPage(BasePage):
    path = "/dynamic-properties"

    @property
    def enable_after(self) -> Locator:
        return self.page.locator("#enableAfter")

    @property
    def visible_after(self) -> Locator:
        return self.page.locator("#visibleAfter")

    @property
    def color_change(self) -> Locator:
        return self.page.locator("#colorChange")


class UploadDownloadPage(BasePage):
    path = "/upload-download"

    def upload(self, file_path):
        self.page.set_input_files("#uploadFile", file_path)

    @property
    def uploaded_path(self) -> Locator:
        return self.page.locator("#uploadedFilePath")

    def download(self):
        with self.page.expect_download() as info:
            self.page.click("#downloadButton")
        return info.value
