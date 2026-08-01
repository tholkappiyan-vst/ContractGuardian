"""Orchestrates the full analysis pipeline: extract → analyze → store."""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.contract import Contract, Document
from app.models.analysis import Clause, Entity, RiskScore, Analysis, NegotiationSuggestion
from app.services import document as doc_service, ai as ai_service, storage as storage_service
from app.core.exceptions import NotFoundError, AnalysisError


async def run_analysis(contract_id: str, db: AsyncSession) -> Analysis:
    """Full pipeline: extract text from documents, run AI analysis, store results."""
    contract = await db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError("Contract")

    # Update status
    contract.status = "extracting"
    await db.flush()

    # Step 1: Extract text from all documents
    result = await db.execute(select(Document).where(Document.contract_id == contract_id))
    documents = result.scalars().all()

    full_text_parts = []
    total_pages = 0

    for doc in documents:
        if doc.raw_text:
            full_text_parts.append(doc.raw_text)
            total_pages += doc.page_count or 0
            continue

        content = await storage_service.download_file(doc.storage_key)
        extraction = await doc_service.extract_text(content, doc.file_type)

        doc.raw_text = extraction["text"]
        doc.ocr_used = extraction["ocr_used"]
        doc.ocr_confidence = extraction["ocr_confidence"]
        doc.page_count = extraction["page_count"]

        full_text_parts.append(extraction["text"])
        total_pages += extraction["page_count"] or 0

    full_text = "\n\n---\n\n".join(full_text_parts)
    contract.status = "extracted"
    contract.page_count = total_pages
    contract.word_count = len(full_text.split())
    await db.flush()

    # Step 2: Run AI analysis
    contract.status = "analyzing"
    await db.flush()

    try:
        ai_result = await ai_service.analyze_contract(full_text)
    except Exception as e:
        contract.status = "failed"
        contract.error_message = str(e)[:500]
        await db.flush()
        raise AnalysisError(f"AI analysis failed: {e}")

    # Step 3: Store results
    meta = ai_result.get("_meta", {})

    analysis = Analysis(
        contract_id=contract_id,
        status="completed",
        executive_summary=ai_result.get("executive_summary"),
        contract_type=ai_result.get("contract_type"),
        parties=ai_result.get("parties"),
        dates=ai_result.get("dates"),
        payment_summary=ai_result.get("payment_summary"),
        obligations=ai_result.get("obligations"),
        risk_score=ai_result.get("overall_risk", {}).get("score"),
        risk_label=ai_result.get("overall_risk", {}).get("label"),
        risk_summary=ai_result.get("overall_risk", {}).get("summary"),
        top_risks=ai_result.get("top_risks"),
        action_items=ai_result.get("action_items"),
        model_used=meta.get("model_used"),
        tokens_input=meta.get("tokens_input"),
        tokens_output=meta.get("tokens_output"),
        processing_ms=meta.get("processing_ms"),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(analysis)

    # Store clauses
    clause_id_map = {}  # index → clause.id
    for c in ai_result.get("clauses", []):
        clause = Clause(
            contract_id=contract_id,
            clause_index=c["index"],
            section_number=c.get("section_number"),
            title=c.get("title"),
            body=c["body"],
            category=c["category"],
            subcategory=c.get("subcategory"),
            confidence=c.get("confidence", 0.0),
            risk_score=c.get("risk_score"),
            is_standard=c.get("is_standard"),
        )
        db.add(clause)
        await db.flush()
        clause_id_map[c["index"]] = clause.id

    # Store entities
    for e in ai_result.get("entities", []):
        entity = Entity(
            contract_id=contract_id,
            clause_id=clause_id_map.get(e.get("clause_index")),
            entity_type=e["entity_type"],
            value=e["value"],
            original_text=e["original_text"],
            normalized=e.get("normalized"),
            confidence=e.get("confidence", 0.0),
            role=e.get("role"),
        )
        db.add(entity)

    # Store risk scores
    for r in ai_result.get("risks", []):
        risk = RiskScore(
            contract_id=contract_id,
            clause_id=clause_id_map.get(r.get("clause_index")),
            scope=r.get("scope", "clause"),
            score=r["score"],
            label=r["label"],
            category=r["category"],
            explanation=r["explanation"],
            consequence=r["consequence"],
            affected_party=r.get("affected_party"),
            is_standard=r.get("is_standard"),
            standard_note=r.get("standard_note"),
        )
        db.add(risk)

    # Store overall contract risk
    overall = ai_result.get("overall_risk", {})
    if overall.get("score"):
        contract_risk = RiskScore(
            contract_id=contract_id,
            clause_id=None,
            scope="contract",
            score=overall["score"],
            label=overall.get("label", ""),
            category="overall",
            explanation=overall.get("summary", ""),
            consequence=overall.get("summary", ""),
        )
        db.add(contract_risk)

    # Store negotiation suggestions
    for n in ai_result.get("negotiations", []):
        neg = NegotiationSuggestion(
            contract_id=contract_id,
            clause_id=clause_id_map.get(n.get("clause_index"), list(clause_id_map.values())[0] if clause_id_map else None),
            difficulty=n["difficulty"],
            label=n["label"],
            original_text=n["original_text"],
            alternative_text=n["alternative_text"],
            explanation=n["explanation"],
            talking_points=n.get("talking_points"),
            likelihood=n.get("likelihood"),
            sort_order=n.get("clause_index", 0),
        )
        db.add(neg)

    # Update contract
    contract.status = "analyzed"
    contract.analyzed_at = datetime.now(timezone.utc)
    contract.risk_score = overall.get("score")
    contract.contract_type = ai_result.get("contract_type", {}).get("type") if isinstance(ai_result.get("contract_type"), dict) else ai_result.get("contract_type")

    await db.flush()
    return analysis
