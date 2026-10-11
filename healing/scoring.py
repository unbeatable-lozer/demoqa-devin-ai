"""Similarity scoring between a reference fingerprint and DOM candidates."""
import re
from difflib import SequenceMatcher

WEIGHTS = {
    "tag": 2.0, "id": 3.0, "name": 2.0, "classes": 1.5, "text": 3.0,
    "label": 2.0, "context": 2.5, "attrs": 2.5, "parent": 1.0, "rect": 1.0,
}
INPUT_LIKE = {"input", "textarea", "select"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _tokens(s: str) -> set:
    return {t for t in re.split(r"[^a-z0-9]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", s or "").lower()) if t}


def text_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    na, nb = _norm(a), _norm(b)
    if na == nb:
        return 1.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = _tokens(a), _tokens(b)
    jac = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    return max(seq, jac)


def free_text_sim(a: str, b: str) -> float:
    """Stricter than text_sim: 'Permanent Address' must not look like 'Current Address'."""
    if not a or not b:
        return 0.0
    if _norm(a) == _norm(b):
        return 1.0
    ta, tb = _tokens(a), _tokens(b)
    jac = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    if len(ta) > 1 and len(tb) > 1:
        return jac
    return max(jac, SequenceMatcher(None, _norm(a), _norm(b)).ratio() ** 2)


def _set_sim(a, b) -> float:
    a, b = set(a or []), set(b or [])
    return len(a & b) / len(a | b) if a | b else 0.0


def _tag_sim(a: str, b: str) -> float:
    if a == b:
        return 1.0
    return 0.5 if a in INPUT_LIKE and b in INPUT_LIKE else 0.0


def _rect_sim(a, b) -> float:
    if not a or not b:
        return 0.0
    dist = abs(a[0] - b[0]) + abs(a[1] - b[1])
    return max(0.0, 1.0 - dist / 600)


def score(ref: dict, cand: dict) -> tuple[float, dict]:
    """Weighted similarity in [0, 1], normalised over the fields the reference actually has."""
    parts, total = {}, 0.0
    if ref.get("tag"):
        parts["tag"] = _tag_sim(ref["tag"], cand.get("tag", ""))
    for f in ("id", "name"):
        if ref.get(f):
            parts[f] = text_sim(ref[f], cand.get(f, ""))
    for f in ("text", "label", "context"):
        if ref.get(f):
            parts[f] = free_text_sim(ref[f], cand.get(f, ""))
    if ref.get("classes"):
        parts["classes"] = _set_sim(ref["classes"], cand.get("classes"))
    if ref.get("attrs"):
        ra, ca = ref["attrs"], cand.get("attrs") or {}
        parts["attrs"] = sum(free_text_sim(v, ca.get(k, "")) for k, v in ra.items()) / len(ra)
    if ref.get("parent") and cand.get("parent"):
        rp, cp = ref["parent"], cand["parent"]
        sims = [_tag_sim(rp["tag"], cp["tag"])]
        if rp.get("id"):
            sims.append(text_sim(rp["id"], cp.get("id")))
        if rp.get("classes"):
            sims.append(_set_sim(rp["classes"], cp.get("classes")))
        parts["parent"] = sum(sims) / len(sims)
    if ref.get("rect"):
        parts["rect"] = _rect_sim(ref["rect"], cand.get("rect"))
    weight = sum(WEIGHTS[k] for k in parts)
    total = sum(WEIGHTS[k] * v for k, v in parts.items())
    s = total / weight if weight else 0.0
    if ref.get("visible") and not cand.get("visible"):
        s *= 0.7
    return s, parts


_COMPOUND = re.compile(r"""^([a-zA-Z][\w-]*)?""")


def fingerprint_from_selector(selector: str) -> dict:
    """Best-effort reference built from the selector text alone (used when no baseline exists)."""
    sel = selector.strip()
    text = None
    m = re.match(r"""^text=["']?(.+?)["']?$""", sel)
    if m:
        return {"text": m.group(1)}
    m = re.search(r""":(?:text-is|has-text|text)\(["'](.+?)["']\)""", sel)
    if m:
        text = m.group(1)
        sel = sel[: m.start()] + sel[m.end():]
    last = re.split(r"\s*>\s*|\s+", re.sub(r"\[[^\]]*\]", lambda x: x.group(0).replace(" ", "\0"), sel))[-1]
    last = last.replace("\0", " ")
    ref = {}
    tag = _COMPOUND.match(last).group(1)
    if tag:
        ref["tag"] = tag.lower()
    ids = re.findall(r"#([\w-]+)", last)
    if ids:
        ref["id"] = ids[0]
    classes = re.findall(r"\.([\w-]+)", last)
    if classes:
        ref["classes"] = classes
    attrs = {}
    for k, v in re.findall(r"""\[([\w-]+)\s*[*^$~|]?=\s*["']?([^"'\]]+)["']?\]""", last):
        if k == "name":
            ref["name"] = v
        elif k == "id":
            ref["id"] = v
        else:
            attrs[k] = v
    if attrs:
        ref["attrs"] = attrs
    if text:
        ref["text"] = text
    return ref
