# Knowledge Graph Schema for SEBI & RBI Regulatory Intelligence

This schema defines the formal ontology used for entity and relation extraction from SEBI circulars and RBI Master Directions. Every extraction prompt in the system directly references this schema.

---

## 1. Node Types (Entities)

| Node Label | Category | Description | Examples | Properties |
| :--- | :--- | :--- | :--- | :--- |
| **`Regulation`** | Legal Act / Master Direction | High-level regulatory statutory framework, Master Direction, or Act | *SEBI (Mutual Funds) Regulations 1996*, *Foreign Exchange Management Act 1999*, *RBI Master Direction - Lending to Priority Sector* | `id`, `name`, `year`, `regulator` |
| **`Circular`** | Operational Guideline | Specific circular, notification, or amendment issued by the regulator | *SEBI/HO/IMD/DF2/CIR/P/2021/024*, *RBI/2023-24/105 DOR.STR.REC.58/21.04.048/2023-24* | `id`, `code`, `title`, `date`, `regulator`, `source_file` |
| **`Entity`** | Institution / Market Participant | Regulated entities, regulatory authorities, financial institutions, intermediaries | *Reserve Bank of India (RBI)*, *SEBI*, *Asset Management Companies (AMCs)*, *HDFC AMC*, *Scheduled Commercial Banks (SCBs)*, *Custodian*, *Depository* | `id`, `name`, `entity_type` (Regulator, Bank, AMC, Intermediary, Corporate) |
| **`Instrument`** | Financial Asset / Product | Regulated investment products, credit facilities, or securities | *Debt Mutual Fund Scheme*, *Alternative Investment Fund (AIF)*, *External Commercial Borrowings (ECB)*, *Green Bonds*, *Credit Default Swaps* | `id`, `name`, `asset_class` |
| **`Section`** | Statutory Sub-division | Subsections, paragraphs, clauses, or schedules of a regulation/circular | *Clause 3.2*, *Chapter IV*, *Section 45ZA*, *Schedule II* | `id`, `name`, `parent_doc` |
| **`Obligation`** | Compliance Requirement | Mandatory compliance duty, ceiling, floor, restriction, or reporting requirement | *Net Worth minimum requirement of Rs 50 Crore*, *Mandatory 2-factor authentication for redemptions*, *15-day reporting to SEBI*, *Risk-o-meter monthly disclosure* | `id`, `description`, `compliance_type` (disclosure, capital_adequacy, operational, penalty) |
| **`Date`** | Temporal Marker | Effective dates, enforcement deadlines, reporting cutoff dates | *2023-04-01*, *October 1, 2024*, *within 30 days* | `id`, `date_string`, `iso_date` |

---

## 2. Edge Types (Relationships)

| Edge Type | Source Node -> Target Node | Description | Inverse Relation |
| :--- | :--- | :--- | :--- |
| **`SUPERSEDES`** | `Circular` -> `Circular` | The source circular fully replaces or voids an earlier circular | *SUPERSEDED_BY* |
| **`AMENDS`** | `Circular` -> `Regulation` or `Circular` | Modifies, inserts, or deletes specific clauses in a parent regulation or previous circular | *AMENDED_BY* |
| **`REFERS_TO`** | `Circular` / `Section` -> `Circular` / `Regulation` / `Section` | Cross-references a related circular, statute, or external guideline | *REFERRED_BY* |
| **`APPLIES_TO`** | `Circular` / `Regulation` / `Obligation` -> `Entity` / `Instrument` | Defines the scope of applicability for specific participants or instruments | *GOVERNED_BY* |
| **`ISSUED_BY`** | `Circular` / `Regulation` -> `Entity` | The regulatory authority that issued the policy | *ISSUES* |
| **`GOVERNS`** | `Regulation` / `Circular` -> `Instrument` / `Entity` | Formal oversight or regulatory jurisdiction over a market asset class or institution | *IS_GOVERNED_BY* |
| **`EFFECTIVE_FROM`**| `Circular` / `Regulation` / `Obligation` -> `Date` | The enforcement or commencement date of the regulatory action | *APPLIES_ON* |
| **`MANDATES`** | `Circular` / `Section` -> `Obligation` | Creates a binding duty, threshold, or reporting mandate | *MANDATED_BY* |

---

## 3. Node Normalization Rules

To prevent knowledge graph fragmentation:
1. **Case & Punctuation**: Node IDs are normalized using lowercase, stripped punctuation, and single spaces (e.g., `"S.E.B.I."` -> `"sebi"`, `"Asset Management Company"` -> `"asset management company"`).
2. **Canonical Aliases**:
   - `RBI`, `Reserve Bank of India`, `Reserve Bank` -> `reserve bank of india`
   - `SEBI`, `Securities and Exchange Board of India` -> `securities and exchange board of india`
   - `AMC`, `Asset Management Companies`, `Asset Management Company` -> `asset management company`
   - `SCB`, `Scheduled Commercial Banks` -> `scheduled commercial bank`
3. **Circular Codes**: Preserved in standardized uppercase for canonical matching (e.g., `SEBI/HO/IMD/DF2/CIR/P/2021/024`).

---

## 4. LLM Extraction JSON Schema

When the extraction pipeline processes a document chunk, the LLM must strictly output:

```json
{
  "entities": [
    {
      "id": "normalized_unique_id",
      "name": "Exact Surface Text",
      "type": "Regulation | Circular | Entity | Instrument | Section | Obligation | Date",
      "properties": {
        "description": "Optional brief context",
        "category": "Optional sub-category"
      }
    }
  ],
  "relationships": [
    {
      "source": "normalized_unique_id_of_source",
      "target": "normalized_unique_id_of_target",
      "type": "SUPERSEDES | AMENDS | REFERS_TO | APPLIES_TO | ISSUED_BY | GOVERNS | EFFECTIVE_FROM | MANDATES",
      "description": "Brief explanation of the relationship extracted from text",
      "confidence": 0.95
    }
  ]
}
```
