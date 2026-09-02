"""
Modulo per la formattazione e conversione di report in formato Word.

Questo modulo contiene tutte le funzioni per:
- Caricare template Word
- Convertire Markdown in Word
- Gestire la formattazione (grassetto, corsivo, tabelle, etc.)
"""

from docx import Document
from cat.log import log
import os
import re
from pathlib import Path


def _resolve_static_file(filename: str) -> Path:
    """Risolve un file statico del core senza dipendere dalla working directory."""
    plugin_cat_dir = Path(__file__).resolve().parents[2]
    candidates = []

    ccat_root = os.environ.get("CCAT_ROOT")
    if ccat_root:
        candidates.append(Path(ccat_root) / "cat" / "static" / filename)

    candidates.append(plugin_cat_dir / "static" / filename)
    candidates.append(Path.cwd() / "cat" / "static" / filename)
    candidates.append(Path(__file__).resolve().parent / filename)
    candidates.append(Path.cwd() / filename)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if ccat_root else candidates[1]


def load_template_document(cat):
    """
    Carica il template Word format.docx da diverse posizioni possibili.
    
    Args:
        cat: Istanza del cat per logging e notifiche
    
    Returns:
        Document: Documento Word (da template o vuoto)
    """
    
    template_path = _resolve_static_file("format.docx")
    template_candidates = [
        str(template_path),
        str(Path(__file__).resolve().parent / "format.docx"),
        str(Path.cwd() / "format.docx"),
        "/app/format.docx",
        "/app/cat/format.docx",
    ]

    log.info(f"Template lookup candidates: {template_candidates}")
    # Carica il template se esiste
    if template_path.exists():
        try:
            doc = Document(str(template_path))
            log.info(f"Successfully loaded template from: {template_path}")
            
            cat.send_ws_message(
                "📋 Template format.docx caricato con successo",
                msg_type="notification"
            )
            return doc
            
        except Exception as e:
            log.warning(f"Error loading template from {template_path}: {e}")
            cat.send_ws_message(
                f"⚠️ Impossibile caricare il template: {e}. Uso documento vuoto.",
                msg_type="notification"
            )
            return Document()
    else:
        log.warning(f"Template format.docx not found in any of these locations: {template_candidates}")
        cat.send_ws_message(
            "⚠️ Template format.docx non trovato. Uso documento vuoto. "
            "Per usare un template personalizzato, posiziona il file 'format.docx' in cat/static/",
            msg_type="notification"
        )
        return Document()


def parse_markdown_to_word(doc, markdown_content):
    """
    Converte contenuto Markdown in un documento Word.
    
    Args:
        doc: Documento Word (python-docx Document object)
        markdown_content: Stringa contenente Markdown da convertire
    """
    
    lines = markdown_content.split('\n')
    in_table = False
    table_rows = []
    in_code_block = False
    code_lines = []
    
    for line in lines:
        # ===== GESTIONE BLOCCHI DI CODICE =====
        if line.strip().startswith('```'):
            if in_code_block:
                # Fine del blocco di codice
                code_text = '\n'.join(code_lines)
                p = doc.add_paragraph(code_text)
                try:
                    p.style = 'Intense Quote'
                except:
                    p.style = 'Normal'
                code_lines = []
                in_code_block = False
            else:
                # Inizio del blocco di codice
                in_code_block = True
            continue
        
        if in_code_block:
            code_lines.append(line)
            continue
        
        # ===== GESTIONE TABELLE MARKDOWN =====
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_rows = []
            
            # Rimuove spazi e pipe iniziali/finali
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            # Ignora la riga separatore (|---|---|)
            if all(set(cell.strip()) <= set('-:| ') for cell in cells):
                continue
            
            table_rows.append(cells)
            continue
        else:
            # Se eravamo in una tabella, creala ora
            if in_table and table_rows:
                create_word_table(doc, table_rows)
                table_rows = []
                in_table = False
        
        # ===== GESTIONE HEADERS (TITOLI) =====
        if line.startswith('# '):
            doc.add_heading(line[2:].strip(), level=1)
        elif line.startswith('## '):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith('### '):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith('#### '):
            doc.add_heading(line[5:].strip(), level=4)
        
        # ===== GESTIONE LISTE BULLET =====
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            text = line.strip()[2:]
            text_segments = parse_inline_formatting(text)
            try:
                p = doc.add_paragraph(style='List Bullet')
            except:
                p = doc.add_paragraph()
            add_formatted_text(p, text_segments)
        
        # ===== GESTIONE LISTE NUMERATE =====
        elif re.match(r'^\d+\.\s', line.strip()):
            text = re.sub(r'^\d+\.\s', '', line.strip())
            text_segments = parse_inline_formatting(text)
            try:
                p = doc.add_paragraph(style='List Number')
            except:
                p = doc.add_paragraph()
            add_formatted_text(p, text_segments)
        
        # ===== GESTIONE QUOTE =====
        elif line.strip().startswith('>'):
            text = line.strip()[1:].strip()
            try:
                doc.add_paragraph(text, style='Intense Quote')
            except:
                doc.add_paragraph(text)
        
        # ===== LINEE VUOTE =====
        elif not line.strip():
            doc.add_paragraph()
        
        # ===== TESTO NORMALE =====
        else:
            if line.strip():
                text_segments = parse_inline_formatting(line)
                p = doc.add_paragraph()
                add_formatted_text(p, text_segments)
    
    # Gestisce tabella rimasta in sospeso
    if in_table and table_rows:
        create_word_table(doc, table_rows)


