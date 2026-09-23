// Command platformctl administers the platform's own accounts from the shell.
//
// The console has no screen for this yet, and the first owner of a fresh installation has to exist
// before anyone can sign in. It reuses the control-plane's own password hashing, so an account it
// creates is indistinguishable from one created through the API.
//
//	platformctl create-owner --email you@example.com --name "Your Name" [--password …]
//	platformctl set-role     --email you@example.com --role super_admin|user
//	platformctl set-plan     --email you@example.com --plan free|developer|pro|agency|enterprise
//	platformctl grant-credits --email you@example.com --credits 500000 --reason "founder grant"
//	platformctl list-users   [--limit 50]
//
// DATABASE_URL (or OMNISTACKAI_DATABASE_URL) points at the control-plane's PostgreSQL.
package main

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"flag"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/password"
)

const usage = `platformctl - platform account administration

  create-owner   --email E [--name N] [--password P] [--credits N]   create (or promote) the platform owner
  set-role       --email E --role super_admin|user                   change what an account may do
  set-plan       --email E --plan free|developer|pro|agency|enterprise
  grant-credits  --email E --credits N [--reason R]                  add model credits
  list-users     [--limit N]                                          who exists, with role, plan and balance

The database comes from DATABASE_URL or OMNISTACKAI_DATABASE_URL.
`

var validPlans = map[string]bool{"free": true, "developer": true, "pro": true, "agency": true, "enterprise": true}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprint(os.Stderr, usage)
		os.Exit(2)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := run(ctx, os.Args[1], os.Args[2:]); err != nil {
		fmt.Fprintf(os.Stderr, "platformctl: %v\n", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, command string, args []string) error {
	switch command {
	case "create-owner":
		return createOwner(ctx, args)
	case "set-role":
		return setRole(ctx, args)
	case "set-plan":
		return setPlan(ctx, args)
	case "grant-credits":
		return grantCredits(ctx, args)
	case "list-users":
		return listUsers(ctx, args)
	case "help", "-h", "--help":
		fmt.Print(usage)
		return nil
	default:
		return fmt.Errorf("unknown command %q\n\n%s", command, usage)
	}
}

func connect(ctx context.Context) (*pgxpool.Pool, error) {
	dsn := firstNonEmpty(os.Getenv("DATABASE_URL"), os.Getenv("OMNISTACKAI_DATABASE_URL"))
	if dsn == "" {
		return nil, errors.New("set DATABASE_URL to the control-plane's PostgreSQL")
	}
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, fmt.Errorf("connect: %w", err)
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("the database did not answer: %w", err)
	}
	return pool, nil
}

func createOwner(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("create-owner", flag.ExitOnError)
	email := flags.String("email", "", "the owner's email address")
	name := flags.String("name", "", "the owner's full name")
	pass := flags.String("password", "", "password; a strong one is generated when omitted")
	credits := flags.Int64("credits", 1_000_000, "starting model credits")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if strings.TrimSpace(*email) == "" {
		return errors.New("--email is required")
	}

	plain := *pass
	generated := false
	if plain == "" {
		var err error
		if plain, err = generatePassword(); err != nil {
			return err
		}
		generated = true
	}
	if len([]rune(plain)) < 12 {
		return errors.New("the owner's password must be at least 12 characters")
	}

	hash, err := password.Hash(plain)
	if err != nil {
		return fmt.Errorf("hash the password: %w", err)
	}

	pool, err := connect(ctx)
	if err != nil {
		return err
	}
	defer pool.Close()

	normalized := strings.ToLower(strings.TrimSpace(*email))
	fullName := strings.TrimSpace(*name)
	if fullName == "" {
		fullName = normalized
	}

	var id, role, plan string
	err = pool.QueryRow(ctx, `
		INSERT INTO users (email, password_hash, full_name, role, plan, credit_balance)
		VALUES ($1, $2, $3, 'super_admin', 'enterprise', $4)
		ON CONFLICT (email) DO UPDATE
		   SET password_hash = EXCLUDED.password_hash,
		       full_name     = EXCLUDED.full_name,
		       role          = 'super_admin',
		       plan          = 'enterprise',
		       credit_balance = GREATEST(users.credit_balance, EXCLUDED.credit_balance),
		       updated_at    = now()
		RETURNING id, role, plan`,
		normalized, hash, fullName, *credits,
	).Scan(&id, &role, &plan)
	if err != nil {
		return fmt.Errorf("create the owner: %w", err)
	}

	fmt.Printf("owner ready\n  id       %s\n  email    %s\n  name     %s\n  role     %s\n  plan     %s\n", id, normalized, fullName, role, plan)
	if generated {
		fmt.Printf("  password %s\n\nWrite that password down now; it is not stored anywhere in plain text.\n", plain)
	}
	return nil
}

