"""Generate a synthetic KFS PDF for testing the portfolio demo only."""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


OUTPUT_PATH = Path("sample_documents/synthetic_kfs_for_demo.pdf")


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Synthetic KFS Sample for Demo Testing",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("SYNTHETIC SAMPLE — NOT A REAL FINANCIAL DOCUMENT", styles["Title"]),
        Spacer(1, 5 * mm),
        Paragraph(
            "This fictional Key Fact Statement is provided only to test a portfolio demonstration. "
            "It contains no real borrower data and must not be used for lending, legal, or compliance decisions.",
            styles["BodyText"],
        ),
        Spacer(1, 6 * mm),
        Paragraph("Illustrative Digital Personal Loan", styles["Heading1"]),
        Paragraph("Lender: Example Finance Ltd. (fictional)", styles["BodyText"]),
        Paragraph("Borrower: Demo Borrower (fictional)", styles["BodyText"]),
        Paragraph("Principal amount: INR 50,000", styles["BodyText"]),
        Paragraph("Tenure: 12 months", styles["BodyText"]),
        Paragraph("Repayment: 12 monthly instalments", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Illustrative Charges and Terms", styles["Heading2"]),
        Paragraph("Annual Percentage Rate (APR): 18% per annum.", styles["BodyText"]),
        Paragraph("Processing fee: INR 1,000, payable at disbursal.", styles["BodyText"]),
        Paragraph("Late payment charge: 2% interest on overdue amounts, compounded monthly.", styles["BodyText"]),
        Paragraph("Cooling-off / look-up period: Not stated in this sample.", styles["BodyText"]),
        Paragraph("Nodal grievance officer: Contact details not stated in this sample.", styles["BodyText"]),
        Spacer(1, 6 * mm),
        Paragraph(
            "Expected demo behavior: the tool may flag the treatment of the processing fee in APR, "
            "compounded late charges, and missing cooling-off and grievance details. The result depends "
            "on configured reference passages and is not an authoritative assessment.",
            styles["BodyText"],
        ),
    ]
    document.build(story)
    print(f"Created synthetic test PDF: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()