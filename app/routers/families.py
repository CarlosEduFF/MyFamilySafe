import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.database import get_db
from app.deps import get_current_user, is_family_member, require_family_member
from app.models import Family, FamilyMember, User
from app.schemas import (
    FamilyCreate, FamilyMemberOut, FamilyOut, JoinRequest, UserOut,
)
from app.utils import generate_invite_code

router = APIRouter(prefix="/api/families", tags=["families"])


@router.post("", response_model=FamilyOut, status_code=status.HTTP_201_CREATED)
async def create_family(body: FamilyCreate, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    # Uma única transação cria a família e insere o dono como admin,
    # como o tx de handler.go:91.
    family = Family(name=body.name, owner_id=user.id,
                    invite_code=generate_invite_code())
    db.add(family)
    await db.flush()
    db.add(FamilyMember(family_id=family.id, user_id=user.id, role="admin"))
    await db.commit()
    await db.refresh(family)
    return family


@router.post("/join")
async def join_family(body: JoinRequest, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """Correção #1: substitui POST /api/families/:id/invite, que ignorava o :id
    e cujo path o app chamava errado."""
    result = await db.execute(
        select(Family.id).where(Family.invite_code == body.invite_code)
    )
    family_id = result.scalar_one_or_none()
    if family_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "invalid invite code")

    if await is_family_member(db, family_id, user.id):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "already a member of this family")

    db.add(FamilyMember(family_id=family_id, user_id=user.id, role="member"))
    await db.commit()
    return {"family_id": str(family_id), "message": "joined successfully"}


@router.get("/{id}", response_model=FamilyOut)
async def get_family(family_id: uuid.UUID = Depends(require_family_member),
                     db: AsyncSession = Depends(get_db)):
    family = await db.get(Family, family_id)
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "family not found")
    return family


@router.get("/{id}/members", response_model=list[FamilyMemberOut])
async def get_members(family_id: uuid.UUID = Depends(require_family_member),
                      db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FamilyMember, User)
        .join(User, User.id == FamilyMember.user_id)
        .where(FamilyMember.family_id == family_id)
        .order_by(FamilyMember.joined_at.asc())
    )
    return [
        FamilyMemberOut(
            family_id=fm.family_id, user_id=fm.user_id, role=fm.role,
            joined_at=fm.joined_at, user=UserOut.model_validate(u),
        )
        for fm, u in result.all()
    ]


@router.delete("/{id}/members/{user_id}")
async def remove_member(id: uuid.UUID, user_id: uuid.UUID,
                        user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    # Só o dono ou o próprio membro pode remover (handler.go:237).
    family = await db.get(Family, id)
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "family not found")
    if user.id != family.owner_id and user.id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized")

    member = await db.get(FamilyMember, {"family_id": id, "user_id": user_id})
    if member is not None:
        await db.delete(member)
        await db.commit()
    return {"message": "member removed"}