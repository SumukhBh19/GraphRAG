"""
Generates authentic sample SEBI and RBI regulatory circular PDFs for immediate ingestion,
testing, knowledge graph construction, and evaluation benchmarks.
"""
import os
from pathlib import Path
import fitz  # PyMuPDF

def create_circular_pdf(output_path: Path, title: str, circular_code: str, date: str, regulator: str, pages_text: list):
    doc = fitz.open()
    
    for page_idx, page_content in enumerate(pages_text):
        page = doc.new_page(width=595, height=842) # A4
        # Header
        reg_header = "SECURITIES AND EXCHANGE BOARD OF INDIA" if regulator == "SEBI" else "RESERVE BANK OF INDIA"
        page.insert_text((50, 50), reg_header, fontsize=12, fontname="helv", color=(0.1, 0.2, 0.5))
        page.insert_text((50, 68), f"Circular Ref: {circular_code}", fontsize=9, fontname="helv")
        page.insert_text((420, 68), f"Date: {date}", fontsize=9, fontname="helv")
        page.draw_line((50, 78), (545, 78), color=(0.7, 0.7, 0.7), width=1)
        
        # Title on first page
        y_offset = 100
        if page_idx == 0:
            page.insert_text((50, y_offset), title, fontsize=11, fontname="helv", color=(0, 0, 0))
            y_offset += 30

        # Body text paragraphs
        rect = fitz.Rect(50, y_offset, 545, 780)
        page.insert_textbox(rect, page_content, fontsize=9.5, fontname="helv", align=0)

        # Footer
        page.draw_line((50, 800), (545, 800), color=(0.8, 0.8, 0.8), width=0.5)
        page.insert_text((50, 815), f"{circular_code} - Regulatory Compliance Intelligence System", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))
        page.insert_text((500, 815), f"Page {page_idx + 1}", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    print(f"Generated: {output_path.name}")

def main():
    base_dir = Path(__file__).resolve().parent.parent
    raw_dir = base_dir / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 1. SEBI Multi Cap & Large Mid Cap Scheme Categorization
    create_circular_pdf(
        raw_dir / "SEBI_MF_2020_172.pdf",
        title="Circular on Asset Allocation of Multi Cap Funds under Scheme Categorization",
        circular_code="SEBI/HO/IMD/DF3/CIR/P/2020/172",
        date="September 11, 2020",
        regulator="SEBI",
        pages_text=[
            """1. All Mutual Funds / Asset Management Companies (AMCs) / Trustee Companies / Board of Trustees.

2. Vide SEBI circular SEBI/HO/IMD/DF3/CIR/P/2017/114 dated October 06, 2017, categories of mutual fund schemes were defined to standardize scheme characteristics and portfolio holdings.

3. In order to diversify the underlying portfolio of Multi Cap Funds and ensure true representation of the category, it has been decided to amend the portfolio allocation requirement for Multi Cap schemes as follows:
(a) Minimum investment in equity & equity related instruments shall be 75% of total assets.
(b) Minimum investment in equity & equity related instruments of large cap companies: 25% of total assets.
(c) Minimum investment in equity & equity related instruments of mid cap companies: 25% of total assets.
(d) Minimum investment in equity & equity related instruments of small cap companies: 25% of total assets.

4. All AMCs managing Multi Cap schemes shall ensure compliance with this requirement within one month from the date of publishing of next list of stocks by Association of Mutual Funds in India (AMFI).""",
            """5. Large & Mid Cap Funds: For the avoidance of doubt, the asset allocation for Large and Mid Cap Funds continues to be governed by SEBI circular dated October 06, 2017 requiring minimum investment of 35% in large cap companies and 35% in mid cap companies.

6. Net Worth Requirements: Asset Management Companies are reminded of Regulation 21(1)(f) of SEBI (Mutual Funds) Regulations, 1996 requiring a continuous net worth of not less than Rs 50 Crore. Failure to maintain mandatory net worth impairs eligibility to launch new mutual fund schemes.

7. Custody and Trustees: Trustees of the mutual fund and the Custodian appointed under Regulation 43 shall ensure that scheme securities are segregated and held strictly in accordance with these investment allocation norms.

8. This circular is issued in exercise of powers conferred under Section 11(1) of the Securities and Exchange Board of India Act, 1992 to protect the interests of investors in securities."""
        ]
    )

    # 2. SEBI Liquid Fund Risk Management & Exit Load
    create_circular_pdf(
        raw_dir / "SEBI_MF_2019_101.pdf",
        title="Risk Management Framework and Liquid Assets Requirement for Liquid and Debt Mutual Fund Schemes",
        circular_code="SEBI/HO/IMD/DF2/CIR/P/2019/101",
        date="September 20, 2019",
        regulator="SEBI",
        pages_text=[
            """1. To All Mutual Funds, Asset Management Companies (AMCs), and Association of Mutual Funds in India (AMFI).

2. In supersession of earlier circulars on cut-off timings and valuation, this circular institutes a strengthened liquidity framework for mutual funds following credit events.

3. Mandatory Holding of Liquid Assets:
All open-ended liquid schemes shall hold at least 20% of net assets in liquid assets. Liquid assets for this purpose shall include Cash, Government Securities, Treasury Bills and Repo on Government Securities. In case the exposure to liquid assets falls below 20%, the AMC shall ensure rebalancing within 2 business days.

4. Graded Exit Load in Liquid Funds:
Liquid schemes shall levy a graded exit load on investors who exit within 7 days of subscription:
- Day 1: 0.0070%
- Day 2: 0.0065%
- Day 3: 0.0060%
- Day 4: 0.0055%
- Day 5: 0.0050%
- Day 6: 0.0045%
- Day 7: 0.0000% (No exit load after 7 days).

5. Overnight Funds: Overnight funds shall continue to invest solely in debt securities with residual maturity of 1 business day and are prohibited from levying any exit load.""",
            """6. Cut-Off Timing for Subscription:
The cut-off timing for subscription applications in Liquid Funds and Overnight Funds is established at 1:30 PM for applicable day's NAV. For all other debt and equity mutual fund schemes, the uniform cut-off timing remains 3:00 PM.

7. Single Issuer Debt Investment Ceiling:
Under SEBI (Mutual Funds) Regulations 1996, a mutual fund scheme shall not invest more than 10% of its NAV in debt and money market securities rated AAA/AA issued by a single issuer. This ceiling may be extended to 12% of NAV with prior approval of the Board of Trustees and the Board of Directors of the Asset Management Company.

8. Trustees Oversight: The Board of Trustees of the mutual fund shall review the compliance of the liquidity buffer and report any deviations in the quarterly compliance report (QCR) submitted to SEBI."""
        ]
    )

    # 3. SEBI Segregated Portfolio (Side-Pocketing) Framework
    create_circular_pdf(
        raw_dir / "SEBI_MF_2018_160.pdf",
        title="Creation of Segregated Portfolio in Mutual Fund Schemes (Side-Pocketing)",
        circular_code="SEBI/HO/IMD/DF2/CIR/P/2018/160",
        date="December 28, 2018",
        regulator="SEBI",
        pages_text=[
            """1. Creation of segregated portfolio (side pocketing) may be permitted in mutual fund schemes subject to conditions stated herein.

2. Circumstances for Segregation:
A segregated portfolio may be created in a mutual fund scheme by an Asset Management Company (AMC) in the event of a credit event at issuer level:
(a) Downgrade of a debt or money market instrument to below investment grade (BBB- or lower by SEBI registered Credit Rating Agency).
(b) Subsequent downgrades from rated instruments to default status.

3. Mandatory Approval and Process:
Upon occurrence of credit event, AMC shall seek approval of the Board of Trustees within 2 working days. On approval, the distressed debt instrument shall be segregated into a separate portfolio, and units in the segregated portfolio shall be allotted to existing unitholders pro-rata.

4. Valuation: The segregated portfolio debt securities shall be valued based on AMFI-appointed valuation agencies (CRISIL and ICRA) haircut matrices, and no management fee shall be charged by the AMC on the segregated portfolio.""",
            """5. Total Expense Ratio (TER) of Segregated Portfolio:
AMCs shall not charge any management fees on the segregated portfolio. However, legal and recovery expenses incurred in pursuing resolution of the default security may be charged to the segregated portfolio subject to a cap of 0.10% per annum of the recovery value.

6. Listing and Liquidity:
To provide liquidity to unitholders holding units in the segregated portfolio, the AMC shall list the units of the segregated portfolio on a recognized stock exchange within 10 working days of its creation.

7. Disclosure to Regulators:
Details of the segregated portfolio shall be reported to SEBI immediately and published in the monthly portfolio disclosure on the AMC website."""
        ]
    )

    # 4. SEBI Alignment of Interest (Skin in the Game)
    create_circular_pdf(
        raw_dir / "SEBI_MF_2021_553.pdf",
        title="Alignment of Interest of Designated Employees of Asset Management Companies with the Unit Holders",
        circular_code="SEBI/HO/IMD/IMD-I/DOF5/P/CIR/2021/553",
        date="April 28, 2021",
        regulator="SEBI",
        pages_text=[
            """1. To protect investor interests and foster fiduciary responsibility, this circular establishes mandatory investment guidelines for Key Employees of AMCs.

2. Minimum Investment Requirement:
A minimum of 20% of the gross salary or perks of Designated Employees / Key Managerial Personnel (including Chief Executive Officer, Chief Investment Officer, and Fund Managers) shall be invested in units of the mutual fund schemes they manage or oversee.

3. Lock-in Period:
The mandatory scheme investment by Key Employees shall be locked in for a minimum period of 3 years or the tenure of the scheme, whichever is less.

4. Redemption Restrictions:
Designated employees cannot redeem units from the locked-in portfolio prior to the expiry of the lock-in period, except in circumstances of severe medical emergency or retirement with prior Trustee approval.

5. Risk-o-meter Alignment:
The allocation of compensation across schemes shall match the risk profile of the schemes under management as classified in the monthly Risk-o-meter disclosures."""
        ]
    )

    # 5. RBI Priority Sector Lending (PSL) Master Direction
    create_circular_pdf(
        raw_dir / "RBI_FIDD_2020_008.pdf",
        title="Master Direction - Priority Sector Lending (PSL) - Targets and Classification",
        circular_code="RBI/FIDD/2020-21/72 FIDD.CO.Plan.BC.5/04.09.01/2020-21",
        date="September 04, 2020",
        regulator="RBI",
        pages_text=[
            """1. Introduction and Applicability:
This Master Direction is issued by Reserve Bank of India under Section 21 and Section 35A of the Banking Regulation Act, 1949. It applies to all Scheduled Commercial Banks (SCBs) including Regional Rural Banks (RRBs) and Small Finance Banks (SFBs).

2. Overall Targets for Domestic Commercial Banks:
Total Priority Sector Lending target for Domestic Scheduled Commercial Banks and Foreign Banks with 20 branches and above shall be 40% of Adjusted Net Bank Credit (ANBC) or Credit Equivalent Amount of Off-Balance Sheet Exposure (CEOBE), whichever is higher.

3. Sub-targets for Domestic Commercial Banks:
(a) Agriculture: 18% of ANBC, with a prescribed sub-target of 10% for Small and Marginal Farmers.
(b) Micro Enterprises: 7.5% of ANBC.
(c) Advances to Weaker Sections: 12% of ANBC.

4. Foreign Banks with Less Than 20 Branches:
Foreign banks with less than 20 branches are also mandated to achieve overall PSL target of 40% of ANBC. However, they are exempt from specific sub-targets (Agriculture and Micro Enterprises) and can achieve the target across any eligible priority sector category.""",
            """5. Priority Sector Lending Certificates (PSLCs):
Banks having shortfall in achievement of PSL targets may purchase Priority Sector Lending Certificates (PSLCs) through RBI's core banking solution (e-Kuber) platform to meet quarterly and annual targets without transfer of underlying credit risk.

6. Penalty for Non-Achievement:
Banks having continuous shortfall in PSL targets shall be required to contribute to the Rural Infrastructure Development Fund (RIDF) established with NABARD or other designated funds as determined by the Reserve Bank of India from time to time."""
        ]
    )

    # 6. RBI Master Direction on External Commercial Borrowings (ECB)
    create_circular_pdf(
        raw_dir / "RBI_FED_2019_001.pdf",
        title="Master Direction - External Commercial Borrowings, Trade Credits and Structured Obligations",
        circular_code="RBI/FED/2018-19/67 FED Master Direction No.5/2018-19",
        date="March 26, 2019",
        regulator="RBI",
        pages_text=[
            """1. General Framework:
Borrowings from non-resident entities by eligible Indian entities are governed by Foreign Exchange Management (Borrowing and Lending in Foreign Exchange) Regulations under FEMA 1999.

2. Routes of ECB:
(a) Automatic Route: For borrowings up to USD 750 million or equivalent per financial year. Requires no prior RBI approval; registration through Authorized Dealer (AD Category-I) bank and Loan Registration Number (LRN) from RBI is mandatory.
(b) Approval Route: For cases exceeding USD 750 million or outside parameters of automatic route, requiring prior Empowered Committee and RBI approval.

3. Minimum Average Maturity Period (MAMP):
The MAMP for ECB shall be 3 years for all general corporate purposes. For ECBs raised by manufacturing companies up to USD 50 million, MAMP may be 1 year.

4. Mandatory Hedging Requirements:
Entities raising foreign currency denominated ECBs with an average maturity of less than 5 years must maintain a minimum 70% financial currency hedge for the entire exposure (principal and coupon).""",
            """5. Negative List / End-Use Restrictions:
ECB proceeds cannot be utilized for the following prohibited activities:
(a) Real estate activities or purchase of agricultural land.
(b) Investment in capital market or equity shares.
(c) Working capital and general corporate purposes (except from foreign equity holders with MAMP of 5 years).
(d) On-lending to entities for the above prohibited activities.

6. Reporting and Allotment:
Borrowers shall submit monthly Form ECB-2 returns through AD Category-I banks within 7 working days from the close of the reference month."""
        ]
    )

    print("All sample regulatory PDF circulars generated successfully in data/raw/")

if __name__ == "__main__":
    main()
