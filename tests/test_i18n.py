from core.i18n import tr, load_language, set_language, _TRANSLATIONS, _locales_path


class TestI18n:
    def test_tr_returns_known_key(self):
        load_language("zh-CN")
        assert tr("app_title") == "微墨 WeMark"

    def test_tr_english_translation(self):
        load_language("en-US")
        assert tr("app_title") == "WeMark Editor"

    def test_tr_fallback_to_key_for_missing(self):
        load_language("zh-CN")
        result = tr("nonexistent_key_xyz")
        assert result == "nonexistent_key_xyz"

    def test_tr_with_format_args(self):
        load_language("zh-CN")
        result = tr("word_count").format(42)
        assert result == "字数: 42"

    def test_tr_english_with_format_args(self):
        load_language("en-US")
        result = tr("word_count").format(100)
        assert result == "Words: 100"

    def test_tr_with_format_read_time(self):
        load_language("zh-CN")
        result = tr("read_time").format(5)
        assert result == "预计阅读: 5 分钟"

    def test_tr_multiline_about_text(self):
        load_language("zh-CN")
        result = tr("about_text")
        assert "微墨 WeMark" in result
        assert "微信公众号" in result

    def test_tr_english_about_text(self):
        load_language("en-US")
        result = tr("about_text")
        assert "WeMark" in result

    def test_locales_directory_exists(self):
        path = _locales_path()
        assert path.exists()
        assert path.is_dir()

    def test_default_is_chinese_when_not_set(self, isolated_home):
        load_language(None)
        assert tr("app_title") == "微墨 WeMark"

    def test_set_language_persists(self, isolated_home):
        set_language("en-US")
        assert tr("app_title") == "WeMark Editor"
        set_language("zh-CN")
        assert tr("app_title") == "微墨 WeMark"


class TestI18nEdgeCases:
    def test_tr_unknown_format_key_does_not_crash(self):
        load_language("zh-CN")
        result = tr("app_title", unknown_arg="test")
        assert result == "微墨 WeMark"

    def test_tr_empty_kwargs(self):
        load_language("zh-CN")
        result = tr("word_count")
        assert result == "字数: {0}"

    def test_all_zh_keys_exist_in_en(self):
        """Ensure zh-CN and en-US have the same keys."""
        import json
        zh = json.loads((_locales_path() / "zh-CN.json").read_text("utf-8"))
        en = json.loads((_locales_path() / "en-US.json").read_text("utf-8"))
        for key in zh:
            assert key in en, f"Key '{key}' missing from en-US.json"

    def test_all_en_keys_exist_in_zh(self):
        """Ensure en-US keys also exist in zh-CN."""
        import json
        en = json.loads((_locales_path() / "en-US.json").read_text("utf-8"))
        zh = json.loads((_locales_path() / "zh-CN.json").read_text("utf-8"))
        for key in en:
            assert key in zh, f"Key '{key}' missing from zh-CN.json"
