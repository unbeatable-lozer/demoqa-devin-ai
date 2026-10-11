import re

import pytest
from healing import expect

from pages.forms import PracticeFormPage, Student

pytestmark = pytest.mark.ui


@pytest.fixture
def form(page):
    return PracticeFormPage(page).open()


@pytest.mark.smoke
def test_submit_full_form(form, tmp_path):
    picture = tmp_path / "avatar.png"
    picture.write_bytes(b"\x89PNG\r\n\x1a\n")
    s = Student(
        first_name="John", last_name="Doe", email="john.doe@example.com", gender="Male",
        mobile="0123456789", subjects=["Maths", "English"], hobbies=["Sports", "Music"],
        address="221B Baker Street", state="NCR", city="Delhi", picture=str(picture),
    )
    form.fill(s)
    form.submit()

    expect(form.modal_title).to_have_text("Thanks for submitting the form")
    expect(form.result("Student Name")).to_have_text("John Doe")
    expect(form.result("Student Email")).to_have_text("john.doe@example.com")
    expect(form.result("Gender")).to_have_text("Male")
    expect(form.result("Mobile")).to_have_text("0123456789")
    expect(form.result("Subjects")).to_have_text("Maths, English")
    expect(form.result("Hobbies")).to_have_text("Sports, Music")
    expect(form.result("Picture")).to_have_text("avatar.png")
    expect(form.result("Address")).to_have_text("221B Baker Street")
    expect(form.result("State and City")).to_have_text("NCR Delhi")

    form.close_modal(via_button=False)
    expect(form.modal_title).to_be_hidden()


@pytest.mark.xfail(reason="Known demoqa bug: the modal's Close button does not dismiss it", strict=False)
def test_close_button_dismisses_modal(form):
    form.fill(Student(first_name="Ana", last_name="Lee", email="", gender="Female", mobile="9876543210"))
    form.submit()
    expect(form.modal_title).to_be_visible()
    form.close_modal()
    expect(form.modal_title).to_be_hidden(timeout=3_000)


def test_submit_required_fields_only(form):
    form.fill(Student(first_name="Ana", last_name="Lee", email="", gender="Female", mobile="9876543210"))
    form.submit()
    expect(form.modal_title).to_be_visible()
    expect(form.result("Student Name")).to_have_text("Ana Lee")
    expect(form.result("Gender")).to_have_text("Female")


def test_empty_form_is_not_submitted(form, page):
    form.submit()
    expect(page.locator("#userForm")).to_have_class(re.compile("was-validated"))
    expect(form.modal_title).to_have_count(0)
    for field in ("#firstName", "#lastName", "#userNumber"):
        assert page.locator(field).evaluate("e => e.matches(':invalid')")


@pytest.mark.parametrize("mobile", ["12345", "abcdefghij"])
def test_invalid_mobile_is_rejected(form, page, mobile):
    form.fill(Student(first_name="Ana", last_name="Lee", email="", gender="Other", mobile=mobile))
    form.submit()
    expect(form.modal_title).to_have_count(0)
    assert page.locator("#userNumber").evaluate("e => e.matches(':invalid')")