func setRole(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("set-role", flag.ExitOnError)
	email := flags.String("email", "", "the account to change")
	role := flags.String("role", "", "super_admin or user")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *role != "super_admin" && *role != "user" {
		return errors.New("--role must be super_admin or user")
	}
	return update(ctx, *email, `UPDATE users SET role = $2, updated_at = now() WHERE email = $1 RETURNING id`, *role, "role", *role)
}

func setPlan(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("set-plan", flag.ExitOnError)
	email := flags.String("email", "", "the account to change")
	plan := flags.String("plan", "", "free, developer, pro, agency or enterprise")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if !validPlans[*plan] {
		return errors.New("--plan must be free, developer, pro, agency or enterprise")
	}
	return update(ctx, *email, `UPDATE users SET plan = $2, updated_at = now() WHERE email = $1 RETURNING id`, *plan, "plan", *plan)
}

func grantCredits(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("grant-credits", flag.ExitOnError)
	email := flags.String("email", "", "the account to credit")
	credits := flags.Int64("credits", 0, "how many credits to add")
	reason := flags.String("reason", "manual grant", "why, for the ledger")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *credits <= 0 {
		return errors.New("--credits must be positive")
	}

	pool, err := connect(ctx)
	if err != nil {
		return err
	}
	defer pool.Close()

	normalized := strings.ToLower(strings.TrimSpace(*email))
	tx, err := pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback(ctx) }()

	var id string
	var balance int64
	err = tx.QueryRow(ctx,
		`UPDATE users SET credit_balance = credit_balance + $2, updated_at = now()
		  WHERE email = $1 RETURNING id, credit_balance`, normalized, *credits).Scan(&id, &balance)
	if err != nil {
		return fmt.Errorf("no account with email %s: %w", normalized, err)
	}

	// The ledger is the record; the balance column is its running total.
	if _, err = tx.Exec(ctx,
		`INSERT INTO credit_ledger (user_id, delta, reason, balance_after) VALUES ($1, $2, $3, $4)`,
		id, *credits, *reason, balance); err != nil {
		return fmt.Errorf("write the ledger entry: %w", err)
	}
	if err := tx.Commit(ctx); err != nil {
		return err
	}

	fmt.Printf("credited %s with %d; balance is now %d\n", normalized, *credits, balance)
	return nil
}

func listUsers(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("list-users", flag.ExitOnError)
	limit := flags.Int("limit", 50, "how many to show")
	if err := flags.Parse(args); err != nil {
		return err
	}

	pool, err := connect(ctx)
	if err != nil {
		return err
	}
	defer pool.Close()

	rows, err := pool.Query(ctx,
		`SELECT email, COALESCE(NULLIF(full_name, ''), '-'), role, plan, credit_balance, created_at
		   FROM users ORDER BY created_at ASC LIMIT $1`, *limit)
	if err != nil {
		return err
	}
	defer rows.Close()

	fmt.Printf("%-36s %-24s %-12s %-11s %12s  %s\n", "EMAIL", "NAME", "ROLE", "PLAN", "CREDITS", "CREATED")
	count := 0
	for rows.Next() {
		var email, name, role, plan string
		var credits int64
		var created time.Time
		if err := rows.Scan(&email, &name, &role, &plan, &credits, &created); err != nil {
			return err
		}
		fmt.Printf("%-36s %-24s %-12s %-11s %12d  %s\n", email, name, role, plan, credits, created.Format("2006-01-02"))
		count++
	}
	if err := rows.Err(); err != nil {
		return err
	}
	if count == 0 {
		fmt.Println("(no accounts yet — create one with: platformctl create-owner --email you@example.com)")
	}
	return nil
}

func update(ctx context.Context, email, sql, value, label, shown string) error {
	if strings.TrimSpace(email) == "" {
		return errors.New("--email is required")
	}
	pool, err := connect(ctx)
	if err != nil {
		return err
	}
	defer pool.Close()

	normalized := strings.ToLower(strings.TrimSpace(email))
	var id string
	if err := pool.QueryRow(ctx, sql, normalized, value).Scan(&id); err != nil {
		return fmt.Errorf("no account with email %s: %w", normalized, err)
	}
	fmt.Printf("%s is now %s=%s\n", normalized, label, shown)
	return nil
}

// generatePassword returns 24 URL-safe characters from crypto/rand.
func generatePassword() (string, error) {
	raw := make([]byte, 18)
	if _, err := rand.Read(raw); err != nil {
		return "", fmt.Errorf("generate a password: %w", err)
	}
	return base64.RawURLEncoding.EncodeToString(raw), nil
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}
