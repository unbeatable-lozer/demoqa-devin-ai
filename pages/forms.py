from dataclasses import dataclass, field

from playwright.sync_api import Locator

from pages.base_page import BasePage


@dataclass
class Student:
    first_name: str
    last_name: str
    email: str
    gender: str
    mobile: str
    subjects: list = field(default_factory=list)
    hobbies: list = field(default_factory=list)
    address: str = ""
    state: str = ""
    city: str = ""
    picture: str | None = None


class PracticeFormPage(BasePage):
    path = "/automation-practice-form"

    def fill(self, s: Student):
        p = self.page
        p.fill("#firstName", s.first_name)
        p.fill("#lastName", s.last_name)
        p.fill("#userEmail", s.email)
        p.locator("#genterWrapper label").get_by_text(s.gender, exact=True).click()
        p.fill("#userNumber", s.mobile)
        for subject in s.subjects:
            p.fill("#subjectsInput", subject)
            p.locator("[id^=react-select-2-option]", has_text=subject).first.click()
        for hobby in s.hobbies:
            p.locator("#hobbiesWrapper label").get_by_text(hobby, exact=True).click()
        if s.picture:
            p.set_input_files("#uploadPicture", s.picture)
        p.fill("#currentAddress", s.address)
        if s.state:
            p.fill("#react-select-3-input", s.state)
            p.keyboard.press("Enter")
        if s.city:
            p.fill("#react-select-4-input", s.city)
            p.keyboard.press("Enter")

    def submit(self):
        self.page.click("#submit")

    @property
    def modal_title(self) -> Locator:
        return self.page.locator("#example-modal-sizes-title-lg")

    def result(self, label: str) -> Locator:
        return self.page.locator(".modal-content tr", has=self.page.locator(f"td:text-is('{label}')")).locator("td").nth(1)

    def close_modal(self, via_button: bool = True):
        if via_button:
            self.page.click("#closeLargeModal")
        else:
            self.page.keyboard.press("Escape")
