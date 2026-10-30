"""Hosted KFS audit engine: local PDF retrieval plus Groq model inference."""

from __future__ import annotations

import json
import math
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from groq import Groq
from pypdf import PdfReader

import config

COMPLIANCE_SYSTEM_PROMPT = """You are an AI document-analysis assistant supporting a qualified Indian NBFC compliance reviewer.
Analyze a draft digital-loan Key Fact Statement against ONLY the RBI source evidence supplied in this request. Do not use outside knowledge and do not invent clauses, page numbers, quotations, or citations.

Assess these four checks independently: APR and upfront fee disclosure; flat penal charges versus compounding; cooling-off/look-up period; nodal grievance officer identity/contact details.

For each check choose exactly one category:
- Compliant: the KFS shows the required item and supplied RBI evidence supports the requirement.
- Potential Gap: the KFS evidence indicates a missing, unclear, or conflicting disclosure and supplied RBI evidence supports the requirement.
- Insufficient Evidence: either the KFS text or supplied RBI evidence is not enough to assess the item.

Return exactly four checks named "APR Disclosure", "Penal Charges", "Cooling-off Period", and "Grievance Redressal Details". Return only JSON with this shape:
{"overall_assessment":"Compliant|Potential Gap|Insufficient Evidence","checks":[{"check":"APR Disclosure","category":"Compliant|Potential Gap|Insufficient Evidence","finding":"...","document_evidence":"short exact quote from KFS or explain absence","document_pages":["K1"],"rule_evidence":["R1"],"recommended_action":"..."}]}
Use only the supplied K page IDs and R evidence IDs. If a check cannot be verified, choose Insufficient Evidence. These are AI-generated demonstration assessments, not legal advice or a final regulatory decision."""

CHECK_QUERIES = (
    ("APR Disclosure", "annual percentage rate APR all upfront fees processing charges KFS"),
    ("Penal Charges", "penal charges flat fee penal interest compounding default delay"),
    ("Cooling-off Period", "cooling-off period look-up period exit loan prepayment penalty days"),
    ("Grievance Redressal Details", "grievance redressal nodal officer name email phone contact KFS"),
)
VALID_CATEGORIES = {"Compliant", "Potential Gap", "Insufficient Evidence"}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text) if len(token) > 1]


def _split_text(text: str) -> list[str]:
    """Split page text into overlapping windows without losing page metadata."""
    text = re.sub(r"\s+", " ", text).strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + config.CHUNK_SIZE_CHARS, len(text))
        if end < len(text):
            boundary = text.rfind(". ", start + config.CHUNK_SIZE_CHARS // 2, end)
            if boundary > start:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start + 1, end - config.CHUNK_OVERLAP_CHARS)
    return chunks


@lru_cache(maxsize=4)
def _load_rule_chunks(signature: tuple[tuple[str, int, int], ...]) -> tuple[dict[str, Any], ...]:
    chunks: list[dict[str, Any]] = []
    for file_path, _, _ in signature:
        try:
            reader = PdfReader(file_path)
            for page_number, page in enumerate(reader.pages, start=1):
                for text in _split_text(page.extract_text() or ""):
                    chunks.append({"text": text, "source": Path(file_path).name, "page": page_number})
        except Exception as exc:
            raise RuntimeError(f"Could not read RBI source PDF '{Path(file_path).name}': {exc}") from exc
    return tuple(chunks)


def _get_rule_chunks() -> tuple[dict[str, Any], ...]:
    docs_dir = Path(config.RBI_DOCS_DIR)
    pdf_paths = sorted(path for path in docs_dir.glob("*.pdf") if path.is_file()) if docs_dir.is_dir() else []
    signature = tuple((str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size) for path in pdf_paths)
    return _load_rule_chunks(signature)


