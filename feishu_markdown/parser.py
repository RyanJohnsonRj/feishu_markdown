"""飞书文档 Block → Markdown 转换器

支持的块类型:
  - 文本 (text / heading)
  - 图片 (image)
  - 表格 (table / table_cell)
  - 超链接 (inline link)
  - 双链 / mention_doc
  - 代码块 (code)
  - 有序 / 无序列表 (ordered / bullet)
  - 引用 (quote)
  - 分割线 (divider)
  - todo
"""

from __future__ import annotations

from typing import Any


# ======================================================================
# Text element helpers
# ======================================================================

def _style_to_md(text: str, style: dict[str, Any] | None) -> str:
    """根据文本样式 (bold / italic / strikethrough / code) 包裹 Markdown 标记。"""
    if not style or not text:
        return text
    if style.get("inline_code"):
        return f"`{text}`"
    if style.get("bold"):
        text = f"**{text}**"
    if style.get("italic"):
        text = f"*{text}*"
    if style.get("strikethrough"):
        text = f"~~{text}~~"
    return text


def _render_text_element(elem: dict[str, Any]) -> str:
    """将单个 TextElement 转为 Markdown 文本片段。"""
    # mention_doc → 双链
    if "mention_doc" in elem:
        md = elem["mention_doc"]
        title = md.get("title", "链接")
        token = md.get("token", "")
        obj_type = md.get("obj_type", "")
        url = md.get("url", "")
        if url:
            return f"[{title}]({url})"
        if token:
            link = f"https://feishu.cn/docx/{token}" if obj_type == "docx" else f"https://feishu.cn/wiki/{token}"
            return f"[{title}]({link})"
        return f"[[{title}]]"

    # text_run → 普通 / 带样式 / 带链接
    tr = elem.get("text_run")
    if not tr:
        return ""
    content = tr.get("content", "")
    style = tr.get("text_element_style", {})

    # 链接
    link = style.get("link", {})
    link_url = link.get("url", "") if isinstance(link, dict) else ""

    styled = _style_to_md(content, style)
    if link_url:
        return f"[{styled}]({link_url})"
    return styled


def _render_text_elements(elements: list[dict[str, Any]]) -> str:
    """将一组 TextElement 合并为一行 Markdown。"""
    return "".join(_render_text_element(e) for e in elements)


# ======================================================================
# Block‑level renderers
# ======================================================================

def _render_heading(block: dict[str, Any]) -> str:
    level = block.get("heading", {}).get("level", 1)
    # Feishu heading levels: 1‑9，Markdown 只支持 1‑6
    level = min(level, 6)
    elements = block.get("heading", {}).get("elements", [])
    text = _render_text_elements(elements)
    return f"{'#' * level} {text}"


def _render_text_block(block: dict[str, Any]) -> str:
    elements = block.get("text", {}).get("elements", [])
    return _render_text_elements(elements)


def _render_code(block: dict[str, Any]) -> str:
    code_info = block.get("code", {})
    elements = code_info.get("elements", [])
    language = code_info.get("language", "")
    # language 可能是数字枚举，做个简单映射
    lang_map: dict[int, str] = {
        1: "plaintext", 2: "abap", 3: "ada", 4: "apache", 5: "apex",
        6: "assembly", 7: "bash", 8: "csharp", 9: "cpp", 10: "c",
        11: "cobol", 12: "css", 13: "coffeescript", 14: "d", 15: "dart",
        16: "delphi", 17: "django", 18: "dockerfile", 19: "erlang",
        22: "go", 25: "html", 28: "java", 29: "javascript",
        31: "json", 33: "kotlin", 35: "lua", 37: "markdown",
        40: "objectivec", 43: "php", 46: "python", 49: "ruby",
        50: "rust", 52: "scala", 54: "shell", 55: "sql",
        56: "swift", 59: "typescript", 62: "xml", 63: "yaml",
    }
    if isinstance(language, int):
        language = lang_map.get(language, "")
    text = _render_text_elements(elements)
    return f"```{language}\n{text}\n```"


def _render_bullet(block: dict[str, Any]) -> str:
    elements = block.get("bullet", {}).get("elements", [])
    text = _render_text_elements(elements)
    return f"- {text}"


def _render_ordered(block: dict[str, Any]) -> str:
    elements = block.get("ordered", {}).get("elements", [])
    text = _render_text_elements(elements)
    return f"1. {text}"


def _render_quote(block: dict[str, Any]) -> str:
    elements = block.get("quote", {}).get("elements", [])
    text = _render_text_elements(elements)
    return f"> {text}"


