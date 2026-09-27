package admin

import (
	"context"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

type pgconnTag = pgconn.CommandTag

type txExec struct{ tx pgx.Tx }

func (t txExec) Exec(ctx context.Context, sql string, args ...any) (pgconnTag, error) {
	return t.tx.Exec(ctx, sql, args...)
}

type poolExec struct{ pool *pgxpool.Pool }

func (p poolExec) Exec(ctx context.Context, sql string, args ...any) (pgconnTag, error) {
	return p.pool.Exec(ctx, sql, args...)
}
