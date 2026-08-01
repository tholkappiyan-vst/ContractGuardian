"""API routes that use the LangChain/Gemini AI engine instead of direct Anthropic calls."""
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.models.user import User
from app.models.contract import Contract, Document
from app.models.chat import ChatMessage
from app.ai_engine import ContractAIEngine

router = APIRouter()


def _get_engine() -> ContractAIEngine:
    return ContractAIEngine()


@router.post("/{contract_id}/analyze-full")
async def full_analysis(
    contract_id: str,
    user_role: str = "the person signing",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the full AI engine pipeline on a contract."""
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()

    # Get document content
    result = await db.execute(select(Document).where(Document.contract_id == contract_id).limit(1))
    document = result.scalar_one_or_none()
    if not document:
        raise BadRequestError("No document found for this contract")

    # Get raw content from storage
    from app.services.storage import download_file
    content = await download_file(document.storage_key)

    # Run engine
    engine = _get_engine()
    analysis = await engine.analyze(
        content=content,
        file_type=document.file_type,
        filename=document.file_name,
        contract_id=contract_id,
        user_role=user_role,
    )

    # Update contract status
    contract.status = "analyzed"
    contract.risk_score = analysis.risks.get("overall_risk", {}).get("score")
    contract.contract_type = analysis.metadata.get("contract_type")
    contract.page_count = analysis.metadata.get("page_count")
    contract.word_count = analysis.metadata.get("word_count")

    return {
        "summary": analysis.summary,
        "clauses": analysis.clauses,
        "risks": analysis.risks,
        "explanations": analysis.explanations,
        "negotiations": analysis.negotiations,
        "metadata": analysis.metadata,
    }


@router.post("/{contract_id}/chat-rag")
async def chat_rag(
    contract_id: str,
    question: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """RAG-powered chat about a contract."""
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()

    # Get chat history
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.contract_id == contract_id)
        .order_by(ChatMessage.created_at)
    )
    history = [{"role": m.role, "content": m.content} for m in result.scalars().all()]

    # Get full text as fallback
    doc_result = await db.execute(select(Document).where(Document.contract_id == contract_id))
    documents = doc_result.scalars().all()
    full_text = "\n\n".join(d.raw_text for d in documents if d.raw_text)

    # Run RAG chat
    engine = _get_engine()
    response = await engine.chat(
        contract_id=contract_id,
        question=question,
        history=history,
        full_text=full_text or None,
    )

    # Save messages
    user_msg = ChatMessage(contract_id=contract_id, user_id=user.id, role="user", content=question)
    assistant_msg = ChatMessage(contract_id=contract_id, user_id=user.id, role="assistant", content=response["answer"])
    db.add(user_msg)
    db.add(assistant_msg)

    return {
        "answer": response["answer"],
        "sources": response.get("sources", []),
    }


@router.post("/compare")
async def compare_contracts(
    contract_id_a: str = Form(...),
    contract_id_b: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare two contracts using the AI engine."""
    # Validate access to both contracts
    for cid in [contract_id_a, contract_id_b]:
        contract = await db.get(Contract, cid)
        if not contract or contract.deleted_at:
            raise NotFoundError(f"Contract {cid}")
        if contract.user_id != user.id:
            raise ForbiddenError()

    # Get texts
    async def get_text(cid: str) -> tuple[str, str]:
        result = await db.execute(select(Document).where(Document.contract_id == cid))
        docs = result.scalars().all()
        text = "\n\n".join(d.raw_text for d in docs if d.raw_text)
        contract = await db.get(Contract, cid)
        return text, contract.title

    text_a, title_a = await get_text(contract_id_a)
    text_b, title_b = await get_text(contract_id_b)

    if not text_a or not text_b:
        raise BadRequestError("Both contracts must have extracted text")

    engine = _get_engine()
    return await engine.compare(
        text_a=text_a,
        text_b=text_b,
        title_a=title_a,
        title_b=title_b,
    )
