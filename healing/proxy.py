"""Drop-in wrappers that route Playwright selectors through the healer."""
from playwright.sync_api import Locator, Page, TimeoutError as PWTimeout
from playwright.sync_api import expect as pw_expect

from healing.healer import Healer, get_healer

LOCATOR_ACTIONS = [
    "click", "dblclick", "fill", "type", "press", "press_sequentially", "check", "uncheck",
    "set_checked", "hover", "focus", "blur", "tap", "clear", "select_option", "set_input_files",
    "drag_to", "input_value", "inner_text", "text_content", "inner_html", "get_attribute",
    "is_checked", "is_disabled", "is_enabled", "is_editable", "bounding_box", "evaluate",
    "scroll_into_view_if_needed", "screenshot", "dispatch_event", "select_text",
]
PAGE_SELECTOR_ACTIONS = [
    "click", "dblclick", "fill", "type", "press", "check", "uncheck", "set_checked", "hover",
    "focus", "tap", "select_option", "set_input_files", "input_value", "inner_text",
    "text_content", "inner_html", "get_attribute", "is_checked", "is_disabled", "is_enabled",
    "is_editable", "dispatch_event",
]


class HealingLocator(Locator):
    """A real Playwright Locator that heals its selector when it stops matching."""

    def __init__(self, base: Locator, page: "HealingPage", selector: str, healable: bool = True):
        super().__init__(base._impl_obj)
        self._hp, self._selector, self._healable = page, selector, healable
        self._plain = base
        self._origin = page._healer.frames_in_sources(3) if healable else []

    @property
    def _healer(self) -> Healer:
        return self._hp._healer

    def _healed_cached(self) -> Locator | None:
        sel = self._healer.cache.get(self._healer.key(self._hp.url, self._selector))
        if sel:
            loc = self._hp._page.locator(sel)
            if loc.count() > 0:
                return loc
        return None

    def resolve(self, wait: bool = True) -> Locator:
        """Return the original locator if it matches, otherwise a healed one (or the original)."""
        if not (self._healable and self._healer.config.enabled):
            return self._plain
        if self._plain.count() > 0:
            self._healer.capture(self._hp._page, self._selector, self._plain)
            return self._plain
        cached = self._healed_cached()
        if cached is not None:
            return cached
        if wait:
            try:
                self._plain.first.wait_for(state="attached", timeout=self._healer.config.wait_ms)
                self._healer.capture(self._hp._page, self._selector, self._plain)
                return self._plain
            except PWTimeout:
                pass
        result = self._healer.heal(self._hp._page, self._selector, self._origin)
        return self._hp._page.locator(result.selector) if result else self._plain

    def wait_for(self, *args, **kwargs):
        state = kwargs.get("state", args[0] if args else None)
        target = self.resolve() if state in (None, "attached", "visible") else self._plain
        return Locator.wait_for(target, *args, **kwargs)

    # derived locators reuse an existing heal, but never trigger one eagerly
    def _base_for_chain(self) -> Locator:
        if self._healable and self._plain.count() == 0:
            return self._healed_cached() or self._plain
        return self._plain

    @property
    def first(self) -> Locator:
        return self._base_for_chain().first

    @property
    def last(self) -> Locator:
        return self._base_for_chain().last

    def nth(self, index: int) -> Locator:
        return self._base_for_chain().nth(index)

    def locator(self, *args, **kwargs) -> Locator:
        return self._base_for_chain().locator(*args, **kwargs)

    def filter(self, *args, **kwargs) -> Locator:
        return self._base_for_chain().filter(*args, **kwargs)


def _make_action(name):
    def action(self, *args, **kwargs):
        target = self.resolve()
        if name == "drag_to" and args and isinstance(args[0], HealingLocator):
            args = (args[0].resolve(),) + args[1:]
        return getattr(Locator, name)(target, *args, **kwargs)
    action.__name__ = name
    return action


for _n in LOCATOR_ACTIONS:
    setattr(HealingLocator, _n, _make_action(_n))


class HealingPage:
    """Proxy around a Playwright Page; selector-based APIs go through HealingLocator."""

    def __init__(self, page: Page, healer: Healer | None = None):
        self._page = page.unwrap() if isinstance(page, HealingPage) else page
        self._healer = healer or get_healer()

    def unwrap(self) -> Page:
        return self._page

    def __getattr__(self, item):
        return getattr(self._page, item)

    def locator(self, selector: str, **kwargs) -> HealingLocator:
        return HealingLocator(self._page.locator(selector, **kwargs), self, selector, healable=not kwargs)

    def drag_and_drop(self, source: str, target: str, **kwargs):
        return self.locator(source).drag_to(self.locator(target), **kwargs)


def _make_page_action(name):
    def action(self, selector, *args, strict=None, timeout=None, **kwargs):
        if timeout is not None:
            kwargs["timeout"] = timeout
        return getattr(self.locator(selector), name)(*args, **kwargs)
    action.__name__ = name
    return action


for _n in PAGE_SELECTOR_ACTIONS:
    setattr(HealingPage, _n, _make_page_action(_n))


class _HealingAssertions:
    def __init__(self, actual, message):
        self._actual, self._message = actual, message

    def __getattr__(self, name):
        actual = self._actual
        if isinstance(actual, HealingPage):
            actual = actual.unwrap()
        if not isinstance(actual, HealingLocator):
            return getattr(pw_expect(actual, self._message), name)

        def assertion(*args, **kwargs):
            try:
                getattr(pw_expect(actual._plain, self._message), name)(*args, **kwargs)
            except AssertionError:
                # Only heal when the locator matches nothing; a present-but-wrong element is a real failure.
                if not (actual._healable and actual._healer.config.enabled) or actual._plain.count() > 0:
                    raise
                healed = actual.resolve(wait=False)
                if healed is actual._plain:
                    raise
                getattr(pw_expect(healed, self._message), name)(*args, **kwargs)
            else:
                if not name.startswith("not_") and name not in ("to_be_hidden", "to_have_count"):
                    actual._healer.capture(actual._hp._page, actual._selector, actual._plain)
        return assertion


def expect(actual, message: str | None = None):
    """Drop-in replacement for playwright.sync_api.expect that understands healing wrappers."""
    return _HealingAssertions(actual, message)


expect.set_options = pw_expect.set_options
