from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.core.exceptions import (
    NotFoundError, ForbiddenError, FileTooLargeError,
    UnsupportedFileError, RateLimitError,
)
from app.models.user import User
from app.models.contract import Contract, Document
from app.schemas.contract import ContractResponse, ContractListResponse, DocumentResponse
from app.services import storage as storage_service, audit as audit_service

router = APIRouter()


def _check_file(file: UploadFile):
    settings = get_settings()
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in settings.allowed_extensions:
        raise UnsupportedFileError(settings.allowed_extensions)


async def _check_quota(user: User, db: AsyncSession):
    if user.contracts_used >= user.contracts_limit:
        raise RateLimitError()


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def upload_contract(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(None),
    org_id: str = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_file(file)
    await _check_quota(user, db)

    settings = get_settings()
    ext = file.filename.rsplit(".", 1)[-1].lower()

    # Upload to storage
    storage_key, file_size = await storage_service.upload_file(file, user.id)

    if file_size > settings.max_file_size_mb * 1024 * 1024:
        await storage_service.delete_file(storage_key)
        raise FileTooLargeError(settings.max_file_size_mb)

    # Create contract
    contract = Contract(user_id=user.id, org_id=org_id, title=title, description=description)
    db.add(contract)
    await db.flush()

    # Create document
    document = Document(
        contract_id=contract.id,
        file_name=file.filename,
        file_type=ext,
        file_size=file_size,
        storage_key=storage_key,
    )
    db.add(document)

    # Update quota
    user.contracts_used += 1

    await audit_service.log_action(
        db, action="contract.upload", resource_type="contract",
        user_id=user.id, contract_id=contract.id,
        details={"file_name": file.filename, "file_size": file_size},
        ip_address=request.client.host if request.client else None,
    )

    await db.flush()
    return contract


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    skip: int = 0,
    limit: int = 20,
    status_filter: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Contract).where(
        Contract.user_id == user.id,
        Contract.deleted_at.is_(None),
    )
    if status_filter:
        query = query.where(Contract.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Contract.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    contracts = result.scalars().all()

    return ContractListResponse(contracts=contracts, total=total)


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()
    return contract


@router.get("/{contract_id}/documents", response_model=list[DocumentResponse])
async def get_documents(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()

    result = await db.execute(select(Document).where(Document.contract_id == contract_id))
    return result.scalars().all()


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contract = await db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()

    from datetime import datetime, timezone
    contract.deleted_at = datetime.now(timezone.utc)

    await audit_service.log_action(
        db, action="contract.delete", resource_type="contract",
        user_id=user.id, contract_id=contract.id,
        ip_address=request.client.host if request.client else None,
    )
