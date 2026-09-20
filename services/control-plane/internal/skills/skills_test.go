package skills

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

func TestValidateSkillName(t *testing.T) {
	validNames := []string{
		"design-system",
		"coding-standards",
		"domain-rules",
		"copy-and-tone",
		"react19",
		"v2",
		"a",
		"skill-1-test",
	}
	for _, name := range validNames {
		if err := ValidateSkillName(name); err != nil {
			t.Errorf("expected valid name %q, got error: %v", name, err)
		}
	}

	invalidNames := []string{
		"Design-System", // uppercase
		"design_system", // underscore
		"-leading",      // leading hyphen
		"trailing-",     // trailing hyphen
		"double--dash",  // double hyphen
		"with spaces",   // spaces
		"",              // empty
		"special!char",  // special char
	}
	for _, name := range invalidNames {
		if err := ValidateSkillName(name); err == nil {
			t.Errorf("expected invalid name %q to fail, but passed", name)
		}
	}
}

// MockStore implements Store for testing
type MockStore struct {
	skills    map[string]Skill
	knowledge map[string]string
	attached  map[string][]string // projectID -> []skillID
}

func NewMockStore() *MockStore {
	return &MockStore{
		skills:    make(map[string]Skill),
		knowledge: make(map[string]string),
		attached:  make(map[string][]string),
	}
}

func (m *MockStore) ListSkills(ctx context.Context, userID string) ([]Skill, error) {
	var list []Skill
	for _, s := range m.skills {
		if s.UserID == userID {
			list = append(list, s)
		}
	}
	return list, nil
}

func (m *MockStore) CreateSkill(ctx context.Context, userID, name, title, description, body string, isDefault bool) (*Skill, error) {
	if err := ValidateSkillName(name); err != nil {
		return nil, err
	}
	if strings.TrimSpace(title) == "" {
		return nil, ErrEmptySkillTitle
	}
	if len(body) > 8192 {
		return nil, ErrSkillBodyTooLarge
	}
	for _, s := range m.skills {
		if s.UserID == userID && s.Name == name {
			return nil, ErrSkillAlreadyExists
		}
	}
	sk := Skill{
		ID:          "skill-" + name,
		UserID:      userID,
		Name:        name,
		Title:       title,
		Description: description,
		Body:        body,
		IsDefault:   isDefault,
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}
	m.skills[sk.ID] = sk
	return &sk, nil
}

func (m *MockStore) GetSkill(ctx context.Context, userID, skillID string) (*Skill, error) {
	sk, ok := m.skills[skillID]
	if !ok || sk.UserID != userID {
		return nil, ErrSkillNotFound
	}
	return &sk, nil
}

func (m *MockStore) UpdateSkill(ctx context.Context, userID, skillID, title, description, body string, isDefault bool) (*Skill, error) {
	sk, ok := m.skills[skillID]
	if !ok || sk.UserID != userID {
		return nil, ErrSkillNotFound
	}
	if strings.TrimSpace(title) == "" {
		return nil, ErrEmptySkillTitle
	}
	if len(body) > 8192 {
		return nil, ErrSkillBodyTooLarge
	}
	sk.Title = title
	sk.Description = description
	sk.Body = body
	sk.IsDefault = isDefault
	sk.UpdatedAt = time.Now()
	m.skills[skillID] = sk
	return &sk, nil
}

func (m *MockStore) DeleteSkill(ctx context.Context, userID, skillID string) error {
	sk, ok := m.skills[skillID]
	if !ok || sk.UserID != userID {
		return ErrSkillNotFound
	}
	delete(m.skills, skillID)
	return nil
}

func (m *MockStore) GetProjectKnowledge(ctx context.Context, userID, projectID string) (*ProjectKnowledge, error) {
	k, ok := m.knowledge[projectID]
	if !ok {
		return &ProjectKnowledge{Knowledge: "", UpdatedAt: time.Now()}, nil
	}
	return &ProjectKnowledge{Knowledge: k, UpdatedAt: time.Now()}, nil
}

func (m *MockStore) UpdateProjectKnowledge(ctx context.Context, userID, projectID, knowledge string) (*ProjectKnowledge, error) {
	if len(knowledge) > 16384 {
		return nil, ErrKnowledgeTooLarge
	}
	m.knowledge[projectID] = knowledge
	return &ProjectKnowledge{Knowledge: knowledge, UpdatedAt: time.Now()}, nil
}

func (m *MockStore) ListProjectSkills(ctx context.Context, userID, projectID string) ([]Skill, error) {
	ids := m.attached[projectID]
	var res []Skill
	for _, id := range ids {
		if sk, ok := m.skills[id]; ok && sk.UserID == userID {
			res = append(res, sk)
		}
	}
	return res, nil
}

func (m *MockStore) AttachProjectSkill(ctx context.Context, userID, projectID, skillID string) error {
	sk, ok := m.skills[skillID]
	if !ok || sk.UserID != userID {
		return ErrSkillNotFound
	}
	m.attached[projectID] = append(m.attached[projectID], skillID)
	return nil
}

func (m *MockStore) DetachProjectSkill(ctx context.Context, userID, projectID, skillID string) error {
	ids := m.attached[projectID]
	var filtered []string
	for _, id := range ids {
		if id != skillID {
			filtered = append(filtered, id)
		}
	}
	m.attached[projectID] = filtered
	return nil
}

