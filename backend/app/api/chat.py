from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.models.user import User
from app.models.contract import Contract, Document
from app.models.chat import ChatMessage
from app.schemas.chat import ChatRequest, ChatMessageResponse, ChatHistoryResponse
from app.services import ai as ai_service

router = APIRouter()


@router.post("/{contract_id}", response_model=ChatMessageResponse)
async def send_message(
    contract_id: str,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()
    if contract.status != "analyzed":
        raise BadRequestError("Contract must be analyzed before chatting")

    # Get contract text
    result = await db.execute(select(Document).where(Document.contract_id == contract_id))
    documents = result.scalars().all()
    contract_text = "\n\n".join(d.raw_text for d in documents if d.raw_text)

    if not contract_text:
        raise BadRequestError("No extracted text available")

    # Get conversation history
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.contract_id == contract_id)
        .order_by(ChatMessage.created_at)
    )
    history = result.scalars().all()

    # Build messages for Claude
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": body.message})

    # Save user message
    user_msg = ChatMessage(
        contract_id=contract_id,
        user_id=user.id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)

    # Get AI response
    ai_response = await ai_service.chat_about_contract(contract_text, messages)

    # Save assistant message
    assistant_msg = ChatMessage(
        contract_id=contract_id,
        user_id=user.id,
        role="assistant",
        content=ai_response["content"],
        tokens_used=ai_response.get("tokens_used"),
        model_used=ai_response.get("model_used"),
    )
    db.add(assistant_msg)
    await db.flush()

    return assistant_msg


@router.get("/{contract_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.contract_id == contract_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    return ChatHistoryResponse(messages=messages, contract_id=contract_id)


@router.delete("/{contract_id}", status_code=204)
async def clear_chat(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()

    result = await db.execute(
        select(ChatMessage).where(ChatMessage.contract_id == contract_id)
    )
    for msg in result.scalars().all():
        await db.delete(msg)
