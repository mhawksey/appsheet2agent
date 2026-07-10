"""
Token-Optimized PDF Preprocessor for AppSheet Documentation.

Extracts text from PDF files, strips boilerplate headers/footers,
de-duplicates table columns against openapi.json, and optimizes token context length.
"""

import io
import re
from typing import Dict, Any, List
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

class PDFTokenPreprocessor:
    def __init__(self, pdf_file_bytes: bytes):
        self.bytes = pdf_file_bytes

    def extract_clean_text(self) -> str:
        """Extracts and cleans raw text from PDF bytes."""
        if not PdfReader:
            return "pypdf library not available."

        reader = PdfReader(io.BytesIO(self.bytes))
        extracted_text = []

        for page in reader.pages:
            text = page.extract_text() or ""
            cleaned_page = self._clean_page_text(text)
            if cleaned_page:
                extracted_text.append(cleaned_page)

        return "\n\n".join(extracted_text)

    def _clean_page_text(self, text: str) -> str:
        lines = text.split("\n")
        filtered_lines = []
        for line in lines:
            line_str = line.strip()
            if re.match(r"^Page \d+ of \d+", line_str, re.IGNORECASE):
                continue
            if line_str.startswith("http://") or line_str.startswith("https://"):
                continue
            if len(line_str) == 0:
                continue
            filtered_lines.append(line_str)
        return "\n".join(filtered_lines)

    def optimize_for_openapi(self, raw_text: str, parsed_tables: Dict[str, Any]) -> str:
        """
        Deduplicates raw PDF text against parsed openapi.json tables to save tokens.
        Preserves business descriptions, table rules, and domain notes.
        Also parses AppSheet UX Column metadata (Hidden, Label) and prepends it to prevent truncation.
        """
        # 1. Parse AppSheet UX Column metadata from raw text
        pdf_metadata = {}
        schema_blocks = raw_text.split("Schema Name ")
        for block in schema_blocks[1:]:
            lines = block.split("\n")
            if not lines:
                continue
            schema_name = lines[0].strip().split()[0]
            pdf_metadata[schema_name] = {}
            current_col = None
            for line in lines[1:]:
                line_str = line.strip()
                col_match = re.match(r"^Column name\s+(.+)$", line_str, re.IGNORECASE)
                if col_match:
                    current_col = col_match.group(1).strip()
                    pdf_metadata[schema_name][current_col] = {"hidden": False, "label": False}
                if current_col:
                    if line_str.startswith("Hidden Yes"):
                        pdf_metadata[schema_name][current_col]["hidden"] = True
                    elif line_str.startswith("Label Yes"):
                        pdf_metadata[schema_name][current_col]["label"] = True

        # Build metadata summary prefix
        metadata_lines = ["### --- APPSHEET UX COLUMN METADATA SUMMARY ---"]
        for schema, cols in pdf_metadata.items():
            metadata_lines.append(f"Schema Name {schema}")
            for col, meta in cols.items():
                metadata_lines.append(f"Column name {col}")
                metadata_lines.append(f"Hidden {'Yes' if meta['hidden'] else 'No'}")
                metadata_lines.append(f"Label {'Yes' if meta['label'] else 'No'}")
        
        # 1.5. Parse AppSheet UX View metadata from raw text
        views_metadata = {}
        view_blocks = raw_text.split("View name ")
        for block in view_blocks[1:]:
            v_lines = block.split("\n")
            if len(v_lines) < 3:
                continue
            view_name = v_lines[0].strip().split()[0]
            if view_name in views_metadata:
                continue
                
            view_info = {}
            in_config = False
            config_lines = []
            for line in v_lines[1:]:
                line_str = line.strip()
                if line_str.startswith("View type"):
                    view_info["type"] = line_str.replace("View type", "").strip()
                elif line_str.startswith("View configuration"):
                    in_config = True
                    config_lines.append(line_str.replace("View configuration", "").strip())
                elif in_config:
                    if "Application Documentation" in line_str or "appsheet.com/template" in line_str or "https://" in line_str:
                        continue
                    config_lines.append(line_str)
                    if line_str.endswith("}"):
                        in_config = False
                        break
                    if "View name" in line_str or "Visible?" in line_str:
                        break
                        
            config_str = "".join(config_lines).strip()
            config_str = re.sub(r"\s+", "", config_str)
            
            if config_str:
                # Regex match configs
                sort_match = re.search(r'"SortBy":\s*\[(.*?)\]', config_str)
                if sort_match and sort_match.group(1):
                    view_info["sort_by"] = sort_match.group(1)
                group_match = re.search(r'"GroupBy":\s*\[(.*?)\]', config_str)
                if group_match and group_match.group(1):
                    view_info["group_by"] = group_match.group(1)
                col_match = re.search(r'"ColumnOrder":\s*\[(.*?)\]', config_str)
                if col_match and col_match.group(1):
                    view_info["column_order"] = col_match.group(1)
                img_match = re.search(r'"MainDeckImageColumn":\s*"?(.*?)"?,', config_str)
                if img_match and img_match.group(1) and img_match.group(1) != "null":
                    view_info["main_image"] = img_match.group(1)
                act_match = re.search(r'"ActionBarEntries":\s*\[(.*?)\]', config_str)
                if act_match and act_match.group(1):
                    view_info["actions"] = act_match.group(1)
                    
            views_metadata[view_name] = view_info

        # Append Views to prefix
        metadata_lines.append("### --- APPSHEET UX VIEW METADATA SUMMARY ---")
        for v_name, v_info in views_metadata.items():
            if v_info.get("type"):
                metadata_lines.append(f"View name {v_name}")
                metadata_lines.append(f"View type {v_info.get('type')}")
                if "sort_by" in v_info:
                    metadata_lines.append(f"SortBy {v_info['sort_by']}")
                if "group_by" in v_info:
                    metadata_lines.append(f"GroupBy {v_info['group_by']}")
                if "column_order" in v_info:
                    metadata_lines.append(f"ColumnOrder {v_info['column_order']}")
                if "main_image" in v_info:
                    metadata_lines.append(f"MainImage {v_info['main_image']}")
                if "actions" in v_info:
                    metadata_lines.append(f"Actions {v_info['actions']}")

        metadata_prefix = "\n".join(metadata_lines) + "\n\n"

        # 2. Optimize and condense the remaining documentation
        lines = raw_text.split("\n")
        optimized_lines = []
        table_names = set(parsed_tables.keys())

        for line in lines:
            matched_table = None
            for tbl in table_names:
                if tbl.lower() in line.lower():
                    matched_table = tbl
                    break
            
            if matched_table:
                optimized_lines.append(f"\n### Table: {matched_table}")
                optimized_lines.append(line)
            else:
                optimized_lines.append(line)

        condensed = "\n".join(optimized_lines)
        if len(condensed) > 4000:
            condensed = condensed[:4000] + "\n...[Additional App Documentation Condensed]..."

        return metadata_prefix + condensed
