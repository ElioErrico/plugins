from docx import Document
from cat.log import log
import os
import re


def load_template_document(cat):
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(plugin_dir, "..", "..", ".."))
    core_cat_dir = os.path.abspath(os.path.join(plugin_dir, "..", ".."))

    template_paths = [
        "core\cat\static\format.docx",
        "cat/plugins/format.docx",
        "format.docx",
        "/app/format.docx",
        "/app/cat/format.docx",
    ]

    template_path = None
    for path in template_paths:
        if os.path.isfile(path):
            template_path = path
            log.info(f"Template found at: {template_path}")
            break

    if template_path and os.path.isfile(template_path):
        try:
            doc = Document(template_path)
            log.info(f"Successfully loaded template from: {template_path}")
            cat.send_ws_message(
                "📋 Template format.docx caricato con successo",
                msg_type="notification",
            )
            return doc
        except Exception as e:
            log.warning(f"Error loading template from {template_path}: {e}")
            cat.send_ws_message(
                f"⚠️ Impossibile caricare il template: {e}. Uso documento vuoto.",
                msg_type="notification",
            )
            return Document()

    log.warning(f"Template format.docx not found in any of these locations: {template_paths}")
    cat.send_ws_message(
        "⚠️ Template format.docx non trovato. Uso documento vuoto. "
        "Per usare un template personalizzato, posiziona il file 'format.docx' in cat/static/",
        msg_type="notification",
    )
    return Document()


def parse_markdown_to_word(doc, markdown_content):
    lines = markdown_content.split("\n")
    in_table = False
    table_rows = []
    in_code_block = False
    code_lines = []

    for line in lines:
        if line.strip().startswith("```"):
            if in_code_block:
                code_text = "\n".join(code_lines)
                p = doc.add_paragraph(code_text)
                try:
                    p.style = "Intense Quote"
                except Exception:
                    p.style = "Normal"
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if "|" in line and line.strip().startswith("|"):
            if not in_table:
                in_table = True
                table_rows = []

            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            if all(set(cell.strip()) <= set("-:| ") for cell in cells):
                continue

            table_rows.append(cells)
            continue
        elif in_table and table_rows:
            create_word_table(doc, table_rows)
            table_rows = []
            in_table = False

        if line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith("#### "):
            doc.add_heading(line[5:].strip(), level=4)
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            text = line.strip()[2:]
            p = _add_paragraph_with_style(doc, "List Bullet")
            add_formatted_text(p, parse_inline_formatting(text))
        elif re.match(r"^\d+\.\s", line.strip()):
            text = re.sub(r"^\d+\.\s", "", line.strip())
            p = _add_paragraph_with_style(doc, "List Number")
            add_formatted_text(p, parse_inline_formatting(text))
        elif line.strip().startswith(">"):
            text = line.strip()[1:].strip()
            try:
                doc.add_paragraph(text, style="Intense Quote")
            except Exception:
                doc.add_paragraph(text)
        elif not line.strip():
            doc.add_paragraph()
        else:
            p = doc.add_paragraph()
            add_formatted_text(p, parse_inline_formatting(line))

    if in_table and table_rows:
        create_word_table(doc, table_rows)


def create_word_table(doc, table_rows):
    if not table_rows:
        return

    table = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
    try:
        table.style = "Light Grid Accent 1"
    except Exception:
        try:
            table.style = "Table Grid"
        except Exception:
            pass

    for i, row_data in enumerate(table_rows):
        row_cells = table.rows[i].cells
        for j, cell_data in enumerate(row_data):
            if j < len(row_cells):
                row_cells[j].text = cell_data
                if i == 0:
                    for paragraph in row_cells[j].paragraphs:
                        for run in paragraph.runs:
                            run.font.bold = True

    doc.add_paragraph()


def parse_inline_formatting(text):
    segments = []
    current_pos = 0
    patterns = [
        (r"\*\*\*(.+?)\*\*\*", {"bold": True, "italic": True}),
        (r"\*\*(.+?)\*\*", {"bold": True, "italic": False}),
        (r"\*(.+?)\*", {"bold": False, "italic": True}),
        (r"__(.+?)__", {"bold": True, "italic": False}),
        (r"_(.+?)_", {"bold": False, "italic": True}),
    ]

    while current_pos < len(text):
        earliest_match = None
        earliest_pos = len(text)
        matched_pattern = None

        for pattern, formatting in patterns:
            match = re.search(pattern, text[current_pos:])
            if match and match.start() < earliest_pos:
                earliest_pos = match.start()
                earliest_match = match
                matched_pattern = formatting

        if earliest_match:
            if earliest_pos > 0:
                normal_text = text[current_pos:current_pos + earliest_pos]
                segments.append((normal_text, {"bold": False, "italic": False}))

            formatted_text = earliest_match.group(1)
            segments.append((formatted_text, matched_pattern))
            current_pos += earliest_pos + len(earliest_match.group(0))
        else:
            segments.append((text[current_pos:], {"bold": False, "italic": False}))
            break

    return segments


def add_formatted_text(paragraph, text_segments):
    if isinstance(text_segments, str):
        text_segments = [(text_segments, {"bold": False, "italic": False})]

    for text, formatting in text_segments:
        run = paragraph.add_run(text)
        if formatting.get("bold"):
            run.font.bold = True
        if formatting.get("italic"):
            run.font.italic = True


def _add_paragraph_with_style(doc, style_name):
    try:
        return doc.add_paragraph(style=style_name)
    except Exception:
        return doc.add_paragraph()
