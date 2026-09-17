// Package migrations embeds the control-plane's SQL migration files and applies them.
//
// docker-entrypoint-initdb.d (the fast path wired in infra/environments/local/compose.yaml) only
// runs against a brand-new, empty Postgres volume — a developer's existing local volume never
// sees a later migration file just by restarting the container. Every migration in this
// directory is written idempotently (IF NOT EXISTS / ON CONFLICT DO NOTHING), so Apply can safely
// replay all of them, in order, on every control-plane boot: a fresh volume is a no-op past what
// docker-entrypoint-initdb.d already did, and an existing volume gets caught up.
package migrations

import (
	"context"
	"embed"
	"fmt"
	"io/fs"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
)

//go:embed *.up.sql
var upFiles embed.FS

var versionPattern = regexp.MustCompile(`^(\d+)_.*\.up\.sql$`)

type migration struct {
	version int64
	name    string
	sql     string
}

// Apply runs every embedded migration, in ascending version order, each inside its own
// transaction. It is safe to call on every process start.
func Apply(ctx context.Context, pool *pgxpool.Pool) error {
	pending, err := loadMigrations()
	if err != nil {
		return err
	}
	for _, m := range pending {
		if err := applyOne(ctx, pool, m); err != nil {
			return fmt.Errorf("migration %d (%s): %w", m.version, m.name, err)
		}
	}
	return nil
}

func loadMigrations() ([]migration, error) {
	entries, err := fs.ReadDir(upFiles, ".")
	if err != nil {
		return nil, err
	}

	loaded := make([]migration, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		match := versionPattern.FindStringSubmatch(entry.Name())
		if match == nil {
			continue
		}
		version, err := strconv.ParseInt(match[1], 10, 64)
		if err != nil {
			return nil, fmt.Errorf("invalid migration filename %q: %w", entry.Name(), err)
		}
		contents, err := upFiles.ReadFile(entry.Name())
		if err != nil {
			return nil, err
		}
		loaded = append(loaded, migration{version: version, name: entry.Name(), sql: string(contents)})
	}

	sort.Slice(loaded, func(i, j int) bool { return loaded[i].version < loaded[j].version })
	return loaded, nil
}

func applyOne(ctx context.Context, pool *pgxpool.Pool, m migration) error {
	tx, err := pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback(ctx) }()

	for _, stmt := range statements(m.sql) {
		if _, err := tx.Exec(ctx, stmt); err != nil {
			return err
		}
	}
	return tx.Commit(ctx)
}

// statements splits a migration file into individual executable SQL statements, dropping the
// transaction-control BEGIN/COMMIT lines (the transaction itself is managed in Go by applyOne so
// that pgx never has to execute more than one statement per call). This is a plain split on ';'
// rather than a full SQL parser because every migration in this directory is hand-written by this
// project and deliberately avoids semicolons inside string literals.
func statements(sql string) []string {
	var out []string
	for _, raw := range strings.Split(sql, ";") {
		stmt := strings.TrimSpace(raw)
		if stmt == "" {
			continue
		}
		if strings.EqualFold(stmt, "BEGIN") || strings.EqualFold(stmt, "COMMIT") {
			continue
		}
		out = append(out, stmt)
	}
	return out
}
