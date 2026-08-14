# 📝 微墨 WeMark · 微信公众号 Markdown 编辑器 / WeChat Markdown Editor

> **中文为主 · English follows**（完整中文介绍 + 完整英文简介）

**微墨 WeMark** 是一款专为微信公众号排版打造的桌面 Markdown 编辑器 —— **简约 · 高效 · 专注**。写作、预览、一键复制公众号富文本，全程无需切换工具。

*WeMark is a desktop Markdown editor crafted for WeChat Official Account (WeChat MP) publishing — minimal, efficient, focused. Write, preview, and copy rich text for WeChat with one click, without ever leaving the app.*

## 目录 / Table of Contents

- [中文介绍（完整）](#中文介绍完整)
- [English Introduction (Full)](#english-introduction-full)
- [品牌与关注 / Follow Us](#品牌与关注--follow-us)

## 中文介绍（完整）

### 功能特性

#### ✍️ 写作体验

- **所见即所得**：左侧编辑、右侧实时预览（200ms 防抖自动刷新），支持 Markdown 语法高亮与当前行高亮
- **一键格式化**：自动整理空行、标题层级、列表与表格对齐，脏乱草稿秒变规范排版
- **完整格式工具栏**：加粗 / 斜体 / 删除线 / 行内代码 / H1-H3 标题 / 引用 / 有序·无序列表 / 链接 / 代码块 / 图片 / 表格 / 分隔线
- **编辑增强**：括号自动配对、`/` 命令唤起代码片段、智能缩进（Tab/Shift+Tab）、复制行 / 上移 / 下移、行号开关、字体 / 行距 / 段距可调、拖拽图片直接插入
- **专注模式与打字机模式**：聚焦当前段落（Ctrl+J）、打字机滚动（Ctrl+L）、全屏沉浸写作（F11）
- **自动保存**：默认每 60 秒自动保存，意外关闭不丢稿
- **查找替换**：支持正则、区分大小写、全词匹配（Ctrl+F，F3 / Shift+F3 上一个 / 下一个）

#### 🤖 AI 辅助（默认对接 DeepSeek V4，支持任意 OpenAI 兼容端点）

- **一键动作**：✍ 续写（Ctrl+Shift+W）/ ✨ 润色（Ctrl+Shift+P）/ 🌐 翻译（Ctrl+Shift+T）/ 📋 摘要（Ctrl+Shift+M）——选中文本即刻处理，结果可直接替换原文
- **AI 对话面板**（Ctrl+Shift+A）：气泡式对话、思考过程展示（可折叠）、重新生成、停止生成
- **提示词管理**：内置提示词库，支持自定义预设与 🎭 角色设定（自定义人格 + 开场白）
- **对话历史**：自动保存、搜索、重命名、删除，一键新建对话
- **可调参数**：temperature / top_p / 思考模式 / max_tokens / 上下文轮数上限

#### 📤 公众号发布

- **一键复制公众号富文本**（Ctrl+Shift+C）：样式内联，粘贴即用
- **24 套精选主题模板**：default、academic、business、cloud、coral、cozy、elegant_dark、forest、fresh、impact、lavender、literary、magazine、minimal、news、nord、ocean、paper、retro、sunset、tech、typewriter、warm 等，支持自定义 CSS
- **导出**：📄 PDF / 🖼 图片（长图）/ 📋 微信富文本 / 📝 HTML（Ctrl+Shift+E 导出对话框，Ctrl+Shift+I 复制预览图）
- **数学公式**：支持 `$...$` LaTeX 行内与块级公式渲染

#### 🧭 界面与个性化

- **大纲面板**（Ctrl+Shift+O）：标题层级导航，点击跳转
- **多标签页**：同时编辑多篇文章，Ctrl+W 关闭
- **布局灵活**：AI 面板 / 预览面板可停靠可调宽，一键左右布局切换（Ctrl+Shift+L）与重置
- **主题**：亮色 / 暗色
- **中英双语界面**：zh-CN / en-US 一键切换
- **最近文件**：菜单直达，续写无缝

### 安装与启动

```bash
# Python 3.9+ / 3.10+
pip install -r requirements.txt
python main.py
```

### AI 配置

1. 打开「设置」（Ctrl+,），填入 API Key（默认端点 https://api.deepseek.com，模型 deepseek-v4-flash）
2. 支持任意 OpenAI 兼容 API：修改 base_url 与 model 即可

配置保存在 `~/.wemark2/config.json`。

### 快捷键速查

| 快捷键 | 功能 |
|--------|------|
| Ctrl+Shift+W / P / T / M | AI 续写 / 润色 / 翻译 / 摘要 |
| Ctrl+Shift+A | AI 对话面板 |
| Ctrl+Shift+E / C / I | 导出 / 复制微信格式 / 复制预览图 |
| Ctrl+P | 预览面板 |
| Ctrl+Shift+O | 大纲面板 |
| Ctrl+J / Ctrl+L | 专注模式 / 打字机滚动 |
| Ctrl+Shift+L | 左右布局切换 |
| Ctrl+F | 查找替换 |
| F11 | 全屏 |
| Ctrl+, | 设置 |

### 技术栈

Python · PySide6 + QtWebEngine · markdown-it-py（+ dollarmath 公式插件）· openai · httpx · beautifulsoup4 · PyInstaller（可打包）

### 测试

```bash
pip install -r tests/requirements-test.txt
pytest
```

13 个测试模块覆盖：AI 客户端、渲染器、剪贴板、配置、会话管理、编辑器、大纲、模板选择、i18n、Markdown 高亮等（359 个用例）。

---

## English Introduction (Full)

### 📝 WeMark — WeChat Official Account Markdown Editor

**WeMark** (Chinese: 微墨) is a **desktop Markdown editor purpose-built for WeChat Official Account publishing** — minimal, efficient, focused. It is an independent product by **ShiYi AIGC (十一AIGC)**.

### Features

**Writing**
- Live split view: Markdown editor + real-time preview (200ms debounced refresh, QtWebEngine-based)
- One-click Markdown formatting: auto-fixes blank lines, heading levels, list and table alignment
- Full formatting toolbar: bold / italic / strikethrough / inline code / H1–H3 / quotes / lists / links / code blocks / images / tables / horizontal rules
- Editor enhancements: bracket auto-pairing, `/` snippet commands, smart indent, duplicate / move lines, line numbers, adjustable font / line spacing / paragraph spacing, drag-and-drop image insertion
- Focus mode (Ctrl+J), typewriter scrolling (Ctrl+L), fullscreen (F11), auto-save every 60s
- Find & replace with regex / case-sensitive / whole-word options

**AI Assistant (defaults to DeepSeek V4, any OpenAI-compatible endpoint works)**
- One-click actions on selected text: ✍ continue writing (Ctrl+Shift+W) / ✨ polish (Ctrl+Shift+P) / 🌐 translate (Ctrl+Shift+T) / 📋 summarize (Ctrl+Shift+M)
- Chat panel (Ctrl+Shift+A) with bubble UI, collapsible reasoning display, regenerate & stop
- Prompt presets, custom prompts, and 🎭 character roles (persona + greeting)
- Conversation history with search / rename / delete; configurable temperature, top_p, reasoning, and context-turn limits

**WeChat Publishing**
- One-click copy of WeChat rich text (Ctrl+Shift+C) — inline styles, paste-ready
- 24 curated themes (default, academic, business, cloud, coral, cozy, elegant_dark, forest, fresh, impact, lavender, literary, magazine, minimal, news, nord, ocean, paper, retro, sunset, tech, typewriter, warm…) plus custom CSS
- Export: PDF / image (long screenshot) / WeChat rich text / HTML (Ctrl+Shift+E)
- LaTeX math rendering (`$...$` via markdown-it dollarmath)

**UI & Personalization**
- Outline panel (Ctrl+Shift+O), multi-tab editing (Ctrl+W), dockable AI & preview panels, layout swap (Ctrl+Shift+L) and reset
- Light / dark themes, zh-CN / en-US UI, recent-files menu

### Getting Started

```bash
pip install -r requirements.txt
python main.py
```

Open Settings (Ctrl+,) and enter your API Key (defaults to https://api.deepseek.com, model deepseek-v4-flash; any OpenAI-compatible base URL and model works). Config is stored at `~/.wemark2/config.json`.

### Tech Stack

Python · PySide6 + QtWebEngine · markdown-it-py (dollarmath plugin) · openai · httpx · beautifulsoup4 · PyInstaller

### Tests

```bash
pip install -r tests/requirements-test.txt
pytest
```

13 test modules cover the AI client, renderer, clipboard, config, conversation manager, editor, outline, template selector, i18n, and Markdown highlighting (359 test cases).

---

## 品牌与关注 / Follow Us

**微墨 WeMark** 与 **鲸语 WhaleTalk** 由 **十一AIGC** 出品——专注 AI 工具与效率应用的独立创作者。

更多 AI 玩法、工具教程与新品动态，欢迎关注公众号：

> **📱 微信公众号：十一AIGC**

*WeMark and WhaleTalk are crafted by **ShiYi AIGC (十一AIGC)**, an independent creator focused on AI tools and productivity apps. Follow our official WeChat account for more AI tips, tutorials, and product news.*

如果你喜欢这个项目，欢迎 ⭐ Star、分享给朋友，或在评论区留下你的建议 —— 你的支持是我们持续更新的最大动力！

*If you like this project, please ⭐ Star it, share it, and leave your feedback — your support keeps us shipping!*
