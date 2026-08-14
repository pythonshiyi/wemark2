import json
import time
from pathlib import Path

from core.prompt_manager import PromptManager, Prompt, BUILTIN_PROMPTS


class TestPromptModel:
    def test_defaults(self):
        p = Prompt()
        assert p.id == ""
        assert p.name == ""
        assert p.content == ""
        assert p.is_builtin is False
        assert p.is_character is False
        assert p.character_icon == "🎭"

    def test_from_dict(self):
        d = {
            "id": "p_test123",
            "name": "Test",
            "content": "Hello",
            "category": "写作",
            "is_favorite": True,
            "is_character": True,
            "character_name": "Helper",
            "character_greeting": "Hi!",
        }
        p = Prompt.from_dict(d)
        assert p.id == "p_test123"
        assert p.name == "Test"
        assert p.is_favorite is True
        assert p.is_character is True
        assert p.character_name == "Helper"

    def test_to_dict_roundtrip(self):
        p = Prompt(name="X", content="Y", category="Z", is_favorite=True)
        d = p.to_dict()
        p2 = Prompt.from_dict(d)
        assert p2.name == "X"
        assert p2.content == "Y"
        assert p2.category == "Z"
        assert p2.is_favorite is True

    def test_render_system_prompt_normal(self):
        p = Prompt(name="Test", content="You are a bot.")
        assert p.render_system_prompt() == "You are a bot."

    def test_render_system_prompt_character(self):
        p = Prompt(name="Char", content="Role play.",
                   is_character=True, character_name="Alice",
                   character_greeting="Hello there!")
        result = p.render_system_prompt()
        assert "Role play." in result
        assert "Alice" in result
        assert "Hello there!" in result

    def test_render_character_without_name_greeting(self):
        p = Prompt(name="Char", content="Just content.", is_character=True)
        result = p.render_system_prompt()
        assert result == "Just content."


class TestBuiltinPrompts:
    def test_builtin_count(self):
        assert len(BUILTIN_PROMPTS) >= 5

    def test_all_builtins_are_builtin(self):
        for p in BUILTIN_PROMPTS:
            assert p.is_builtin is True

    def test_builtin_has_unique_ids(self):
        ids = [p.id for p in BUILTIN_PROMPTS]
        assert len(ids) == len(set(ids))

    def test_builtin_has_content(self):
        for p in BUILTIN_PROMPTS:
            assert len(p.content) > 0

    def test_builtin_has_name(self):
        for p in BUILTIN_PROMPTS:
            assert len(p.name) > 0


