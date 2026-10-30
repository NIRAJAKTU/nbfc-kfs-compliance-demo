"""
app.py — Harvey for Finance: KFS Compliance Auditor
====================================================
Streamlit executive dashboard for auditing draft Key Fact Statements (KFS)
against RBI Digital Lending Guidelines.

Launch:
    streamlit run app.py
"""

import os
import tempfile
from pathlib import Path

import streamlit as st
import config

# ---------------------------------------------------------------------------
# Page configuration (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="KFS Compliance Auditor | RBI Digital Lending",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_groq_api_key() -> str | None:
    environment_key = os.getenv("GROQ_API_KEY")
    if environment_key:
        return environment_key

    local_secrets = Path.cwd() / ".streamlit" / "secrets.toml"
    if not local_secrets.is_file():
        return None
    try:
        return st.secrets.get("GROQ_API_KEY")
    except Exception:
        return None


groq_api_key = get_groq_api_key()
rbi_pdf_paths = sorted(Path(config.RBI_DOCS_DIR).glob("*.pdf"))
has_rbi_sources = bool(rbi_pdf_paths)
uses_sample_rules = any("sample" in path.name.lower() for path in rbi_pdf_paths)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚖️ Harvey for Finance")
    st.caption("AI-Native Compliance Infrastructure for Indian NBFCs")

    st.divider()

    st.markdown("**Regulatory Scope**")
    st.markdown("- RBI Digital Lending Guidelines (2022)")
    st.markdown("- Master Directions — NBFC")
    st.markdown("- Fair Practices Code")

    st.divider()

    st.markdown("**Audit Checklist**")
    st.markdown("1. APR transparency (all-inclusive)")
    st.markdown("2. Penal charges — flat fee only")
    st.markdown("3. Cooling-off / look-up period")
    st.markdown("4. Nodal Grievance Officer details")

    st.divider()

    st.markdown("**Hosted Demo Stack**")
    st.markdown("- Groq — hosted language model")
    st.markdown("- Local PDF text retrieval with source pages")
    st.markdown("- Streamlit — hosted interface")

    st.divider()

    if groq_api_key:
        st.success("AI service: Configured", icon="✅")
    else:
        st.error("AI service: API key missing", icon="❌")

    if has_rbi_sources:
        st.success(f"Rule PDFs: {len(rbi_pdf_paths)} loaded", icon="✅")
        with st.expander("Configured rule sources"):
            for path in rbi_pdf_paths:
                st.caption(path.name)
    else:
        st.warning("Rule PDFs: None configured", icon="⚠️")

# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------
audit_tab, why_tab, architecture_tab, contact_tab = st.tabs(
    ["KFS Audit", "Why this exists", "AI Architecture", "Contact"]
)

