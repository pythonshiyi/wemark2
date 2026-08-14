import json

from bs4 import BeautifulSoup

from core.renderer import (
    render_html,
    render_full_page,
    _has_mermaid,
    _has_math,
    _preserve_spaces,
    _convert_mermaid_blocks,
    _sanitize,
    _apply_styles,
    _load_template,
    get_template_names,
    strip_max_width,
    _fix_local_image_paths,
    MERMAID_SCRIPT,
)


class TestRenderHtml:
    def test_heading_levels(self):
        html = render_html("# H1\n## H2\n### H3")
        assert "<h1 " in html
        assert "<h2 " in html
        assert "<h3 " in html
        assert "H1" in html and "H2" in html and "H3" in html

    def test_bold_and_italic(self):
        html = render_html("**bold** and *italic*")
        assert "<strong" in html
        assert "<em" in html

    def test_strikethrough(self):
        html = render_html("~~strikethrough~~")
        assert "<s>" in html or "<del>" in html or "<s " in html

    def test_inline_code(self):
        html = render_html("Use `code` here")
        assert "<code" in html

    def test_unordered_list(self):
        html = render_html("- item 1\n- item 2")
        assert "<ul" in html
        assert "<li" in html

    def test_ordered_list(self):
        html = render_html("1. first\n2. second")
        assert "<ol" in html

    def test_blockquote(self):
        html = render_html("> quoted text")
        assert "<blockquote" in html

    def test_link(self):
        html = render_html("[text](https://example.com)")
        assert '<a href="https://example.com"' in html

    def test_image(self):
        html = render_html("![alt](img.png)")
        assert 'src="img.png"' in html

    def test_horizontal_rule(self):
        html = render_html("---")
        assert "<hr" in html

    def test_table(self):
        html = render_html("| A | B |\n| --- | --- |\n| 1 | 2 |")
        assert "<table" in html

    def test_code_block(self):
        html = render_html("```python\nprint('hello')\n```")
        assert "<pre" in html or "<code" in html
        assert "python" in html

    def test_mermaid_block_conversion(self):
        html = render_html("```mermaid\ngraph TD;\nA-->B;\n```")
        assert '<div class="mermaid"' in html

    def test_math_inline(self):
        html = render_html("Math $E = mc^2$ here")
        assert 'class="math inline"' in html

    def test_math_block(self):
        html = render_html("$$\nE = mc^2\n$$")
        assert 'class="math block"' in html

    def test_empty_input(self):
        html = render_html("")
        assert html == "" or html.strip() == ""

    def test_just_whitespace(self):
        html = render_html("   \n\n  ")
        assert html.strip() == ""

    def test_multiple_newlines(self):
        html = render_html("Para 1\n\n\n\nPara 2")
        assert "Para 1" in html
        assert "Para 2" in html

    def test_html_is_not_escaped_in_code_blocks(self):
        html = render_html("```html\n<div>content</div>\n```")
        assert "&lt;div&gt;" in html or "<div>" in html

    def test_template_application(self):
        html = render_html("# Heading", "paper")
        assert "font-family" in html or "font-size" in html or "margin" in html

    def test_no_crash_with_broken_templates(self):
        html = render_html("Hello", "nonexistent_template_xyz")
        assert "Hello" in html


class TestRenderFullPage:
    def test_returns_full_html_document(self):
        page = render_full_page("# Hello")
        assert page.startswith("<!DOCTYPE html>")
        assert "<html>" in page
        assert "<body>" in page
        assert "</html>" in page

    def test_includes_meta_charset(self):
        page = render_full_page("# Hello")
        assert 'charset="utf-8"' in page

    def test_includes_viewport_meta(self):
        page = render_full_page("# Hello")
        assert "viewport" in page

    def test_mermaid_scripts_included_when_needed(self):
        page = render_full_page("```mermaid\ngraph TD\n```")
        assert "mermaid" in page

    def test_katex_scripts_included_when_needed(self):
        page = render_full_page("Math $x^2$")
        assert "katex" in page

    def test_template_css_applied(self):
        page = render_full_page("# Title", "paper")
        assert "<style>" in page

    def test_content_in_body(self):
        page = render_full_page("**bold**")
        assert "bold" in page


