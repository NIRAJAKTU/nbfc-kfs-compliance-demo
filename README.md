# AI-Native Financial Document Intelligence (Portfolio Demo)

An AI/GenAI portfolio demonstration of financial document intelligence and evidence-grounded regulatory analysis.

This independent demonstration uses synthetic regulatory reference documents and sample financial documents. It is not an official RBI compliance system, does not establish regulatory compliance and is not intended for production financial decision-making.

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

## What This Demo Does

1. You upload a draft KFS/loan PDF in the web app.
2. System extracts text from your PDF.
3. System retrieves relevant passages from configured rule PDFs and retains their file/page references.
4. Groq-hosted LLM assesses four topics:
   - APR disclosure
   - Penal charges as flat fee (no compounding)
   - Cooling-off/look-up period
   - Nodal grievance officer details
5. The app returns one category per check: `Compliant`, `Potential Gap`, or `Insufficient Evidence`.
6. The reviewer can inspect KFS page excerpts and retrieved rule passages, see recommended actions, and download a PDF assessment report.

---

## Local Architecture (Beginner View)

Input PDF -> Text Extractor -> RBI Rule Retriever -> LLM Auditor -> JSON Result -> Streamlit UI

### Practical flow
- RBI rule PDFs are bundled in `rbi_documents/` and read directly by the app.
- During audit, lightweight lexical scoring retrieves topic-relevant, page-labeled passages.
- LLM receives:
  1) strict compliance instructions,
  2) retrieved source passages with evidence IDs,
  3) extracted KFS text with page IDs,
  and returns a structured JSON assessment that is validated before display.

---

## Why This Stack (MVP Reasoning)

### Streamlit
- Fastest way to build a clean web UI in Python.
- Great for internal demos with minimal frontend effort.

### Groq + GPT-OSS 120B
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
  - Handles bounded PDF upload, staged processing indicators, three-category result cards, evidence display, and report download.
  - Includes Business Challenges, AI Architecture, and AI Solutions tabs for portfolio viewers.

2. `audit_engine.py`
   - Main business logic for compliance checking.
   - Core function: `audit_kfs_document(pdf_path)`.
  - Extracts KFS text, retrieves source/page-labeled passages, calls Groq, validates evidence IDs and the JSON result.
   - If you want to understand the actual audit flow, this is the most important file.

3. `ingest_rbi.py`
  - Checks that the RBI PDFs are readable. The audit engine loads and chunks PDFs directly at runtime; no separate index build is needed.

4. `config.py`
   - Central configuration layer.
  - Holds Groq model, source directory, chunking, retrieval, and upload limits.
   - Change this file if you want to switch model or tune retrieval behavior.

5. `audit_report.py`
  - Creates the downloadable PDF assessment, including per-check findings, evidence references, recommendations, and the demonstration disclaimer.

### Supporting files

- `requirements.txt`
  - Dependency list used to recreate the environment.

- `.streamlit/config.toml`
  - Streamlit UI configuration, including upload-size limit and telemetry preference.

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
- `audit_report.py` = downloadable PDF report
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

- Structured LLM output:
  A machine-readable assessment with one of three categories per check, validated against retrieved evidence references.

---

## MVP Scope (Current)

Included now:
- Hosted Groq-based financial document intelligence demonstration
- RAG-style lexical retrieval and source/page evidence display
- Three-category assessments and downloadable PDF reports
- Business challenges, AI architecture, and implementation contact tabs
- Sample-oriented safeguards and explicit synthetic-data disclaimer

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

The app has 10 MB upload and 25-page limits. Extracted KFS text and retrieved rule passages are sent to Groq. Outputs are AI-generated demonstration assessments for human review, not legal advice or production decisions. Do not upload confidential borrower information.
