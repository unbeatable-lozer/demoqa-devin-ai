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
conftest.py          # ad blocking, viewport, API client + throwaway-user fixtures
pages/               # page objects per site section
utils/api_client.py  # Book Store REST API wrapper (Playwright APIRequestContext)
tests/ui, tests/api  # test modules
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

## Notes

- demoqa.com serves heavy third-party ads; `conftest.py` blocks ad/analytics hosts to keep tests fast and stop overlays from intercepting clicks.
- API/login tests create a random user via `/Account/v1/User` and delete it on teardown.
- CI: `.github/workflows/tests.yml` runs the suite on push, PRs, and daily, uploading the report as an artifact.
