import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

ORM = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    model_config = ORM
    # password_hash nunca aparece — equivale a `json:"-"` no Go.
    id: uuid.UUID
    name: str
    email: EmailStr
    avatar_url: str | None = None
    fcm_token: str | None = None
    created_at: datetime
    updated_at: datetime


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserOut
    family_id: uuid.UUID | None = None  # correção #2


class FamilyOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    invite_code: str
    created_at: datetime


class FamilyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class JoinRequest(BaseModel):
    invite_code: str


class FamilyMemberOut(BaseModel):
    family_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime
    user: UserOut | None = None


class LocationOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    user_id: uuid.UUID
    latitude: float
    longitude: float
    accuracy: float
    address: str | None = None
    created_at: datetime


class LocationCreate(BaseModel):
    family_id: uuid.UUID
    latitude: float
    longitude: float
    accuracy: float = 0
    address: str | None = None


class MemberLocationOut(BaseModel):
    user: UserOut
    location: LocationOut | None = None
    is_online: bool = False
    last_seen: datetime | None = None


class WifiUpdate(BaseModel):
    family_id: uuid.UUID
    ssid: str
    bssid: str


class WifiOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    family_id: uuid.UUID
    ssid: str
    bssid: str
    is_trusted: bool
    updated_at: datetime
    user_name: str
    user_avatar_url: str | None = None


class TrustedNetworkCreate(BaseModel):
    ssid: str
    bssid: str
    label: str = ""


class GeofenceCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius: float = 0  # <= 0 vira 200 no handler, como resources.go:321


class GeofenceOut(BaseModel):
    model_config = ORM
    id: uuid.UUID
    family_id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    radius: float
    created_at: datetime


class AlertOut(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    user_id: uuid.UUID
    type: str
    message: str
    is_read: bool
    created_at: datetime
    user_name: str
    user_avatar_url: str | None = None


class UpdateMeRequest(BaseModel):
    name: str | None = None
    avatar_url: str | None = None
    fcm_token: str | None = None