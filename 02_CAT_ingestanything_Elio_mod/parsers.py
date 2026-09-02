# parsers.py
import os
import json
from typing import Iterator
from abc import ABC

import pandas as pd
from langchain_core.documents import Document
from langchain_community.document_loaders.base import BaseBlobParser
from langchain_community.document_loaders.blob_loaders import Blob


class TableParser(BaseBlobParser, ABC):
    """Parsa CSV/XLSX. Per XLSX emette 1 Document per foglio."""

    def _get_source(self, blob: Blob) -> str:
        p = getattr(blob, "path", None) or getattr(blob, "source", None) or ""
        try:
            return os.path.basename(p) if p else ""
        except Exception:
            return str(p)

    def lazy_parse(self, blob: Blob) -> Iterator[Document]:
        with blob.as_bytes_io() as file:
            if blob.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                # Un Document per sheet
                df_dict = pd.read_excel(file, sheet_name=None)
                for sheet_name, sheet_df in df_dict.items():
                    if sheet_df is None or sheet_df.empty:
                        continue
                    records = sheet_df.to_dict("records")
                    # opzionale: traccia la provenienza riga->foglio
                    for r in records:
                        r.setdefault("_sheet", sheet_name)

                    yield Document(
                        page_content=json.dumps(records, ensure_ascii=False),
                        metadata={
                            "source": self._get_source(blob),
                            "mimetype": blob.mimetype,
                            "sheet_name": sheet_name,
                            "row_count": len(records),
                            "parser": "TableParser",
                        },
                    )

            elif blob.mimetype == "text/csv":
                df = pd.read_csv(file)
                records = df.to_dict("records") if not df.empty else []
                for r in records:
                    r.setdefault("_sheet", "CSV")

                yield Document(
                    page_content=json.dumps(records, ensure_ascii=False),
                    metadata={
                        "source": self._get_source(blob),
                        "mimetype": blob.mimetype,
                        "sheet_name": "CSV",
                        "row_count": len(records),
                        "parser": "TableParser",
                    },
                )
            else:
                raise ValueError(f"Unsupported table mime type: {blob.mimetype}")

class PowerPointParser(BaseBlobParser, ABC):
    """Estrae il testo dalle slide e include metadati utili."""

    def _get_source(self, blob: Blob) -> str:
        p = getattr(blob, "path", None) or getattr(blob, "source", None) or ""
        try:
            return os.path.basename(p) if p else ""
        except Exception:
            return str(p)

    def lazy_parse(self, blob: Blob) -> Iterator[Document]:
        pptx_mime_types = [
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
            "application/vnd.ms-powerpoint",  # .ppt
            "application/powerpoint",  # Alternative .ppt
        ]
        if blob.mimetype not in pptx_mime_types:
            raise ValueError(f"Unsupported mime type: {blob.mimetype}")

        with blob.as_bytes_io() as file_obj:
            import pptx as _pptx

            presentation = _pptx.Presentation(file_obj)

            all_text = []
            slide_contents = {}

            for i, slide in enumerate(presentation.slides, 1):
                slide_text = []
                title = ""

                # Title (se presente)
                for shape in slide.shapes:
                    if hasattr(shape, "text") and getattr(shape, "is_title", False):
                        title = shape.text or ""
                        break

                # Tutti i testi della slide
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        slide_text.append(shape.text)

                slide_content = "\n".join(slide_text)
                all_text.append(slide_content)
                slide_contents[f"Slide {i}"] = {"title": title, "content": slide_content}

            full_text = "\n\n".join(all_text)

            yield Document(
                page_content=full_text,
                metadata={
                    "source": self._get_source(blob),
                    "mimetype": blob.mimetype,
                    "parser": "PowerPointParser",
                },
            )
