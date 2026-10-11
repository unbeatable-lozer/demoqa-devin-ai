"""pytest plugin: options, baseline persistence, strict mode, and report-only healing summaries.

Healing never edits tests or page objects: it reports the exact lines that need a manual
selector update (terminal summary, GitHub annotations/job summary, pytest-html, Markdown/JSON).
"""
import html
import json
import os
from pathlib import Path

import pytest

from healing.healer import Healer, HealingConfig, get_healer, set_healer


def pytest_addoption(parser):
    g = parser.getgroup("self-healing locators")
    g.addoption("--no-healing", action="store_true", help="disable locator self-healing")
    g.addoption("--healing-strict", action="store_true",
                help="heal to gather diagnostics, but fail any test that needed a heal")
    g.addoption("--healing-threshold", type=float, default=0.4, help="minimum match score (0-1)")
    g.addoption("--healing-margin", type=float, default=0.1,
                help="required score lead of the best candidate over the runner-up")
    g.addoption("--healing-wait", type=int, default=5_000,
                help="ms to wait for the original locator before healing")
    g.addoption("--healing-refresh-baseline", action="store_true",
                help="re-record all element fingerprints in healing/baseline.json")


def _is_controller(config) -> bool:
    return not hasattr(config, "workerinput")


def pytest_configure(config):
    config.addinivalue_line("markers", "healing: tests for the self-healing locator engine")
    set_healer(Healer(HealingConfig(
        enabled=not config.getoption("--no-healing"),
        threshold=config.getoption("--healing-threshold"),
        margin=config.getoption("--healing-margin"),
        wait_ms=config.getoption("--healing-wait"),
        refresh_baseline=config.getoption("--healing-refresh-baseline"),
    )))


def pytest_sessionstart(session):
    if _is_controller(session.config):
        events = get_healer().config.events_path
        for stale in (events, events.with_name("healing-report.md"), events.with_name("healing-report.json")):
            stale.unlink(missing_ok=True)
        if session.config.getoption("--healing-refresh-baseline"):
            get_healer().config.baseline_path.write_text("{}")


def pytest_sessionfinish(session):
    get_healer().save_baseline()


@pytest.fixture(autouse=True)
def _healing_strict(request):
    healer = get_healer()
    start = len(healer.events)
    yield
    healed = [e for e in healer.events[start:] if e["status"] == "healed"]
    if healed and request.config.getoption("--healing-strict"):
        lines = "\n".join(f"  {e['original']!r} -> {e['healed']!r} (score {e['score']})" for e in healed)
        pytest.fail(f"--healing-strict: locators needed healing:\n{lines}", pytrace=False)


# ---- aggregation ----------------------------------------------------------------
def load_findings(path: Path) -> list[dict]:
    """Collapse raw heal events (from all xdist workers) into one finding per selector/outcome."""
    if not path.exists():
        return []
    findings: dict = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        f = findings.setdefault((e["original"], e["healed"], e["status"]),
                                dict(e, tests=[], call_sites=[], count=0))
        f["count"] += 1
        if e["test"] and e["test"] not in f["tests"]:
            f["tests"].append(e["test"])
        for site in e.get("call_sites", []):
            if site not in f["call_sites"]:
                f["call_sites"].append(site)
    return list(findings.values())


def recommendation(f: dict) -> str:
    if f["status"] == "healed":
        return (f"Selector {f['original']!r} no longer matches; healed to {f['healed']!r} "
                f"(score {f['score']}, runner-up {f['runner_up']}, via {f['source']}). "
                f"Manual update recommended - verify the feature/UI change before editing.")
    return (f"Selector {f['original']!r} no longer matches and could not be healed "
            f"({f['status']}, best score {f['score']}, runner-up {f['runner_up']}). Manual fix required.")


def _gh_escape(s: str, prop: bool = False) -> str:
    s = s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return s.replace(":", "%3A").replace(",", "%2C") if prop else s


