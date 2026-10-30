"""
Generates a sample RBI Digital Lending Guidelines PDF for demo/testing.
Run once: python create_sample_rbi_pdf.py
The output PDF is placed in ./rbi_documents/ for ingestion by ingest_rbi.py.
"""

import os
import struct

RBI_CONTENT = """\
RESERVE BANK OF INDIA
Digital Lending Guidelines 2022
RBI/2022-23/111 DOR.CRE.REC.66/21.07.001/2022-23
Issued: September 2, 2022

GUIDELINES ON DIGITAL LENDING

These guidelines apply to all Regulated Entities (REs) including Non-Banking Financial
Companies (NBFCs) and their Lending Service Providers (LSPs) engaged in digital lending.

=============================================================================
SECTION A: KEY FACT STATEMENT (KFS) REQUIREMENTS
=============================================================================

Clause 2.1 - Key Fact Statement Mandatory Disclosure
All digital loans must be accompanied by a Key Fact Statement (KFS) that discloses
all material terms of the loan in a standardised format prescribed by RBI.
The KFS must be provided to the borrower prior to execution of the loan agreement.
No digital loan shall be disbursed without receipt of signed KFS from the borrower.

Clause 2.2 - Annual Percentage Rate (APR)
The Annual Percentage Rate (APR) must be explicitly and prominently stated in the KFS.
The APR must be inclusive of ALL upfront charges, processing fees, insurance premiums,
documentation charges, verification fees and any other fee levied on the borrower.
The APR shall be expressed as an annualised rate so borrowers can compare loan products.
Non-disclosure of APR, partial disclosure, or disclosure that excludes any fee or charge
constitutes a direct violation of these guidelines (Page 4, Clause 2.2).
Regulated Entities must ensure the APR calculation methodology is transparent.

Clause 2.3 - Penal Charges
Penal charges for default or delayed repayment must be disclosed in the KFS as a FLAT FEE.
Penal charges shall NOT be in the nature of penal interest that compounds over time.
Compounding of penal charges on the outstanding principal or interest is strictly prohibited.
The quantum of penal charges must be reasonable, proportionate and disclosed upfront.
Any NBFC levying compounded penal interest instead of a flat penal charge shall be in
violation of these Digital Lending Guidelines (Page 5, Clause 2.3).
Penal charges must be expressed as a specific rupee amount (e.g., Rs. 500 per month of
delay) and NOT as a percentage that accrues or compounds on the outstanding amount.

Clause 2.4 - Cooling-Off Period / Look-Up Period
Every digital loan product must provide a cooling-off period (also called look-up period).
The minimum cooling-off period for digital loans is THREE (3) days for loan tenors above
seven days and ONE (1) day for loan tenors equal to or below seven days.
During the cooling-off period, the borrower may exit the loan by repaying only the
principal and proportionate APR without being subject to any prepayment penalty.
The Key Fact Statement must explicitly state the cooling-off period in number of days.
Failure to provide the minimum prescribed cooling-off period, or failure to mention it in
the KFS, constitutes a violation of RBI Digital Lending Guidelines (Page 5, Clause 2.4).
LSPs and NBFCs must honour exit requests made within the cooling-off window.

Clause 2.5 - Grievance Redressal Officer
The Key Fact Statement must explicitly state the name and complete contact details of
the Nodal Grievance Redressal Officer designated by the NBFC.
Contact details must include: full name, email address, phone number, and postal address.
The Nodal Grievance Officer must be accessible to borrowers for all complaints related
to the digital loan, loan agreement, KFS, or conduct of the Lending Service Provider.
Absence of Grievance Officer contact information in the KFS is a direct violation of
RBI Digital Lending Guidelines and Fair Practices Code (Page 6, Clause 2.5).
Borrowers must be able to escalate unresolved complaints to the RBI Ombudsman.

=============================================================================
SECTION B: FAIR PRACTICES CODE FOR NBFCs
=============================================================================

Clause 3.1 - Transparency in Loan Terms
NBFCs must ensure full transparency in all loan terms communicated to borrowers.
All fees and charges must be disclosed in the sanction letter and KFS before loan disbursal.
No fee shall be collected without prior disclosure and consent of the borrower.
Hidden charges are a violation of the Fair Practices Code and these Digital Lending Guidelines.

Clause 3.2 - Recovery Practices
Recovery agents must follow RBI guidelines on fair debt collection practices.
Harassment of borrowers or their family members is strictly prohibited.
Digital lending apps must not access borrower contacts, photos, or media beyond
what is necessary for KYC and credit underwriting purposes.

Clause 3.3 - Data Privacy and Consent
All data collected from borrowers must be with explicit informed consent.
Data must be stored within India as per applicable data localisation requirements.
Borrowers have the right to access, correct and delete their personal data.
NBFCs and LSPs must comply with the Digital Personal Data Protection Act 2023.

=============================================================================
SECTION C: PENALTIES FOR NON-COMPLIANCE
=============================================================================

Clause 4.1 - Regulatory Action
RBI may impose monetary penalties on NBFCs that fail to comply with these guidelines.
Penalties for non-compliance with KFS requirements may range from Rs. 1 lakh to Rs. 1 crore
depending on the severity and frequency of violations.
Repeated violations may result in suspension of the Certificate of Registration.
RBI reserves the right to direct NBFCs to refund fees collected in violation of these norms.

Clause 4.2 - Implementation Timeline
All NBFCs and their LSPs must implement these Digital Lending Guidelines with immediate effect
from September 2, 2022.
NBFCs that commenced digital lending prior to this date must achieve compliance within 90 days.
RBI supervisory officers will verify KFS compliance during annual inspections.

=============================================================================
END OF RBI DIGITAL LENDING GUIDELINES SUMMARY
Reserve Bank of India | www.rbi.org.in
=============================================================================
"""


