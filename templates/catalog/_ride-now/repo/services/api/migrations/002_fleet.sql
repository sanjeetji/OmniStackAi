-- RideNow fleet: vehicle types and pricing, drivers, their documents, surge zones.
CREATE TABLE vehicle_types (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    seats           INT NOT NULL,
    base_fare       NUMERIC(10,2) NOT NULL,
    per_km          NUMERIC(10,2) NOT NULL,
    per_min         NUMERIC(10,2) NOT NULL,
    min_fare        NUMERIC(10,2) NOT NULL,
    booking_fee     NUMERIC(10,2) NOT NULL DEFAULT 0,
    commission_pct  NUMERIC(5,2) NOT NULL DEFAULT 20,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    sort            INT NOT NULL DEFAULT 0
);

CREATE TABLE drivers (
    user_id          UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    vehicle_type     TEXT NOT NULL REFERENCES vehicle_types (id),
    vehicle_make     TEXT NOT NULL,
    vehicle_model    TEXT NOT NULL,
    vehicle_color    TEXT NOT NULL,
    plate            TEXT NOT NULL UNIQUE,
    license_no       TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'suspended')),
    online           BOOLEAN NOT NULL DEFAULT FALSE,
    simulated        BOOLEAN NOT NULL DEFAULT FALSE,
    lat              DOUBLE PRECISION,
    lng              DOUBLE PRECISION,
    heading          DOUBLE PRECISION NOT NULL DEFAULT 0,
    last_seen_at     TIMESTAMPTZ,
    rating_avg       NUMERIC(3,2) NOT NULL DEFAULT 5.00,
    rating_count     INT NOT NULL DEFAULT 0,
    offers_received  INT NOT NULL DEFAULT 0,
    offers_accepted  INT NOT NULL DEFAULT 0,
    joined_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX drivers_dispatch_idx ON drivers (vehicle_type, status, online);

CREATE TABLE driver_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id   UUID NOT NULL REFERENCES drivers (user_id) ON DELETE CASCADE,
    kind        TEXT NOT NULL CHECK (kind IN ('license', 'registration', 'insurance', 'permit', 'photo')),
    number      TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    expires_on  DATE,
    note        TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (driver_id, kind)
);

CREATE TABLE zones (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    center_lat  DOUBLE PRECISION NOT NULL,
    center_lng  DOUBLE PRECISION NOT NULL,
    radius_km   NUMERIC(5,2) NOT NULL,
    surge       NUMERIC(3,2) NOT NULL DEFAULT 1.00 CHECK (surge >= 1.00 AND surge <= 3.00),
    active      BOOLEAN NOT NULL DEFAULT TRUE
);
