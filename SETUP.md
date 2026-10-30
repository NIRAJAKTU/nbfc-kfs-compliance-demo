# Harvey for Finance — Hosted Demo Setup
# Streamlit + Groq inference

---

## Prerequisites

### 1. Install Python 3.10+
Check your version:
```
python --version
```
Download from https://python.org if needed.

## Project Setup

### Step 1 — Install uv (fast modern Python package manager)

**Windows (PowerShell):**
```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Mac / Linux:**
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:
```
uv --version
```

> `uv` installs as a standalone binary. Project dependencies are installed into the virtual environment.

### Step 2 — Create a virtual environment

**Windows:**
```
uv venv venv --python 3.12
venv\Scripts\activate
```

**Mac / Linux:**
```
uv venv venv --python 3.12
source venv/bin/activate
```

### Step 3 — Install dependencies
```
uv pip install -r requirements.txt
```
Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`, then put your Groq API key in that local ignored file. Never commit the real key.

---

## Ingest RBI Documents

### Step 4 — Add RBI PDF documents
Drop one or more RBI PDF files into the `rbi_documents/` folder.

Recommended documents (download free from rbi.org.in):
- Digital Lending Guidelines 2022 (RBI/2022-23/111)
- Master Direction — NBFC Directions 2016
- Fair Practices Code for NBFCs (Master Circular)

### Step 5 — Check the source PDFs
```
python ingest_rbi.py
```
This verifies the PDFs are readable. The app reads and searches them directly at runtime; no separate vector-index build is performed.

---

## Run the Dashboard

### Step 6 — Launch the Streamlit app
```
streamlit run app.py
```
The dashboard opens at: http://localhost:8501

---

## Usage

1. Open http://localhost:8501 in your browser
2. Check the sidebar for the AI service and configured rule PDF sources
3. Upload a draft KFS or Loan Agreement PDF using the file uploader
4. Click **Run RBI Audit**
5. Review the PASS / FAIL status and individual violation cards

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Groq API key missing | Add `GROQ_API_KEY` to local Streamlit secrets or hosted app secrets |
| No rules retrieved | Put text-based rule PDFs in `./rbi_documents/` |
| Groq request rejected | Check API key, model availability, and provider limits |
| Blank/empty PDF error | The PDF is likely a scanned image. Use a text-based PDF instead. |

---

## System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| Runtime | Streamlit-hosted | Streamlit-hosted |
| Python | 3.12 | 3.12 |
| Internet | Required for Groq requests | Required |

---

## File Structure

```
MVP_Compalaince/
├── app.py                  # Streamlit dashboard
├── audit_engine.py         # Core audit function
├── ingest_rbi.py           # RBI document ingestion pipeline
├── config.py               # All configuration constants
├── requirements.txt        # Python dependencies
├── rbi_documents/          # Drop RBI PDFs here
│   └── .gitkeep
└── .streamlit/secrets.toml # Local API secret; do not commit
```

## Deploy to Streamlit Community Cloud

1. Push the project to a personal GitHub repository, not a company repository.
2. Create an app at https://share.streamlit.io and select that repository, branch, and `app.py`.
3. Open app Settings → Secrets and enter `GROQ_API_KEY = "your-key"`. Never commit the key.
4. Deploy, verify the hosted app, then share the URL assigned by Streamlit.

The checked-in RBI PDF is synthetic demo content. Replace it with verified official RBI sources before presenting results as regulation-based. Do not upload real borrower or confidential PDFs to a public demo.
