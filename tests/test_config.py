import json
from pathlib import Path

from core.config import ConfigManager, _deep_merge, DEFAULT_CONFIG


class TestDeepMerge:
    def test_simple_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99}, "b": 3}

    def test_new_key_in_override(self):
        base = {"a": 1}
        override = {"b": 2}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_override_non_dict_with_dict(self):
        base = {"a": 1, "b": {"x": 1}}
        override = {"a": {"y": 2}}
        result = _deep_merge(base, override)
        assert result == {"a": {"y": 2}, "b": {"x": 1}}

    def test_empty_override(self):
        base = {"a": 1}
        result = _deep_merge(base, {})
        assert result == {"a": 1}

    def test_deeply_nested(self):
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"c": 99}}}
        result = _deep_merge(base, override)
        assert result == {"a": {"b": {"c": 99, "d": 2}}}


class TestConfigManagerDefaults:
    def test_default_config_has_required_keys(self):
        assert "window" in DEFAULT_CONFIG
        assert "editor" in DEFAULT_CONFIG
        assert "ai" in DEFAULT_CONFIG
        assert "language" in DEFAULT_CONFIG
        assert "theme" in DEFAULT_CONFIG
        assert "recent_files" in DEFAULT_CONFIG

    def test_default_config_window_dimensions(self):
        assert DEFAULT_CONFIG["window"]["width"] == 1400
        assert DEFAULT_CONFIG["window"]["height"] == 900

    def test_default_config_editor_font(self):
        assert DEFAULT_CONFIG["editor"]["font_size"] == 16
        assert "Consolas" in DEFAULT_CONFIG["editor"]["font_family"]

    def test_default_config_language(self):
        assert DEFAULT_CONFIG["language"] == "zh-CN"

    def test_default_config_theme(self):
        assert DEFAULT_CONFIG["theme"] == "light"


class TestConfigManagerPersistence:
    def test_load_without_existing_file_returns_defaults(self, isolated_home):
        cm = ConfigManager()
        assert cm.get("language") == "zh-CN"
        assert cm.get("theme") == "light"
        assert cm.get("window.width") == 1400

    def test_save_and_reload(self, isolated_home):
        cm = ConfigManager()
        cm.set("theme", "dark")
        cm.set("window.width", 800)

        cm2 = ConfigManager()
        assert cm2.get("theme") == "dark"
        assert cm2.get("window.width") == 800

    def test_set_nested_key(self, isolated_home):
        cm = ConfigManager()
        cm.set("ai.model", "deepseek-v4-flash")
        assert cm.get("ai.model") == "deepseek-v4-flash"

    def test_get_with_default_fallback(self, isolated_home):
        cm = ConfigManager()
        assert cm.get("nonexistent.key", "fallback") == "fallback"

    def test_get_partial_key_returns_dict(self, isolated_home):
        cm = ConfigManager()
        editor = cm.get("editor")
        assert isinstance(editor, dict)
        assert editor["font_size"] == 16

    def test_get_missing_key_none(self, isolated_home):
        cm = ConfigManager()
        assert cm.get("completely.missing") is None

    def test_update_merges_correctly(self, isolated_home):
        cm = ConfigManager()
        cm.update({"theme": "dark", "editor": {"font_size": 20}})
        assert cm.get("theme") == "dark"
        assert cm.get("editor.font_size") == 20
        assert cm.get("editor.font_family") == DEFAULT_CONFIG["editor"]["font_family"]

    def test_save_persists_to_file(self, isolated_home):
        cm = ConfigManager()
        cm.set("theme", "dark")
        config_path = Path.home() / ".wemark2" / "config.json"
        assert config_path.exists()
        with open(config_path, "r") as f:
            data = json.load(f)
        assert data["theme"] == "dark"


class TestConfigManagerEdgeCases:
    def test_invalid_json_file_falls_back_to_defaults(self, isolated_home):
        config_path = Path.home() / ".wemark2" / "config.json"
        config_path.write_text("{invalid json}", encoding="utf-8")
        cm = ConfigManager()
        assert cm.get("language") == "zh-CN"
        assert cm.get("window.width") == 1400

    def test_set_creates_intermediate_keys(self, isolated_home):
        cm = ConfigManager()
        cm.set("custom.deeply.nested.key", "value")
        assert cm.get("custom.deeply.nested.key") == "value"

    def test_config_property(self, isolated_home):
        cm = ConfigManager()
        assert isinstance(cm.as_dict(), dict)

    def test_save_returns_true_on_success(self, isolated_home):
        cm = ConfigManager()
        assert cm.save() is True

    def test_empty_user_config_uses_defaults(self, isolated_home):
        config_path = Path.home() / ".wemark2" / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        cm = ConfigManager()
        assert cm.get("language") == "zh-CN"
        assert cm.get("window.width") == 1400
        assert cm.get("ai.model") == "deepseek-v4-flash"

    def test_override_with_new_section(self, isolated_home):
        cm = ConfigManager()
        cm.set("plugins.my_plugin.enabled", True)
        assert cm.get("plugins.my_plugin.enabled") is True
        assert cm.get("plugins.my_plugin") == {"enabled": True}
