package database

import (
	"database/sql"
	"fmt"
	"os"

	_ "github.com/lib/pq"
)

func Connect() (*sql.DB, error) {
	dsn := fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=require",
		os.Getenv("DB_HOST"),
		os.Getenv("DB_PORT"),
		os.Getenv("DB_USER"),
		os.Getenv("DB_PASSWORD"),
		os.Getenv("DB_NAME"),
	)

	db, err := sql.Open("postgres", dsn)
	if err != nil {
		return nil, err
	}

	if err := db.Ping(); err != nil {
		return nil, err
	}

	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)

	return db, nil
}

func RunMigrations(db *sql.DB) error {
	_, err := db.Exec(schema)
	return err
}

const schema = `
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
	id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	name          VARCHAR(100) NOT NULL,
	email         VARCHAR(255) UNIQUE NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	avatar_url    TEXT,
	fcm_token     TEXT,
	created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS families (
	id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	name        VARCHAR(100) NOT NULL,
	owner_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
	invite_code VARCHAR(12) UNIQUE NOT NULL,
	created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS family_members (
	family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
	user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
	role      VARCHAR(20) NOT NULL DEFAULT 'member',
	joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	PRIMARY KEY (family_id, user_id)
);

CREATE TABLE IF NOT EXISTS locations (
	id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
	latitude   DOUBLE PRECISION NOT NULL,
	longitude  DOUBLE PRECISION NOT NULL,
	accuracy   DOUBLE PRECISION NOT NULL DEFAULT 0,
	address    TEXT,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_locations_user_id ON locations(user_id);
CREATE INDEX IF NOT EXISTS idx_locations_created_at ON locations(created_at DESC);

CREATE TABLE IF NOT EXISTS wifi_status (
	id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
	family_id  UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
	ssid       VARCHAR(255) NOT NULL,
	bssid      VARCHAR(50) NOT NULL,
	is_trusted BOOLEAN NOT NULL DEFAULT FALSE,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	UNIQUE(user_id, family_id)
);

CREATE TABLE IF NOT EXISTS trusted_networks (
	id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
	ssid      VARCHAR(255) NOT NULL,
	bssid     VARCHAR(50) NOT NULL,
	label     VARCHAR(100) NOT NULL DEFAULT '',
	UNIQUE(family_id, bssid)
);

CREATE TABLE IF NOT EXISTS geofences (
	id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	family_id  UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
	name       VARCHAR(100) NOT NULL,
	latitude   DOUBLE PRECISION NOT NULL,
	longitude  DOUBLE PRECISION NOT NULL,
	radius     DOUBLE PRECISION NOT NULL DEFAULT 200,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
	id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
	family_id  UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
	user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
	type       VARCHAR(50) NOT NULL,
	message    TEXT NOT NULL,
	is_read    BOOLEAN NOT NULL DEFAULT FALSE,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_family_id ON alerts(family_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);
`
