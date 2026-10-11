"""Core self-healing engine: baseline fingerprints, DOM-snapshot matching, event log."""
import fcntl
import json
import os
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from healing import dom
from healing.scoring import fingerprint_from_selector, score

ROOT = Path(__file__).resolve().parent.parent


@contextmanager
def _locked(path: Path, mode: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode) as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield fh
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


@dataclass
class HealingConfig:
    enabled: bool = True
    threshold: float = 0.4
    margin: float = 0.1
    wait_ms: int = 5_000
    baseline_path: Path = ROOT / "healing" / "baseline.json"
    events_path: Path = ROOT / "reports" / "healing-events.jsonl"
    record_baseline: bool = True
    refresh_baseline: bool = False


@dataclass
class HealResult:
    selector: str
    score: float
    source: str
    parts: dict = field(default_factory=dict)
    runner_up: float = 0.0


class Healer:
    def __init__(self, config: HealingConfig | None = None):
        self.config = config or HealingConfig()
        self.baseline: dict = self._load_baseline()
        self._new: dict = {}
        self._seen: set = set()
        self.cache: dict = {}
        self.events: list = []

    # ---- baseline ---------------------------------------------------------
    def _load_baseline(self) -> dict:
        p = self.config.baseline_path
        if p.exists() and not self.config.refresh_baseline:
            return json.loads(p.read_text() or "{}")
        return {}

    @staticmethod
    def key(page_url: str, selector: str) -> str:
        return f"{urlparse(page_url).path or '/'} :: {selector}"

    def capture(self, page, selector: str, locator) -> None:
        """Remember what a working locator points at (once per key per session)."""
        if not self.config.record_baseline:
            return
        k = self.key(page.url, selector)
        if k in self._seen or k in self.baseline:
            return
        self._seen.add(k)
        try:
            if locator.count() != 1:
                return
            self._new[k] = locator.evaluate(dom.FINGERPRINT)
        except Exception:
            pass

    def save_baseline(self) -> None:
        if not self._new:
            return
        p = self.config.baseline_path
        p.touch(exist_ok=True)
        with _locked(p, "r+") as fh:
            raw = fh.read()
            data = {} if self.config.refresh_baseline and not raw else json.loads(raw or "{}")
            data.update(self._new)
            fh.seek(0)
            fh.truncate()
            json.dump(dict(sorted(data.items())), fh, indent=1, sort_keys=True)
        self._new.clear()

    # ---- healing ----------------------------------------------------------
    def heal(self, page, selector: str) -> HealResult | None:
        k = self.key(page.url, selector)
        ref, source = self.baseline.get(k) or self._new.get(k), "baseline"
        if not ref:
            ref, source = fingerprint_from_selector(selector), "selector"
        if not ref:
            return None
        candidates = page.evaluate(dom.SNAPSHOT)
        ranked = sorted(((score(ref, c), c) for c in candidates), key=lambda x: x[0][0], reverse=True)
        if not ranked:
            return None
        (best, parts), cand = ranked[0]
        runner_up = ranked[1][0][0] if len(ranked) > 1 else 0.0
        result_meta = dict(original=selector, page=page.url, source=source, score=round(best, 3),
                           runner_up=round(runner_up, 3), parts={k: round(v, 2) for k, v in parts.items()})
        if best < self.config.threshold or best - runner_up < self.config.margin:
            self._log(dict(result_meta, healed=None, status="refused"))
            return None
        for sel in page.evaluate(dom.BUILD_SELECTORS, cand["idx"]):
            try:
                if page.locator(sel).count() == 1:
                    self.cache[k] = sel
                    self._log(dict(result_meta, healed=sel, status="healed"))
                    return HealResult(sel, best, source, parts, runner_up)
            except Exception:
                continue
        self._log(dict(result_meta, healed=None, status="no-unique-selector"))
        return None

    @staticmethod
    def call_sites() -> list[dict]:
        """Lines in page objects/tests (innermost first) that led to the failing selector."""
        sites = []
        for fr in reversed(traceback.extract_stack()):
            path = Path(fr.filename).resolve()
            if ROOT not in path.parents or ".venv" in path.parts or path.parent == ROOT / "healing":
                continue
            rel = str(path.relative_to(ROOT))
            if rel.startswith(("pages/", "tests/")):
                sites.append({"file": rel, "line": fr.lineno, "code": (fr.line or "").strip()})
        return sites

    def _log(self, event: dict) -> None:
        event["call_sites"] = self.call_sites()
        event["test"] = os.environ.get("PYTEST_CURRENT_TEST", "").rsplit(" (", 1)[0]
        self.events.append(event)
        with _locked(self.config.events_path, "a") as fh:
            fh.write(json.dumps(event) + "\n")


_healer: Healer | None = None


def get_healer() -> Healer:
    global _healer
    if _healer is None:
        _healer = Healer()
    return _healer


def set_healer(healer: Healer) -> None:
    global _healer
    _healer = healer
