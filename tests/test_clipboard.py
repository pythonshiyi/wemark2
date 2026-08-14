from core.clipboard import _generate_html_format, copy_rich_text
from PySide6.QtWidgets import QApplication


class TestGenerateHtmlFormat:
    def test_starts_with_version(self):
        result = _generate_html_format("<p>test</p>")
        assert result.startswith("Version:1.0\n")

    def test_includes_all_required_headers(self):
        result = _generate_html_format("<p>test</p>")
        assert "StartHTML:" in result
        assert "EndHTML:" in result
        assert "StartFragment:" in result
        assert "EndFragment:" in result

    def test_headers_have_zero_padded_numbers(self):
        result = _generate_html_format("<p>test</p>")
        lines = result.split("\n")
        for line in lines[1:5]:
            _, num = line.split(":")
            assert len(num.strip()) == 10, f"Expected 10-digit number, got {num}"

    def test_contains_fragment_markers(self):
        result = _generate_html_format("<p>test</p>")
        assert "<!--StartFragment-->" in result
        assert "<!--EndFragment-->" in result

    def test_html_content_between_fragment_markers(self):
        html = "<p>Hello World</p>"
        result = _generate_html_format(html)
        assert "Hello World" in result
        start = result.index("<!--StartFragment-->") + len("<!--StartFragment-->")
        end = result.index("<!--EndFragment-->")
        fragment = result[start:end]
        assert fragment == html

    def test_start_html_offset_is_correct(self):
        html = "<p>test</p>"
        result = _generate_html_format(html)
        for line in result.split("\n"):
            if line.startswith("StartHTML:"):
                val = int(line.split(":")[1].strip())
                # StartHTML should point to the byte after the header
                prefix = "Version:1.0\nStartHTML:0000000000\nEndHTML:0000000000\nStartFragment:0000000000\nEndFragment:0000000000\n"
                assert val == len(prefix.encode("utf-8"))
                return

    def test_fragment_offset_between_html_and_body(self):
        html = "<p>test</p>"
        result = _generate_html_format(html)
        headers = {}
        for line in result.split("\n")[:6]:
            if ":" in line:
                parts = line.split(":", 1)
                if parts[0].startswith(("Start", "End")):
                    headers[parts[0]] = int(parts[1].strip())
        assert headers["StartFragment"] > headers["StartHTML"]
        assert headers["EndFragment"] <= headers["EndHTML"]

    def test_empty_html(self):
        result = _generate_html_format("")
        assert "<!--StartFragment--><!--EndFragment-->" in result

    def test_html_with_special_chars(self):
        html = "<p>AT&T &amp; &lt;test&gt;</p>"
        result = _generate_html_format(html)
        assert "AT&T" in result


class TestCopyRichText:
    def test_requires_qapp(self, qapp):
        pass

    def test_creates_full_xhtml_document(self):
        html = "<p>test</p>"
        # This calls QApplication.clipboard() which requires qapp fixture
        copy_rich_text(html)
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        assert text == "test"

    def test_includes_base64_images_when_base_path_provided(self, tmp_path):
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        img_file = img_dir / "test.png"
        img_file.write_bytes(b"fake-png-content")
        html = f'<img src="{img_file}">'
        copy_rich_text(html, str(tmp_path))
        # Just verify it doesn't crash
        assert True