def github_annotations(findings: list[dict]) -> list[str]:
    """`::warning` workflow commands, rendered by GitHub as inline comments on each line.

    One annotation per source line (GitHub caps annotations per step), page objects first.
    """
    by_line: dict = {}
    for f in findings:
        for s in f["call_sites"]:
            by_line.setdefault((s["file"], s["line"]), []).append(f)
    ordered = sorted(by_line.items(), key=lambda kv: (not kv[0][0].startswith("pages/"), kv[0]))
    out = []
    for (file, line), fs in ordered:
        broken = any(f["status"] != "healed" for f in fs)
        title = _gh_escape("Self-healing locator: broken selector" if broken
                           else "Self-healing locator: update selector", prop=True)
        tests = sorted({t for f in fs for t in f["tests"]})
        msg = _gh_escape("\n".join(recommendation(f) for f in fs) + "\nTests: " + ", ".join(tests))
        out.append(f"::{'error' if broken else 'warning'} file={_gh_escape(file, True)},line={line},"
                   f"title={title}::{msg}")
    return out


# ---- outputs --------------------------------------------------------------------
def pytest_terminal_summary(terminalreporter, config):
    if not _is_controller(config):
        return
    findings = load_findings(get_healer().config.events_path)
    if not findings:
        return
    tr = terminalreporter
    tr.section("self-healing locators (report only - manual update recommended)", sep="=", yellow=True)
    for f in findings:
        healed = f["status"] == "healed"
        head = (f"HEALED  {f['original']!r}  ->  recommended {f['healed']!r}" if healed
                else f"BROKEN  {f['original']!r}  ({f['status']})")
        tr.write_line(f"{head}  score={f['score']} runner-up={f['runner_up']} via={f['source']}",
                      yellow=healed, red=not healed)
        for s in f["call_sites"]:
            tr.write_line(f"    {s['file']}:{s['line']}  {s['code']}")
    healed = sum(f["status"] == "healed" for f in findings)
    tr.write_line(f"{healed} selector(s) healed at runtime, {len(findings) - healed} unhealable. "
                  f"Source files were NOT modified; see reports/healing-report.md")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for a in github_annotations(findings):
            tr.write_line(a)
    _write_reports(get_healer().config.events_path.parent, findings)


def markdown_report(findings: list[dict]) -> str:
    md = ["## Self-healing locator report", "",
          "Report only: tests and page objects were **not** modified. Review each line and update it",
          "manually once the UI change is confirmed (a feature may still be OFF in other environments).", "",
          "| Status | Line(s) to update | Original selector | Recommended selector | Score | Tests |",
          "|---|---|---|---|---|---|"]
    for f in findings:
        lines = "<br>".join(f"`{s['file']}:{s['line']}`" for s in f["call_sites"]) or "-"
        rec = f"`{f['healed']}`" if f["healed"] else "-"
        md.append(f"| {f['status']} | {lines} | `{f['original']}` | {rec} | "
                  f"{f['score']} (next {f['runner_up']}) | {'<br>'.join(f['tests'])} |")
    return "\n".join(md) + "\n"


def _write_reports(out: Path, findings: list[dict]):
    out.mkdir(parents=True, exist_ok=True)
    (out / "healing-report.json").write_text(json.dumps(findings, indent=2))
    md = markdown_report(findings)
    (out / "healing-report.md").write_text(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(md)


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_summary(prefix, summary, postfix):
    findings = load_findings(get_healer().config.events_path)
    if not findings:
        return
    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td><code>{}</code></td><td><code>{}</code></td><td>{}</td></tr>".format(
            html.escape(f["status"]),
            "<br>".join(html.escape(f"{s['file']}:{s['line']}") for s in f["call_sites"]),
            html.escape(f["original"]), html.escape(f["healed"] or "-"), f["score"])
        for f in findings)
    postfix.append(
        "<h2>Self-healing locators (manual update recommended)</h2>"
        "<p>Tests and page objects were not modified.</p><table border='1'><tr><th>Status</th>"
        "<th>Line(s) to update</th><th>Original</th><th>Recommended</th><th>Score</th></tr>"
        f"{rows}</table>")
