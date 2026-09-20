package payments

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/secrets"
)

type mockPaymentsStore struct {
	gateways map[string]string
}

func newMockPaymentsStore() *mockPaymentsStore {
	return &mockPaymentsStore{gateways: make(map[string]string)}
}

func (m *mockPaymentsStore) GetPaymentGateway(ctx context.Context, projectID, userID string) (string, error) {
	return m.gateways[projectID], nil
}

func (m *mockPaymentsStore) SetPaymentGateway(ctx context.Context, projectID, userID, gateway string) error {
	if gateway != "stripe" && gateway != "razorpay" {
		return ErrInvalidGateway
	}
	m.gateways[projectID] = gateway
	return nil
}

func (m *mockPaymentsStore) ClearPaymentGateway(ctx context.Context, projectID, userID string) error {
	delete(m.gateways, projectID)
	return nil
}

type mockAuthStore struct {
	user auth.User
	err  error
}

func (m mockAuthStore) CreateUser(context.Context, string, string, string, int64) (auth.User, error) {
	return m.user, m.err
}
func (m mockAuthStore) FindUserByEmail(context.Context, string) (auth.User, string, error) {
	return m.user, "hash", m.err
}
func (m mockAuthStore) FindUserByID(context.Context, string) (auth.User, error) {
	return m.user, m.err
}
func (m mockAuthStore) CreateSession(context.Context, string, string, time.Time) error {
	return m.err
}
func (m mockAuthStore) FindUserBySessionToken(context.Context, string) (auth.User, error) {
	if m.err != nil {
		return auth.User{}, m.err
	}
	return m.user, nil
}
func (m mockAuthStore) DeleteSession(context.Context, string) error {
	return m.err
}

type mockProjectStore struct {
	project projects.Project
	err     error
}

func (m mockProjectStore) CreateProject(ctx context.Context, userID, name, desc string) (projects.Project, error) {
	return m.project, m.err
}
func (m mockProjectStore) ListProjects(ctx context.Context, userID, status string, limit int) ([]projects.Project, error) {
	return []projects.Project{m.project}, m.err
}
func (m mockProjectStore) GetProject(ctx context.Context, id, userID string) (projects.Project, error) {
	if m.err != nil {
		return projects.Project{}, m.err
	}
	return m.project, nil
}
func (m mockProjectStore) UpdateProject(ctx context.Context, id, userID string, name, desc *string) (projects.Project, error) {
	return m.project, m.err
}
func (m mockProjectStore) UpdateProjectBuildResult(ctx context.Context, id, userID, name, prompt, commitSHA string, entities json.RawMessage, fileCount int, messageDelta int) error {
	return m.err
}
func (m mockProjectStore) DebitProjectCredits(ctx context.Context, userID, projectID string, requested int64, reason string) (int64, int64, error) {
	return 0, 0, m.err
}
func (m mockProjectStore) ArchiveProject(ctx context.Context, id, userID string) error {
	return m.err
}
func (m mockProjectStore) DeleteProject(ctx context.Context, id, userID string) error {
	return m.err
}
func (m mockProjectStore) TouchProjectOpened(ctx context.Context, id, userID string) error {
	return m.err
}

type mockSecretsStore struct {
	secrets []secrets.SecretMetadata
}

func (m *mockSecretsStore) ListSecrets(ctx context.Context, projectID, userID string) ([]secrets.SecretMetadata, error) {
	return m.secrets, nil
}
func (m *mockSecretsStore) SetSecret(ctx context.Context, projectID, userID, key, value, description string) (*secrets.SecretMetadata, error) {
	return nil, nil
}
func (m *mockSecretsStore) DeleteSecret(ctx context.Context, projectID, userID, key string) error {
	return nil
}
func (m *mockSecretsStore) RevealSecret(ctx context.Context, projectID, userID, key string) (string, error) {
	return "", nil
}
func (m *mockSecretsStore) ForProject(ctx context.Context, projectID string) (map[string]string, error) {
	return nil, nil
}
func (m *mockSecretsStore) IsAvailable() bool {
	return true
}

