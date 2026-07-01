#!/usr/bin/env python3
"""
Convert Quant Hub handbook .docx files to readable plain text / markdown.

Usage:
    python3 docx_to_text.py <input.docx> [output.md]

If output path is omitted, writes <input_stem>.md next to the input file.

Preserves:
- Heading levels (as markdown #, ##, ###...)
- Paragraph text
- Tables (as markdown tables)
- Bullet / numbered list text (best-effort, based on paragraph style name)
"""

import sys
import os
from docx import Document
from docx.oxml.ns import qn


def iter_block_items(parent):
    """
    Yield each paragraph and table child, in document order, from parent
    (a Document or a _Cell object).
    """
    from docx.document import Document as _Document
    from docx.table import _Cell
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table import CT_Tbl
    from docx.text.paragraph import Paragraph
    from docx.table import Table

    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("unsupported parent type")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def heading_level(paragraph):
    style_name = (paragraph.style.name or "").lower()
    if style_name.startswith("heading"):
        parts = style_name.split()
        if len(parts) == 2 and parts[1].isdigit():
            return int(parts[1])
        return 1
    if style_name == "title":
        return 1
    return None


def paragraph_to_md(paragraph):
    text = paragraph.text.strip()
    if not text:
        return ""
    lvl = heading_level(paragraph)
    style_name = (paragraph.style.name or "").lower()
    if lvl:
        return f"{'#' * min(lvl, 6)} {text}"
    if "list" in style_name or "bullet" in style_name:
        return f"- {text}"
    return text


def table_to_md(table):
    rows = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows.append(cells)
    if not rows:
        return ""
    md_lines = []
    header = rows[0]
    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for r in rows[1:]:
        md_lines.append("| " + " | ".join(r) + " |")
    return "\n".join(md_lines)


def convert(input_path, output_path=None):
    if output_path is None:
        stem = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(os.path.dirname(input_path) or ".", f"{stem}.md")

    doc = Document(input_path)
    out_lines = []

    for block in iter_block_items(doc):
        cls_name = block.__class__.__name__
        if cls_name == "Paragraph":
            md = paragraph_to_md(block)
            if md:
                out_lines.append(md)
                out_lines.append("")
        elif cls_name == "Table":
            md = table_to_md(block)
            if md:
                out_lines.append(md)
                out_lines.append("")

    content = "\n".join(out_lines).strip() + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path, len(content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(in_path):
        print(f"ERROR: file not found: {in_path}")
        sys.exit(1)

    result_path, char_count = convert(in_path, out_path)
    print(f"Converted: {in_path}")
    print(f"Output:    {result_path}")
    print(f"Length:    {char_count:,} characters")
