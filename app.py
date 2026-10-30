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
from audit_report import DISCLAIMER, build_audit_pdf

# ---------------------------------------------------------------------------
# Page configuration (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Financial Document Intelligence | Demo",
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
    st.title("AI-Native Financial Document Intelligence")
    st.caption("Regulatory analysis · Independent AI/GenAI portfolio demo")

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
    ["Document Intelligence", "Business Challenges", "AI Architecture", "AI Solutions"]
)

with audit_tab:
    st.title("AI-Powered Financial Document Intelligence")
    st.markdown(
        "An intelligent document analysis engine demonstrating how Generative AI, RAG and "
        "evidence-grounded reasoning can streamline financial document review."
    )

    st.warning(DISCLAIMER, icon="⚠️")
    st.caption("AI-generated demonstration assessment · Human review required · Do not upload confidential documents")

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
        label="Upload a sample financial document",
        type=["pdf"],
        help=f"Text-based PDF only · up to {config.MAX_UPLOAD_MB} MB · up to {config.MAX_KFS_PAGES} pages.",
        label_visibility="visible",
    )

    if uploaded_file is not None:
        uploaded_bytes = uploaded_file.getvalue()
        file_size_mb = len(uploaded_bytes) / (1024 * 1024)
        upload_too_large = file_size_mb > config.MAX_UPLOAD_MB
        if upload_too_large:
            st.error(f"File is {file_size_mb:.1f} MB; the limit is {config.MAX_UPLOAD_MB} MB.")
        else:
            from pypdf import PdfReader
            from io import BytesIO

            try:
                page_count = len(PdfReader(BytesIO(uploaded_bytes)).pages)
            except Exception:
                page_count = 0
            if not page_count:
                st.error("This file could not be read as a PDF. Choose a valid, text-based PDF.")
                upload_too_large = True
            elif page_count > config.MAX_KFS_PAGES:
                st.error(f"This PDF has {page_count} pages; the limit is {config.MAX_KFS_PAGES} pages.")
                upload_too_large = True
            else:
                st.success(
                    f"Ready for analysis · **{uploaded_file.name}** · {page_count} pages · {file_size_mb:.1f} MB",
                    icon="📄",
                )

        run_btn = st.button(
            label="Analyze document",
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
                with st.status("Preparing document intelligence workflow…", expanded=True) as progress:
                    from audit_engine import audit_kfs_document

                    def report_stage(stage: str) -> None:
                        progress.update(label=stage, state="running", expanded=True)

                    result = audit_kfs_document(
                        tmp_path,
                        api_key=groq_api_key,
                        progress_callback=report_stage,
                    )
                    progress.update(label="Assessment generated · Ready for human review", state="complete", expanded=False)

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
        overall: str = result.get("overall_assessment", "Insufficient Evidence")
        checks: list = result.get("checks", [])
        category_counts = {
            category: sum(item.get("category") == category for item in checks)
            for category in ("Compliant", "Potential Gap", "Insufficient Evidence")
        }

        st.divider()
        st.subheader("AI-generated assessment")
        st.markdown(f"**Document:** {filename} · **Overall:** {overall}")
        st.caption("Decision support only. Interpret findings against the cited source documents; a human reviewer makes the decision.")

        summary_cols = st.columns(3)
        summary_cols[0].metric("Compliant", category_counts["Compliant"])
        summary_cols[1].metric("Potential Gap", category_counts["Potential Gap"])
        summary_cols[2].metric("Insufficient Evidence", category_counts["Insufficient Evidence"])

        st.subheader("Validation results")
        category_icons = {"Compliant": "✓", "Potential Gap": "!", "Insufficient Evidence": "?"}
        for check in checks:
            category = check.get("category", "Insufficient Evidence")
            with st.container(border=True):
                st.markdown(f"### {category_icons.get(category, '•')} {check.get('check', 'Document check')} · {category}")
                st.write(check.get("finding", "No finding was generated."))

                document_details = check.get("document_details", [])
                source_details = check.get("source_details", [])
                evidence_col, source_col = st.columns(2)
                with evidence_col:
                    st.markdown("**Document evidence**")
                    if document_details:
                        for item in document_details:
                            st.caption(item.get("reference", "KFS page"))
                            st.code(item.get("excerpt", ""), language=None)
                    else:
                        st.caption("No specific KFS page was cited.")
                with source_col:
                    st.markdown("**Retrieved source references**")
                    if source_details:
                        for item in source_details:
                            st.caption(f"{item.get('source', 'Rule source')} · page {item.get('page', '?')} · ref {item.get('id', '')}")
                            st.write(item.get("text", ""))
                    else:
                        st.caption("No supporting rule passage was retrieved for this check.")

                st.markdown("**Recommended next action**")
                if category == "Potential Gap":
                    st.warning(check.get("recommended_action", "Review this disclosure with a compliance professional."), icon="⚠️")
                elif category == "Insufficient Evidence":
                    st.info(check.get("recommended_action", "Review the source document and KFS manually."), icon="ℹ️")
                else:
                    st.success(check.get("recommended_action", "No corrective action suggested by this demonstration."), icon="✅")

        report_bytes = build_audit_pdf(filename, result)
        safe_filename = Path(filename).stem.replace(" ", "_")
        st.download_button(
            "Download AI assessment report (PDF)",
            data=report_bytes,
            file_name=f"{safe_filename}_ai_assessment.pdf",
            mime="application/pdf",
            type="secondary",
        )

        with st.expander("View Raw JSON Audit Report"):
            st.json(result)

        if st.button("Clear Results", type="secondary"):
            st.session_state.pop("audit_result", None)
            st.session_state.pop("audit_filename", None)
            st.rerun()

with why_tab:
    st.title("Business Challenges & AI Opportunities")
    st.markdown(
        "Financial institutions work across changing regulations, high-volume documents, "
        "multiple systems, and human review queues. Missed or unclear information can increase "
        "customer harm, remediation work, operational friction, and supervisory risk. AI can "
        "help teams surface relevant information sooner while keeping accountable decisions with people."
    )
    st.markdown(
        "This portfolio demo focuses on one narrow use case: **AI-assisted review of a "
        "digital lending KFS before disbursal**, comparing selected disclosures with supplied "
        "regulatory passages and surfacing evidence-backed questions for a human reviewer."
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

    st.subheader("Where AI may help financial institutions")
    opportunity_cols = st.columns(2)
    opportunities = [
        ("Automated document intelligence", "Extract fields, classify documents, compare versions, and route exceptions for review."),
        ("Regulatory document analysis", "Search circulars and directions, summarize changes, and link findings back to source clauses."),
        ("Compliance workflow automation", "Prepare review queues, evidence packs, and escalation tasks while retaining human approvals."),
        ("Financial document extraction", "Read KFS, agreements, statements, and applications into structured data for downstream systems."),
        ("Intelligent reporting", "Draft concise summaries, exception reports, and audit-ready evidence references from validated inputs."),
        ("Human-assisted decision support", "Give specialists traceable context and recommendations without handing decisions to an autonomous model."),
    ]
    for index, (title, detail) in enumerate(opportunities):
        with opportunity_cols[index % 2]:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(detail)

    with st.expander("Future opportunities (not implemented in this demo)"):
        st.markdown(
            "- Regulatory change monitoring with human-approved impact assessments\n"
            "- Policy and SOP change proposals with source-linked redlines\n"
            "- LOS/workflow integrations that pause or route exceptions before disbursal\n"
            "- Agentic AI workflows for multi-step execution with approval gates\n"
            "- Multi-regulator and organization-specific knowledge spaces\n"
            "- Evaluation dashboards for retrieval quality, false positives, and reviewer feedback\n\n"
            "These are future opportunities, not capabilities implemented in this demo."
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

    st.subheader("AI / GenAI capabilities demonstrated")
    concepts = [
        (
            "Intelligent Document Processing (IDP) + chunking",
            "Extract text and page-level context from PDFs, then split long regulatory documents into overlapping passages with provenance.",
        ),
        (
            "Bounded local rule corpus",
            "Configured regulatory PDFs form the evidence base; selected excerpts are supplied to the model instead of asking it to recall rules from training memory.",
        ),
        (
            "RAG + context-aware regulatory analysis",
            "Four topic queries rank relevant passages by lexical relevance. This lightweight MVP does not use embeddings or vector search.",
        ),
        (
            "Multi-stage workflow + prompt design",
            "Extraction → topic-specific retrieval → LLM assessment → reference validation → human review, with instructions to avoid unsupported citations.",
        ),
        (
            "LLM-powered document intelligence",
            "Groq serves GPT-OSS 120B to compare KFS text with retrieved passages and draft a structured assessment; uploaded text is sent to the provider.",
        ),
        (
            "Structured outputs + explainable evidence (XAI)",
            "JSON-mode results use validated KFS page IDs and retrieved rule IDs, making the supporting evidence visible for reviewer inspection.",
        ),
        (
            "Human-in-the-loop (HITL) decision support",
            "This is an assistive finding, not an autonomous decision. A qualified reviewer verifies evidence and owns any business or compliance action.",
        ),
    ]
    concept_cols = st.columns(2)
    for index, (concept, explanation) in enumerate(concepts):
        with concept_cols[index % 2]:
            with st.container(border=True):
                st.markdown(f"**{concept}**")
                st.caption(explanation)

    st.warning(
        "Current limitation: rules bundled with this demo are synthetic. Replace them with verified official RBI documents, "
        "and evaluate retrieval and citations before presenting this as regulation-grounded. Not legal advice.",
        icon="⚠️",
    )

with contact_tab:
    st.title("AI Solutions & Implementation")
    st.markdown(
        "I build AI and GenAI solutions that connect a real business use case to a practical application. "
        "I can work with your team to understand the workflow, shape the right technical approach, "
        "and build a proof of concept, MVP, or integration around what the business needs."
    )
    service_cols = st.columns(2)
    services = [
        "Generative AI application development",
        "Custom LLM and RAG solutions",
        "Agentic AI and AI workflow automation",
        "Intelligent document processing",
        "AI-powered business process automation",
        "Enterprise AI integration",
        "AI consulting, PoC and MVP development",
    ]
    for index, service in enumerate(services):
        with service_cols[index % 2]:
            st.markdown(f"- {service}")

    st.subheader("Have an AI idea or business challenge? Let's build a solution.")
    contact_col1, contact_col2 = st.columns(2)
    with contact_col1:
        st.link_button("Email Niraj", "mailto:singhn9282@gmail.com", use_container_width=True)
    with contact_col2:
        st.link_button("Connect on LinkedIn", "https://www.linkedin.com/in/niraj-s-8b9984152/", use_container_width=True)
    st.caption("Please do not send confidential customer, borrower, or regulated data through this public demo.")