def _render_todo(block: dict[str, Any]) -> str:
    todo = block.get("todo", {})
    elements = todo.get("elements", [])
    done = todo.get("style", {}).get("done", False)
    text = _render_text_elements(elements)
    checkbox = "[x]" if done else "[ ]"
    return f"- {checkbox} {text}"


def _render_divider(block: dict[str, Any]) -> str:  # noqa: ARG001
    return "---"


def _render_image(block: dict[str, Any]) -> str:
    img = block.get("image", {})
    file_token = img.get("token", "")
    alt = img.get("alt", "image")
    if not alt:
        alt = "image"
    if file_token:
        return f"![{alt}](feishu://file/{file_token})"
    return f"![{alt}]()"


# ======================================================================
# Table helpers
# ======================================================================

def _render_table(block: dict[str, Any], blocks_by_id: dict[str, dict[str, Any]]) -> str:
    """将 table block 渲染为 Markdown 表格。

    Feishu table 结构:
      table block → children 为 table_cell block_id 列表
      table.property 包含 row_size / column_size
    """
    table_info = block.get("table", {})
    prop = table_info.get("property", {})
    cols = prop.get("column_size", 0)
    rows = prop.get("row_size", 0)
    children = block.get("children", [])

    if not cols or not rows:
        return ""

    # children 按行优先排列
    md_rows: list[list[str]] = []
    for r in range(rows):
        row_cells: list[str] = []
        for c in range(cols):
            idx = r * cols + c
            if idx < len(children):
                cell_id = children[idx]
                cell_block = blocks_by_id.get(cell_id, {})
                cell_text = _render_table_cell(cell_block, blocks_by_id)
            else:
                cell_text = ""
            row_cells.append(cell_text)
        md_rows.append(row_cells)

    if not md_rows:
        return ""

    lines: list[str] = []
    # header row
    lines.append("| " + " | ".join(md_rows[0]) + " |")
    lines.append("| " + " | ".join(["---"] * cols) + " |")
    for row in md_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _render_table_cell(cell_block: dict[str, Any], blocks_by_id: dict[str, dict[str, Any]]) -> str:
    """递归渲染 table_cell 中的子块，合并为单行文本。"""
    children = cell_block.get("children", [])
    parts: list[str] = []
    for child_id in children:
        child = blocks_by_id.get(child_id, {})
        text = render_block(child, blocks_by_id)
        if text:
            parts.append(text.replace("\n", " "))
    return " ".join(parts)


# ======================================================================
# Public API
# ======================================================================

BLOCK_RENDERERS: dict[int, Any] = {
    2: _render_text_block,    # text
    3: _render_heading,       # heading1‑9 统一在 heading 里
    4: _render_heading,
    5: _render_heading,
    6: _render_heading,
    7: _render_heading,
    8: _render_heading,
    9: _render_heading,
    10: _render_heading,
    11: _render_heading,
    13: _render_bullet,       # bullet list
    14: _render_ordered,      # ordered list
    15: _render_code,         # code
    17: _render_quote,        # quote_container (simplified)
    19: _render_todo,         # todo
    22: _render_divider,      # divider
    27: _render_image,        # image
}


def render_block(block: dict[str, Any], blocks_by_id: dict[str, dict[str, Any]] | None = None) -> str:
    """将单个 Feishu block 渲染为 Markdown 文本。"""
    block_type = block.get("block_type", 0)
    if blocks_by_id is None:
        blocks_by_id = {}

    # table 需要上下文
    if block_type == 31:
        return _render_table(block, blocks_by_id)

    renderer = BLOCK_RENDERERS.get(block_type)
    if renderer:
        return renderer(block)
    return ""


def blocks_to_markdown(blocks: list[dict[str, Any]]) -> str:
    """将飞书文档的 block 列表整体转换为 Markdown 字符串。"""
    blocks_by_id: dict[str, dict[str, Any]] = {}
    for b in blocks:
        bid = b.get("block_id", "")
        if bid:
            blocks_by_id[bid] = b

    md_parts: list[str] = []
    # 需要跳过的 block_id（已经被 table 等复合块渲染过的子块）
    consumed: set[str] = set()
    for b in blocks:
        bid = b.get("block_id", "")
        if bid in consumed:
            continue

        block_type = b.get("block_type", 0)
        # 标记 table 子节点
        if block_type == 31:
            for child_id in b.get("children", []):
                consumed.add(child_id)
                child = blocks_by_id.get(child_id, {})
                for grand in child.get("children", []):
                    consumed.add(grand)

        text = render_block(b, blocks_by_id)
        if text:
            md_parts.append(text)

    return "\n\n".join(md_parts) + "\n" if md_parts else ""
