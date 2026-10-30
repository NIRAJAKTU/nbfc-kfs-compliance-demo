"""Hosted KFS audit engine: local PDF retrieval plus Groq model inference."""

from __future__ import annotations

import json
import math
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from groq import Groq
from pypdf import PdfReader

import config

COMPLIANCE_SYSTEM_PROMPT = """You are an elite, ruthless Chief Compliance Officer for an Indian NBFC.
Your sole job is to audit a draft Key Fact Statement (KFS) for a digital loan against the official RBI Digital Lending Guidelines provided in your knowledge base.
Evaluate the KFS based ONLY on the provided RBI context. Do NOT use outside knowledge.
Check: 1) APR explicitly stated and inclusive of all upfront fees; 2) penal charges are a flat fee, not compounded penal interest; 3) an explicit cooling-off/look-up period is stated; 4) name and contact details of the Nodal Grievance Officer are provided.
Return only JSON: {"status":"PASS"|"FAIL","violations":[{"issue":"...","rbi_clause":"...","required_fix":"..."}]}
If the provided context does not support a check, report FAIL with issue "UNABLE TO VERIFY DUE TO MISSING RBI CONTEXT". Cite only clause/page/source details explicitly present in context. Never invent citations. This is a preliminary AI review, not legal advice."""

CHECK_QUERIES = (
    "annual percentage rate APR all upfront fees processing charges KFS",
    "penal charges flat fee penal interest compounding default delay",
    "cooling-off period look-up period exit loan prepayment penalty days",
    "grievance redressal nodal officer name email phone contact KFS",
)
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


def _extract_pdf_text(pdf_path: str) -> str:
    path = Path(pdf_path)
    if not path.is_file():
        raise RuntimeError(f"KFS PDF not found: {path}")
    try:
        reader = PdfReader(str(path))
        if len(reader.pages) > config.MAX_KFS_PAGES:
            raise RuntimeError(f"PDF has {len(reader.pages)} pages; demo limit is {config.MAX_KFS_PAGES}.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Could not read the uploaded PDF: {exc}") from exc
    if not text:
        raise RuntimeError("The PDF has no extractable text. Scanned/image-only PDFs are not supported.")
    return text[:config.MAX_KFS_TEXT_CHARS]


def _validate_report(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("status") not in {"PASS", "FAIL"}:
        raise ValueError("The model returned an invalid audit report.")
    violations = data.get("violations")
    if not isinstance(violations, list):
        raise ValueError("The model returned an invalid violations list.")
    clean = []
    for item in violations:
        if not isinstance(item, dict):
            raise ValueError("The model returned a malformed violation.")
        clean.append({
            "issue": str(item.get("issue", "Unspecified issue")),
            "rbi_clause": str(item.get("rbi_clause", "Not cited")),
            "required_fix": str(item.get("required_fix", "Review against the cited source.")),
        })
    return {"status": "FAIL" if clean else data["status"], "violations": clean}


def audit_kfs_document(pdf_path: str, api_key: str | None = None) -> dict[str, Any]:
    """Audit a KFS PDF using local RBI PDFs and Groq hosted inference."""
    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Groq API key is missing. Add GROQ_API_KEY to Streamlit Secrets.")

    kfs_text = _extract_pdf_text(pdf_path)
    chunks = _get_rule_chunks()
    if not chunks:
        return {"status": "FAIL", "violations": [{
            "issue": "UNABLE TO VERIFY DUE TO MISSING RBI CONTEXT",
            "rbi_clause": "No readable RBI PDF sources are configured.",
            "required_fix": "Add verified official RBI guideline PDFs to the rbi_documents folder.",
        }]}

    evidence: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for query in CHECK_QUERIES:
        for chunk in _rank_chunks(query, chunks, config.RETRIEVAL_CHUNKS_PER_CHECK):
            identity = (chunk["source"], chunk["page"], chunk["text"])
            if identity not in seen:
                seen.add(identity)
                evidence.append(chunk)
    if not evidence:
        return {"status": "FAIL", "violations": [{
            "issue": "UNABLE TO VERIFY DUE TO MISSING RBI CONTEXT",
            "rbi_clause": "No relevant text was retrieved from configured sources.",
            "required_fix": "Check that official RBI PDFs contain text and cover these requirements.",
        }]}

    context = "\n\n".join(
        f"[Source: {item['source']}, page {item['page']}]\n{item['text']}" for item in evidence
    )
    try:
        client = Groq(api_key=api_key, timeout=config.GROQ_TIMEOUT_SECONDS)
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            temperature=0,
            max_tokens=1600,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": COMPLIANCE_SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"RBI source context (cite only these sources and page numbers):\n{context}\n\n"
                    f"Draft KFS text:\n{kfs_text}\n\nReturn only the requested JSON report."
                )},
            ],
        )
    except Exception as exc:
        raise RuntimeError(f"Groq audit request failed: {exc}") from exc

    response_text = completion.choices[0].message.content or ""
    try:
        return _validate_report(json.loads(response_text))
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"The AI service returned an invalid audit report: {exc}") from exc