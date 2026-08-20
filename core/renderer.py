import json
import re
import threading
import urllib.parse
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

_MD_OPTIONS = {"html": True, "linkify": False, "typographer": True, "breaks": True}

_local = threading.local()


def _get_md() -> MarkdownIt:
    md = getattr(_local, "md", None)
    if md is None:
        md = MarkdownIt("default", _MD_OPTIONS)
        md.use(dollarmath_plugin)
        _local.md = md
    return md

# 需要移除的标签：文档元数据 + 活跃内容（脚本/插件/表单/CSS 注入，防 XSS）
REMOVE_TAGS = {
    "meta", "title", "head", "link", "style",
    "script", "iframe", "object", "embed", "base", "form",
}
UNWRAP_TAGS = {"html", "body"}

_EVENT_ATTR_RE = re.compile(r"^on[a-z]+$", re.I)
_UNSAFE_URL_RE = re.compile(r"^\s*(javascript|vbscript|data:text/html)\s*:", re.I)


def _templates_dir() -> Path:
    return Path(__file__).parent.parent / "assets" / "templates"


@lru_cache(maxsize=32)
def _load_template(name: str) -> dict:
    tf = _templates_dir() / f"{name}.json"
    if tf.exists():
        with open(tf, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _parse_styles(style_str: str) -> dict:
    result = {}
    for prop in style_str.split(";"):
        prop = prop.strip()
        if ":" in prop:
            k, v = prop.split(":", 1)
            result[k.strip()] = v.strip()
    return result


def _style_to_str(props: dict) -> str:
    return "; ".join(f"{k}: {v}" for k, v in props.items()) + ";"


def _is_simple_tag(key: str) -> bool:
    return re.match(r'^[a-zA-Z0-9]+$', key) is not None

def _apply_styles(dom: BeautifulSoup, template: dict) -> BeautifulSoup:
    for key, style_str in template.items():
        if key.startswith("_") or not _is_simple_tag(key):
            continue
        template_props = _parse_styles(style_str)
        for tag in dom.find_all(key):
            existing = tag.get("style", "")
            existing_props = _parse_styles(existing) if existing else {}
            merged = {**existing_props, **template_props}
            tag["style"] = _style_to_str(merged)
    return dom

def _get_extra_css(template: dict) -> str:
    rules = []
    for key, style_str in template.items():
        if key.startswith("_") or _is_simple_tag(key):
            continue
        rules.append(f"{key} {{ {style_str} }}")
    return "\n".join(rules)


def _sanitize(dom: BeautifulSoup) -> BeautifulSoup:
    for tag_name in REMOVE_TAGS:
        for tag in dom.find_all(tag_name):
            tag.decompose()
    for tag_name in UNWRAP_TAGS:
        for tag in dom.find_all(tag_name):
            tag.unwrap()
    # 移除事件属性（onclick / onerror / onload 等），防事件型 XSS
    for tag in dom.find_all(True):
        for attr in list(tag.attrs):
            if _EVENT_ATTR_RE.match(attr):
                del tag.attrs[attr]
    # 拦截 javascript: / vbscript: / data:text/html 危险 URL（href / src / xlink:href）
    for tag in dom.find_all(True):
        for attr in ("href", "src", "xlink:href"):
            val = tag.attrs.get(attr)
            if isinstance(val, str) and _UNSAFE_URL_RE.match(val):
                del tag.attrs[attr]
    return dom


def _convert_mermaid_blocks(dom: BeautifulSoup) -> BeautifulSoup:
    for pre in dom.find_all("pre"):
        code = pre.find("code")
        if code and code.get("class") and "language-mermaid" in code.get("class"):
            mermaid_text = code.get_text()
            div = dom.new_tag("div", **{"class": "mermaid"})
            div.string = mermaid_text
            pre.replace_with(div)
    return dom


def _cleanup_list_paragraphs(dom: BeautifulSoup) -> BeautifulSoup:
    for li in dom.find_all("li"):
        ps = li.find_all("p", recursive=False)
        if len(ps) == 1 and not li.find(["ul", "ol"], recursive=False):
            p = ps[0]
            p.unwrap()
    return dom


def _has_mermaid(content: str) -> bool:
    return '<div class="mermaid">' in content


def _has_math(content: str) -> bool:
    return 'class="math inline"' in content or 'class="math block"' in content


KATEX_CSS = (
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css">'
)
KATEX_SCRIPT = (
    '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js"></script>'
    '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16/dist/contrib/auto-render.min.js"'
    ' onload="renderMathInElement(document.body,{delimiters:[{left:\'$\',right:\'$\',display:false},{left:\'$$\',right:\'$$\',display:true}]});"></script>'
)

MERMAID_CSS = (
    "<style>"
    ".mermaid{background:#fafafa;border-radius:6px;padding:12px;margin:8px 0;overflow-x:auto;text-align:center;}"
    ".mermaid svg{max-width:100%;height:auto;}"
    "</style>"
)

MERMAID_SCRIPT = (
    '<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"'
    ' onload="mermaid.initialize({startOnLoad:false,theme:\'default\',securityLevel:\'strict\'});'
    "mermaid.run({querySelector:'.mermaid'});\"></script>"
)


def strip_max_width(css_text: str) -> str:
    return re.sub(r'max-width\s*:\s*\d+px\s*;?\s*', '', css_text)


def _fix_local_image_paths(html: str) -> str:
    def _fix(m):
        src = m.group(1)
        if not src or src.startswith(("http://", "https://", "data:", "file://")):
            return m.group(0)
        decoded = urllib.parse.unquote(src)
        p = Path(decoded)
        if p.is_absolute() and p.exists():
            return m.group(0).replace(f'src="{src}"', f'src="{p.as_uri()}"', 1)
        return m.group(0)
    return re.sub(r'src="([^"]*)"', _fix, html)


def _make_anchor(title: str) -> str:
    return re.sub(r'[^\w\u4e00-\u9fff-]', '', title.lower().replace(" ", "-"))


def _expand_toc(markdown_text: str) -> str:
    if "[TOC]" not in markdown_text:
        return markdown_text
    headings = []
    seen_anchors = {}
    for line in markdown_text.split("\n"):
        m = re.match(r'^(#{1,6})\s+(.+?)(?:\s+#+)?$', line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            anchor = _make_anchor(title)
            if anchor in seen_anchors:
                seen_anchors[anchor] += 1
                anchor = f"{anchor}-{seen_anchors[anchor]}"
            else:
                seen_anchors[anchor] = 0
            indent = "  " * (level - 1)
            headings.append((level, title, anchor, indent))
    if not headings:
        return markdown_text
    toc_lines = ['<div class="toc">']
    for level, title, anchor, indent in headings:
        toc_lines.append(
            f'{indent}<a href="#{anchor}" '
            f'style="text-decoration:none;color:#1a73e8;display:block;'
            f'padding:2px 0;font-size:{max(12, 16 - level)}px;">'
            f'{"&nbsp;" * (level - 1)}{title}</a>'
        )
    toc_lines.append('</div>')
    toc_html = "\n".join(toc_lines)
    return markdown_text.replace("[TOC]", toc_html, 1)


def _add_heading_ids(dom: BeautifulSoup) -> BeautifulSoup:
    seen_anchors = {}
    for tag in dom.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        title = tag.get_text().strip()
        anchor = _make_anchor(title)
        if anchor in seen_anchors:
            seen_anchors[anchor] += 1
            anchor = f"{anchor}-{seen_anchors[anchor]}"
        else:
            seen_anchors[anchor] = 0
        tag["id"] = anchor
    return dom


def render_html(markdown_text: str, template_name: str = "default") -> str:
    markdown_text = _expand_toc(markdown_text)
    html = _get_md().render(markdown_text)
    dom = BeautifulSoup(html, "html.parser")
    dom = _sanitize(dom)
    dom = _add_heading_ids(dom)
    dom = _convert_mermaid_blocks(dom)
    dom = _cleanup_list_paragraphs(dom)
    template = _load_template(template_name)
    if template:
        dom = _apply_styles(dom, template)

    body = dom.body if dom.body else dom
    content = "".join(
        str(c)
        for c in body.children
        if c.name or (hasattr(c, "strip") and c.strip())
    )
    content = _preserve_spaces(content)
    content = _fix_local_image_paths(content)
    return content


def _preserve_spaces(html: str) -> str:
    def _replace(m):
        return "\u00a0" * len(m.group(0))
    skip_re = re.compile(
        r'(<pre[^>]*>.*?</pre>|<code[^>]*>.*?</code>|'
        r'<span[^>]*class="math[^"]*"[^>]*>.*?</span>|<div[^>]*class="math[^"]*"[^>]*>.*?</div>)',
        re.I | re.S
    )
    parts = []
    last = 0
    for m in skip_re.finditer(html):
        parts.append(re.sub(r'  +', _replace, html[last:m.start()]))
        parts.append(m.group())
        last = m.end()
    parts.append(re.sub(r'  +', _replace, html[last:]))
    return "".join(parts)


def _custom_css() -> str:
    try:
        from core.config import config_manager
        return config_manager.get("template.custom_css", "")
    except Exception:
        return ""


def render_full_page(markdown_text: str, template_name: str = "default") -> str:
    content = render_html(markdown_text, template_name)
    template = _load_template(template_name)
    base_style = template.get("_page_style", "")
    extra_css = _get_extra_css(template) if template else ""
    extra_head = ""
    if _has_mermaid(content):
        extra_head += MERMAID_CSS + MERMAID_SCRIPT
    if _has_math(content):
        extra_head += KATEX_CSS + KATEX_SCRIPT
    custom = _custom_css()
    base_css = (
        "html{color-scheme:only light;}html,body{margin:0;padding:0;}"
        "img{display:block;margin-left:auto;margin-right:auto;}"
    )
    all_styles = base_css + base_style
    if extra_css:
        all_styles += "\n" + extra_css
    return (
        f"<!DOCTYPE html><html><head>"
        f'<meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f"<style>{all_styles}</style>"
        f"{'<style>'+custom+'</style>' if custom else ''}"
        f"{extra_head}"
        f"</head><body>{content}</body></html>"
    )


def get_template_names() -> list:
    return sorted(
        [tf.stem for tf in _templates_dir().glob("*.json") if not tf.stem.startswith("_")]
    )
