# Harvey for Finance (Hosted Demo MVP)

AI-Native Compliance Auditor for Indian NBFC digital lending flows.

This is a prototype that audits a draft KFS/loan PDF against the PDF rule sources in `rbi_documents/`. It uses local PDF retrieval and Groq-hosted model inference. It is not legal advice or an authoritative compliance decision.

---

## Quick Start (For Demo)

For local testing, create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`, enter your own Groq key in that ignored local file, then run:

```powershell
cd "c:\Users\niraj\VsCodes\MVP_Compalaince"
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

Open http://localhost:8501. No local Ollama process is needed for this hosted version.

---

## One-Time Setup (Already Done Once)

You only do these once per machine:

1. Install Python 3.12 and `uv`.
2. Create venv + install packages (using uv):

   uv venv venv --python 3.12
   .\venv\Scripts\activate
   uv pip install -r requirements.txt

3. Put permitted RBI reference PDFs in `rbi_documents/`. For a hosted deployment, the source PDFs must be committed to your personal repository; keep confidential customer documents out of it.

4. Optionally check PDF readability:

  python ingest_rbi.py

The app reads the configured source PDFs directly; no separate vector index is built.

---

## What This MVP Does (Simple)

1. You upload a draft KFS/loan PDF in the web app.
2. System extracts text from your PDF.
3. System retrieves relevant passages from configured rule PDFs and retains their file/page references.
4. Groq-hosted LLM checks 4 items:
   - APR disclosure
   - Penal charges as flat fee (no compounding)
   - Cooling-off/look-up period
   - Nodal grievance officer details
5. App returns PASS/FAIL with exact violations and fixes.

---

## Local Architecture (Beginner View)

Input PDF -> Text Extractor -> RBI Rule Retriever -> LLM Auditor -> JSON Result -> Streamlit UI

### Practical flow
- RBI rule PDFs are bundled in `rbi_documents/` and read directly by the app.
- During audit, lightweight keyword scoring retrieves relevant, page-labeled passages.
- LLM receives:
  1) strict compliance instructions,
  2) retrieved RBI context,
  3) uploaded KFS text,
  and returns a strict JSON audit report.

---

## Why This Stack (MVP Reasoning)

### Streamlit
- Fastest way to build a clean web UI in Python.
- Great for internal demos with minimal frontend effort.

### Groq
- Provides hosted model inference, so the public app does not need a GPU or a local Ollama server.
- Requires an API key stored in Streamlit Secrets; free-tier availability and usage limits are controlled by Groq.

### Lightweight lexical retrieval
- Finds source passages by matching compliance-topic terms, without downloading a large embedding model.
- Keeps hosting memory and dependency needs low; it is less semantic than vector search and must be evaluated against real documents.

### pypdf
- Simple PDF text extraction from uploaded KFS and RBI docs.
- Works well for text-based PDFs.

### uv package manager
- Faster dependency resolution/install than pip.
- Cleaner workflow for modern Python projects.

---

## File Map (Where Core Logic Lives)

If you want to understand the project quickly, read files in this order:

1. `app.py`
   - UI and demo entry point.
   - Handles PDF upload, button click, spinner, PASS/FAIL rendering, and showing violation cards.
   - Calls the audit engine when user clicks `Run RBI Audit`.

2. `audit_engine.py`
   - Main business logic for compliance checking.
   - Core function: `audit_kfs_document(pdf_path)`.
  - Extracts KFS text, retrieves source/page-labeled passages, calls Groq, validates the JSON result.
   - If you want to understand the actual audit flow, this is the most important file.

3. `ingest_rbi.py`
  - Checks that the RBI PDFs are readable. The audit engine loads and chunks PDFs directly at runtime; no separate index build is needed.

4. `config.py`
   - Central configuration layer.
  - Holds Groq model, source directory, chunking, retrieval, and upload limits.
   - Change this file if you want to switch model or tune retrieval behavior.

### Supporting files

- `requirements.txt`
  - Dependency list used to recreate the environment.

- `README.md`
  - Beginner-friendly explanation of setup, architecture, and demo flow.

- `SETUP.md`
  - More command-focused setup notes.

- `create_sample_rbi_pdf.py`
  - Utility script used to generate a sample RBI guideline PDF for local demo/testing.

- `rbi_documents/`
  - Input folder for RBI rule PDFs before ingestion.

- `.streamlit/secrets.toml`
  - Local-only Groq API key file. It is ignored by Git; never commit the real key.

- `venv/`
  - Local Python virtual environment.

### In one line

- `app.py` = interface
- `audit_engine.py` = core audit brain
- `ingest_rbi.py` = checks RBI source PDFs
- `config.py` = controls behavior

---

## Basic Concepts (Very Short)

- LLM:
  A language model that reads instructions + context and generates structured output.

- Lexical retrieval:
  Ranks passages using the words they share with a compliance-topic query. This MVP uses it instead of a large embedding model to stay lightweight when hosted.

- RAG (Retrieval-Augmented Generation):
  First retrieve rule context, then ask the LLM to evaluate using that context. Retrieval helps ground output but does not guarantee correctness.

- Chunking:
  Splitting long documents into smaller pieces so retrieval is accurate and efficient.

- Compliance Rule Engine (in this MVP):
  A strict prompt + retrieved RBI clauses that force a PASS/FAIL JSON decision.

---

## MVP Scope (Current)

Included now:
- Hosted Groq-based RBI KFS prototype
- PASS/FAIL with actionable violation messages
- Local PDF source retrieval with page labels

Not included yet:
- Multi-tenant auth and role controls
- Automated horizon scanning crawlers
- Auto-redlining of internal SOPs
- Full immutable audit ledger and enterprise integrations

---

## Troubleshooting

### Groq key missing
For local use, add `GROQ_API_KEY` to `.streamlit/secrets.toml`. On Streamlit Community Cloud, add it under the app's Settings → Secrets. Never put the real key in GitHub.

### RBI sources missing or unreadable
Add readable, verified source PDFs to `rbi_documents/`, then check them with:

python ingest_rbi.py

### App not opening
Confirm Streamlit is running and open http://localhost:8501.

---

## Demo Tip (Non-Technical Audience)

Use synthetic KFS examples only while the synthetic sample RBI document is configured. Replace that source with verified official RBI documents before presenting results as RBI-based analysis.

## Publish a Personal Demo

1. Push this project to a personal GitHub repository. Do not select your organization repository.
2. Connect that personal repository in Streamlit Community Cloud and deploy `app.py`.
3. Add `GROQ_API_KEY` under the deployed app's Settings → Secrets. Never put the real key in GitHub or chat.
4. Open the URL assigned by Streamlit and test with synthetic PDFs only.

The app has 10 MB upload and 25-page limits. Extracted KFS text and retrieved rule passages are sent to Groq. This prototype is not legal advice; do not use it with confidential borrower information.