def _rank_chunks(query: str, chunks: tuple[dict[str, Any], ...], limit: int) -> list[dict[str, Any]]:
    """Small TF-IDF-style lexical retriever; needs no server-side embedding model."""
    query_tokens = set(_tokens(query))
    if not query_tokens or not chunks:
        return []
    tokenized = [_tokens(chunk["text"]) for chunk in chunks]
    document_frequency: dict[str, int] = {}
    for terms in tokenized:
        for term in set(terms):
            document_frequency[term] = document_frequency.get(term, 0) + 1
    total = len(chunks)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for chunk, terms in zip(chunks, tokenized):
        frequencies: dict[str, int] = {}
        for term in terms:
            frequencies[term] = frequencies.get(term, 0) + 1
        score = sum(
            (1 + math.log(frequencies[term])) * math.log(1 + total / (1 + document_frequency[term]))
            for term in query_tokens if frequencies.get(term, 0)
        )
        if score > 0:
            ranked.append((score, chunk))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in ranked[:limit]]


def _extract_pdf_pages(pdf_path: str) -> list[dict[str, Any]]:
    path = Path(pdf_path)
    if not path.is_file():
        raise RuntimeError(f"KFS PDF not found: {path}")
    try:
        reader = PdfReader(str(path))
        if len(reader.pages) > config.MAX_KFS_PAGES:
            raise RuntimeError(f"PDF has {len(reader.pages)} pages; demo limit is {config.MAX_KFS_PAGES}.")
        pages = [
            {"id": f"K{page_number}", "page": page_number, "text": page.extract_text() or ""}
            for page_number, page in enumerate(reader.pages, start=1)
        ]
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Could not read the uploaded PDF: {exc}") from exc
    pages = [page for page in pages if page["text"].strip()]
    if not pages:
        raise RuntimeError("The PDF has no extractable text. Scanned/image-only PDFs are not supported.")
    remaining = config.MAX_KFS_TEXT_CHARS
    bounded_pages = []
    for page in pages:
        if remaining <= 0:
            break
        text = page["text"][:remaining]
        bounded_pages.append({**page, "text": text})
        remaining -= len(text)
    return bounded_pages


def _overall_assessment(checks: list[dict[str, Any]]) -> str:
    categories = {item["category"] for item in checks}
    if "Potential Gap" in categories:
        return "Potential Gap"
    if "Insufficient Evidence" in categories:
        return "Insufficient Evidence"
    return "Compliant"


