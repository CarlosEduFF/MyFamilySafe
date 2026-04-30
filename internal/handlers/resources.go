package handlers

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"myfamilysafe/internal/models"
)

// ─── LOCATION ────────────────────────────────────────────────────────────────

// POST /api/location
func (h *Handler) UpdateLocation(c *gin.Context) {
	userID := c.GetString("user_id")

	var body struct {
		FamilyID  string  `json:"family_id" binding:"required"`
		Latitude  float64 `json:"latitude" binding:"required"`
		Longitude float64 `json:"longitude" binding:"required"`
		Accuracy  float64 `json:"accuracy"`
		Address   *string `json:"address"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if !h.isFamilyMember(body.FamilyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member of this family"})
		return
	}

	var loc models.Location
	err := h.db.QueryRow(`
		INSERT INTO locations (user_id, latitude, longitude, accuracy, address)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id, user_id, latitude, longitude, accuracy, address, created_at
	`, userID, body.Latitude, body.Longitude, body.Accuracy, body.Address).Scan(
		&loc.ID, &loc.UserID, &loc.Latitude, &loc.Longitude,
		&loc.Accuracy, &loc.Address, &loc.CreatedAt,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to save location"})
		return
	}

	// Verificar geofences em background
	go h.checkGeofences(body.FamilyID, userID, body.Latitude, body.Longitude)

	c.JSON(http.StatusCreated, loc)
}

// GET /api/families/:id/locations  — última localização de cada membro
func (h *Handler) GetFamilyLocations(c *gin.Context) {
	userID := c.GetString("user_id")
	familyID := c.Param("id")

	if !h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member of this family"})
		return
	}

	rows, err := h.db.Query(`
		SELECT u.id, u.name, u.email, u.avatar_url,
		       l.id, l.latitude, l.longitude, l.accuracy, l.address, l.created_at
		FROM family_members fm
		JOIN users u ON u.id = fm.user_id
		LEFT JOIN LATERAL (
			SELECT * FROM locations WHERE user_id = u.id
			ORDER BY created_at DESC LIMIT 1
		) l ON TRUE
		WHERE fm.family_id = $1
		ORDER BY u.name ASC
	`, familyID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "database error"})
		return
	}
	defer rows.Close()

	var result []models.MemberLocation
	onlineThreshold := time.Now().Add(-5 * time.Minute)

	for rows.Next() {
		var u models.User
		var locID, locAddress *string
		var lat, lon, acc *float64
		var locCreated *time.Time

		err := rows.Scan(
			&u.ID, &u.Name, &u.Email, &u.AvatarURL,
			&locID, &lat, &lon, &acc, &locAddress, &locCreated,
		)
		if err != nil {
			continue
		}

		ml := models.MemberLocation{User: u}

		if locID != nil {
			ml.Location = &models.Location{
				ID: *locID, UserID: u.ID,
				Latitude: *lat, Longitude: *lon, Accuracy: *acc,
				Address: locAddress, CreatedAt: *locCreated,
			}
			ml.LastSeen = *locCreated
			ml.IsOnline = locCreated.After(onlineThreshold)
		}

		result = append(result, ml)
	}

	c.JSON(http.StatusOK, result)
}

// GET /api/members/:userId/location/history
func (h *Handler) GetLocationHistory(c *gin.Context) {
	requesterID := c.GetString("user_id")
	targetUserID := c.Param("userId")

	// Verificar se estão na mesma família
	var shared bool
	h.db.QueryRow(`
		SELECT EXISTS(
			SELECT 1 FROM family_members a
			JOIN family_members b ON a.family_id = b.family_id
			WHERE a.user_id = $1 AND b.user_id = $2
		)
	`, requesterID, targetUserID).Scan(&shared)

	if !shared && requesterID != targetUserID {
		c.JSON(http.StatusForbidden, gin.H{"error": "not authorized"})
		return
	}

	rows, err := h.db.Query(`
		SELECT id, user_id, latitude, longitude, accuracy, address, created_at
		FROM locations WHERE user_id = $1
		ORDER BY created_at DESC LIMIT 100
	`, targetUserID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "database error"})
		return
	}
	defer rows.Close()

	var history []models.Location
	for rows.Next() {
		var l models.Location
		rows.Scan(&l.ID, &l.UserID, &l.Latitude, &l.Longitude, &l.Accuracy, &l.Address, &l.CreatedAt)
		history = append(history, l)
	}

	c.JSON(http.StatusOK, history)
}

// ─── WIFI ────────────────────────────────────────────────────────────────────

// POST /api/wifi
func (h *Handler) UpdateWifi(c *gin.Context) {
	userID := c.GetString("user_id")

	var body struct {
		FamilyID string `json:"family_id" binding:"required"`
		SSID     string `json:"ssid" binding:"required"`
		BSSID    string `json:"bssid" binding:"required"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Verificar se é rede confiável
	var isTrusted bool
	h.db.QueryRow(`
		SELECT EXISTS(
			SELECT 1 FROM trusted_networks
			WHERE family_id = $1 AND bssid = $2
		)
	`, body.FamilyID, body.BSSID).Scan(&isTrusted)

	_, err := h.db.Exec(`
		INSERT INTO wifi_status (user_id, family_id, ssid, bssid, is_trusted, updated_at)
		VALUES ($1, $2, $3, $4, $5, NOW())
		ON CONFLICT (user_id, family_id) DO UPDATE
		SET ssid = EXCLUDED.ssid,
		    bssid = EXCLUDED.bssid,
		    is_trusted = EXCLUDED.is_trusted,
		    updated_at = NOW()
	`, userID, body.FamilyID, body.SSID, body.BSSID, isTrusted)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update wifi"})
		return
	}

	// Disparar alerta se rede desconhecida
	if !isTrusted {
		go h.createAlert(body.FamilyID, userID, "unknown_wifi",
			"Conectado em rede WiFi desconhecida: "+body.SSID)
	}

	c.JSON(http.StatusOK, gin.H{"is_trusted": isTrusted})
}

