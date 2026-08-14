import json
import time

from core.conversation_manager import (
    new_id,
    save_conversation,
    load_conversation,
    list_conversations,
    delete_conversation,
    delete_all,
    CONVERSATIONS_DIR,
)


class TestConversationManager:
    def test_new_id_generates_unique_ids(self):
        ids = {new_id() for _ in range(100)}
        assert len(ids) == 100

    def test_new_id_format(self):
        cid = new_id()
        assert cid.startswith("conv_")

    def test_save_and_load_conversation(self, isolated_home):
        cid = new_id()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        save_conversation(cid, messages, "Test Chat")
        loaded = load_conversation(cid)
        assert loaded == messages

    def test_save_creates_file(self, isolated_home):
        cid = new_id()
        save_conversation(cid, [{"role": "user", "content": "Hi"}])
        path = CONVERSATIONS_DIR / f"{cid}.json"
        assert path.exists()

    def test_load_nonexistent_returns_none(self, isolated_home):
        result = load_conversation("nonexistent_id_12345")
        assert result is None

    def test_list_conversations(self, isolated_home):
        save_conversation("conv_001", [{"role": "user", "content": "First"}], "First Chat")
        save_conversation("conv_002", [{"role": "user", "content": "Second"}], "Second Chat")
        time.sleep(0.01)
        convs = list_conversations()
        assert len(convs) >= 2

    def test_list_conversations_structure(self, isolated_home):
        save_conversation("conv_test", [{"role": "user", "content": "Msg"}], "Test")
        convs = list_conversations()
        conv = next(c for c in convs if c["id"] == "conv_test")
        assert conv["id"] == "conv_test"
        assert conv["title"] == "Test"
        assert conv["message_count"] == 1
        assert "created_at" in conv

    def test_delete_conversation(self, isolated_home):
        cid = new_id()
        save_conversation(cid, [{"role": "user", "content": "X"}])
        delete_conversation(cid)
        assert load_conversation(cid) is None

    def test_delete_all(self, isolated_home):
        save_conversation("conv_a", [{"role": "user", "content": "A"}])
        save_conversation("conv_b", [{"role": "user", "content": "B"}])
        delete_all()
        assert list_conversations() == []

    def test_auto_title_from_first_user_message(self, isolated_home):
        cid = new_id()
        messages = [
            {"role": "user", "content": "如何使用 Markdown？"},
            {"role": "assistant", "content": "Here's how..."},
        ]
        save_conversation(cid, messages)
        convs = list_conversations()
        conv = next(c for c in convs if c["id"] == cid)
        assert conv["title"] == "如何使用 Markdown？"

    def test_empty_messages_default_title(self, isolated_home):
        cid = new_id()
        save_conversation(cid, [], "")
        convs = list_conversations()
        conv = next(c for c in convs if c["id"] == cid)
        assert conv["title"] == "未命名对话"

    def test_conversation_preserves_created_at(self, isolated_home):
        cid = new_id()
        save_conversation(cid, [{"role": "user", "content": "Hi"}], "Chat")
        created_at = json.loads(
            (CONVERSATIONS_DIR / f"{cid}.json").read_text("utf-8")
        )["created_at"]
        # Save again with different content
        time.sleep(0.01)
        save_conversation(cid, [{"role": "user", "content": "Bye"}], "Chat")
        new_created_at = json.loads(
            (CONVERSATIONS_DIR / f"{cid}.json").read_text("utf-8")
        )["created_at"]
        assert new_created_at == created_at

    def test_message_count(self, isolated_home):
        cid = new_id()
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]
        save_conversation(cid, messages, "Test")
        convs = list_conversations()
        conv = next(c for c in convs if c["id"] == cid)
        assert conv["message_count"] == 4

    def test_rename_conversation(self, isolated_home):
        cid = new_id()
        save_conversation(cid, [{"role": "user", "content": "Hi"}], "Old Name")
        from core.conversation_manager import rename_conversation
        assert rename_conversation(cid, "New Name") is True
        conv = json.loads((CONVERSATIONS_DIR / f"{cid}.json").read_text("utf-8"))
        assert conv["title"] == "New Name"

    def test_rename_nonexistent(self, isolated_home):
        from core.conversation_manager import rename_conversation
        assert rename_conversation("nonexistent_id", "X") is False