class TestHelpers:
    def test_has_mermaid_true(self):
        assert _has_mermaid('<div class="mermaid">') is True

    def test_has_mermaid_false(self):
        assert _has_mermaid("<p>No diagram</p>") is False

    def test_has_math_inline(self):
        assert _has_math('class="math inline"') is True

    def test_has_math_block(self):
        assert _has_math('class="math block"') is True

    def test_has_math_false(self):
        assert _has_math("<p>No math</p>") is False

    def test_preserve_spaces(self):
        result = _preserve_spaces("<p>hello  world</p>")
        assert "\u00a0" in result

    def test_preserve_spaces_skips_code(self):
        result = _preserve_spaces("<code>hello  world</code>")
        assert "  " in result

    def test_sanitize_removes_meta(self):
        soup = BeautifulSoup("<meta name='a'><title>T</title><p>text</p>", "html.parser")
        soup = _sanitize(soup)
        assert soup.find("meta") is None
        assert soup.find("title") is None
        assert soup.find("p") is not None

    def test_sanitize_removes_script(self):
        soup = BeautifulSoup("<p>a</p><script>alert(1)</script>", "html.parser")
        soup = _sanitize(soup)
        assert soup.find("script") is None
        assert soup.find("p") is not None

    def test_sanitize_removes_active_tags(self):
        soup = BeautifulSoup(
            "<iframe src='https://evil.example'></iframe>"
            "<object data='x'></object><embed src='y'>"
            "<style>body{display:none}</style><form action='x'></form>",
            "html.parser",
        )
        soup = _sanitize(soup)
        for name in ("iframe", "object", "embed", "style", "form"):
            assert soup.find(name) is None, name

    def test_sanitize_removes_event_attributes(self):
        soup = BeautifulSoup(
            "<img src='a.png' onerror='alert(1)' onclick='x()' style='color:red'>",
            "html.parser",
        )
        soup = _sanitize(soup)
        img = soup.find("img")
        assert "onerror" not in img.attrs
        assert "onclick" not in img.attrs
        assert img.get("style") == "color:red"  # 合法属性保留

    def test_sanitize_removes_javascript_urls(self):
        soup = BeautifulSoup(
            "<a href='javascript:alert(1)'>x</a><img src='vbscript:msgbox(1)'>",
            "html.parser",
        )
        soup = _sanitize(soup)
        assert "href" not in soup.find("a").attrs
        assert "src" not in soup.find("img").attrs

    def test_render_html_strips_script_and_events(self):
        html = render_html(
            "hello\n\n<script>alert(1)</script>\n\n<img src='x.png' onerror='alert(2)'>"
        )
        assert "<script>" not in html
        assert "onerror" not in html
        assert "hello" in html

    def test_render_html_blocks_javascript_link(self):
        # markdown-it 默认 validateLink 拒绝 javascript:，退化为纯文本（不生成链接）
        html = render_html("[点我](javascript:alert(1))")
        assert "<a" not in html
        assert 'href="javascript:' not in html
        # 原始 HTML 直写危险 URL 时由 sanitize 兜底
        html2 = render_html("<a href='javascript:alert(1)'>x</a>")
        assert 'href="javascript:' not in html2
        assert "x" in html2

    def test_mermaid_uses_strict_security(self):
        assert "securityLevel:'loose'" not in MERMAID_SCRIPT
        assert "securityLevel:'strict'" in MERMAID_SCRIPT

    def test_convert_mermaid_blocks(self):
        soup = BeautifulSoup(
            '<pre><code class="language-mermaid">graph TD</code></pre>',
            "html.parser",
        )
        soup = _convert_mermaid_blocks(soup)
        assert soup.find("div", class_="mermaid") is not None
        assert soup.find("pre") is None

    def test_get_template_names(self):
        names = get_template_names()
        assert isinstance(names, list)
        assert len(names) > 0
        assert "default" in names
        assert "paper" in names

    def test_load_template(self):
        tmpl = _load_template("default")
        assert isinstance(tmpl, dict)
        assert len(tmpl) > 0

    def test_load_nonexistent_template(self):
        tmpl = _load_template("__nonexistent__")
        assert tmpl == {}

    def test_apply_styles(self):
        soup = BeautifulSoup("<h1>Title</h1><p>Text</p>", "html.parser")
        result = _apply_styles(soup, {"h1": "color: red; font-size: 24px;"})
        h1 = result.find("h1")
        assert h1 is not None
        assert "color: red" in h1.get("style", "")
        assert "font-size: 24px" in h1.get("style", "")