with audit_tab:
    st.title("RBI KFS Compliance Auditor")
    st.markdown(
        "Upload a draft **Key Fact Statement (KFS)** or **Loan Agreement** to perform a "
        "prototype review against the configured RBI source PDFs."
    )

    st.warning(
        "**Prototype only.** This is not legal advice or an authoritative compliance decision. "
        "Do not upload real borrower or confidential information. Uploaded PDF text is sent to Groq for analysis.",
        icon="⚠️",
    )

    if uses_sample_rules:
        st.error(
            "The configured RBI source includes a synthetic sample document, not official RBI rules. "
            "Replace it with verified official RBI PDFs before presenting results as regulatory analysis.",
            icon="🚨",
        )

    prereqs_ok = bool(groq_api_key and has_rbi_sources)
    if not groq_api_key:
        st.info("Add `GROQ_API_KEY` in Streamlit App Settings → Secrets to enable audits.")
    if not has_rbi_sources:
        st.info("Add verified RBI source PDFs to the `rbi_documents/` folder before deployment.")

    st.divider()

    uploaded_file = st.file_uploader(
        label="Drag and drop or browse your draft KFS / Loan Agreement",
        type=["pdf"],
        help=f"Text-based PDF only; maximum {config.MAX_UPLOAD_MB} MB and {config.MAX_KFS_PAGES} pages.",
        label_visibility="visible",
    )

    if uploaded_file is not None:
        uploaded_bytes = uploaded_file.getvalue()
        file_size_mb = len(uploaded_bytes) / (1024 * 1024)
        upload_too_large = file_size_mb > config.MAX_UPLOAD_MB
        if upload_too_large:
            st.error(f"File is {file_size_mb:.1f} MB; the limit is {config.MAX_UPLOAD_MB} MB.")
        else:
            st.success(f"Uploaded: **{uploaded_file.name}** | {file_size_mb:.1f} MB", icon="📄")

        run_btn = st.button(
            label="⚖️ Run RBI Audit",
            type="primary",
            use_container_width=True,
            disabled=not prereqs_ok or upload_too_large,
            help="Configure the Groq secret and rule PDFs first." if not prereqs_ok else "",
        )

        if run_btn:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_bytes)
                tmp_path = tmp.name

            try:
                with st.spinner("Retrieving rule excerpts and requesting the audit…"):
                    from audit_engine import audit_kfs_document
                    result = audit_kfs_document(tmp_path, api_key=groq_api_key)

                st.session_state["audit_result"] = result
                st.session_state["audit_filename"] = uploaded_file.name

            except RuntimeError as exc:
                st.error(f"**Audit failed:** {exc}", icon="🚨")
                st.session_state.pop("audit_result", None)

            except Exception as exc:
                st.error(f"**Unexpected error:** {exc}", icon="🚨")
                st.session_state.pop("audit_result", None)

            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    if "audit_result" in st.session_state:
        result: dict = st.session_state["audit_result"]
        filename: str = st.session_state.get("audit_filename", "document.pdf")
        status: str = result.get("status", "FAIL").upper()
        violations: list = result.get("violations", [])

        st.divider()
        st.subheader(f"Audit Report — {filename}")

        if status == "PASS":
            st.success(
                "**COMPLIANT — PASS** &nbsp; This KFS satisfies all checked RBI Digital Lending mandates.",
                icon="✅",
            )
        else:
            st.error(
                f"**NON-COMPLIANT — FAIL** &nbsp; {len(violations)} violation(s) detected. "
                "Review each finding against the cited source and have a qualified compliance professional assess it.",
                icon="❌",
            )

        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Audit Status", status)
        m_col2.metric("Violations Found", len(violations))
        m_col3.metric("Checks Performed", 4, help="APR · Penal Charges · Cooling-Off Period · Grievance Officer")

        if violations:
            st.subheader("Violation Details")
            for idx, violation in enumerate(violations, start=1):
                issue_title = violation.get("issue", "Unknown Issue")
                with st.expander(f"Violation {idx} of {len(violations)}: {issue_title}", expanded=True):
                    left, right = st.columns([1, 1])
                    with left:
                        st.markdown("##### Issue Detected")
                        st.write(violation.get("issue", "—"))
                        st.markdown("##### RBI Clause / Reference")
                        st.code(violation.get("rbi_clause", "—"), language=None)
                    with right:
                        st.markdown("##### Required Fix")
                        st.warning(violation.get("required_fix", "—"), icon="✏️")
        elif status == "PASS":
            st.info("No violations found. All 4 RBI compliance checks passed.", icon="ℹ️")

        with st.expander("View Raw JSON Audit Report"):
            st.json(result)

        if st.button("Clear Results", type="secondary"):
            st.session_state.pop("audit_result", None)
            st.session_state.pop("audit_filename", None)
            st.rerun()

with why_tab:
    st.title("Why this exists")
    st.markdown(
        "A regulatory requirement only protects customers when it is translated into a "
        "repeatable operational check. When a loan disclosure is incomplete, a pricing "
        "control is missed, or a required process is not followed, the consequences can "
        "include customer harm, remediation, restrictions on new business, financial "
        "penalties, and in serious cases licence action."
    )
    st.markdown(
        "This project explores a specific prevention point in digital lending: review the "
        "Key Fact Statement **before disbursal**, compare it with configured regulatory "
        "evidence, and surface potential gaps for a compliance professional to resolve. "
        "The aim is to move checks closer to the operational decision, not to replace "
        "compliance teams or claim that one KFS check prevents every enforcement event."
    )

    st.subheader("Regulatory events that show the stakes")
    st.markdown(
        "**Navi Finserv and three other NBFCs (2024):** RBI directed them to cease new "
        "loan sanctions and disbursals from October 21, citing concerns including "
        "excessive pricing/spreads, fair-practice issues, and other supervisory findings. "
        "Navi's restrictions were lifted on December 2, 2024 after RBI accepted remediation. "
        "This was a supervisory restriction, not a three-month ban. "
        "[RBI: restrictions imposed](https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=58921) · "
        "[RBI: restrictions lifted](https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=59226)"
    )
    st.markdown(
        "**Paytm Payments Bank (2024–2026).** RBI's 2024 directions restricted further "
        "deposits/credits and certain services; they were not a licence cancellation at "
        "that point. RBI later cancelled the bank's licence effective April 24, 2026, "
        "citing statutory and licence-condition grounds. Paytm Payments Bank is a payments "
        "bank, not an NBFC, so this is a distinct example of regulatory action. "
        "[RBI FAQ on 2024 restrictions](https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=3573) · "
        "[RBI: 2026 licence cancellation](https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62621)"
    )
    st.caption(
        "These events have different facts and legal bases. This KFS tool only checks four disclosure topics; "
        "it would not have prevented every issue in these cases."
    )

    st.warning(
        "The current bundled RBI PDF is synthetic demo material. Replace it with verified official source documents "
        "before claiming RBI-grounded results. The model's output needs human compliance review; this is not legal advice.",
        icon="⚠️",
    )

