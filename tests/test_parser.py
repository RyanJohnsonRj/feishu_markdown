"""飞书文档 Block → Markdown 解析器测试"""

from feishu_markdown.parser import (
    blocks_to_markdown,
    render_block,
    _render_text_elements,
    _style_to_md,
)


class TestStyleToMd:
    """文本样式 → Markdown 标记。"""

    def test_bold(self):
        assert _style_to_md("hello", {"bold": True}) == "**hello**"

    def test_italic(self):
        assert _style_to_md("hello", {"italic": True}) == "*hello*"

    def test_strikethrough(self):
        assert _style_to_md("hello", {"strikethrough": True}) == "~~hello~~"

    def test_inline_code(self):
        assert _style_to_md("code", {"inline_code": True}) == "`code`"

    def test_bold_italic(self):
        result = _style_to_md("hello", {"bold": True, "italic": True})
        assert "**" in result
        assert "*" in result

    def test_no_style(self):
        assert _style_to_md("hello", None) == "hello"
        assert _style_to_md("hello", {}) == "hello"

    def test_empty_text(self):
        assert _style_to_md("", {"bold": True}) == ""


class TestRenderTextElements:
    """TextElement 列表渲染。"""

    def test_plain_text(self):
        elements = [{"text_run": {"content": "Hello world"}}]
        assert _render_text_elements(elements) == "Hello world"

    def test_styled_text(self):
        elements = [
            {"text_run": {"content": "bold", "text_element_style": {"bold": True}}},
            {"text_run": {"content": " normal"}},
        ]
        assert _render_text_elements(elements) == "**bold** normal"

    def test_hyperlink(self):
        elements = [
            {
                "text_run": {
                    "content": "Click here",
                    "text_element_style": {
                        "link": {"url": "https://example.com"}
                    },
                }
            }
        ]
        result = _render_text_elements(elements)
        assert result == "[Click here](https://example.com)"

    def test_mention_doc_with_url(self):
        elements = [
            {
                "mention_doc": {
                    "title": "Related Page",
                    "token": "abc123",
                    "obj_type": "docx",
                    "url": "https://feishu.cn/docx/abc123",
                }
            }
        ]
        result = _render_text_elements(elements)
        assert result == "[Related Page](https://feishu.cn/docx/abc123)"

    def test_mention_doc_without_url(self):
        elements = [
            {
                "mention_doc": {
                    "title": "Wiki Page",
                    "token": "wiki123",
                    "obj_type": "wiki",
                }
            }
        ]
        result = _render_text_elements(elements)
        assert "[Wiki Page]" in result
        assert "wiki123" in result

    def test_mention_doc_no_token(self):
        elements = [{"mention_doc": {"title": "Unknown"}}]
        result = _render_text_elements(elements)
        assert result == "[[Unknown]]"

    def test_empty_element(self):
        elements = [{}]
        assert _render_text_elements(elements) == ""


class TestRenderBlock:
    """单个 Block 渲染。"""

    def test_text_block(self):
        block = {
            "block_type": 2,
            "text": {"elements": [{"text_run": {"content": "A paragraph"}}]},
        }
        assert render_block(block) == "A paragraph"

    def test_heading_block(self):
        for level in range(1, 7):
            block = {
                "block_type": level + 2,  # heading1=3, heading2=4 ...
                "heading": {
                    "level": level,
                    "elements": [{"text_run": {"content": f"Heading {level}"}}],
                },
            }
            result = render_block(block)
            assert result == f"{'#' * level} Heading {level}"

    def test_heading_level_capped_at_6(self):
        block = {
            "block_type": 11,
            "heading": {
                "level": 9,
                "elements": [{"text_run": {"content": "Deep"}}],
            },
        }
        result = render_block(block)
        assert result.startswith("######")

    def test_bullet_list(self):
        block = {
            "block_type": 13,
            "bullet": {"elements": [{"text_run": {"content": "item"}}]},
        }
        assert render_block(block) == "- item"

    def test_ordered_list(self):
        block = {
            "block_type": 14,
            "ordered": {"elements": [{"text_run": {"content": "first"}}]},
        }
        assert render_block(block) == "1. first"

    def test_code_block(self):
        block = {
            "block_type": 15,
            "code": {
                "language": 29,  # javascript
                "elements": [{"text_run": {"content": "console.log('hi')"}}],
            },
        }
        result = render_block(block)
        assert result == "```javascript\nconsole.log('hi')\n```"

    def test_code_block_string_language(self):
        block = {
            "block_type": 15,
            "code": {
                "language": "python",
                "elements": [{"text_run": {"content": "print(1)"}}],
            },
        }
        result = render_block(block)
        assert result == "```python\nprint(1)\n```"

    def test_quote_block(self):
        block = {
            "block_type": 17,
            "quote": {"elements": [{"text_run": {"content": "a quote"}}]},
        }
        assert render_block(block) == "> a quote"

    def test_todo_block_unchecked(self):
        block = {
            "block_type": 19,
            "todo": {
                "elements": [{"text_run": {"content": "task"}}],
                "style": {"done": False},
            },
        }
        assert render_block(block) == "- [ ] task"

    def test_todo_block_checked(self):
        block = {
            "block_type": 19,
            "todo": {
                "elements": [{"text_run": {"content": "done task"}}],
                "style": {"done": True},
            },
        }
        assert render_block(block) == "- [x] done task"

    def test_divider_block(self):
        block = {"block_type": 22}
        assert render_block(block) == "---"

    def test_image_block(self):
        block = {
            "block_type": 27,
            "image": {"token": "img_token_123", "alt": "screenshot"},
        }
        result = render_block(block)
        assert result == "![screenshot](feishu://file/img_token_123)"

    def test_image_block_no_alt(self):
        block = {
            "block_type": 27,
            "image": {"token": "img_token_456", "alt": ""},
        }
        result = render_block(block)
        assert result == "![image](feishu://file/img_token_456)"

    def test_unknown_block_type(self):
        block = {"block_type": 999}
        assert render_block(block) == ""


