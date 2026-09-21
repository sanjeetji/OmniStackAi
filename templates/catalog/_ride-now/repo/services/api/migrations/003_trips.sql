-- RideNow trips: places, promos, trips and their event log, dispatch offers, ratings.
CREATE TABLE places (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users (id) ON DELETE CASCADE,
    label       TEXT NOT NULL,
    name        TEXT NOT NULL,
    address     TEXT NOT NULL DEFAULT '',
    lat         DOUBLE PRECISION NOT NULL,
    lng         DOUBLE PRECISION NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX places_user_idx ON places (user_id);

CREATE TABLE promo_codes (
    code          TEXT PRIMARY KEY,
    description   TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('percent', 'flat')),
    value         NUMERIC(10,2) NOT NULL CHECK (value > 0),
    max_discount  NUMERIC(10,2),
    min_fare      NUMERIC(10,2) NOT NULL DEFAULT 0,
    valid_until   TIMESTAMPTZ,
    usage_limit   INT,
    per_user_limit INT NOT NULL DEFAULT 1,
    used_count    INT NOT NULL DEFAULT 0,
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE SEQUENCE trip_code_seq START 10001;

CREATE TABLE trips (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            TEXT NOT NULL UNIQUE DEFAULT ('RN-' || nextval('trip_code_seq')),
    rider_id        UUID NOT NULL REFERENCES users (id),
    driver_id       UUID REFERENCES drivers (user_id),
    vehicle_type    TEXT NOT NULL REFERENCES vehicle_types (id),
    status          TEXT NOT NULL CHECK (status IN (
                        'requested', 'driver_assigned', 'driver_arrived', 'in_progress',
                        'completed', 'cancelled', 'no_driver')),
    pickup_name     TEXT NOT NULL,
    pickup_lat      DOUBLE PRECISION NOT NULL,
    pickup_lng      DOUBLE PRECISION NOT NULL,
    drop_name       TEXT NOT NULL,
    drop_lat        DOUBLE PRECISION NOT NULL,
    drop_lng        DOUBLE PRECISION NOT NULL,
    distance_km     NUMERIC(8,2) NOT NULL,
    duration_min    NUMERIC(8,2) NOT NULL,
    surge           NUMERIC(3,2) NOT NULL DEFAULT 1.00,
    fare_estimate   NUMERIC(10,2) NOT NULL,
    promo_code      TEXT REFERENCES promo_codes (code),
    discount        NUMERIC(10,2) NOT NULL DEFAULT 0,
    fare_final      NUMERIC(10,2),
    commission      NUMERIC(10,2),
    driver_earning  NUMERIC(10,2),
    payment_method  TEXT NOT NULL CHECK (payment_method IN ('wallet', 'cash')),
    payment_status  TEXT NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'refunded', 'waived')),
    pin             TEXT NOT NULL,
    cancel_reason   TEXT,
    cancelled_by    TEXT CHECK (cancelled_by IN ('rider', 'driver', 'admin', 'system')),
    dispatch_attempts INT NOT NULL DEFAULT 0,
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    assigned_at     TIMESTAMPTZ,
    arrived_at      TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ
);
CREATE INDEX trips_rider_idx ON trips (rider_id, requested_at DESC);
CREATE INDEX trips_driver_idx ON trips (driver_id, requested_at DESC);
CREATE INDEX trips_status_idx ON trips (status, requested_at DESC);
-- One active trip per rider and per driver.
CREATE UNIQUE INDEX trips_one_active_rider ON trips (rider_id)
    WHERE status IN ('requested', 'driver_assigned', 'driver_arrived', 'in_progress');
CREATE UNIQUE INDEX trips_one_active_driver ON trips (driver_id)
    WHERE driver_id IS NOT NULL AND status IN ('driver_assigned', 'driver_arrived', 'in_progress');

CREATE TABLE trip_events (
    id          BIGSERIAL PRIMARY KEY,
    trip_id     UUID NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    actor       TEXT NOT NULL,
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
    at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX trip_events_trip_idx ON trip_events (trip_id, at);

CREATE TABLE ride_offers (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id      UUID NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
    driver_id    UUID NOT NULL REFERENCES drivers (user_id) ON DELETE CASCADE,
    status       TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'expired', 'withdrawn')),
    pickup_km    NUMERIC(8,2) NOT NULL,
    offered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL,
    responded_at TIMESTAMPTZ
);
CREATE INDEX ride_offers_driver_idx ON ride_offers (driver_id, status);
CREATE UNIQUE INDEX ride_offers_one_pending ON ride_offers (trip_id) WHERE status = 'pending';

CREATE TABLE ratings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id     UUID NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
    from_user   UUID NOT NULL REFERENCES users (id),
    to_user     UUID NOT NULL REFERENCES users (id),
    stars       INT NOT NULL CHECK (stars BETWEEN 1 AND 5),
    tags        TEXT[] NOT NULL DEFAULT '{}',
    comment     TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trip_id, from_user)
);
CREATE INDEX ratings_to_idx ON ratings (to_user, created_at DESC);
