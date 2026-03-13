"""飞书鉴权模块测试"""

import time
from unittest.mock import MagicMock, patch

import pytest

from feishu_markdown.auth import FeishuAuth


class TestFeishuAuth:
    """FeishuAuth 单元测试。"""

    def _mock_token_response(self, token: str = "t-test123", expire: int = 7200):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "code": 0,
            "msg": "ok",
            "tenant_access_token": token,
            "expire": expire,
        }
        return resp

    @patch("feishu_markdown.auth.requests.post")
    def test_token_property_fetches_on_first_call(self, mock_post):
        mock_post.return_value = self._mock_token_response("t-abc")
        auth = FeishuAuth(app_id="app123", app_secret="secret456")

        token = auth.token

        assert token == "t-abc"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["app_id"] == "app123"
        assert call_kwargs[1]["json"]["app_secret"] == "secret456"

    @patch("feishu_markdown.auth.requests.post")
    def test_token_is_cached(self, mock_post):
        mock_post.return_value = self._mock_token_response("t-cached")
        auth = FeishuAuth(app_id="a", app_secret="s")

        _ = auth.token
        _ = auth.token  # second call should use cache

        mock_post.assert_called_once()

    @patch("feishu_markdown.auth.requests.post")
    def test_token_refreshes_when_expired(self, mock_post):
        mock_post.return_value = self._mock_token_response("t-new", expire=7200)
        auth = FeishuAuth(app_id="a", app_secret="s")

        _ = auth.token
        # 手动使 token 过期
        auth._token_expire = time.time() - 1
        _ = auth.token

        assert mock_post.call_count == 2

    @patch("feishu_markdown.auth.requests.post")
    def test_token_error_raises_runtime_error(self, mock_post):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"code": 10003, "msg": "invalid app_id"}
        mock_post.return_value = resp
        auth = FeishuAuth(app_id="bad", app_secret="bad")

        with pytest.raises(RuntimeError, match="invalid app_id"):
            _ = auth.token

    @patch("feishu_markdown.auth.requests.post")
    def test_headers_contain_authorization(self, mock_post):
        mock_post.return_value = self._mock_token_response("t-hdr")
        auth = FeishuAuth(app_id="a", app_secret="s")

        headers = auth.headers

        assert headers["Authorization"] == "Bearer t-hdr"
        assert "Content-Type" in headers
