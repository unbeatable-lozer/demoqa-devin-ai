"""Self-healing engine checks against local HTML that changes between 'releases'."""
import pytest
from playwright.sync_api import TimeoutError as PWTimeout

from healing import expect
from healing.scoring import fingerprint_from_selector

pytestmark = pytest.mark.healing

V1 = """
<form id="profile">
  <label for="userName">Full Name</label><input id="userName" class="form-control" placeholder="Full Name">
  <label for="userEmail">Email</label><input id="userEmail" class="form-control" type="email" placeholder="name@example.com">
  <button id="submit" class="btn btn-primary">Submit</button>
  <button id="reset" class="btn btn-light">Reset</button>
  <p id="result"></p>
</form>
<script>document.getElementById('submit').onclick = e => { e.preventDefault();
  document.getElementById('result').textContent = 'Saved ' + document.querySelector('input').value; };</script>
"""

# Next "release": ids, classes and wrapper markup changed; labels/placeholders/text kept.
V2 = """
<form id="profile-v2"><div class="row">
  <label for="fullName">Full Name</label><input id="fullName" class="input input--text" placeholder="Full Name">
  <label for="emailAddress">Email</label><input id="emailAddress" class="input" type="email" placeholder="name@example.com">
</div><div class="actions">
  <button id="btn-save" class="button primary">Submit</button>
  <button id="btn-clear" class="button">Reset</button>
</div><p id="result"></p></form>
<script>document.getElementById('btn-save').onclick = e => { e.preventDefault();
  document.getElementById('result').textContent = 'Saved ' + document.querySelector('input').value; };</script>
"""


def _run_flow(hpage):
    hpage.fill("#userName", "Ada")
    hpage.fill("#userEmail", "ada@example.com")
    hpage.click("#submit")
    expect(hpage.locator("#result")).to_have_text("Saved Ada")


def test_heals_from_baseline_after_ui_change(hpage, healer):
    hpage.set_content(V1)
    _run_flow(hpage)
    assert not healer.events
    assert len(healer._new) == 4

    hpage.set_content(V2)
    _run_flow(hpage)

    healed = {e["original"]: e["healed"] for e in healer.events if e["status"] == "healed"}
    assert healed == {"#userName": "#fullName", "#userEmail": "#emailAddress", "#submit": "#btn-save"}
    assert all(e["source"] == "baseline" for e in healer.events)


def test_baseline_survives_save_and_reload(hpage, healer):
    from healing import Healer
    hpage.set_content(V1)
    _run_flow(hpage)
    healer.save_baseline()
    fresh = Healer(healer.config)
    assert set(fresh.baseline) == {f"blank :: {s}" for s in ("#userName", "#userEmail", "#submit", "#result")}


def test_heals_from_selector_text_without_baseline(hpage, healer):
    hpage.set_content('<button id="cancel-btn">Cancel</button><button id="submit-btn">Send</button>')
    hpage.click("#submit")
    assert healer.events[0]["status"] == "healed"
    assert healer.events[0]["healed"] == "#submit-btn"
    assert healer.events[0]["source"] == "selector"
    site = healer.events[0]["call_sites"][0]
    assert site["file"] == "tests/healing/test_healer_offline.py" and 'hpage.click("#submit")' in site["code"]


def test_reports_lines_without_touching_sources(hpage, healer):
    from healing.plugin import github_annotations, load_findings, markdown_report
    hpage.set_content('<button id="submit-btn">Send</button>')
    hpage.click("#submit")
    hpage.click("#submit")
    findings = load_findings(healer.config.events_path)
    assert len(findings) == 1
    [note] = github_annotations(findings)
    assert note.startswith("::warning file=tests/healing/test_healer_offline.py,line=")
    assert "Manual update recommended" in note
    assert "| healed | `tests/healing/test_healer_offline.py:" in markdown_report(findings)


def test_cached_heal_is_reused(hpage, healer):
    hpage.set_content('<button id="submit-btn">Send</button>')
    for _ in range(3):
        hpage.click("#submit")
    assert len(healer.events) == 1


def test_refuses_ambiguous_match(hpage, healer):
    hpage.set_content('<div id="item-1">a</div><div id="item-2">a</div>')
    with pytest.raises(PWTimeout):
        hpage.click("#item", timeout=500)
    assert healer.events[0]["status"] == "refused"


def test_refuses_low_confidence_match(hpage, healer):
    hpage.set_content('<button id="logout">Log out</button>')
    with pytest.raises(PWTimeout):
        hpage.click("#submit", timeout=500)
    assert healer.events[0]["status"] == "refused"


def test_real_assertion_failure_is_not_masked(hpage, healer):
    hpage.set_content('<p id="result">Error</p>')
    with pytest.raises(AssertionError):
        expect(hpage.locator("#result")).to_have_text("Saved", timeout=500)
    assert not healer.events


def test_absence_assertions_never_heal(hpage, healer):
    hpage.set_content('<p id="result-message">Saved</p>')
    expect(hpage.locator("#result")).to_have_count(0)
    expect(hpage.locator("#result")).to_be_hidden()
    assert hpage.locator("#result").count() == 0
    assert not healer.events


def test_assertions_heal_with_baseline(hpage, healer):
    hpage.set_content('<div class="alert" id="msg">Welcome back</div>')
    expect(hpage.locator("#msg")).to_be_visible()
    hpage.set_content('<div class="toast" id="notification">Welcome back</div>')
    expect(hpage.locator("#msg")).to_have_text("Welcome back", timeout=500)
    assert healer.events[0]["healed"] == "#notification"


def test_disabled_healing_fails_normally(hpage, healer):
    healer.config.enabled = False
    hpage.set_content('<button id="submit-btn">Send</button>')
    with pytest.raises(PWTimeout):
        hpage.click("#submit", timeout=500)
    assert not healer.events


@pytest.mark.parametrize("selector, expected", [
    ("#userName", {"id": "userName"}),
    ("#output #email", {"id": "email"}),
    ("label[for=yesRadio]", {"tag": "label", "attrs": {"for": "yesRadio"}}),
    ("input[name='q'].search", {"tag": "input", "name": "q", "classes": ["search"]}),
    (".rc-tree-title:text-is('Home')", {"classes": ["rc-tree-title"], "text": "Home"}),
    ("text=Submit", {"text": "Submit"}),
])
def test_fingerprint_from_selector(selector, expected):
    assert fingerprint_from_selector(selector) == expected
