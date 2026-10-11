import pytest
from playwright.sync_api import expect

from pages.interactions import DroppablePage, SortablePage

pytestmark = pytest.mark.ui


def test_drag_and_drop(page):
    dp = DroppablePage(page).open()
    expect(dp.simple_target).to_have_text("Drop Here")
    dp.drag_simple()
    expect(dp.simple_target).to_have_text("Dropped!")


def test_sortable_list(page):
    sp = SortablePage(page).open()
    expect(sp.items).to_have_text(["One", "Two", "Three", "Four", "Five", "Six"])
    sp.move("One", "Three")
    expect(sp.items).to_have_text(["Two", "Three", "One", "Four", "Five", "Six"])