def _validate_report(
    data: Any,
    evidence_by_check: dict[str, list[dict[str, Any]]],
    document_pages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate model categories and keep only references actually provided to it."""
    if not isinstance(data, dict) or not isinstance(data.get("checks"), list):
        raise ValueError("The model returned an invalid assessment structure.")

    document_ids = {page["id"] for page in document_pages}
    document_map = {page["id"]: page for page in document_pages}
    checks_by_name = {item["check"]: item for item in data["checks"] if isinstance(item, dict)}
    validated = []
    for check_name, _ in CHECK_QUERIES:
        item = checks_by_name.get(check_name)
        available_rules = evidence_by_check.get(check_name, [])
        if not item or not available_rules:
            validated.append({
                "check": check_name,
                "category": "Insufficient Evidence",
                "finding": "The available document context was insufficient to assess this check.",
                "document_evidence": "Not established from the supplied KFS text.",
                "document_pages": [],
                "rule_evidence": [],
                "source_details": [],
                "recommended_action": "Have a compliance reviewer inspect the KFS and the applicable official rule source.",
            })
            continue

        category = item.get("category")
        doc_refs = item.get("document_pages", [])
        rule_refs = item.get("rule_evidence", [])
        if not isinstance(doc_refs, list) or not isinstance(rule_refs, list):
            category = "Insufficient Evidence"
            doc_refs, rule_refs = [], []
        doc_refs = [ref for ref in doc_refs if isinstance(ref, str) and ref in document_ids]
        rule_map = {source["id"]: source for source in available_rules}
        rule_refs = [ref for ref in rule_refs if isinstance(ref, str) and ref in rule_map]
        if category not in VALID_CATEGORIES or not rule_refs:
            category = "Insufficient Evidence"
        if category != "Insufficient Evidence" and not doc_refs:
            category = "Insufficient Evidence"

        validated.append({
            "check": check_name,
            "category": category,
            "finding": str(item.get("finding", "No finding supplied.")),
            "document_evidence": str(item.get("document_evidence", "No exact document excerpt supplied.")),
            "document_pages": doc_refs,
            "document_details": [
                {
                    "reference": f"{ref}, page {document_map[ref]['page']}",
                    "excerpt": document_map[ref]["text"][:700],
                }
                for ref in doc_refs
            ],
            "rule_evidence": rule_refs,
            "source_details": [rule_map[ref] for ref in rule_refs],
            "recommended_action": str(item.get("recommended_action", "Review with a qualified compliance professional.")),
        })

    return {"overall_assessment": _overall_assessment(validated), "checks": validated}


def audit_kfs_document(
    pdf_path: str,
    api_key: str | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Audit a KFS PDF using local RBI PDFs and Groq hosted inference."""
    def report_progress(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Groq API key is missing. Add GROQ_API_KEY to Streamlit Secrets.")

    report_progress("Extracting document text and page references")
    document_pages = _extract_pdf_pages(pdf_path)
    chunks = _get_rule_chunks()
    if not chunks:
        return {
            "overall_assessment": "Insufficient Evidence",
            "checks": [{
                "check": check_name,
                "category": "Insufficient Evidence",
                "finding": "No readable regulatory reference passages are configured.",
                "document_evidence": "Not assessed because regulatory context is missing.",
                "document_pages": [],
                "rule_evidence": [],
                "source_details": [],
                "recommended_action": "Add and verify the applicable official regulatory PDFs before running an assessment.",
            } for check_name, _ in CHECK_QUERIES],
        }

    report_progress("Retrieving rule passages for each audit topic")
    evidence_by_check: dict[str, list[dict[str, Any]]] = {}
    all_rules: dict[tuple[str, int, str], dict[str, Any]] = {}
    evidence_index = 1
    for check_name, query in CHECK_QUERIES:
        matches = _rank_chunks(query, chunks, config.RETRIEVAL_CHUNKS_PER_CHECK)
        check_evidence = []
        for chunk in matches:
            identity = (chunk["source"], chunk["page"], chunk["text"])
            if identity not in all_rules:
                all_rules[identity] = {**chunk, "id": f"R{evidence_index}"}
                evidence_index += 1
            check_evidence.append(all_rules[identity])
        evidence_by_check[check_name] = check_evidence

    rule_context_parts = []
    for check_name, _ in CHECK_QUERIES:
        check_rules = evidence_by_check.get(check_name, [])
        rule_context_parts.append(f"CHECK: {check_name}")
        if check_rules:
            rule_context_parts.extend(
                f"[{item['id']}] Source: {item['source']}, page {item['page']}\n{item['text']}"
                for item in check_rules
            )
        else:
            rule_context_parts.append("[No relevant regulatory passage retrieved for this check]")
    rule_context = "\n\n".join(rule_context_parts)
    kfs_context = "\n\n".join(
        f"[{page['id']}] KFS page {page['page']}\n{page['text']}"
        for page in document_pages
    )
    try:
        report_progress("Running grounded LLM analysis and generating structured results")
        client = Groq(api_key=api_key, timeout=config.GROQ_TIMEOUT_SECONDS)
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            temperature=0,
            max_tokens=1600,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": COMPLIANCE_SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"RULE EVIDENCE (cite only IDs listed here):\n{rule_context}\n\n"
                    f"KFS EVIDENCE (cite only page IDs listed here):\n{kfs_context}\n\n"
                    f"For each check, use only the rule passages retrieved for its topic. "
                    f"Source PDFs configured: {', '.join(path.name for path in sorted(Path(config.RBI_DOCS_DIR).glob('*.pdf')))}. "
                    f"Return all four checks in the requested JSON format."
                )},
            ],
        )
    except Exception as exc:
        raise RuntimeError(f"Groq audit request failed: {exc}") from exc

    response_text = completion.choices[0].message.content or ""
    try:
        report_progress("Validating evidence references and assessment categories")
        return _validate_report(json.loads(response_text), evidence_by_check, document_pages)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"The AI service returned an invalid audit report: {exc}") from exc