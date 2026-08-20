import pytest

from core import image_hosting
from core.config import config_manager


class FakeResponse:
    def __init__(self, text="", json_data=None):
        self._text = text
        self._json_data = json_data
        self.status_code = 200

    @property
    def text(self):
        return self._text

    def raise_for_status(self):
        return None

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    image_hosting.clear_cache()
    image_hosting._cache_loaded = False
    yield
    config_manager.set("image_host.uploader", "none")
    image_hosting.clear_cache()


class TestUploaderSelection:
    def test_is_enabled_none(self):
        config_manager.set("image_host.uploader", "none")
        assert image_hosting.is_enabled() is False

    def test_is_enabled_catbox(self):
        config_manager.set("image_host.uploader", "catbox")
        assert image_hosting.is_enabled() is True

    def test_is_enabled_custom(self):
        config_manager.set("image_host.uploader", "custom")
        assert image_hosting.is_enabled() is True


class TestUploadImage:
    def test_catbox_upload(self, monkeypatch, tmp_path):
        config_manager.set("image_host.uploader", "catbox")
        img = tmp_path / "a.png"
        img.write_bytes(b"\x89PNG\r\n")

        def fake_post(url, files=None, data=None, timeout=None):
            assert url == "https://catbox.moe/user/api.php"
            assert data == {"reqtype": "fileupload"}
            return FakeResponse(text="https://files.catbox.moe/abc123.png")

        monkeypatch.setattr(image_hosting.httpx, "post", fake_post)
        assert image_hosting.upload_image(str(img)) == "https://files.catbox.moe/abc123.png"

    def test_catbox_bad_response(self, monkeypatch, tmp_path):
        config_manager.set("image_host.uploader", "catbox")
        img = tmp_path / "a.png"
        img.write_bytes(b"x")

        def fake_post(url, files=None, data=None, timeout=None):
            return FakeResponse(text="error")

        monkeypatch.setattr(image_hosting.httpx, "post", fake_post)
        with pytest.raises(RuntimeError):
            image_hosting.upload_image(str(img))

    def test_custom_upload_json(self, monkeypatch, tmp_path):
        config_manager.set("image_host.uploader", "custom")
        config_manager.set("image_host.custom_url", "https://host/upload")
        config_manager.set("image_host.custom_field", "file")
        img = tmp_path / "a.png"
        img.write_bytes(b"x")

        def fake_post(url, files=None, timeout=None):
            assert url == "https://host/upload"
            assert "file" in files
            return FakeResponse(json_data={"url": "https://host/i/1.png"})

        monkeypatch.setattr(image_hosting.httpx, "post", fake_post)
        assert image_hosting.upload_image(str(img)) == "https://host/i/1.png"

    def test_custom_upload_plain_text(self, monkeypatch, tmp_path):
        config_manager.set("image_host.uploader", "custom")
        config_manager.set("image_host.custom_url", "https://host/upload")
        img = tmp_path / "a.png"
        img.write_bytes(b"x")

        def fake_post(url, files=None, timeout=None):
            return FakeResponse(text="https://host/i/2.png")

        monkeypatch.setattr(image_hosting.httpx, "post", fake_post)
        assert image_hosting.upload_image(str(img)) == "https://host/i/2.png"

    def test_custom_missing_url(self, tmp_path):
        config_manager.set("image_host.uploader", "custom")
        config_manager.set("image_host.custom_url", "")
        img = tmp_path / "a.png"
        img.write_bytes(b"x")
        with pytest.raises(RuntimeError):
            image_hosting.upload_image(str(img))

    def test_no_uploader(self, tmp_path):
        config_manager.set("image_host.uploader", "none")
        img = tmp_path / "a.png"
        img.write_bytes(b"x")
        with pytest.raises(RuntimeError):
            image_hosting.upload_image(str(img))


class TestUploadWithCache:
    def test_caches_url(self, monkeypatch, tmp_path):
        config_manager.set("image_host.uploader", "catbox")
        img = tmp_path / "a.png"
        img.write_bytes(b"x")
        calls = []

        def fake_post(url, files=None, data=None, timeout=None):
            calls.append(1)
            return FakeResponse(text="https://files.catbox.moe/cached.png")

        monkeypatch.setattr(image_hosting.httpx, "post", fake_post)
        first = image_hosting.upload_with_cache(str(img))
        second = image_hosting.upload_with_cache(str(img))
        assert first == second == "https://files.catbox.moe/cached.png"
        assert len(calls) == 1


class TestReplaceLocalImages:
    def test_replaces_local_paths(self, monkeypatch, tmp_path):
        config_manager.set("image_host.uploader", "catbox")
        img = tmp_path / "img.png"
        img.write_bytes(b"x")

        def fake_upload(path, timeout=30.0):
            return "https://files.catbox.moe/remote.png"

        monkeypatch.setattr(image_hosting, "upload_with_cache", fake_upload)
        html = f'<p><img src="{img}" alt="x"></p>'
        new_html, count, failed = image_hosting.replace_local_images(html)
        assert count == 1
        assert failed == 0
        assert 'src="https://files.catbox.moe/remote.png"' in new_html

    def test_relative_path_with_base(self, monkeypatch, tmp_path):
        config_manager.set("image_host.uploader", "catbox")
        (tmp_path / "img.png").write_bytes(b"x")

        def fake_upload(path, timeout=30.0):
            return "https://files.catbox.moe/r.png"

        monkeypatch.setattr(image_hosting, "upload_with_cache", fake_upload)
        html = '<p><img src="img.png"></p>'
        new_html, count, _ = image_hosting.replace_local_images(html, str(tmp_path))
        assert count == 1
        assert 'src="https://files.catbox.moe/r.png"' in new_html

    def test_skips_http_and_data(self, monkeypatch):
        def fake_upload(path, timeout=30.0):
            raise AssertionError("should not upload")

        monkeypatch.setattr(image_hosting, "upload_with_cache", fake_upload)
        html = '<p><img src="https://a.com/x.png"><img src="data:image/png;base64,AA=="></p>'
        new_html, count, failed = image_hosting.replace_local_images(html)
        assert count == 0
        assert failed == 0
        assert "https://a.com/x.png" in new_html
        assert "data:image/png;base64,AA==" in new_html

    def test_keeps_original_on_upload_failure(self, monkeypatch, tmp_path):
        config_manager.set("image_host.uploader", "catbox")
        img = tmp_path / "img.png"
        img.write_bytes(b"x")

        def fake_upload(path, timeout=30.0):
            raise RuntimeError("network down")

        monkeypatch.setattr(image_hosting, "upload_with_cache", fake_upload)
        html = f'<p><img src="{img}"></p>'
        new_html, count, failed = image_hosting.replace_local_images(html)
        assert count == 0
        assert failed == 1
        assert f'src="{img}"' in new_html