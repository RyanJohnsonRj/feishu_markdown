"""飞书客户端模块测试"""

from unittest.mock import MagicMock, patch

import pytest

from feishu_markdown.client import FeishuClient, parse_wiki_token
from feishu_markdown.auth import FeishuAuth


class TestParseWikiToken:
    """parse_wiki_token 单元测试。"""

    def test_extract_from_full_url(self):
        url = "https://my.feishu.cn/wiki/F14cwgZrGiM3CxkekUxcEr5YnSg"
        assert parse_wiki_token(url) == "F14cwgZrGiM3CxkekUxcEr5YnSg"

    def test_extract_from_custom_domain(self):
        url = "https://company.feishu.cn/wiki/ABC123"
        assert parse_wiki_token(url) == "ABC123"

    def test_plain_token(self):
        assert parse_wiki_token("F14cwgZrGiM3CxkekUxcEr5YnSg") == "F14cwgZrGiM3CxkekUxcEr5YnSg"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            parse_wiki_token("https://example.com/not-a-wiki")


class TestFeishuClient:
    """FeishuClient API 调用测试（使用 mock）。"""

    def _make_client(self):
        auth = MagicMock(spec=FeishuAuth)
        auth.headers = {"Authorization": "Bearer test-token"}
        return FeishuClient(auth=auth)

    @patch("feishu_markdown.client.requests.get")
    def test_get_wiki_node(self, mock_get):
        resp = MagicMock()
        resp.json.return_value = {
            "code": 0,
            "data": {
                "node": {
                    "node_token": "nt1",
                    "obj_token": "ot1",
                    "obj_type": "docx",
                    "title": "Test Page",
                    "space_id": "sp1",
                }
            },
        }
        mock_get.return_value = resp
        client = self._make_client()

        node = client.get_wiki_node("nt1")

        assert node["title"] == "Test Page"
        assert node["obj_type"] == "docx"

    @patch("feishu_markdown.client.requests.get")
    def test_get_wiki_child_nodes(self, mock_get):
        resp = MagicMock()
        resp.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {"node_token": "child1", "title": "Child 1"},
                    {"node_token": "child2", "title": "Child 2"},
                ],
                "has_more": False,
            },
        }
        mock_get.return_value = resp
        client = self._make_client()

        children = client.get_wiki_child_nodes("sp1", "parent1")

        assert len(children) == 2
        assert children[0]["title"] == "Child 1"

    @patch("feishu_markdown.client.requests.get")
    def test_get_wiki_child_nodes_pagination(self, mock_get):
        page1_resp = MagicMock()
        page1_resp.json.return_value = {
            "code": 0,
            "data": {
                "items": [{"node_token": "c1", "title": "C1"}],
                "has_more": True,
                "page_token": "pt2",
            },
        }
        page2_resp = MagicMock()
        page2_resp.json.return_value = {
            "code": 0,
            "data": {
                "items": [{"node_token": "c2", "title": "C2"}],
                "has_more": False,
            },
        }
        mock_get.side_effect = [page1_resp, page2_resp]
        client = self._make_client()

        children = client.get_wiki_child_nodes("sp1", "parent1")

        assert len(children) == 2
        assert mock_get.call_count == 2

    @patch("feishu_markdown.client.requests.get")
    def test_get_document_blocks(self, mock_get):
        resp = MagicMock()
        resp.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {"block_id": "b1", "block_type": 2, "text": {"elements": []}},
                ],
                "has_more": False,
            },
        }
        mock_get.return_value = resp
        client = self._make_client()

        blocks = client.get_document_blocks("doc1")

        assert len(blocks) == 1
        assert blocks[0]["block_id"] == "b1"

    @patch("feishu_markdown.client.requests.get")
    def test_get_document_raw_content(self, mock_get):
        resp = MagicMock()
        resp.json.return_value = {
            "code": 0,
            "data": {"content": "Hello World"},
        }
        mock_get.return_value = resp
        client = self._make_client()

        content = client.get_document_raw_content("doc1")

        assert content == "Hello World"

    @patch("feishu_markdown.client.requests.get")
    def test_api_error_raises(self, mock_get):
        resp = MagicMock()
        resp.json.return_value = {"code": 99999, "msg": "no permission"}
        mock_get.return_value = resp
        client = self._make_client()

        with pytest.raises(RuntimeError, match="no permission"):
            client.get_wiki_node("bad_token")
