import json
import re
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
import httpx
from groq import Groq
import spacy
from backend.config import settings

# ----------------- Pydantic Models -----------------

class ExtractedEntity(BaseModel):
    id: str = Field(description="Normalized unique identifier (e.g. sebi, reserve_bank_of_india)")
    name: str = Field(description="Exact entity name as mentioned in text")
    type: str = Field(description="Regulation | Circular | Entity | Instrument | Date | Section | Obligation")
    properties: Dict[str, Any] = Field(default_factory=dict)

class ExtractedRelationship(BaseModel):
    source: str = Field(description="Source entity ID")
    target: str = Field(description="Target entity ID")
    type: str = Field(description="SUPERSEDES | AMENDS | REFERS_TO | APPLIES_TO | ISSUED_BY | GOVERNS | EFFECTIVE_FROM | MANDATES")
    description: Optional[str] = Field(default="", description="Contextual summary of relationship")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)

class ExtractionResult(BaseModel):
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)

# ----------------- Entity Extractor Class -----------------

class EntityExtractor:
    """
    Extracts structured knowledge graph entities and relations from regulatory chunks
    using spaCy NER and LLM structured prompt extraction.
    """

    def __init__(self):
        self._nlp = None
        self._groq_client = None

    @property
    def nlp(self):
        if self._nlp is None:
            try:
                self._nlp = spacy.load("en_core_web_sm")
            except Exception:
                try:
                    # Try downloading or loading blank model
                    import subprocess
                    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=False)
                    self._nlp = spacy.load("en_core_web_sm")
                except Exception:
                    self._nlp = spacy.blank("en")
        return self._nlp

    @property
    def groq_client(self):
        if self._groq_client is None and settings.groq_api_key:
            try:
                self._groq_client = Groq(api_key=settings.groq_api_key)
            except Exception:
                self._groq_client = None
        return self._groq_client

    @staticmethod
    def normalize_id(text: str) -> str:
        """Normalizes entity names to unique graph node IDs."""
        norm = text.lower().strip()
        # Aliases
        if norm in ["sebi", "securities and exchange board of india", "s.e.b.i."]:
            return "sebi"
        if norm in ["rbi", "reserve bank of india", "r.b.i."]:
            return "reserve_bank_of_india"
        if norm in ["amc", "amcs", "asset management companies", "asset management company"]:
            return "asset_management_company"
        if norm in ["scb", "scbs", "scheduled commercial banks", "scheduled commercial bank"]:
            return "scheduled_commercial_bank"

        # General normalization: strip punctuation, replace spaces with underscores
        norm = re.sub(r"[^\w\s-]", "", norm)
        norm = re.sub(r"[\s-]+", "_", norm).strip("_")
        return norm or "unknown_entity"

    def extract_spacy_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extracts named entities using spaCy NER as pre-filtering signals."""
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            if ent.label_ in ["ORG", "DATE", "GPE", "MONEY", "LAW"]:
                type_mapping = {
                    "ORG": "Entity",
                    "DATE": "Date",
                    "GPE": "Entity",
                    "MONEY": "Obligation",
                    "LAW": "Regulation"
                }
                entities.append({
                    "name": ent.text.strip(),
                    "type": type_mapping.get(ent.label_, "Entity"),
                    "label": ent.label_
                })
        return entities

    def extract_from_chunk(self, chunk: Dict[str, Any]) -> ExtractionResult:
        """
        Extracts entities and relationships from a single chunk.
        Uses LLM if available, with deterministic fallback parser.
        """
        chunk_text = chunk["text"]
        circular_code = chunk.get("circular_code", "CIRCULAR")
        regulator = chunk.get("regulator", "REGULATOR")

        # First run spaCy to gather local entity spans
        spacy_ents = self.extract_spacy_entities(chunk_text)
        spacy_hints = ", ".join([f"{e['name']} ({e['type']})" for e in spacy_ents[:8]])

        # If LLM is configured and reachable
        if settings.llm_backend == "groq" and self.groq_client:
            try:
                return self._call_groq_extraction(chunk_text, circular_code, regulator, spacy_hints)
            except Exception as e:
                print(f"Groq extraction failed, falling back to rule-based: {e}")

        if settings.llm_backend == "ollama":
            try:
                return self._call_ollama_extraction(chunk_text, circular_code, regulator, spacy_hints)
            except Exception as e:
                print(f"Ollama extraction failed, falling back to rule-based: {e}")

        # Fallback heuristic extractor
        return self._heuristic_extraction(chunk, spacy_ents)

    def _build_prompt(self, chunk_text: str, circular_code: str, regulator: str, spacy_hints: str) -> str:
        return f"""You are an expert regulatory knowledge graph extractor analyzing Indian financial regulations (SEBI & RBI).

Given the following text from circular '{circular_code}' issued by '{regulator}', extract all entities and relationships strictly conforming to the schema.

Schema Node Types:
- Regulation (e.g. SEBI Mutual Funds Regulations 1996, FEMA)
- Circular (e.g. {circular_code})
- Entity (financial institutions, banks, AMCs, SEBI, RBI)
- Instrument (mutual funds, debt schemes, AIFs, equity, green bonds)
- Date (effective dates, compliance deadlines)
- Section (paragraphs, clauses, circular reference numbers)
- Obligation (compliance requirements, net worth thresholds, disclosures)

Schema Relationship Types:
SUPERSEDES, AMENDS, REFERS_TO, APPLIES_TO, ISSUED_BY, GOVERNS, EFFECTIVE_FROM, MANDATES

Identified candidate entities from text: {spacy_hints}

Text to extract:
\"\"\"{chunk_text}\"\"\"