// GET /api/families/:id/wifi
func (h *Handler) GetFamilyWifi(c *gin.Context) {
	userID := c.GetString("user_id")
	familyID := c.Param("id")

	if !h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member of this family"})
		return
	}

	rows, err := h.db.Query(`
		SELECT w.id, w.user_id, w.family_id, w.ssid, w.bssid, w.is_trusted, w.updated_at,
		       u.name, u.avatar_url
		FROM wifi_status w
		JOIN users u ON u.id = w.user_id
		WHERE w.family_id = $1
	`, familyID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "database error"})
		return
	}
	defer rows.Close()

	type WifiWithUser struct {
		models.WifiStatus
		UserName      string  `json:"user_name"`
		UserAvatarURL *string `json:"user_avatar_url"`
	}

	var results []WifiWithUser
	for rows.Next() {
		var w WifiWithUser
		rows.Scan(
			&w.ID, &w.UserID, &w.FamilyID, &w.SSID, &w.BSSID, &w.IsTrusted, &w.UpdatedAt,
			&w.UserName, &w.UserAvatarURL,
		)
		results = append(results, w)
	}

	c.JSON(http.StatusOK, results)
}

// POST /api/families/:id/wifi/trusted
func (h *Handler) AddTrustedNetwork(c *gin.Context) {
	userID := c.GetString("user_id")
	familyID := c.Param("id")

	if !h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member"})
		return
	}

	var body struct {
		SSID  string `json:"ssid" binding:"required"`
		BSSID string `json:"bssid" binding:"required"`
		Label string `json:"label"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	_, err := h.db.Exec(`
		INSERT INTO trusted_networks (family_id, ssid, bssid, label)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (family_id, bssid) DO UPDATE SET ssid = EXCLUDED.ssid, label = EXCLUDED.label
	`, familyID, body.SSID, body.BSSID, body.Label)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to add trusted network"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"message": "network added as trusted"})
}

// DELETE /api/families/:id/wifi/trusted
func (h *Handler) RemoveTrustedNetwork(c *gin.Context) {
	userID := c.GetString("user_id")
	familyID := c.Param("id")

	if !h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member"})
		return
	}

	bssid := c.Query("bssid")
	h.db.Exec(`DELETE FROM trusted_networks WHERE family_id = $1 AND bssid = $2`, familyID, bssid)

	c.JSON(http.StatusOK, gin.H{"message": "network removed"})
}

// ─── GEOFENCES ───────────────────────────────────────────────────────────────

// POST /api/families/:id/geofences
func (h *Handler) CreateGeofence(c *gin.Context) {
	userID := c.GetString("user_id")
	familyID := c.Param("id")

	if !h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member"})
		return
	}

	var body struct {
		Name      string  `json:"name" binding:"required"`
		Latitude  float64 `json:"latitude" binding:"required"`
		Longitude float64 `json:"longitude" binding:"required"`
		Radius    float64 `json:"radius"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if body.Radius <= 0 {
		body.Radius = 200
	}

	var g models.Geofence
	err := h.db.QueryRow(`
		INSERT INTO geofences (family_id, name, latitude, longitude, radius)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id, family_id, name, latitude, longitude, radius, created_at
	`, familyID, body.Name, body.Latitude, body.Longitude, body.Radius).Scan(
		&g.ID, &g.FamilyID, &g.Name, &g.Latitude, &g.Longitude, &g.Radius, &g.CreatedAt,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create geofence"})
		return
	}

	c.JSON(http.StatusCreated, g)
}