def _escape_pdf_string(text: str) -> bytes:
    """Encode a text string for use in a PDF content stream."""
    out = []
    for ch in text:
        code = ord(ch)
        if code < 32 or code > 126:
            out.append(ord(' '))
        elif ch in ('\\', '(', ')'):
            out.append(ord('\\'))
            out.append(code)
        else:
            out.append(code)
    return bytes(out)


def create_rbi_pdf(output_path: str) -> None:
    """Write a multi-page PDF containing the RBI guidelines text."""
    lines = RBI_CONTENT.split('\n')
    lines_per_page = 55
    pages_text = [
        lines[i:i + lines_per_page]
        for i in range(0, len(lines), lines_per_page)
    ]

    # Build content streams for each page
    page_streams = []
    for page_lines in pages_text:
        parts = [b"BT\n/F1 9 Tf\n40 800 Td\n11 TL\n"]
        for line in page_lines:
            escaped = _escape_pdf_string(line)
            parts.append(b"(" + escaped + b") Tj\nT*\n")
        parts.append(b"ET\n")
        page_streams.append(b"".join(parts))

    # ---- Build PDF objects ----
    objects = {}  # obj_num -> bytes

    obj = 1
    # Catalog
    objects[obj] = b"<< /Type /Catalog /Pages 2 0 R >>"
    obj += 1  # obj=2

    # Will fill Pages after we know page object numbers
    pages_obj = obj
    obj += 1  # obj=3

    # Font
    font_obj = obj
    objects[obj] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>"
    obj += 1

    page_obj_nums = []
    for stream in page_streams:
        # Content stream
        content_obj = obj
        objects[obj] = f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        obj += 1
        # Page
        page_obj_nums.append(obj)
        objects[obj] = (
            f"<< /Type /Page /Parent {pages_obj} 0 R "
            f"/MediaBox [0 0 612 792] "
            f"/Contents {content_obj} 0 R "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> >>"
        ).encode()
        obj += 1

    kids = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objects[pages_obj] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_nums)} >>".encode()

    # ---- Serialise PDF ----
    buf = bytearray(b"%PDF-1.4\n")
    offsets = {}
    max_obj = max(objects.keys())

    for n in range(1, max_obj + 1):
        offsets[n] = len(buf)
        body = objects[n]
        buf += f"{n} 0 obj\n".encode()
        buf += body
        buf += b"\nendobj\n"

    xref_pos = len(buf)
    buf += b"xref\n"
    buf += f"0 {max_obj + 1}\n".encode()
    buf += b"0000000000 65535 f \n"
    for n in range(1, max_obj + 1):
        buf += f"{offsets[n]:010d} 00000 n \n".encode()

    buf += b"trailer\n"
    buf += f"<< /Size {max_obj + 1} /Root 1 0 R >>\n".encode()
    buf += b"startxref\n"
    buf += f"{xref_pos}\n".encode()
    buf += b"%%EOF\n"

    with open(output_path, "wb") as f:
        f.write(buf)


if __name__ == "__main__":
    os.makedirs("rbi_documents", exist_ok=True)
    out = os.path.join("rbi_documents", "RBI_Digital_Lending_Guidelines_2022_Sample.pdf")
    create_rbi_pdf(out)
    print(f"Created: {os.path.abspath(out)}")
    print("You can now run: python ingest_rbi.py")
