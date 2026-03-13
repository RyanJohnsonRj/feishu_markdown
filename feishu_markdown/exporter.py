"""飞书知识库导出器

递归遍历知识库节点，将文档导出为 Markdown 文件。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from .client import FeishuClient, parse_wiki_token
from .parser import blocks_to_markdown


@dataclass
class ExportResult:
    """单个文档的导出结果。"""
    title: str
    token: str
    markdown: str
    children: list["ExportResult"] = field(default_factory=list)


class FeishuExporter:
    """将飞书知识库页面递归导出为 Markdown。"""

    def __init__(self, client: FeishuClient) -> None:
        self.client = client

    # ------------------------------------------------------------------
    # 导出单个文档
    # ------------------------------------------------------------------

    def export_document(self, document_id: str) -> str:
        """读取文档块并转换为 Markdown 字符串。"""
        blocks = self.client.get_document_blocks(document_id)
        return blocks_to_markdown(blocks)

    # ------------------------------------------------------------------
    # 导出知识库页面（含子页面）
    # ------------------------------------------------------------------

    def export_wiki_page(self, wiki_url_or_token: str, *, recursive: bool = True) -> ExportResult:
        """导出单个知识库页面，可选递归导出子页面。

        Parameters
        ----------
        wiki_url_or_token:
            飞书知识库 URL 或 wiki token
        recursive:
            是否递归导出子页面
        """
        token = parse_wiki_token(wiki_url_or_token)
        node = self.client.get_wiki_node(token)
        return self._export_node(node, recursive=recursive)

    # ------------------------------------------------------------------
    # 保存到磁盘
    # ------------------------------------------------------------------

    def save(self, result: ExportResult, output_dir: str, *, flat: bool = False) -> list[str]:
        """将导出结果保存为 Markdown 文件。

        Parameters
        ----------
        result:
            ExportResult 树
        output_dir:
            输出目录
        flat:
            True 时所有文件平铺在同一目录；False 时按层级创建子目录
        """
        os.makedirs(output_dir, exist_ok=True)
        saved: list[str] = []
        self._save_recursive(result, output_dir, saved, flat=flat)
        return saved

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _export_node(self, node: dict[str, Any], *, recursive: bool) -> ExportResult:
        title = node.get("title", "Untitled")
        node_token = node.get("node_token", "")
        obj_token = node.get("obj_token", "")
        obj_type = node.get("obj_type", "")
        space_id = node.get("space_id", "")

        # 导出文档内容
        markdown = ""
        if obj_type in ("docx", "doc"):
            markdown = self.export_document(obj_token)

        result = ExportResult(title=title, token=node_token, markdown=markdown)

        # 递归子页面
        if recursive and space_id and node_token:
            children_nodes = self.client.get_wiki_child_nodes(space_id, node_token)
            for child_node in children_nodes:
                child_result = self._export_node(child_node, recursive=True)
                result.children.append(child_result)

        return result

    def _save_recursive(
        self,
        result: ExportResult,
        directory: str,
        saved: list[str],
        *,
        flat: bool,
    ) -> None:
        safe_name = _safe_filename(result.title)
        filepath = os.path.join(directory, f"{safe_name}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(result.markdown)
        saved.append(filepath)

        for child in result.children:
            if flat:
                self._save_recursive(child, directory, saved, flat=True)
            else:
                child_dir = os.path.join(directory, _safe_filename(child.title))
                os.makedirs(child_dir, exist_ok=True)
                self._save_recursive(child, child_dir, saved, flat=False)


def _safe_filename(name: str) -> str:
    """将标题转为安全的文件 / 目录名。"""
    # 替换常见的非法字符
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip() or "untitled"
