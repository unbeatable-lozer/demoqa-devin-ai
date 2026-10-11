# demoqa.com automation (pytest + Playwright)

End-to-end UI and API test suite for <https://demoqa.com> built with
[pytest](https://pytest.org) and [pytest-playwright](https://playwright.dev/python/), using the Page Object Model.

## Coverage

| Area | File | What's tested |
|---|---|---|
| Elements | `tests/ui/test_elements.py` | Text box (+ email validation), check box tree, radio buttons, web tables (add/edit/delete/search/validation), click types, dynamic properties, upload/download |
| Forms | `tests/ui/test_forms.py` | Practice form full submission, required-only, empty-form and mobile validation |
| Alerts, Frames & Windows | `tests/ui/test_alerts_frames_windows.py` | New tab/window, alert/timed/confirm/prompt dialogs, frames, nested frames, modals |
| Widgets | `tests/ui/test_widgets.py` | Accordion, progress bar, slider, tabs, tooltip, select menus |
| Interactions | `tests/ui/test_interactions.py` | Drag & drop, sortable list |
| Book Store UI | `tests/ui/test_book_store.py` | Invalid login, login with API-created user, search, book details |
| Book Store API | `tests/api/test_book_store_api.py` | Books/Book endpoints, account creation & validation, token/auth, add/remove books |

## Layout

```
conftest.py          # ad blocking, viewport, healing page wrapper, API client + throwaway-user fixtures
pages/               # page objects per site section
healing/             # self-healing locator engine, pytest plugin, baseline.json fingerprints
utils/api_client.py  # Book Store REST API wrapper (Playwright APIRequestContext)
tests/ui, tests/api  # test modules
tests/healing        # healer tests (offline HTML + live DOM-mutation on demoqa)
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
```

## Running

```bash
pytest                      # full suite, headless chromium
pytest -n 4                 # parallel (pytest-xdist)
pytest -m smoke             # quick critical-path subset
pytest -m api               # API tests only
pytest --headed --slowmo 300 tests/ui/test_forms.py   # watch it run
pytest --browser firefox --browser webkit             # cross-browser
pytest --reruns 2           # retry flaky failures (public site + ads)
```

Reports: `reports/report.html` (pytest-html). On failure, screenshots, videos and
Playwright traces are saved in `test-results/` — open a trace with
`playwright show-trace test-results/<test>/trace.zip`.

## Self-healing locators

Every selector used through the `page` fixture or a page object goes through `healing.HealingPage`,
and tests use the drop-in `from healing import expect`.

1. **Baseline**: when a selector works, a fingerprint of the element is stored in
   `healing/baseline.json`, keyed by URL path and selector. It records tag, id, name, classes,
   text, label, the text of the surrounding row, attributes, parent and position.
   Commit this file. Refresh it with `pytest --healing-refresh-baseline`.
2. **Heal**: if a selector matches nothing after `--healing-wait` ms, the healer takes a DOM
   snapshot and scores every element against the baseline fingerprint. If there is no baseline,
   it scores against hints parsed from the selector text. It then builds a unique selector for
   the best match and retries the action or assertion with it. It refuses to heal when the best
   score is below `--healing-threshold` (0.4) or within `--healing-margin` (0.1) of the
   runner-up.
3. **Safety**: healing only kicks in when the original selector matches **zero** elements.
   `to_be_hidden`/`to_have_count(0)` checks and wrong-text failures on an element that exists
   are never healed.
4. **Report only**: tests and page objects are **never modified**. Each heal is reported with
   the exact page-object and test lines taken from the call stack, plus the recommended selector:
   - the pytest terminal summary (`self-healing locators` section);
   - GitHub Actions `::warning` annotations, which show as inline comments on those lines in
     PRs and runs (one per source line, page objects first), and the job summary;
   - the pytest-html report, plus `reports/healing-report.md` / `.json`.

   Update selectors by hand once the UI change is confirmed. A feature may still be OFF in
   other environments, which is why nothing is rewritten automatically.

```bash
pytest --healing-strict      # still heal for diagnostics, but fail tests that needed it
pytest --no-healing          # plain Playwright behaviour
pytest -m healing            # healer's own tests
```

## Notes

- demoqa.com serves heavy third-party ads; `conftest.py` blocks ad/analytics hosts to keep tests fast and stop overlays from intercepting clicks.
- API/login tests create a random user via `/Account/v1/User` and delete it on teardown.
- CI: `.github/workflows/tests.yml` runs the suite on push, PRs, and daily, uploading the report as an artifact.
