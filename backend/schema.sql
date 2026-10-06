-- Future optional authenticated sync; not used by the local-first release.
-- Apply only with an authentication/authorization layer and explicit sync consent.
CREATE TABLE IF NOT EXISTS healthup_sync_records (
    owner_id UUID NOT NULL,
    collection TEXT NOT NULL CHECK (collection IN ('profile','preferences','hydration','weight_entries','moods','completed_tasks','favorites','calendar_events','journey','notification_preferences')),
    record_id UUID NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (owner_id, collection, record_id)
);
CREATE INDEX IF NOT EXISTS healthup_sync_updated ON healthup_sync_records(owner_id, updated_at);
