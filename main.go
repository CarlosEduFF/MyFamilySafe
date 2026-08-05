package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"

	"myfamilysafe/internal/database"
	"myfamilysafe/internal/handlers"
	"myfamilysafe/internal/middleware"
)

func main() {
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, using environment variables")
	}

	validateEnv()

	db, err := database.Connect()
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	if err := database.RunMigrations(db); err != nil {
		log.Fatalf("Failed to run migrations: %v", err)
	}

	r := gin.Default()
	r.Use(middleware.CORS())

	// Health check
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "timestamp": time.Now().Format(time.RFC3339)})
	})

	h := handlers.New(db)

	// Public routes
	auth := r.Group("/auth")
	{
		auth.POST("/register", h.Register)
		auth.POST("/login", h.Login)
		auth.POST("/refresh", h.RefreshToken)
	}

	// Protected routes
	api := r.Group("/api")
	api.Use(middleware.JWT())
	{
		// Family
		api.POST("/families", h.CreateFamily)
		api.GET("/families/:id", h.GetFamily)
		api.POST("/families/:id/invite", h.InviteMember)
		api.GET("/families/:id/members", h.GetMembers)
		api.DELETE("/families/:id/members/:userId", h.RemoveMember)

		// Location
		api.POST("/location", h.UpdateLocation)
		api.GET("/families/:id/locations", h.GetFamilyLocations)
		api.GET("/members/:userId/location/history", h.GetLocationHistory)

		// WiFi
		api.POST("/wifi", h.UpdateWifi)
		api.GET("/families/:id/wifi", h.GetFamilyWifi)
		api.POST("/families/:id/wifi/trusted", h.AddTrustedNetwork)
		api.DELETE("/families/:id/wifi/trusted", h.RemoveTrustedNetwork)

		// Geofences
		api.POST("/families/:id/geofences", h.CreateGeofence)
		api.GET("/families/:id/geofences", h.GetGeofences)
		api.DELETE("/families/:id/geofences/:geofenceId", h.DeleteGeofence)

		// Alerts
		api.GET("/families/:id/alerts", h.GetAlerts)
		api.PUT("/alerts/:alertId/read", h.MarkAlertRead)

		// User profile
		api.GET("/me", h.GetMe)
		api.PUT("/me", h.UpdateMe)
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	srv := &http.Server{
		Addr:    ":" + port,
		Handler: r,
	}

	// Iniciar servidor em uma goroutine
	go func() {
		log.Printf("Server running on port %s", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %s\n", err)
		}
	}()

	// Aguardar sinal de interrupção para desligamento suave
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}

	log.Println("Server exiting")
}

func validateEnv() {
	required := []string{
		"DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME",
		"JWT_SECRET", "JWT_REFRESH_SECRET",
	}

	for _, env := range required {
		if os.Getenv(env) == "" {
			log.Fatalf("Critical environment variable missing: %s", env)
		}
	}
}