class TestRenderTable:
    """表格渲染。"""

    def _make_table(self):
        """创建一个 2×2 的表格。"""
        blocks = [
            {
                "block_id": "table1",
                "block_type": 31,
                "table": {
                    "property": {"row_size": 2, "column_size": 2},
                },
                "children": ["cell_0_0", "cell_0_1", "cell_1_0", "cell_1_1"],
            },
            {
                "block_id": "cell_0_0",
                "block_type": 34,  # table_cell
                "children": ["text_a"],
            },
            {
                "block_id": "cell_0_1",
                "block_type": 34,
                "children": ["text_b"],
            },
            {
                "block_id": "cell_1_0",
                "block_type": 34,
                "children": ["text_c"],
            },
            {
                "block_id": "cell_1_1",
                "block_type": 34,
                "children": ["text_d"],
            },
            {
                "block_id": "text_a",
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": "Header A"}}]},
            },
            {
                "block_id": "text_b",
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": "Header B"}}]},
            },
            {
                "block_id": "text_c",
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": "Value C"}}]},
            },
            {
                "block_id": "text_d",
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": "Value D"}}]},
            },
        ]
        return blocks

    def test_table_renders_markdown(self):
        blocks = self._make_table()
        md = blocks_to_markdown(blocks)
        assert "| Header A | Header B |" in md
        assert "| --- | --- |" in md
        assert "| Value C | Value D |" in md

    def test_table_cells_not_rendered_separately(self):
        blocks = self._make_table()
        md = blocks_to_markdown(blocks)
        # Cell content should appear only inside the table, not as separate paragraphs
        lines = [l.strip() for l in md.split("\n") if l.strip()]
        # Should be exactly 3 lines for the table (header + separator + data)
        table_lines = [l for l in lines if l.startswith("|")]
        assert len(table_lines) == 3


class TestBlocksToMarkdown:
    """完整文档转换测试。"""

    def test_multiple_blocks(self):
        blocks = [
            {
                "block_id": "b1",
                "block_type": 3,
                "heading": {
                    "level": 1,
                    "elements": [{"text_run": {"content": "Title"}}],
                },
            },
            {
                "block_id": "b2",
                "block_type": 2,
                "text": {
                    "elements": [{"text_run": {"content": "Paragraph content."}}]
                },
            },
            {
                "block_id": "b3",
                "block_type": 22,
            },
            {
                "block_id": "b4",
                "block_type": 13,
                "bullet": {
                    "elements": [{"text_run": {"content": "bullet item"}}]
                },
            },
        ]
        md = blocks_to_markdown(blocks)
        assert "# Title" in md
        assert "Paragraph content." in md
        assert "---" in md
        assert "- bullet item" in md

    def test_empty_blocks(self):
        assert blocks_to_markdown([]) == ""

    def test_document_with_links_and_images(self):
        blocks = [
            {
                "block_id": "b1",
                "block_type": 2,
                "text": {
                    "elements": [
                        {"text_run": {"content": "See "}},
                        {
                            "text_run": {
                                "content": "this link",
                                "text_element_style": {
                                    "link": {"url": "https://example.com"}
                                },
                            }
                        },
                        {"text_run": {"content": " for details."}},
                    ]
                },
            },
            {
                "block_id": "b2",
                "block_type": 27,
                "image": {"token": "img1", "alt": "diagram"},
            },
            {
                "block_id": "b3",
                "block_type": 2,
                "text": {
                    "elements": [
                        {
                            "mention_doc": {
                                "title": "Related Doc",
                                "token": "rdoc1",
                                "obj_type": "docx",
                                "url": "https://feishu.cn/docx/rdoc1",
                            }
                        }
                    ]
                },
            },
        ]
        md = blocks_to_markdown(blocks)
        assert "[this link](https://example.com)" in md
        assert "![diagram](feishu://file/img1)" in md
        assert "[Related Doc](https://feishu.cn/docx/rdoc1)" in md
