"""飞书导出器测试"""

import os
import tempfile
from unittest.mock import MagicMock, patch

from feishu_markdown.auth import FeishuAuth
from feishu_markdown.client import FeishuClient
from feishu_markdown.exporter import FeishuExporter, ExportResult, _safe_filename


class TestSafeFilename:
    """文件名安全化测试。"""

    def test_normal_name(self):
        assert _safe_filename("hello world") == "hello world"

    def test_special_chars(self):
        result = _safe_filename('test:file/name*"yes"')
        assert ":" not in result
        assert "/" not in result
        assert "*" not in result
        assert '"' not in result

    def test_empty_name(self):
        assert _safe_filename("") == "untitled"


class TestExportResult:
    """ExportResult 数据结构测试。"""

    def test_basic(self):
        r = ExportResult(title="Test", token="t1", markdown="# Test\n")
        assert r.title == "Test"
        assert r.children == []

    def test_with_children(self):
        child = ExportResult(title="Child", token="c1", markdown="content\n")
        parent = ExportResult(title="Parent", token="p1", markdown="# Parent\n", children=[child])
        assert len(parent.children) == 1
        assert parent.children[0].title == "Child"


class TestFeishuExporter:
    """FeishuExporter 集成测试（使用 mock）。"""

    def _mock_client(self):
        auth = MagicMock(spec=FeishuAuth)
        auth.headers = {"Authorization": "Bearer test"}
        client = MagicMock(spec=FeishuClient)
        client.auth = auth
        return client

    def test_export_document(self):
        client = self._mock_client()
        client.get_document_blocks.return_value = [
            {
                "block_id": "b1",
                "block_type": 3,
                "heading": {
                    "level": 1,
                    "elements": [{"text_run": {"content": "Hello"}}],
                },
            },
            {
                "block_id": "b2",
                "block_type": 2,
                "text": {
                    "elements": [{"text_run": {"content": "World"}}],
                },
            },
        ]
        exporter = FeishuExporter(client)
        md = exporter.export_document("doc123")

        assert "# Hello" in md
        assert "World" in md

    def test_export_wiki_page_single(self):
        client = self._mock_client()
        client.get_document_blocks.return_value = [
            {
                "block_id": "b1",
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": "Content"}}]},
            },
        ]

        # mock get_wiki_node
        node = {
            "node_token": "nt1",
            "obj_token": "ot1",
            "obj_type": "docx",
            "title": "Test Page",
            "space_id": "sp1",
        }
        client.get_wiki_node.return_value = node
        client.get_wiki_child_nodes.return_value = []

        exporter = FeishuExporter(client)
        result = exporter.export_wiki_page("https://my.feishu.cn/wiki/ABCDEF")

        assert result.title == "Test Page"
        assert "Content" in result.markdown
        assert result.children == []

    def test_export_wiki_page_with_children(self):
        client = self._mock_client()

        # Parent node
        parent_node = {
            "node_token": "parent_nt",
            "obj_token": "parent_ot",
            "obj_type": "docx",
            "title": "Parent",
            "space_id": "sp1",
        }
        child_node = {
            "node_token": "child_nt",
            "obj_token": "child_ot",
            "obj_type": "docx",
            "title": "Child",
            "space_id": "sp1",
        }

        client.get_wiki_node.return_value = parent_node
        client.get_wiki_child_nodes.side_effect = [
            [child_node],  # parent's children
            [],  # child's children
        ]
        client.get_document_blocks.side_effect = [
            [{"block_id": "b1", "block_type": 2, "text": {"elements": [{"text_run": {"content": "Parent text"}}]}}],
            [{"block_id": "b2", "block_type": 2, "text": {"elements": [{"text_run": {"content": "Child text"}}]}}],
        ]

        exporter = FeishuExporter(client)
        result = exporter.export_wiki_page("parent_token")

        assert result.title == "Parent"
        assert len(result.children) == 1
        assert result.children[0].title == "Child"
        assert "Child text" in result.children[0].markdown

    def test_save_flat(self):
        result = ExportResult(
            title="Root",
            token="r1",
            markdown="# Root\n",
            children=[
                ExportResult(title="Sub1", token="s1", markdown="sub1 content\n"),
                ExportResult(title="Sub2", token="s2", markdown="sub2 content\n"),
            ],
        )
        client = self._mock_client()
        exporter = FeishuExporter(client)

        with tempfile.TemporaryDirectory() as tmpdir:
            saved = exporter.save(result, tmpdir, flat=True)

            assert len(saved) == 3
            # All files in the same directory
            for path in saved:
                assert os.path.dirname(path) == tmpdir
                assert os.path.exists(path)

    def test_save_hierarchical(self):
        result = ExportResult(
            title="Root",
            token="r1",
            markdown="# Root\n",
            children=[
                ExportResult(title="Sub", token="s1", markdown="sub content\n"),
            ],
        )
        client = self._mock_client()
        exporter = FeishuExporter(client)

        with tempfile.TemporaryDirectory() as tmpdir:
            saved = exporter.save(result, tmpdir, flat=False)

            assert len(saved) == 2
            # Root file in tmpdir
            assert saved[0] == os.path.join(tmpdir, "Root.md")
            # Sub file in Sub directory
            assert "Sub" in saved[1]
