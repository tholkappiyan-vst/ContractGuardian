from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.models.user import User
from app.models.contract import Contract, Document
from app.schemas.chat import ComparisonRequest, ComparisonResponse, ComparisonDifference
from app.services import ai as ai_service

router = APIRouter()


async def _get_contract_text(contract_id: str, user: User, db: AsyncSession) -> str:
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()
    if contract.status != "analyzed":
        raise BadRequestError(f"Contract {contract_id} must be analyzed first")

    result = await db.execute(select(Document).where(Document.contract_id == contract_id))
    documents = result.scalars().all()
    text = "\n\n".join(d.raw_text for d in documents if d.raw_text)
    if not text:
        raise BadRequestError(f"No text available for contract {contract_id}")
    return text


@router.post("", response_model=ComparisonResponse)
async def compare_contracts(
    body: ComparisonRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    text_a = await _get_contract_text(body.contract_id_a, user, db)
    text_b = await _get_contract_text(body.contract_id_b, user, db)

    result = await ai_service.compare_contracts(text_a, text_b)

    differences = [
        ComparisonDifference(**d) for d in result.get("differences", [])
    ]

    return ComparisonResponse(
        summary=result.get("summary", ""),
        recommendation=result.get("recommendation", "neither"),
        confidence=result.get("confidence", 0.0),
        risk_a=result.get("risk_a", 0),
        risk_b=result.get("risk_b", 0),
        differences=differences,
        unchanged=result.get("unchanged", []),
    )
