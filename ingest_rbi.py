"""Check that configured RBI PDF source files can be read before deployment."""

from pathlib import Path

from pypdf import PdfReader

import config


def inspect_rbi_documents() -> None:
    documents_dir = Path(config.RBI_DOCS_DIR)
    pdf_files = sorted(documents_dir.glob("*.pdf")) if documents_dir.is_dir() else []
    if not pdf_files:
        raise SystemExit(f"No RBI PDFs found in {documents_dir.resolve()}")

    total_pages = 0
    for pdf_path in pdf_files:
        reader = PdfReader(str(pdf_path))
        pages_with_text = sum(bool(page.extract_text()) for page in reader.pages)
        total_pages += len(reader.pages)
        print(f"{pdf_path.name}: {len(reader.pages)} pages, {pages_with_text} pages with extractable text")

    print(f"Ready: {len(pdf_files)} PDF(s), {total_pages} total pages.")
    print("The app reads these PDFs directly; no separate vector-index build is needed.")


if __name__ == "__main__":
    inspect_rbi_documents()