with architecture_tab:
    st.title("AI Architecture")
    st.markdown(
        "This demo showcases a grounded **GenAI / RAG pipeline**: retrieve relevant regulatory evidence first, "
        "then ask a language model to assess the KFS against that evidence. The model is not treated as the source of law."
    )

    st.subheader("End-to-end GenAI flow")
    st.caption("Knowledge preparation creates the evidence base; inference retrieves evidence for each KFS and generates a reviewable result.")

    st.markdown("**1 · Knowledge preparation**")
    prep_columns = st.columns([1, 0.12, 1, 0.12, 1, 0.12, 1])
    prep_steps = [
        (0, "Regulatory sources", "RBI PDFs with page\nand document identity"),
        (2, "Text + provenance", "Extract text and retain\nsource/page metadata"),
        (4, "Chunking", "Split long text into\noverlapping passages"),
        (6, "Rule corpus", "Prepared passages\nready for retrieval"),
    ]
    for column_index, title, detail in prep_steps:
        with prep_columns[column_index]:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(detail)
    for column_index in (1, 3, 5):
        with prep_columns[column_index]:
            st.markdown("<div style='text-align:center; padding-top:18px'>→</div>", unsafe_allow_html=True)

    st.markdown("**2 · Per-document inference**")
    audit_columns = st.columns([1, 0.1, 1, 0.1, 1, 0.1, 1, 0.1, 1])
    audit_steps = [
        (0, "KFS input", "Extract text from\nthe draft document"),
        (2, "Topic queries", "APR · penalties · exit\nperiod · grievance"),
        (4, "Evidence retrieval", "Rank matching chunks;\nkeep source/page refs"),
        (6, "RAG + LLM", "Prompt combines KFS,\nevidence, audit rules"),
        (8, "Structured review", "Validate JSON; show\nfindings to a human"),
    ]
    for column_index, title, detail in audit_steps:
        with audit_columns[column_index]:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(detail)
    for column_index in (1, 3, 5, 7):
        with audit_columns[column_index]:
            st.markdown("<div style='text-align:center; padding-top:18px'>→</div>", unsafe_allow_html=True)

    st.info(
        "**Core design choice:** retrieval grounds generation (RAG). This helps limit unsupported answers, "
        "but does not guarantee correctness; source quality, retrieval coverage, and human review still matter.",
        icon="🧠",
    )

    st.subheader("AI / GenAI concepts demonstrated")
    concepts = [
        (
            "Document chunking + provenance",
            "Long rulebooks are divided into overlapping passages. Each passage keeps its source PDF and page number so retrieved evidence can be traced back.",
        ),
        (
            "Local rule corpus",
            "Configured RBI documents form the bounded knowledge base. The model receives selected excerpts instead of being asked to recall regulations from training memory.",
        ),
        (
            "Lexical retrieval in a RAG pipeline",
            "Topic-focused queries rank passages by term relevance, then provide those passages as context to generation. This MVP uses lightweight lexical search; it is not an embedding/vector search system.",
        ),
        (
            "Prompt design + task decomposition",
            "Four compliance questions are made explicit, with instructions to use only supplied context, fail closed when evidence is missing, and avoid invented citations.",
        ),
        (
            "LLM inference",
            "Groq serves the configured GPT-OSS 120B model. It compares extracted KFS text with retrieved evidence and drafts a structured assessment; uploaded text is sent to the model provider.",
        ),
        (
            "Structured generation + validation",
            "JSON-mode output is checked for the expected status and violations fields before the UI displays it, reducing malformed-response failures.",
        ),
        (
            "Human-in-the-loop review",
            "The result is an assistive finding, not an autonomous compliance verdict. A qualified reviewer checks the cited document and makes the decision.",
        ),
    ]
    for concept, explanation in concepts:
        st.markdown(f"**{concept}**  \n{explanation}")

    st.warning(
        "Current limitation: rules bundled with this demo are synthetic. Replace them with verified official RBI documents, "
        "and evaluate retrieval and citations before presenting this as regulation-grounded. Not legal advice.",
        icon="⚠️",
    )

with contact_tab:
    st.title("Contact")
    st.markdown(
        "Have a business challenge, an NBFC workflow, or an AI idea you want to explore? "
        "I can connect your use case with my AI, GenAI, and emerging-technology skills, then work with you "
        "to build a practical solution around what your business needs. Reach out to discuss your goal, "
        "shape the approach, or explore an implementation together."
    )
    st.markdown("**Email**  \n[singhn9282@gmail.com](mailto:singhn9282@gmail.com)")
    st.markdown("**LinkedIn**  \n[Connect with Niraj](https://www.linkedin.com/in/niraj-s-8b9984152/)")
    st.caption("Please do not send confidential customer, borrower, or regulated data through this public demo.")