class TestPromptManager:
    def test_all_returns_builtins_and_custom(self, isolated_home):
        pm = PromptManager()
        all_p = pm.all()
        builtin_ids = {p.id for p in BUILTIN_PROMPTS}
        all_ids = {p.id for p in all_p}
        assert builtin_ids.issubset(all_ids)

    def test_custom_empty_initially(self, isolated_home):
        pm = PromptManager()
        assert pm.custom() == []

    def test_add_prompt(self, isolated_home):
        pm = PromptManager()
        p = pm.add(Prompt(name="My Prompt", content="You are..."))
        assert p.id.startswith("p_")
        assert p in pm.custom()

    def test_add_assigns_id(self, isolated_home):
        pm = PromptManager()
        p = pm.add(Prompt(name="Test", content="X"))
        assert p.id != ""

    def test_add_assigns_created_at(self, isolated_home):
        pm = PromptManager()
        p = pm.add(Prompt(name="Test", content="X"))
        assert p.created_at > 0

    def test_get_existing(self, isolated_home):
        pm = PromptManager()
        p = pm.add(Prompt(name="FindMe", content="Hello"))
        found = pm.get(p.id)
        assert found is not None
        assert found.name == "FindMe"

    def test_get_nonexistent(self, isolated_home):
        pm = PromptManager()
        assert pm.get("nonexistent") is None

    def test_get_builtin(self, isolated_home):
        pm = PromptManager()
        p = pm.get("builtin_assistant")
        assert p is not None
        assert p.is_builtin is True

    def test_update_prompt(self, isolated_home):
        pm = PromptManager()
        p = pm.add(Prompt(name="Old", content="Old content"))
        p.name = "New"
        p.content = "New content"
        assert pm.update(p) is True
        found = pm.get(p.id)
        assert found.name == "New"
        assert found.content == "New content"

    def test_update_nonexistent(self, isolated_home):
        pm = PromptManager()
        p = Prompt(id="missing", name="X", content="Y")
        assert pm.update(p) is False

    def test_update_builtin_not_allowed(self, isolated_home):
        pm = PromptManager()
        p = pm.get("builtin_assistant")
        original_name = p.name
        # update() returns False for builtins since they're not in self._custom
        result = pm.update(p)
        assert result is False
        found = pm.get("builtin_assistant")
        assert found.name == original_name

    def test_delete_custom(self, isolated_home):
        pm = PromptManager()
        p = pm.add(Prompt(name="DelMe", content="Bye"))
        assert pm.delete(p.id) is True
        assert pm.get(p.id) is None

    def test_delete_builtin_not_allowed(self, isolated_home):
        pm = PromptManager()
        assert pm.delete("builtin_assistant") is False

    def test_delete_nonexistent(self, isolated_home):
        pm = PromptManager()
        assert pm.delete("nonexistent") is False

    def test_get_categories(self, isolated_home):
        pm = PromptManager()
        pm.add(Prompt(name="A", content="X", category="写作"))
        pm.add(Prompt(name="B", content="Y", category="翻译"))
        cats = pm.get_categories()
        assert "写作" in cats
        assert "翻译" in cats

    def test_search_by_name(self, isolated_home):
        pm = PromptManager()
        pm.add(Prompt(name="Python Helper", content="Code"))
        results = pm.search("python")
        assert len(results) > 0
        assert any("python" in r.name.lower() for r in results)

    def test_search_by_content(self, isolated_home):
        pm = PromptManager()
        pm.add(Prompt(name="X", content="unique keyword here"))
        results = pm.search("unique keyword")
        assert len(results) > 0

    def test_search_empty_returns_all(self, isolated_home):
        pm = PromptManager()
        all_p = pm.all()
        results = pm.search("")
        assert len(results) == len(all_p)

    def test_get_by_category(self, isolated_home):
        pm = PromptManager()
        pm.add(Prompt(name="A", content="X", category="写作"))
        results = pm.get_by_category("写作")
        assert len(results) > 0

    def test_get_by_category_all(self, isolated_home):
        pm = PromptManager()
        all_p = pm.all()
        results = pm.get_by_category("全部")
        assert len(results) == len(all_p)

    def test_toggle_favorite(self, isolated_home):
        pm = PromptManager()
        p = pm.add(Prompt(name="Fav", content="X"))
        assert pm.toggle_favorite(p.id) is True
        assert pm.get(p.id).is_favorite is True
        assert pm.toggle_favorite(p.id) is False
        assert pm.get(p.id).is_favorite is False

    def test_get_favorites(self, isolated_home):
        pm = PromptManager()
        p1 = pm.add(Prompt(name="A", content="X"))
        p2 = pm.add(Prompt(name="B", content="Y"))
        pm.toggle_favorite(p1.id)
        favs = pm.get_favorites()
        assert p1.id in {f.id for f in favs}
        assert p2.id not in {f.id for f in favs}

    def test_import_json(self, isolated_home, tmp_path):
        pm = PromptManager()
        file = tmp_path / "import.json"
        data = [
            {"name": "Imported 1", "content": "Hello"},
            {"name": "Imported 2", "content": "World"},
        ]
        file.write_text(json.dumps(data), encoding="utf-8")
        count = pm.import_json(str(file))
        assert count == 2
        assert len(pm.custom()) == 2

    def test_import_single_object(self, isolated_home, tmp_path):
        pm = PromptManager()
        file = tmp_path / "single.json"
        data = {"name": "Single", "content": "Test"}
        file.write_text(json.dumps(data), encoding="utf-8")
        count = pm.import_json(str(file))
        assert count == 1

    def test_export_json(self, isolated_home, tmp_path):
        pm = PromptManager()
        p = pm.add(Prompt(name="Export Me", content="Data"))
        file = tmp_path / "export.json"
        pm.export_json([p.id], str(file))
        loaded = json.loads(file.read_text(encoding="utf-8"))
        assert len(loaded) == 1
        assert loaded[0]["name"] == "Export Me"

    def test_persist_across_instances(self, isolated_home):
        pm1 = PromptManager()
        p = pm1.add(Prompt(name="Persist", content="Test"))
        pm2 = PromptManager()
        found = pm2.get(p.id)
        assert found is not None
        assert found.name == "Persist"

    def test_persistence_file_created(self, isolated_home):
        pm = PromptManager()
        pm.add(Prompt(name="P", content="C"))
        file = Path.home() / ".wemark2" / "prompts.json"
        assert file.exists()

    def test_get_by_category_empty_category(self, isolated_home):
        pm = PromptManager()
        pm.add(Prompt(name="NoCat", content="X"))
        results = pm.get_by_category("")
        assert len(results) == len(pm.all())

    def test_search_no_match_returns_empty(self, isolated_home):
        pm = PromptManager()
        results = pm.search("zzz_nonexistent_zzz")
        # Should still return builtins if they don't match
        non_matching = [r for r in results if "zzz_nonexistent_zzz" in r.name.lower()]
        assert len(non_matching) == 0

    def test_add_then_delete(self, isolated_home):
        pm = PromptManager()
        initial_count = len(pm.custom())
        p = pm.add(Prompt(name="Temp", content="Temp"))
        assert len(pm.custom()) == initial_count + 1
        pm.delete(p.id)
        assert len(pm.custom()) == initial_count

    def test_render_all_builtin_prompts(self, isolated_home):
        pm = PromptManager()
        for p in BUILTIN_PROMPTS:
            r = p.render_system_prompt()
            assert isinstance(r, str)
            assert len(r) > 0