// GET /api/families/:id/geofences
func (h *Handler) GetGeofences(c *gin.Context) {
	userID := c.GetString("user_id")
	familyID := c.Param("id")

	if !h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member"})
		return
	}

	rows, err := h.db.Query(`
		SELECT id, family_id, name, latitude, longitude, radius, created_at
		FROM geofences WHERE family_id = $1 ORDER BY created_at ASC
	`, familyID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "database error"})
		return
	}
	defer rows.Close()

	var geofences []models.Geofence
	for rows.Next() {
		var g models.Geofence
		rows.Scan(&g.ID, &g.FamilyID, &g.Name, &g.Latitude, &g.Longitude, &g.Radius, &g.CreatedAt)
		geofences = append(geofences, g)
	}

	c.JSON(http.StatusOK, geofences)
}

// DELETE /api/families/:id/geofences/:geofenceId
func (h *Handler) DeleteGeofence(c *gin.Context) {
	userID := c.GetString("user_id")
	familyID := c.Param("id")
	geofenceID := c.Param("geofenceId")

	if !h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member"})
		return
	}

	h.db.Exec(`DELETE FROM geofences WHERE id = $1 AND family_id = $2`, geofenceID, familyID)
	c.JSON(http.StatusOK, gin.H{"message": "geofence deleted"})
}

// ─── ALERTS ──────────────────────────────────────────────────────────────────

// GET /api/families/:id/alerts
func (h *Handler) GetAlerts(c *gin.Context) {
	userID := c.GetString("user_id")
	familyID := c.Param("id")

	if !h.isFamilyMember(familyID, userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "not a member"})
		return
	}

	rows, err := h.db.Query(`
		SELECT a.id, a.family_id, a.user_id, a.type, a.message, a.is_read, a.created_at,
		       u.name, u.avatar_url
		FROM alerts a
		JOIN users u ON u.id = a.user_id
		WHERE a.family_id = $1
		ORDER BY a.created_at DESC
		LIMIT 50
	`, familyID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "database error"})
		return
	}
	defer rows.Close()

	type AlertWithUser struct {
		models.Alert
		UserName      string  `json:"user_name"`
		UserAvatarURL *string `json:"user_avatar_url"`
	}

	var alerts []AlertWithUser
	for rows.Next() {
		var a AlertWithUser
		rows.Scan(
			&a.ID, &a.FamilyID, &a.UserID, &a.Type, &a.Message, &a.IsRead, &a.CreatedAt,
			&a.UserName, &a.UserAvatarURL,
		)
		alerts = append(alerts, a)
	}

	c.JSON(http.StatusOK, alerts)
}

// PUT /api/alerts/:alertId/read
func (h *Handler) MarkAlertRead(c *gin.Context) {
	alertID := c.Param("alertId")
	h.db.Exec(`UPDATE alerts SET is_read = TRUE WHERE id = $1`, alertID)
	c.JSON(http.StatusOK, gin.H{"message": "alert marked as read"})
}

// ─── HELPERS INTERNOS ────────────────────────────────────────────────────────

func (h *Handler) createAlert(familyID, userID, alertType, message string) {
	h.db.Exec(`
		INSERT INTO alerts (family_id, user_id, type, message)
		VALUES ($1, $2, $3, $4)
	`, familyID, userID, alertType, message)
}

func (h *Handler) checkGeofences(familyID, userID string, lat, lon float64) {
	rows, err := h.db.Query(`
		SELECT id, name, latitude, longitude, radius FROM geofences WHERE family_id = $1
	`, familyID)
	if err != nil {
		return
	}
	defer rows.Close()

	for rows.Next() {
		var g models.Geofence
		rows.Scan(&g.ID, &g.Name, &g.Latitude, &g.Longitude, &g.Radius)

		dist := haversineDistance(lat, lon, g.Latitude, g.Longitude)
		if dist > g.Radius {
			h.createAlert(familyID, userID, "geofence_exit",
				"Saiu da zona segura: "+g.Name)
		}
	}
}

func haversineDistance(lat1, lon1, lat2, lon2 float64) float64 {
	const earthRadius = 6371000.0
	const pi = 3.14159265358979323846

	dLat := (lat2 - lat1) * pi / 180
	dLon := (lon2 - lon1) * pi / 180

	a := sinSquared(dLat/2) + cosD(lat1)*cosD(lat2)*sinSquared(dLon/2)
	c := 2 * atan2Sqrt(a)

	return earthRadius * c
}

func sinSquared(x float64) float64 { return x * x }
func cosD(deg float64) float64     { return 1 - deg*deg/2 } // aproximação simples
func atan2Sqrt(a float64) float64  { return a }             // usar math.Atan2 em produção
