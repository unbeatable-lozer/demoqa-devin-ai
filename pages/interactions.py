from playwright.sync_api import Locator

from pages.base_page import BasePage


class DroppablePage(BasePage):
    path = "/droppable"

    def drag_simple(self):
        self.page.locator("#simpleDropContainer #droppable.ui-droppable").wait_for()
        self.page.drag_and_drop("#simpleDropContainer #draggable", "#simpleDropContainer #droppable")

    @property
    def simple_target(self) -> Locator:
        return self.page.locator("#simpleDropContainer #droppable")


class SortablePage(BasePage):
    path = "/sortable"

    @property
    def items(self) -> Locator:
        return self.page.locator("#demo-tabpane-list .list-group-item")

    def move(self, source: str, target: str, attempts: int = 3):
        # react-dnd only reorders once the pointer passes the target's midpoint,
        # and ignores drags made before its backend has attached, so retry.
        before = self.items.all_inner_texts()
        for _ in range(attempts):
            src = self.items.filter(has_text=source)
            dst = self.items.filter(has_text=target)
            s, d = src.bounding_box(), dst.bounding_box()
            self.page.mouse.move(s["x"] + s["width"] / 2, s["y"] + s["height"] / 2)
            self.page.mouse.down()
            self.page.mouse.move(d["x"] + 10, d["y"] + d["height"] - 5, steps=15)
            self.page.mouse.up()
            self.page.wait_for_timeout(300)
            if self.items.all_inner_texts() != before:
                return
