# =============================================================================
# Harvey for Finance — Central Configuration
# All constants live here. Edit this file to switch models or paths.
# =============================================================================

# --- Groq hosted inference ---
# Set GROQ_API_KEY in Streamlit secrets or the local environment, never in source.
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_TIMEOUT_SECONDS = 90.0

# --- Regulatory documents and hosted-demo safeguards ---
RBI_DOCS_DIR = "./rbi_documents"         # Bundle verified source PDFs for deployment
CHUNK_SIZE_CHARS = 2400
CHUNK_OVERLAP_CHARS = 350
RETRIEVAL_CHUNKS_PER_CHECK = 2
MAX_KFS_PAGES = 25
MAX_KFS_TEXT_CHARS = 24000
MAX_UPLOAD_MB = 10

