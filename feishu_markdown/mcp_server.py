"""飞书知识库 MCP Server

提供以下 MCP 工具供 AI 调用:
  - read_wiki_page:  读取飞书知识库页面内容（Markdown 格式）
  - list_wiki_children: 列出知识库页面的子页面
  - export_wiki_tree:  递归导出知识库页面树
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from .auth import FeishuAuth
from .client import FeishuClient, parse_wiki_token
from .exporter import FeishuExporter


def _get_client() -> FeishuClient:
    """从环境变量创建 FeishuClient。"""
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        raise RuntimeError(
            "请设置环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET"
        )
    auth = FeishuAuth(app_id=app_id, app_secret=app_secret)
    return FeishuClient(auth=auth)


# ======================================================================
# Tool implementations
# ======================================================================

def read_wiki_page(wiki_url_or_token: str) -> dict[str, Any]:
    """读取一个飞书知识库页面，返回 Markdown 内容和元信息。"""
    client = _get_client()
    token = parse_wiki_token(wiki_url_or_token)
    node = client.get_wiki_node(token)

    obj_token = node.get("obj_token", "")
    obj_type = node.get("obj_type", "")
    title = node.get("title", "Untitled")

    markdown = ""
    if obj_type in ("docx", "doc"):
        exporter = FeishuExporter(client)
        markdown = exporter.export_document(obj_token)

    return {
        "title": title,
        "token": token,
        "obj_type": obj_type,
        "markdown": markdown,
    }


def list_wiki_children(wiki_url_or_token: str) -> list[dict[str, str]]:
    """列出知识库页面的子页面列表。"""
    client = _get_client()
    token = parse_wiki_token(wiki_url_or_token)
    node = client.get_wiki_node(token)
    space_id = node.get("space_id", "")
    node_token = node.get("node_token", "")

    if not space_id or not node_token:
        return []

    children = client.get_wiki_child_nodes(space_id, node_token)
    return [
        {
            "title": c.get("title", ""),
            "node_token": c.get("node_token", ""),
            "obj_type": c.get("obj_type", ""),
        }
        for c in children
    ]


def export_wiki_tree(wiki_url_or_token: str) -> dict[str, Any]:
    """递归导出整棵知识库页面树，返回 Markdown 内容树。"""
    client = _get_client()
    exporter = FeishuExporter(client)
    result = exporter.export_wiki_page(wiki_url_or_token, recursive=True)
    return _result_to_dict(result)


def _result_to_dict(result: Any) -> dict[str, Any]:
    return {
        "title": result.title,
        "token": result.token,
        "markdown": result.markdown,
        "children": [_result_to_dict(c) for c in result.children],
    }


# ======================================================================
# MCP Server (stdio JSON-RPC)
# ======================================================================

TOOLS = {
    "read_wiki_page": {
        "description": "读取飞书知识库页面并转换为 Markdown。支持通过 app_id/app_secret 鉴权访问，无需登录。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "wiki_url_or_token": {
                    "type": "string",
                    "description": "飞书知识库 URL 或 wiki token",
                }
            },
            "required": ["wiki_url_or_token"],
        },
    },
    "list_wiki_children": {
        "description": "列出飞书知识库页面的子页面和同级页面列表。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "wiki_url_or_token": {
                    "type": "string",
                    "description": "飞书知识库 URL 或 wiki token",
                }
            },
            "required": ["wiki_url_or_token"],
        },
    },
    "export_wiki_tree": {
        "description": "递归导出飞书知识库页面及其所有子页面为 Markdown 格式。支持图片、表格、超链接和双链。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "wiki_url_or_token": {
                    "type": "string",
                    "description": "飞书知识库 URL 或 wiki token",
                }
            },
            "required": ["wiki_url_or_token"],
        },
    },
}

TOOL_FUNCTIONS = {
    "read_wiki_page": read_wiki_page,
    "list_wiki_children": list_wiki_children,
    "export_wiki_tree": export_wiki_tree,
}


def _handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """Handle a single JSON-RPC request."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "feishu-markdown",
                    "version": "0.1.0",
                },
            },
        }

    if method == "notifications/initialized":
        return {}  # no response needed

    if method == "tools/list":
        tool_list = [
            {"name": name, **info} for name, info in TOOLS.items()
        ]
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tool_list},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        fn = TOOL_FUNCTIONS.get(tool_name)
        if not fn:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }
        try:
            result = fn(**arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}
                    ]
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    """MCP stdio server 入口。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = _handle_request(request)
        if response:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
