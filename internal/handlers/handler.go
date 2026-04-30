package handlers

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"net/http"

	"github.com/gin-gonic/gin"

	"myfamilysafe/internal/models"
)

type Handler struct {
	db *sql.DB
}

func New(db *sql.DB) *Handler {
	return &Handler{db: db}
}

// GET /api/me
func (h *Handler) GetMe(c *gin.Context) {
	userID := c.GetString("user_id")

	var user models.User
	err := h.db.QueryRow(`
		SELECT id, name, email, avatar_url, created_at, updated_at
		FROM users WHERE id = $1
	`, userID).Scan(&user.ID, &user.Name, &user.Email, &user.AvatarURL, &user.CreatedAt, &user.UpdatedAt)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "user not found"})
		return
	}

	c.JSON(http.StatusOK, user)
}

// PUT /api/me
func (h *Handler) UpdateMe(c *gin.Context) {
	userID := c.GetString("user_id")

	var body struct {
		Name      string  `json:"name"`
		AvatarURL *string `json:"avatar_url"`
		FCMToken  *string `json:"fcm_token"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var user models.User
	err := h.db.QueryRow(`
		UPDATE users SET
			name = COALESCE(NULLIF($1, ''), name),
			avatar_url = COALESCE($2, avatar_url),
			fcm_token  = COALESCE($3, fcm_token),
			updated_at = NOW()
		WHERE id = $4
		RETURNING id, name, email, avatar_url, created_at, updated_at
	`, body.Name, body.AvatarURL, body.FCMToken, userID).Scan(
		&user.ID, &user.Name, &user.Email, &user.AvatarURL, &user.CreatedAt, &user.UpdatedAt,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update user"})
		return
	}

	c.JSON(http.StatusOK, user)
}

// POST /api/families
func (h *Handler) CreateFamily(c *gin.Context) {
	userID := c.GetString("user_id")

	var body struct {
		Name string `json:"name" binding:"required,min=2,max=100"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	inviteCode, err := generateInviteCode()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to generate invite code"})
		return
	}

	tx, err := h.db.Begin()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "transaction error"})
		return
	}
	defer tx.Rollback()

	var family models.Family
	err = tx.QueryRow(`
		INSERT INTO families (name, owner_id, invite_code)
		VALUES ($1, $2, $3)
		RETURNING id, name, owner_id, invite_code, created_at
	`, body.Name, userID, inviteCode).Scan(
		&family.ID, &family.Name, &family.OwnerID, &family.InviteCode, &family.CreatedAt,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create family"})
		return
	}

	_, err = tx.Exec(`
		INSERT INTO family_members (family_id, user_id, role)
		VALUES ($1, $2, 'admin')
	`, family.ID, userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to add owner as member"})
		return
	}

	tx.Commit()
	c.JSON(http.StatusCreated, family)
}

// GET /api/families/:id
func (h *Handler) GetFamily(c *gin.Context) {
	userID := c.GetString("user_id")
	familyID := c.Param("id")

	if !h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member of this family"})
		return
	}

	var family models.Family
	err := h.db.QueryRow(`
		SELECT id, name, owner_id, invite_code, created_at
		FROM families WHERE id = $1
	`, familyID).Scan(&family.ID, &family.Name, &family.OwnerID, &family.InviteCode, &family.CreatedAt)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "family not found"})
		return
	}

	c.JSON(http.StatusOK, family)
}

// POST /api/families/:id/invite  — aceitar convite pelo código
func (h *Handler) InviteMember(c *gin.Context) {
	userID := c.GetString("user_id")

	var body struct {
		InviteCode string `json:"invite_code" binding:"required"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var familyID string
	err := h.db.QueryRow(`SELECT id FROM families WHERE invite_code = $1`, body.InviteCode).Scan(&familyID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "invalid invite code"})
		return
	}

	if h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusConflict, gin.H{"error": "already a member of this family"})
		return
	}

	_, err = h.db.Exec(`
		INSERT INTO family_members (family_id, user_id, role)
		VALUES ($1, $2, 'member')
	`, familyID, userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to join family"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"family_id": familyID, "message": "joined successfully"})
}

// GET /api/families/:id/members
func (h *Handler) GetMembers(c *gin.Context) {
	userID := c.GetString("user_id")
	familyID := c.Param("id")

	if !h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member of this family"})
		return
	}

	rows, err := h.db.Query(`
		SELECT u.id, u.name, u.email, u.avatar_url, u.created_at, u.updated_at,
		       fm.role, fm.joined_at
		FROM family_members fm
		JOIN users u ON u.id = fm.user_id
		WHERE fm.family_id = $1
		ORDER BY fm.joined_at ASC
	`, familyID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "database error"})
		return
	}
	defer rows.Close()

	var members []models.FamilyMember
	for rows.Next() {
		var m models.FamilyMember
		var u models.User
		err := rows.Scan(
			&u.ID, &u.Name, &u.Email, &u.AvatarURL, &u.CreatedAt, &u.UpdatedAt,
			&m.Role, &m.JoinedAt,
		)
		if err != nil {
			continue
		}
		m.UserID = u.ID
		m.FamilyID = familyID
		m.User = &u
		members = append(members, m)
	}

	c.JSON(http.StatusOK, members)
}

// DELETE /api/families/:id/members/:userId
func (h *Handler) RemoveMember(c *gin.Context) {
	requesterID := c.GetString("user_id")
	familyID := c.Param("id")
	targetUserID := c.Param("userId")

	// Só o dono ou o próprio membro pode remover
	var ownerID string
	h.db.QueryRow(`SELECT owner_id FROM families WHERE id = $1`, familyID).Scan(&ownerID)

	if requesterID != ownerID && requesterID != targetUserID {
		c.JSON(http.StatusForbidden, gin.H{"error": "not authorized"})
		return
	}

	_, err := h.db.Exec(`
		DELETE FROM family_members WHERE family_id = $1 AND user_id = $2
	`, familyID, targetUserID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to remove member"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "member removed"})
}

// helpers
func (h *Handler) isFamilyMember(familyID, userID string) bool {
	var exists bool
	h.db.QueryRow(`
		SELECT EXISTS(SELECT 1 FROM family_members WHERE family_id = $1 AND user_id = $2)
	`, familyID, userID).Scan(&exists)
	return exists
}

func generateInviteCode() (string, error) {
	b := make([]byte, 6)
	_, err := rand.Read(b)
	if err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}
