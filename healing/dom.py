"""JavaScript run in the page to fingerprint elements and snapshot the DOM."""

_FP = r"""
const ATTRS = ['type','placeholder','aria-label','title','role','for','href','value','data-testid','data-test','alt','src'];
function labelOf(el) {
  if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) return l.innerText.trim(); }
  const p = el.closest('label'); if (p) return p.innerText.trim();
  return el.getAttribute('aria-label') || '';
}
function ownText(el) {
  const t = (el.innerText !== undefined ? el.innerText : el.textContent) || '';
  return t.trim().replace(/\s+/g, ' ').slice(0, 120);
}
function contextOf(el) {
  // Visible text of the nearest enclosing row, minus the element itself (e.g. an unlinked label).
  let cur = el.parentElement;
  for (let i = 0; cur && cur !== document.body && i < 3; i++, cur = cur.parentElement) {
    const own = ((el.innerText || el.value || '') + '').trim();
    const t = (cur.innerText || '').replace(own, '').trim().replace(/\s+/g, ' ');
    if (t) return t.length <= 80 ? t : '';
  }
  return '';
}
function fp(el) {
  const r = el.getBoundingClientRect();
  const attrs = {};
  for (const a of ATTRS) { const v = el.getAttribute(a); if (v) attrs[a] = v.slice(0, 120); }
  const parent = el.parentElement;
  return {
    tag: el.tagName.toLowerCase(),
    id: el.id || '',
    name: el.getAttribute('name') || '',
    classes: [...el.classList],
    text: el.children.length > 8 ? '' : ownText(el),
    label: labelOf(el).slice(0, 120),
    context: contextOf(el),
    attrs,
    parent: parent ? { tag: parent.tagName.toLowerCase(), id: parent.id || '', classes: [...parent.classList] } : null,
    rect: [Math.round(r.x + scrollX), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)],
    visible: !!(r.width || r.height) && getComputedStyle(el).visibility !== 'hidden',
  };
}
"""

FINGERPRINT = "(el) => {" + _FP + " return fp(el); }"

SKIP_TAGS = "script,style,noscript,meta,link,head,title,path,svg *,br"

SNAPSHOT = "() => {" + _FP + f"""
  const els = [...document.querySelectorAll('body *')].filter(e => !e.matches('{SKIP_TAGS}'));
  return els.slice(0, 5000).map((e, i) => Object.assign(fp(e), {{ idx: i }}));
}}"""

BUILD_SELECTORS = f"""(idx) => {{
  const els = [...document.querySelectorAll('body *')].filter(e => !e.matches('{SKIP_TAGS}'));
  const el = els[idx]; if (!el) return [];
  const tag = el.tagName.toLowerCase();
  const unique = s => {{ try {{ return document.querySelectorAll(s).length === 1 && document.querySelector(s) === el; }} catch (e) {{ return false; }} }};
  const q = v => v.replace(/\\\\/g, '\\\\\\\\').replace(/"/g, '\\\\"');
  const out = [];
  if (el.id && unique('#' + CSS.escape(el.id))) out.push('#' + CSS.escape(el.id));
  for (const a of ['data-testid','data-test','data-qa','name','aria-label','placeholder','for','title','href']) {{
    const v = el.getAttribute(a);
    if (v && unique(`${{tag}}[${{a}}="${{q(v)}}"]`)) out.push(`${{tag}}[${{a}}="${{q(v)}}"]`);
  }}
  const text = (el.innerText || '').trim();
  if (text && text.length <= 60 && !text.includes('\\n')) out.push(`${{tag}}:text-is("${{q(text)}}")`);
  const parts = []; let cur = el;
  while (cur && cur !== document.body) {{
    if (cur.id && cur !== el && unique('#' + CSS.escape(cur.id))) {{ parts.unshift('#' + CSS.escape(cur.id)); break; }}
    const t = cur.tagName.toLowerCase();
    const sib = [...cur.parentElement.children].filter(c => c.tagName === cur.tagName);
    parts.unshift(sib.length > 1 ? `${{t}}:nth-of-type(${{sib.indexOf(cur) + 1}})` : t);
    cur = cur.parentElement;
  }}
  out.push(parts.join(' > '));
  return out;
}}"""
