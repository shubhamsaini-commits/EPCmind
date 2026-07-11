import re


def extract_doc_header(text):
    """
    Grabs the first few non-numbered lines (title block) before
    the first '1.1' style section heading — this is the doc's identity,
    prepended to every chunk so parent context isn't lost.
    """
    lines = text.split("\n")
    header_lines = []
    for line in lines:
        if re.match(r'^\d+\.\d+\s+[A-Z]', line.strip()):
            break
        if line.strip():
            header_lines.append(line.strip())
        if len(header_lines) >= 4:  # cap it — just the title block, not a whole page
            break
    return " | ".join(header_lines)


def chunk_unstructured(text, filename, max_chunk_chars=1200):
    """
    Splits text by section headings, prepends doc header for context,
    keeps [TABLE] blocks intact, sub-splits long sections by paragraph.
    """
    doc_header = extract_doc_header(text)

    section_pattern = r'\n(?=\d+\.\d+\s+[A-Z])'
    sections = re.split(section_pattern, text)

    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        labeled_section = f"{doc_header}\n\n{section}" if doc_header else section

        # Protect tables from being split — treat a table block as atomic
        if "[TABLE]" in labeled_section and len(labeled_section) <= max_chunk_chars * 2:
            chunks.append(labeled_section)
            continue

        if len(labeled_section) <= max_chunk_chars:
            chunks.append(labeled_section)
        else:
            # Sub-split long sections by paragraph, without breaking tables
            paragraphs = labeled_section.split("\n")
            current = ""
            in_table = False
            for para in paragraphs:
                if "[TABLE]" in para:
                    in_table = True
                if "[/TABLE]" in para:
                    in_table = False

                if len(current) + len(para) > max_chunk_chars and not in_table:
                    if current.strip():
                        chunks.append(current.strip())
                    current = para + "\n"
                else:
                    current += para + "\n"
            if current.strip():
                chunks.append(current.strip())

    return chunks


def chunk_structured(records, doc_type_label, project_name):
    """
    Each Excel row becomes one clean, labeled chunk.
    Empty records were already filtered out in extract_excel().
    """
    chunks = []
    for record in records:
        lines = [f"Document Type: {doc_type_label}", f"Project: {project_name}"]
        for key, val in record.items():
            lines.append(f"{key}: {val}")
        chunk_text = "\n".join(lines)
        chunks.append(chunk_text)
    return chunks


def classify_doc_type(filename, text=""):
    """
    Cheap filename-based classification — upgrade to content-based
    (or LLM-based) classification later without touching downstream code.
    """
    fname = filename.lower()
    if "spec" in fname:
        return "Specification"
    elif "submittal" in fname:
        return "Vendor Submittal"
    elif "rfi" in fname:
        return "RFI"
    elif "schedule" in fname or "procurement" in fname:
        return "Procurement Schedule"
    elif "commission" in fname:
        return "Commissioning Record"
    return "Unknown"


def chunk_document(extracted, project_name="Ironwood Point Data Center"):
    """
    Takes the dict from extract_file() and returns a list of chunk dicts,
    each with the chunk text + metadata for later filtering/citation.
    """
    doc_type_label = classify_doc_type(extracted["filename"], extracted.get("text", ""))

    if extracted["doc_type"] == "unstructured":
        raw_chunks = chunk_unstructured(extracted["text"], extracted["filename"])
    else:
        raw_chunks = chunk_structured(extracted["records"], doc_type_label, project_name)

    result = []
    for i, chunk_text in enumerate(raw_chunks):
        result.append({
            "text": chunk_text,
            "filename": extracted["filename"],
            "filetype": extracted["filetype"],
            "doc_type": extracted["doc_type"],       # "structured" / "unstructured"
            "document_type": doc_type_label,          # "Specification" / "RFI" / etc — filterable
            "chunk_id": f"{extracted['filename']}_{i}",
        })
    return result