def create_word_table(doc, table_rows):
    """
    Crea una tabella Word formattata dai dati delle righe.
    
    Args:
        doc: Documento Word
        table_rows: Lista di liste con i contenuti delle celle
    """
    
    if not table_rows:
        return
    
    # Crea la tabella
    table = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
    
    # Applica stile tabella
    try:
        table.style = 'Light Grid Accent 1'
    except:
        try:
            table.style = 'Table Grid'
        except:
            pass
    
    # Popola le celle
    for i, row_data in enumerate(table_rows):
        row_cells = table.rows[i].cells
        for j, cell_data in enumerate(row_data):
            if j < len(row_cells):
                row_cells[j].text = cell_data
                
                # Formatta la prima riga come header
                if i == 0:
                    for paragraph in row_cells[j].paragraphs:
                        for run in paragraph.runs:
                            run.font.bold = True
    
    # Aggiungi spazio dopo la tabella
    doc.add_paragraph()


def parse_inline_formatting(text):
    """
    Analizza il testo per identificare formattazioni inline (grassetto, corsivo).
    
    Args:
        text: Stringa di testo con markdown inline
    
    Returns:
        Lista di tuple (testo, {'bold': bool, 'italic': bool})
    """
    
    segments = []
    current_pos = 0
    
    # Pattern per **bold**, *italic*, ***bold+italic***
    patterns = [
        (r'\*\*\*(.+?)\*\*\*', {'bold': True, 'italic': True}),
        (r'\*\*(.+?)\*\*', {'bold': True, 'italic': False}),
        (r'\*(.+?)\*', {'bold': False, 'italic': True}),
        (r'__(.+?)__', {'bold': True, 'italic': False}),
        (r'_(.+?)_', {'bold': False, 'italic': True}),
    ]
    
    while current_pos < len(text):
        earliest_match = None
        earliest_pos = len(text)
        matched_pattern = None
        
        # Trova il prossimo pattern
        for pattern, formatting in patterns:
            match = re.search(pattern, text[current_pos:])
            if match and match.start() < earliest_pos:
                earliest_pos = match.start()
                earliest_match = match
                matched_pattern = formatting
        
        if earliest_match:
            # Aggiungi testo normale prima del match
            if earliest_pos > 0:
                normal_text = text[current_pos:current_pos + earliest_pos]
                segments.append((normal_text, {'bold': False, 'italic': False}))
            
            # Aggiungi testo formattato
            formatted_text = earliest_match.group(1)
            segments.append((formatted_text, matched_pattern))
            
            current_pos += earliest_pos + len(earliest_match.group(0))
        else:
            # Nessun pattern trovato, aggiungi il resto come testo normale
            segments.append((text[current_pos:], {'bold': False, 'italic': False}))
            break
    
    return segments


def add_formatted_text(paragraph, text_segments):
    """
    Aggiunge testo formattato a un paragrafo Word.
    
    Args:
        paragraph: Paragrafo Word
        text_segments: Lista di tuple (testo, formato) o stringa
    """
    
    # Se è una stringa semplice, convertila in segments
    if isinstance(text_segments, str):
        text_segments = [(text_segments, {'bold': False, 'italic': False})]
    
    for text, formatting in text_segments:
        run = paragraph.add_run(text)
        if formatting.get('bold'):
            run.font.bold = True
        if formatting.get('italic'):
            run.font.italic = True


def apply_custom_style(paragraph, style_name, fallback_style='Normal'):
    """
    Applica uno stile personalizzato a un paragrafo con fallback.
    
    Args:
        paragraph: Paragrafo Word
        style_name: Nome dello stile da applicare
        fallback_style: Stile di fallback se il primo non esiste
    """
    
    try:
        paragraph.style = style_name
    except:
        try:
            paragraph.style = fallback_style
        except:
            pass


def insert_page_break(doc):
    """
    Inserisce un'interruzione di pagina nel documento.
    
    Args:
        doc: Documento Word
    """
    
    doc.add_page_break()


def add_document_properties(doc, title=None, author=None, subject=None):
    """
    Aggiunge proprietà al documento Word.
    
    Args:
        doc: Documento Word
        title: Titolo del documento
        author: Autore del documento
        subject: Oggetto del documento
    """
    
    core_properties = doc.core_properties
    
    if title:
        core_properties.title = title
    if author:
        core_properties.author = author
    if subject:
        core_properties.subject = subject
