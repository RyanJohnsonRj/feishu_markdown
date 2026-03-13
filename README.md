# feishu_markdown

飞书知识库 MCP 工具 & Markdown 导出器。通过飞书应用的 `app_id` / `app_secret` 鉴权，让 AI 助手（Claude、Cursor 等）无需登录即可读取、导出飞书知识库页面，支持图片、表格、超链接、双链等内容。

---

## 目录

- [功能特性](#功能特性)
- [前置条件：创建飞书应用并配置权限](#前置条件创建飞书应用并配置权限)
- [安装](#安装)
- [配置环境变量](#配置环境变量)
- [作为 MCP Server 供 AI 使用](#作为-mcp-server-供-ai-使用)
  - [Claude Desktop 配置](#claude-desktop-配置)
  - [Cursor 配置](#cursor-配置)
  - [可用工具说明](#可用工具说明)
  - [使用示例](#使用示例)
- [Python API 直接调用](#python-api-直接调用)
  - [读取单个页面](#读取单个页面)
  - [列出子页面](#列出子页面)
  - [递归导出并保存到本地](#递归导出并保存到本地)
- [支持的内容类型](#支持的内容类型)
- [常见问题](#常见问题)

---

## 功能特性

- **无需登录**：通过飞书企业自建应用的 `app_id` / `app_secret` 鉴权，AI 可直接访问私有知识库页面。
- **MCP Server**：符合 [MCP（Model Context Protocol）](https://modelcontextprotocol.io/) 规范，可直接对接 Claude Desktop、Cursor 等支持 MCP 的 AI 工具。
- **子页面递归导出**：自动遍历知识库页面及其所有层级的子页面。
- **同级页面**：可通过 `list_wiki_children` 工具查看同级或子级页面列表，再逐一读取。
- **富内容支持**：文本样式、标题、有序/无序列表、代码块、引用、表格、图片、超链接、双链（mention_doc）、待办事项、分割线。
- **本地保存**：可将导出结果按层级目录或平铺方式保存为 `.md` 文件。

---

## 前置条件：创建飞书应用并配置权限

在使用本工具之前，需要在飞书开放平台创建一个**企业自建应用**，并为其开通相关 API 权限。

1. 登录 [飞书开放平台](https://open.feishu.cn/)，点击 **创建企业自建应用**，填写应用名称等信息。
2. 进入应用详情页，记录 **App ID** 和 **App Secret**（后续将作为环境变量使用）。
3. 在 **权限管理** 中开启以下权限（按实际需要选择）：

   | 权限名称 | 说明 |
   |---|---|
   | `wiki:wiki:readonly` | 读取知识库节点信息及子节点列表 |
   | `docx:document:readonly` | 读取文档内容（块列表） |
   | `drive:drive:readonly` | 下载云盘图片文件 |

4. 在 **版本管理与发布** 中发布应用，或在 **开发者后台** 开启调试模式（开发版本）。
5. 在知识库的 **空间设置 → 权限** 中，将该应用添加为成员（或设置为允许所有应用访问）。

> **提示**：若知识库提示"需要登录"，通常是应用未被添加到对应知识库的权限列表，请检查步骤 5。

---

## 安装

**方式一：通过 pip 安装（推荐）**

```bash
pip install feishu-markdown
```

**方式二：从源码安装**

```bash
git clone https://github.com/RyanJohnsonRj/feishu_markdown.git
cd feishu_markdown
pip install -e ".[dev]"
```

---

## 配置环境变量

工具通过以下两个环境变量读取飞书应用凭证：

| 变量名 | 说明 |
|---|---|
| `FEISHU_APP_ID` | 飞书应用的 App ID |
| `FEISHU_APP_SECRET` | 飞书应用的 App Secret |

**Linux / macOS**

```bash
export FEISHU_APP_ID="cli_xxxxxxxxxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Windows（PowerShell）**

```powershell
$env:FEISHU_APP_ID = "cli_xxxxxxxxxxxxxxxx"
$env:FEISHU_APP_SECRET = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

也可以将上面两行写入 `~/.bashrc`、`~/.zshrc` 或 `.env` 文件（自行 source）使其永久生效。

---

## 作为 MCP Server 供 AI 使用

### Claude Desktop 配置

编辑 Claude Desktop 的配置文件（macOS 路径为 `~/Library/Application Support/Claude/claude_desktop_config.json`），添加如下内容：

```json
{
  "mcpServers": {
    "feishu-markdown": {
      "command": "feishu-markdown",
      "env": {
        "FEISHU_APP_ID": "cli_xxxxxxxxxxxxxxxx",
        "FEISHU_APP_SECRET": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

> 如果通过源码安装，`command` 可改为 `python -m feishu_markdown.mcp_server`，并在 `args` 字段中设置参数。

重启 Claude Desktop 后，AI 即可调用飞书知识库工具。

### Cursor 配置

在 Cursor 的 **Settings → MCP** 中点击 **Add new MCP server**，按如下填写：

- **Name**：`feishu-markdown`
- **Type**：`stdio`
- **Command**：`feishu-markdown`
- **Environment Variables**：添加 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`

保存后 Cursor 会自动连接 MCP Server，AI 对话中即可使用飞书工具。

### 可用工具说明

| 工具名 | 说明 | 参数 |
|---|---|---|
| `read_wiki_page` | 读取单个飞书知识库页面，返回 Markdown 内容及元信息（标题、token、文档类型） | `wiki_url_or_token`：飞书知识库 URL 或 wiki token |
| `list_wiki_children` | 列出某个知识库页面的直接子页面列表（标题、token、类型） | `wiki_url_or_token`：飞书知识库 URL 或 wiki token |
| `export_wiki_tree` | 递归导出某个知识库页面及其**所有层级**的子页面，返回完整内容树 | `wiki_url_or_token`：飞书知识库 URL 或 wiki token |

### 使用示例

在 AI 对话框中，可以用自然语言让 AI 调用工具，例如：

```
请帮我读取这个飞书知识库页面并总结主要内容：
https://my.feishu.cn/wiki/F14cwgZrGiM3CxkekUxcEr5YnSg
```

```
列出 https://my.feishu.cn/wiki/F14cwgZrGiM3CxkekUxcEr5YnSg 下的所有子页面。
```

```
把 https://my.feishu.cn/wiki/F14cwgZrGiM3CxkekUxcEr5YnSg 以及它的所有子页面全部导出为 Markdown。
```

---

## Python API 直接调用

除了 MCP Server，也可以在 Python 代码中直接调用。

### 读取单个页面

```python
import os
from feishu_markdown.auth import FeishuAuth
from feishu_markdown.client import FeishuClient, parse_wiki_token
from feishu_markdown.exporter import FeishuExporter

auth = FeishuAuth(
    app_id=os.environ["FEISHU_APP_ID"],
    app_secret=os.environ["FEISHU_APP_SECRET"],
)
client = FeishuClient(auth=auth)
exporter = FeishuExporter(client)

wiki_url = "https://my.feishu.cn/wiki/F14cwgZrGiM3CxkekUxcEr5YnSg"
result = exporter.export_wiki_page(wiki_url, recursive=False)

print(result.title)
print(result.markdown)
```

### 列出子页面

```python
from feishu_markdown.client import parse_wiki_token

token = parse_wiki_token(wiki_url)
node = client.get_wiki_node(token)
children = client.get_wiki_child_nodes(
    space_id=node["space_id"],
    parent_node_token=node["node_token"],
)
for child in children:
    print(child["title"], child["node_token"])
```

### 递归导出并保存到本地

```python
# recursive=True 会自动遍历所有子页面
result = exporter.export_wiki_page(wiki_url, recursive=True)

# 保存为按层级排列的目录结构
saved_files = exporter.save(result, output_dir="./output")
print("已保存文件：", saved_files)

# 也可以平铺到同一目录
saved_files = exporter.save(result, output_dir="./output_flat", flat=True)
```

---

## 支持的内容类型

| 内容类型 | 支持情况 | 说明 |
|---|---|---|
| 标题（H1–H6） | ✅ | 飞书 H7–H9 映射为 H6 |
| 正文文本 | ✅ | 支持加粗、斜体、删除线、行内代码 |
| 超链接 | ✅ | 转换为 `[文本](url)` |
| 双链（mention_doc） | ✅ | 转换为 `[标题](feishu链接)` |
| 有序列表 | ✅ | |
| 无序列表 | ✅ | |
| 代码块 | ✅ | 自动识别编程语言 |
| 引用块 | ✅ | |
| 待办事项（todo） | ✅ | 转换为 `- [ ]` / `- [x]` |
| 分割线 | ✅ | 转换为 `---` |
| 表格 | ✅ | 转换为 Markdown 表格 |
| 图片 | ✅ | 转换为 `![alt](feishu://file/token)`，token 可配合 `client.download_image()` 下载原图 |

---

## 常见问题

**Q：AI 说"需要登录"或返回 401/403 错误？**

A：请检查：
1. 环境变量 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 是否正确设置。
2. 飞书应用是否已发布（或开启调试）。
3. 应用在飞书开放平台是否已开通 `wiki:wiki:readonly` 等所需权限。
4. 目标知识库的权限设置中是否已添加该应用。

**Q：如何获取 wiki token？**

A：直接将飞书知识库页面的完整 URL 传给工具即可，例如 `https://my.feishu.cn/wiki/F14cwgZrGiM3CxkekUxcEr5YnSg`。工具会自动提取其中的 token（`F14cwgZrGiM3CxkekUxcEr5YnSg`）。

**Q：图片无法显示？**

A：工具导出时图片以 `feishu://file/{token}` 形式保存。如需下载实际图片，可调用 Python API 中的 `client.download_image(file_token)` 获取图片二进制内容，再自行保存到本地并替换 Markdown 中的路径。

**Q：如何只导出某一层级而不递归？**

A：在 Python API 中使用 `exporter.export_wiki_page(url, recursive=False)` 只导出当前页面。MCP 工具 `read_wiki_page` 也只读取单页内容，`export_wiki_tree` 才会递归。

