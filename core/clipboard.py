import base64
import mimetypes
import os

import pyperclip
from bs4 import BeautifulSoup
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication


def _generate_html_format(html: str) -> str:
    content_start = "<html>\n<body>\n<!--StartFragment-->"
    content_end = "<!--EndFragment-->\n</body>\n</html>"

    prefix = (
        "Version:1.0\n"
        "StartHTML:0000000000\n"
        "EndHTML:0000000000\n"
        "StartFragment:0000000000\n"
        "EndFragment:0000000000\n"
    )
    prefix_bytes = prefix.encode("utf-8")
    cs_bytes = content_start.encode("utf-8")
    content_bytes = html.encode("utf-8")
    ce_bytes = content_end.encode("utf-8")

    start_html = len(prefix_bytes)
    start_fragment = start_html + len(cs_bytes)
    end_fragment = start_fragment + len(content_bytes)
    end_html = end_fragment + len(ce_bytes)

    header = (
        f"Version:1.0\n"
        f"StartHTML:{start_html:010d}\n"
        f"EndHTML:{end_html:010d}\n"
        f"StartFragment:{start_fragment:010d}\n"
        f"EndFragment:{end_fragment:010d}\n"
    )
    return header + content_start + html + content_end


def copy_rich_text(html: str, base_path: str = None) -> None:
    soup = BeautifulSoup(html, "html.parser")

    if base_path:
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src.startswith("data:") or src.startswith("http"):
                continue
            local_path = src if os.path.isabs(src) else os.path.join(base_path, src)
            if os.path.exists(local_path):
                try:
                    with open(local_path, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                        mime, _ = mimetypes.guess_type(local_path)
                        img["src"] = f"data:{mime or 'image/png'};base64,{data}"
                except Exception:
                    pass

    inner_html = str(soup)

    full_html = (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'
        '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        "<head>\n"
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0"/>\n'
        "<title></title>\n"
        "<style type=\"text/css\">\n"
        "body,table,p,div,ol,ul,li{margin:0;padding:0;}\n"
        "img{border:0;}\n"
        "table{border-collapse:collapse;}\n"
        "ol,ul{list-style:none;}\n"
        "blockquote{margin:0;}\n"
        "h1,h2,h3,h4,h5,h6,p{margin:0;padding:0;}\n"
        "</style>\n"
        "</head>\n"
        f"<body>{inner_html}</body>\n"
        "</html>"
    )

    clipboard = QApplication.clipboard()
    mime_data = QMimeData()
    html_format = _generate_html_format(full_html)
    mime_data.setData("text/html", html_format.encode("utf-8"))
    text = soup.get_text()
    mime_data.setText(text)
    clipboard.setMimeData(mime_data)


def copy_as_plain_html(html: str) -> None:
    pyperclip.copy(html)
