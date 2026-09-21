package migrations

import (
	"strings"
	"testing"
)

func TestStatementsDropsTransactionControl(t *testing.T) {
	sql := "BEGIN;\n\nCREATE TABLE IF NOT EXISTS example (id INT);\n\nINSERT INTO example (id) VALUES (1);\n\nCOMMIT;\n"

	got := statements(sql)

	want := []string{
		"CREATE TABLE IF NOT EXISTS example (id INT)",
		"INSERT INTO example (id) VALUES (1)",
	}
	if len(got) != len(want) {
		t.Fatalf("statements() = %#v, want %#v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("statements()[%d] = %q, want %q", i, got[i], want[i])
		}
	}
}

func TestStatementsIgnoresEmptySegments(t *testing.T) {
	got := statements("  ;\n;\n\t;")
	if len(got) != 0 {
		t.Fatalf("statements() = %#v, want empty", got)
	}
}

func TestStatementsIsCaseInsensitiveForTransactionControl(t *testing.T) {
	got := statements("begin;\nSELECT 1;\ncommit;")
	if len(got) != 1 || got[0] != "SELECT 1" {
		t.Fatalf("statements() = %#v, want [\"SELECT 1\"]", got)
	}
}

func TestLoadMigrationsFindsEmbeddedFilesInAscendingVersionOrder(t *testing.T) {
	loaded, err := loadMigrations()
	if err != nil {
		t.Fatalf("loadMigrations() error = %v", err)
	}
	if len(loaded) < 2 {
		t.Fatalf("loadMigrations() = %d migrations, want at least 2", len(loaded))
	}
	for i := 1; i < len(loaded); i++ {
		if loaded[i-1].version >= loaded[i].version {
			t.Fatalf("loadMigrations() not sorted ascending: %d then %d", loaded[i-1].version, loaded[i].version)
		}
	}
	if loaded[0].version != 1 {
		t.Fatalf("loadMigrations()[0].version = %d, want 1", loaded[0].version)
	}
	foundVersion2 := false
	for _, m := range loaded {
		if m.version == 2 {
			foundVersion2 = true
			if len(statements(m.sql)) == 0 {
				t.Fatalf("migration 2 (%s) parsed to zero statements", m.name)
			}
		}
	}
	if !foundVersion2 {
		t.Fatalf("loadMigrations() did not find version 2 (000002_users_auth_billing.up.sql)")
	}
}

// TestNoMigrationCommentContainsASemicolon guards the runner's one real constraint: statements()
// splits on every ';', including inside `--` comments, so a comment with a semicolon turns its
// tail into a bogus SQL statement and the control-plane cannot start (hit in R-518).
func TestNoMigrationCommentContainsASemicolon(t *testing.T) {
	loaded, err := loadMigrations()
	if err != nil {
		t.Fatalf("loadMigrations() error = %v", err)
	}
	for _, m := range loaded {
		for lineNumber, line := range strings.Split(m.sql, "\n") {
			if idx := strings.Index(line, "--"); idx >= 0 && strings.Contains(line[idx:], ";") {
				t.Errorf("%s:%d: a comment contains ';', which the statement splitter treats as SQL: %q",
					m.name, lineNumber+1, strings.TrimSpace(line))
			}
		}
	}
}