func (m *MockStore) ResolveContext(ctx context.Context, userID, projectID string, mentionSkillNames []string) (*ContextBlock, error) {
	pk, _ := m.GetProjectKnowledge(ctx, userID, projectID)
	all, _ := m.ListSkills(ctx, userID)
	byName := make(map[string]Skill)
	var defaults []Skill
	for _, s := range all {
		byName[s.Name] = s
		if s.IsDefault {
			defaults = append(defaults, s)
		}
	}

	attached, _ := m.ListProjectSkills(ctx, userID, projectID)

	seen := make(map[string]bool)
	var resolved []SkillPayload

	// 1. Mentions
	for _, name := range mentionSkillNames {
		clean := strings.TrimPrefix(strings.ToLower(strings.TrimSpace(name)), "@")
		if clean != "" && !seen[clean] {
			if sk, ok := byName[clean]; ok {
				seen[clean] = true
				resolved = append(resolved, SkillPayload{Name: sk.Name, Body: sk.Body})
			}
		}
	}

	// 2. Attached
	for _, sk := range attached {
		if !seen[sk.Name] {
			seen[sk.Name] = true
			resolved = append(resolved, SkillPayload{Name: sk.Name, Body: sk.Body})
		}
	}

	// 3. Defaults
	for _, sk := range defaults {
		if !seen[sk.Name] {
			seen[sk.Name] = true
			resolved = append(resolved, SkillPayload{Name: sk.Name, Body: sk.Body})
		}
	}

	return &ContextBlock{
		Knowledge: pk.Knowledge,
		Skills:    resolved,
	}, nil
}

func testHashToken(raw string) string {
	sum := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(sum[:])
}

type MockAuthStore struct {
	sessions map[string]auth.User
}

func (a *MockAuthStore) CreateUser(ctx context.Context, email, passwordHash, name string, startingCredits int64) (auth.User, error) {
	panic("unused")
}
func (a *MockAuthStore) FindUserByEmail(ctx context.Context, email string) (auth.User, string, error) {
	panic("unused")
}
func (a *MockAuthStore) FindUserByID(ctx context.Context, id string) (auth.User, error) {
	panic("unused")
}
func (a *MockAuthStore) CreateSession(ctx context.Context, tokenHash, userID string, expiresAt time.Time) error {
	panic("unused")
}
func (a *MockAuthStore) FindUserBySessionToken(ctx context.Context, tokenHash string) (auth.User, error) {
	if u, ok := a.sessions[tokenHash]; ok {
		return u, nil
	}
	return auth.User{}, auth.ErrSessionNotFound
}
func (a *MockAuthStore) DeleteSession(ctx context.Context, tokenHash string) error {
	panic("unused")
}

func TestSkillsHandlersAndIsolation(t *testing.T) {
	store := NewMockStore()
	user1 := auth.User{ID: "user-1", Email: "u1@example.com"}
	user2 := auth.User{ID: "user-2", Email: "u2@example.com"}
	authStore := &MockAuthStore{
		sessions: map[string]auth.User{
			testHashToken("tok-1"): user1,
			testHashToken("tok-2"): user2,
		},
	}

	mux := http.NewServeMux()
	Register(mux, Deps{
		AuthStore:  authStore,
		SkillStore: store,
	})

	// 1. Create skill as User 1
	bodyJSON, _ := json.Marshal(CreateSkillRequest{
		Name:        "design-system",
		Title:       "Design System",
		Description: "Use Tailwind and shadcn",
		Body:        "Always use OKLCH colors and dark mode.",
		IsDefault:   true,
	})
	req := httptest.NewRequest("POST", "/skills", bytes.NewReader(bodyJSON))
	req.Header.Set("Authorization", "Bearer tok-1")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("expected 201 Created, got %d: %s", rec.Code, rec.Body.String())
	}
	var created Skill
	if err := json.NewDecoder(rec.Body).Decode(&created); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if created.Name != "design-system" || !created.IsDefault {
		t.Fatalf("unexpected skill created: %+v", created)
	}

	// 2. User 2 cannot access User 1's skill
	req = httptest.NewRequest("GET", "/skills/"+created.ID, nil)
	req.Header.Set("Authorization", "Bearer tok-2")
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 for foreign user, got %d", rec.Code)
	}

	// 3. User 1 can update knowledge on their project
	kJSON, _ := json.Marshal(UpdateKnowledgeRequest{
		Knowledge: "Target audience is Indian retail merchants.",
	})
	req = httptest.NewRequest("PUT", "/projects/proj-1/knowledge", bytes.NewReader(kJSON))
	req.Header.Set("Authorization", "Bearer tok-1")
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d", rec.Code)
	}

	// 4. Resolve context for build
	// Add another skill for user 1 (not default)
	_, _ = store.CreateSkill(context.Background(), "user-1", "backend-rules", "Backend Rules", "", "Use Go and Postgres", false)
	// Mention backend-rules explicitly
	ctxBlock, err := store.ResolveContext(context.Background(), "user-1", "proj-1", []string{"backend-rules"})
	if err != nil {
		t.Fatalf("resolve context error: %v", err)
	}
	if ctxBlock.Knowledge != "Target audience is Indian retail merchants." {
		t.Fatalf("unexpected knowledge: %s", ctxBlock.Knowledge)
	}
	// Resolved skills must have backend-rules (mentioned) first, then design-system (default)
	if len(ctxBlock.Skills) != 2 {
		t.Fatalf("expected 2 resolved skills, got %d", len(ctxBlock.Skills))
	}
	if ctxBlock.Skills[0].Name != "backend-rules" {
		t.Errorf("expected mentioned skill 'backend-rules' first, got %s", ctxBlock.Skills[0].Name)
	}
	if ctxBlock.Skills[1].Name != "design-system" {
		t.Errorf("expected default skill 'design-system' second, got %s", ctxBlock.Skills[1].Name)
	}
}