func TestPaymentsEndpoints(t *testing.T) {
	paymentsStore := newMockPaymentsStore()
	authStore := mockAuthStore{user: auth.User{ID: "user-1", Email: "test@example.com"}}
	projStore := mockProjectStore{project: projects.Project{ID: "proj-1", UserID: "user-1", Name: "My Shop"}}
	secStore := &mockSecretsStore{
		secrets: []secrets.SecretMetadata{
			{Key: "STRIPE_SECRET_KEY", UpdatedAt: time.Now()},
		},
	}

	mux := http.NewServeMux()
	Register(mux, Deps{
		AuthStore:     authStore,
		ProjectStore:  projStore,
		PaymentsStore: paymentsStore,
		SecretsStore:  secStore,
	})

	// 1. GET /projects/proj-1/payments when no gateway is configured
	req := httptest.NewRequest(http.MethodGet, "/projects/proj-1/payments", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"payment_gateway":""`) {
		t.Errorf("expected empty payment gateway, got %s", rec.Body.String())
	}

	// 2. PUT /projects/proj-1/payments enabling Stripe
	body := strings.NewReader(`{"gateway":"stripe"}`)
	reqPut := httptest.NewRequest(http.MethodPut, "/projects/proj-1/payments", body)
	reqPut.Header.Set("Authorization", "Bearer valid-token")
	reqPut.Header.Set("Content-Type", "application/json")
	recPut := httptest.NewRecorder()
	mux.ServeHTTP(recPut, reqPut)

	if recPut.Code != http.StatusOK {
		t.Fatalf("expected 200 on PUT, got %d: %s", recPut.Code, recPut.Body.String())
	}

	// 3. GET /projects/proj-1/payments after enabling Stripe
	reqGet := httptest.NewRequest(http.MethodGet, "/projects/proj-1/payments", nil)
	reqGet.Header.Set("Authorization", "Bearer valid-token")
	recGet := httptest.NewRecorder()
	mux.ServeHTTP(recGet, reqGet)

	if recGet.Code != http.StatusOK {
		t.Fatalf("expected 200 on GET, got %d", recGet.Code)
	}
	bodyStr := recGet.Body.String()
	if !strings.Contains(bodyStr, `"payment_gateway":"stripe"`) {
		t.Errorf("expected payment_gateway stripe, got %s", bodyStr)
	}
	if !strings.Contains(bodyStr, `"key":"STRIPE_SECRET_KEY"`) || !strings.Contains(bodyStr, `"status":"set"`) {
		t.Errorf("expected STRIPE_SECRET_KEY to be marked set, got %s", bodyStr)
	}
	if !strings.Contains(bodyStr, `"key":"STRIPE_WEBHOOK_SECRET"`) || !strings.Contains(bodyStr, `"status":"not_set"`) {
		t.Errorf("expected STRIPE_WEBHOOK_SECRET to be marked not_set, got %s", bodyStr)
	}

	// 4. DELETE /projects/proj-1/payments
	reqDel := httptest.NewRequest(http.MethodDelete, "/projects/proj-1/payments", nil)
	reqDel.Header.Set("Authorization", "Bearer valid-token")
	recDel := httptest.NewRecorder()
	mux.ServeHTTP(recDel, reqDel)

	if recDel.Code != http.StatusOK {
		t.Fatalf("expected 200 on DELETE, got %d", recDel.Code)
	}

	// 5. Verify invalid gateway rejected with 400
	reqBad := httptest.NewRequest(http.MethodPut, "/projects/proj-1/payments", strings.NewReader(`{"gateway":"paypal"}`))
	reqBad.Header.Set("Authorization", "Bearer valid-token")
	recBad := httptest.NewRecorder()
	mux.ServeHTTP(recBad, reqBad)

	if recBad.Code != http.StatusBadRequest {
		t.Errorf("expected 400 for unsupported gateway, got %d", recBad.Code)
	}
}