Output MUST be valid JSON with this exact schema, without markdown fences or additional commentary:
{{
  "entities": [
    {{"id": "normalized_id", "name": "Exact Name", "type": "Node Type", "properties": {{"description": "context"}}}}
  ],
  "relationships": [
    {{"source": "source_id", "target": "target_id", "type": "Relationship Type", "description": "context", "confidence": 0.95}}
  ]
}}"""

    def _call_groq_extraction(self, text: str, code: str, regulator: str, hints: str) -> ExtractionResult:
        prompt = self._build_prompt(text, code, regulator, hints)
        response = self.groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": "You are a precise regulatory graph extraction assistant. Output strict JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return self._clean_and_validate(data)

    def _call_ollama_extraction(self, text: str, code: str, regulator: str, hints: str) -> ExtractionResult:
        prompt = self._build_prompt(text, code, regulator, hints)
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False
                }
            )
            resp.raise_for_status()
            res_json = resp.json()
            data = json.loads(res_json["response"])
            return self._clean_and_validate(data)

    def _clean_and_validate(self, data: Dict[str, Any]) -> ExtractionResult:
        """Normalizes IDs and validates using Pydantic."""
        cleaned_entities = []
        for ent in data.get("entities", []):
            norm_id = self.normalize_id(ent.get("id") or ent.get("name", ""))
            cleaned_entities.append(ExtractedEntity(
                id=norm_id,
                name=ent.get("name", norm_id),
                type=ent.get("type", "Entity"),
                properties=ent.get("properties", {})
            ))

        cleaned_rels = []
        for rel in data.get("relationships", []):
            s_id = self.normalize_id(rel.get("source", ""))
            t_id = self.normalize_id(rel.get("target", ""))
            if s_id and t_id and s_id != t_id:
                cleaned_rels.append(ExtractedRelationship(
                    source=s_id,
                    target=t_id,
                    type=rel.get("type", "REFERS_TO").upper(),
                    description=rel.get("description", ""),
                    confidence=float(rel.get("confidence", 0.9))
                ))

        return ExtractionResult(entities=cleaned_entities, relationships=cleaned_rels)

    def _heuristic_extraction(self, chunk: Dict[str, Any], spacy_ents: List[Dict[str, Any]]) -> ExtractionResult:
        """
        High-precision regex and linguistic heuristics fallback for regulatory circulars.
        Guarantees structured extraction even when offline without an active LLM API key.
        """
        entities: List[ExtractedEntity] = []
        relationships: List[ExtractedRelationship] = []
        seen_ids = set()

        # 1. Circular node itself
        circ_id = self.normalize_id(chunk.get("circular_code", chunk["document_name"]))
        circ_name = chunk.get("circular_code", chunk["document_name"])
        entities.append(ExtractedEntity(
            id=circ_id,
            name=circ_name,
            type="Circular",
            properties={"date": chunk.get("circular_date", "Unknown"), "regulator": chunk.get("regulator", "SEBI")}
        ))
        seen_ids.add(circ_id)

        # 2. Regulator node
        regulator_name = chunk.get("regulator", "SEBI")
        reg_id = "sebi" if regulator_name == "SEBI" else "reserve_bank_of_india"
        entities.append(ExtractedEntity(
            id=reg_id,
            name=f"Securities and Exchange Board of India" if reg_id == "sebi" else "Reserve Bank of India",
            type="Entity",
            properties={"category": "Regulator"}
        ))
        seen_ids.add(reg_id)

        relationships.append(ExtractedRelationship(
            source=circ_id,
            target=reg_id,
            type="ISSUED_BY",
            description=f"Circular issued by {regulator_name}",
            confidence=1.0
        ))

        # 3. Process spaCy entities
        text = chunk["text"]
        for ent in spacy_ents:
            norm_id = self.normalize_id(ent["name"])
            if norm_id and norm_id not in seen_ids and len(ent["name"]) > 2:
                entities.append(ExtractedEntity(
                    id=norm_id,
                    name=ent["name"],
                    type=ent["type"],
                    properties={}
                ))
                seen_ids.add(norm_id)
                # Link to circular
                rel_type = "APPLIES_TO" if ent["type"] == "Entity" else ("EFFECTIVE_FROM" if ent["type"] == "Date" else "REFERS_TO")
                relationships.append(ExtractedRelationship(
                    source=circ_id,
                    target=norm_id,
                    type=rel_type,
                    description=f"Referenced in section",
                    confidence=0.85
                ))

        # 4. Pattern check for Circular references & Acts (AMENDS / SUPERSEDES / REFERS_TO)
        act_matches = re.findall(r"([A-Z][a-zA-Z\s]+(?:Act|Regulations),\s*\d{4})", text)
        for act in set(act_matches):
            act_id = self.normalize_id(act)
            if act_id not in seen_ids:
                entities.append(ExtractedEntity(
                    id=act_id,
                    name=act.strip(),
                    type="Regulation"
                ))
                seen_ids.add(act_id)
                relationships.append(ExtractedRelationship(
                    source=circ_id,
                    target=act_id,
                    type="GOVERNS",
                    description="Statutory reference",
                    confidence=0.9
                ))

        # 5. Pattern check for circular superseding/amendment
        if re.search(r"supersed(?:es|ed)|in supersession of", text, re.I):
            superseded = re.findall(r"circular\s+no\.?\s*([A-Z0-9_/]+)", text, re.I)
            for old_c in superseded:
                old_id = self.normalize_id(old_c)
                if old_id not in seen_ids:
                    entities.append(ExtractedEntity(id=old_id, name=old_c, type="Circular"))
                    seen_ids.add(old_id)
                relationships.append(ExtractedRelationship(
                    source=circ_id,
                    target=old_id,
                    type="SUPERSEDES",
                    description="Circular supersedes previous guidelines",
                    confidence=0.95
                ))

        return ExtractionResult(entities=entities, relationships=relationships)
