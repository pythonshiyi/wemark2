import json
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def isolated_home(monkeypatch):
    """Create a temp home directory to isolate file I/O tests."""
    tmp = Path(tempfile.mkdtemp())
    (tmp / ".wemark2").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", lambda: tmp)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_markdown() -> str:
    return """# 标题一

## 标题二

这是一段**加粗**和*斜体*文本，还有~~删除线~~和`行内代码`.

- 无序列表项 1
- 无序列表项 2

1. 有序列表项 1
2. 有序列表项 2

> 这是一段引用

| 列1 | 列2 |
| --- | --- |
| A | B |

```python
def hello():
    print("Hello")
```

![图片](https://example.com/img.png)

[链接文本](https://example.com)

---

数学公式 $E = mc^2$

```mermaid
graph TD;
    A-->B;
```
"""


@pytest.fixture
def config_dict() -> dict:
    return {
        "window": {"width": 1200, "height": 800},
        "editor": {"font_size": 14},
        "ai": {"api_key": "test-key"},
        "language": "en-US",
        "theme": "dark",
        "recent_files": ["/path/to/file.md"],
    }
