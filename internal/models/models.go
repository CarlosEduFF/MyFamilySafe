package models

import "time"

type User struct {
	ID           string    `json:"id" db:"id"`
	Name         string    `json:"name" db:"name"`
	Email        string    `json:"email" db:"email"`
	PasswordHash string    `json:"-" db:"password_hash"`
	AvatarURL    *string   `json:"avatar_url" db:"avatar_url"`
	FCMToken     *string   `json:"fcm_token" db:"fcm_token"`
	CreatedAt    time.Time `json:"created_at" db:"created_at"`
	UpdatedAt    time.Time `json:"updated_at" db:"updated_at"`
}

type Family struct {
	ID        string    `json:"id" db:"id"`
	Name      string    `json:"name" db:"name"`
	OwnerID   string    `json:"owner_id" db:"owner_id"`
	InviteCode string   `json:"invite_code" db:"invite_code"`
	CreatedAt time.Time `json:"created_at" db:"created_at"`
}

type FamilyMember struct {
	FamilyID  string    `json:"family_id" db:"family_id"`
	UserID    string    `json:"user_id" db:"user_id"`
	Role      string    `json:"role" db:"role"` // admin, member
	JoinedAt  time.Time `json:"joined_at" db:"joined_at"`
	User      *User     `json:"user,omitempty"`
}

type Location struct {
	ID        string    `json:"id" db:"id"`
	UserID    string    `json:"user_id" db:"user_id"`
	Latitude  float64   `json:"latitude" db:"latitude"`
	Longitude float64   `json:"longitude" db:"longitude"`
	Accuracy  float64   `json:"accuracy" db:"accuracy"`
	Address   *string   `json:"address" db:"address"`
	CreatedAt time.Time `json:"created_at" db:"created_at"`
}

type MemberLocation struct {
	User     User      `json:"user"`
	Location *Location `json:"location"`
	IsOnline bool      `json:"is_online"`
	LastSeen time.Time `json:"last_seen"`
}

type WifiStatus struct {
	ID        string    `json:"id" db:"id"`
	UserID    string    `json:"user_id" db:"user_id"`
	FamilyID  string    `json:"family_id" db:"family_id"`
	SSID      string    `json:"ssid" db:"ssid"`
	BSSID     string    `json:"bssid" db:"bssid"`
	IsTrusted bool      `json:"is_trusted" db:"is_trusted"`
	UpdatedAt time.Time `json:"updated_at" db:"updated_at"`
}

type TrustedNetwork struct {
	ID       string `json:"id" db:"id"`
	FamilyID string `json:"family_id" db:"family_id"`
	SSID     string `json:"ssid" db:"ssid"`
	BSSID    string `json:"bssid" db:"bssid"`
	Label    string `json:"label" db:"label"` // "Casa", "Trabalho", etc.
}

type Geofence struct {
	ID        string    `json:"id" db:"id"`
	FamilyID  string    `json:"family_id" db:"family_id"`
	Name      string    `json:"name" db:"name"`
	Latitude  float64   `json:"latitude" db:"latitude"`
	Longitude float64   `json:"longitude" db:"longitude"`
	Radius    float64   `json:"radius" db:"radius"` // metros
	CreatedAt time.Time `json:"created_at" db:"created_at"`
}

type Alert struct {
	ID        string     `json:"id" db:"id"`
	FamilyID  string     `json:"family_id" db:"family_id"`
	UserID    string     `json:"user_id" db:"user_id"`
	Type      string     `json:"type" db:"type"` // geofence_exit, geofence_enter, unknown_wifi, offline
	Message   string     `json:"message" db:"message"`
	IsRead    bool       `json:"is_read" db:"is_read"`
	CreatedAt time.Time  `json:"created_at" db:"created_at"`
	User      *User      `json:"user,omitempty"`
}
