"""飞书 API 客户端

封装知识库（Wiki）、文档（Docx）、云盘（Drive）等 API。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests

from .auth import FeishuAuth

FEISHU_API = "https://open.feishu.cn/open-apis"


def parse_wiki_token(url: str) -> str:
    """从飞书知识库链接中提取 wiki token。

    支持格式:
      - https://my.feishu.cn/wiki/F14cwgZrGiM3CxkekUxcEr5YnSg
      - https://xxx.feishu.cn/wiki/XXXX
      - 直接传入 token 字符串
    """
    m = re.search(r"/wiki/([A-Za-z0-9]+)", url)
    if m:
        return m.group(1)
    # 如果不包含 /wiki/，认为本身就是 token
    if re.fullmatch(r"[A-Za-z0-9_]+", url):
        return url
    raise ValueError(f"Cannot extract wiki token from: {url}")


@dataclass
class FeishuClient:
    """飞书开放平台 API 客户端。"""

    auth: FeishuAuth

    # ------------------------------------------------------------------
    # Wiki / 知识库
    # ------------------------------------------------------------------

    def get_wiki_node(self, token: str) -> dict[str, Any]:
        """获取知识库节点信息（包含 obj_token / obj_type 等）。"""
        url = f"{FEISHU_API}/wiki/v2/spaces/get_node"
        resp = requests.get(url, headers=self.auth.headers, params={"token": token}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"get_wiki_node failed: {data.get('msg')}")
        return data["data"]["node"]

    def get_wiki_child_nodes(self, space_id: str, parent_node_token: str) -> list[dict[str, Any]]:
        """获取知识库下某节点的子节点列表。"""
        url = f"{FEISHU_API}/wiki/v2/spaces/{space_id}/nodes"
        all_nodes: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params: dict[str, Any] = {"parent_node_token": parent_node_token, "page_size": 50}
            if page_token:
                params["page_token"] = page_token
            resp = requests.get(url, headers=self.auth.headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"get_wiki_child_nodes failed: {data.get('msg')}")
            items = data.get("data", {}).get("items", [])
            all_nodes.extend(items)
            if not data.get("data", {}).get("has_more", False):
                break
            page_token = data["data"].get("page_token")
        return all_nodes

    # ------------------------------------------------------------------
    # Docx / 文档
    # ------------------------------------------------------------------

    def get_document_blocks(self, document_id: str) -> list[dict[str, Any]]:
        """获取文档所有块（blocks）。"""
        url = f"{FEISHU_API}/docx/v1/documents/{document_id}/blocks"
        all_blocks: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params: dict[str, str] = {"page_size": "500"}
            if page_token:
                params["page_token"] = page_token
            resp = requests.get(url, headers=self.auth.headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"get_document_blocks failed: {data.get('msg')}")
            items = data.get("data", {}).get("items", [])
            all_blocks.extend(items)
            if not data.get("data", {}).get("has_more", False):
                break
            page_token = data["data"].get("page_token")
        return all_blocks

    def get_document_raw_content(self, document_id: str) -> str:
        """获取文档纯文本内容。"""
        url = f"{FEISHU_API}/docx/v1/documents/{document_id}/raw_content"
        resp = requests.get(url, headers=self.auth.headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"get_document_raw_content failed: {data.get('msg')}")
        return data["data"]["content"]

    # ------------------------------------------------------------------
    # Drive / 云盘
    # ------------------------------------------------------------------

    def download_image(self, file_token: str) -> bytes:
        """下载图片（云盘文件）。"""
        url = f"{FEISHU_API}/drive/v1/medias/{file_token}/download"
        resp = requests.get(url, headers=self.auth.headers, timeout=30)
        resp.raise_for_status()
        return resp.content
