"""MCP Server 测试"""

import json

from feishu_markdown.mcp_server import _handle_request, TOOLS


class TestMCPProtocol:
    """MCP 协议处理测试。"""

    def test_initialize(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = _handle_request(req)

        assert resp["id"] == 1
        assert "result" in resp
        assert resp["result"]["serverInfo"]["name"] == "feishu-markdown"
        assert "tools" in resp["result"]["capabilities"]

    def test_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = _handle_request(req)

        tools = resp["result"]["tools"]
        tool_names = {t["name"] for t in tools}
        assert "read_wiki_page" in tool_names
        assert "list_wiki_children" in tool_names
        assert "export_wiki_tree" in tool_names

    def test_tools_list_has_schemas(self):
        for name, info in TOOLS.items():
            assert "description" in info, f"{name} missing description"
            assert "inputSchema" in info, f"{name} missing inputSchema"
            schema = info["inputSchema"]
            assert "properties" in schema
            assert "wiki_url_or_token" in schema["properties"]

    def test_unknown_method(self):
        req = {"jsonrpc": "2.0", "id": 3, "method": "unknown/method", "params": {}}
        resp = _handle_request(req)
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_unknown_tool(self):
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }
        resp = _handle_request(req)
        assert "error" in resp

    def test_tools_call_missing_env(self):
        """调用工具但未设置环境变量应返回错误。"""
        req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "read_wiki_page",
                "arguments": {"wiki_url_or_token": "test"},
            },
        }
        resp = _handle_request(req)
        # Should return error content, not crash
        assert resp["result"]["isError"] is True
        assert "FEISHU_APP_ID" in resp["result"]["content"][0]["text"]

    def test_notifications_initialized(self):
        req = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        resp = _handle_request(req)
        assert resp == {}