class TestRenderEdgeCases:
    def test_table_with_empty_cells(self):
        html = render_html("| A | B |\n| --- | --- |\n|  |  |")
        assert "<table" in html
        assert "<td" in html or "<th" in html

    def test_nested_blockquotes(self):
        html = render_html("> level 1\n>> level 2")
        assert "level 1" in html
        assert "level 2" in html

    def test_task_list_markers(self):
        html = render_html("- [ ] todo\n- [x] done")
        assert "todo" in html
        assert "done" in html

    def test_long_text_without_crash(self):
        text = "# " + "x" * 10000
        html = render_html(text)
        assert html

    def test_special_html_entities(self):
        html = render_html("AT&T <test> &nbsp;")
        assert html

    def test_chinese_characters(self):
        html = render_html("# 你好世界\n这是一段中文。")
        assert "你好世界" in html
        assert "这是一段中文" in html

    def test_mixed_complex_document(self, sample_markdown):
        html = render_html(sample_markdown)
        assert "<h1 " in html
        assert "<h2 " in html
        assert "<strong" in html
        assert "<ul" in html or "<ol" in html
        assert "<blockquote" in html
        assert "<table" in html
        assert '<div class="mermaid"' in html
        assert 'class="math inline"' in html


class TestStripMaxWidth:
    def test_removes_max_width_declaration(self):
        result = strip_max_width('body{max-width:680px;margin:0 auto;}')
        assert 'max-width' not in result
        assert 'margin:0 auto' in result

    def test_removes_max_width_with_spaces(self):
        result = strip_max_width('body { max-width: 680px; color: red; }')
        assert 'max-width' not in result
        assert 'color: red' in result

    def test_no_max_width_unchanged(self):
        css = 'body{margin:0;padding:0;color:#333;}'
        assert strip_max_width(css) == css

    def test_removes_semicolon_after_max_width(self):
        result = strip_max_width('body{max-width:680px;margin:0;}')
        assert result == 'body{margin:0;}'

    def test_empty_string(self):
        assert strip_max_width('') == ''


class TestFixLocalImagePaths:
    def test_http_url_unchanged(self):
        html = '<img src="https://example.com/img.png">'
        assert _fix_local_image_paths(html) == html

    def test_data_uri_unchanged(self):
        html = '<img src="data:image/png;base64,abc123">'
        assert _fix_local_image_paths(html) == html

    def test_relative_path_unchanged_when_not_exists(self):
        html = '<img src="images/foo.png">'
        assert _fix_local_image_paths(html) == html

    def test_empty_src_unchanged(self):
        html = '<img src="">'
        assert _fix_local_image_paths(html) == html

    def test_multiple_images(self):
        html = '<img src="a"><img src="https://x.com/i.png">'
        result = _fix_local_image_paths(html)
        assert 'https://x.com/i.png' in result

    def test_absolute_existing_path_converted(self, tmp_path):
        img = tmp_path / "test_img.png"
        img.write_text("fake-png")
        html = f'<img src="{img}">'
        result = _fix_local_image_paths(html)
        assert "file:///" in result

    def test_path_with_url_encoded_chars(self, tmp_path):
        img = tmp_path / "test_img.png"
        img.write_text("fake-png")
        encoded = str(img).replace("\\", "%5C")
        html = f'<img src="{encoded}">'
        result = _fix_local_image_paths(html)
        assert "file:///" in result

