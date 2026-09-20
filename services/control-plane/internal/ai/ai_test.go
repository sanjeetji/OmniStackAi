package ai

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/crypto"
)

type mockAIStore struct {
	available bool
	keys      map[string]map[string]string // userID -> providerID -> key
	labels    map[string]map[string]string
	models    map[string]ProjectModelConfig // projectID -> config
	calls     []ModelCall
}

func newMockAIStore() *mockAIStore {
	return &mockAIStore{
		available: true,
		keys:      make(map[string]map[string]string),
		labels:    make(map[string]map[string]string),
		models:    make(map[string]ProjectModelConfig),
	}
}

func (m *mockAIStore) IsAvailable() bool { return m.available }

func (m *mockAIStore) ListUserKeys(_ context.Context, userID string) ([]KeyMetadata, error) {
	now := time.Now()
	var res []KeyMetadata
	if uKeys, ok := m.keys[userID]; ok {
		for pID := range uKeys {
			res = append(res, KeyMetadata{
				ProviderID: pID,
				Label:      m.labels[userID][pID],
				CreatedAt:  now,
			})
		}
	}
	return res, nil
}

func (m *mockAIStore) GetUserKey(_ context.Context, userID, providerID string) (string, string, error) {
	if !m.available {
		return "", "", ErrKeyNotConfigured
	}
	if uKeys, ok := m.keys[userID]; ok {
		if k, ok := uKeys[providerID]; ok {
			return k, m.labels[userID][providerID], nil
		}
	}
	return "", "", ErrKeyNotFound
}

func (m *mockAIStore) SetUserKey(_ context.Context, userID, providerID, apiKey, label string) error {
	if !m.available {
		return ErrKeyNotConfigured
	}
	if m.keys[userID] == nil {
		m.keys[userID] = make(map[string]string)
		m.labels[userID] = make(map[string]string)
	}
	m.keys[userID][providerID] = apiKey
	m.labels[userID][providerID] = label
	return nil
}

func (m *mockAIStore) DeleteUserKey(_ context.Context, userID, providerID string) error {
	if uKeys, ok := m.keys[userID]; ok {
		if _, ok := uKeys[providerID]; ok {
			delete(uKeys, providerID)
			delete(m.labels[userID], providerID)
			return nil
		}
	}
	return ErrKeyNotFound
}

func (m *mockAIStore) RecordModelCalls(_ context.Context, calls []ModelCall) error {
	m.calls = append(m.calls, calls...)
	return nil
}

func (m *mockAIStore) GetProjectUsage(_ context.Context, _, projectID string, days int) (*ProjectUsageReport, error) {
	return &ProjectUsageReport{
		ProjectID: projectID,
		RangeDays: days,
		Totals: UsageTotals{
			TotalCalls:      int64(len(m.calls)),
			SuccessfulCalls: int64(len(m.calls)),
			CostMicrosUSD:   1000,
			CreditsSpent:    1,
		},
		ByDay: []DailyUsage{
			{Date: "2026-09-20", Calls: int64(len(m.calls)), CostMicrosUSD: 1000, CreditsSpent: 1},
		},
		ByPurpose: map[string]PurposeUsage{
			"build": {Purpose: "build", Calls: int64(len(m.calls)), CostMicrosUSD: 1000, CreditsSpent: 1},
		},
	}, nil
}

func (m *mockAIStore) GetAccountUsage(_ context.Context, _ string, days int) (*AccountUsageReport, error) {
	return &AccountUsageReport{
		RangeDays: days,
		Totals: UsageTotals{
			TotalCalls:    int64(len(m.calls)),
			CostMicrosUSD: 1000,
			CreditsSpent:  1,
		},
		CreditBalance: 100,
	}, nil
}

func (m *mockAIStore) GetProjectModel(_ context.Context, _, projectID string) (*ProjectModelConfig, error) {
	if cfg, ok := m.models[projectID]; ok {
		return &cfg, nil
	}
	return &ProjectModelConfig{ProjectID: projectID}, nil
}

func (m *mockAIStore) SetProjectModel(_ context.Context, _, projectID, providerID, modelID string) error {
	m.models[projectID] = ProjectModelConfig{
		ProjectID:       projectID,
		ModelProviderID: providerID,
		ModelID:         modelID,
	}
	return nil
}

type mockAuthStore struct {
	user auth.User
}

func (m *mockAuthStore) CreateUser(_ context.Context, _, _, _ string, _ int64) (auth.User, error) {
	return m.user, nil
}

func (m *mockAuthStore) FindUserByEmail(_ context.Context, _ string) (auth.User, string, error) {
	return m.user, "", nil
}

func (m *mockAuthStore) FindUserByID(_ context.Context, _ string) (auth.User, error) {
	return m.user, nil
}

func (m *mockAuthStore) CreateSession(_ context.Context, _, _ string, _ time.Time) error {
	return nil
}

func (m *mockAuthStore) FindUserBySessionToken(_ context.Context, _ string) (auth.User, error) {
	return m.user, nil
}

func (m *mockAuthStore) DeleteSession(_ context.Context, _ string) error {
	return nil
}

func TestCryptoAADProtection(t *testing.T) {
	masterKey := make([]byte, 32)
	_, _ = rand.Read(masterKey)

	plainKey := "sk-test-secret-api-key-12345"
	userA := "user-aaa"
	userB := "user-bbb"
	provider := "openai"

	ciphertext, err := crypto.Encrypt(masterKey, []byte(plainKey), aad(userA, provider))
	if err != nil {
		t.Fatalf("encrypt failed: %v", err)
	}

	// Decrypt with correct user should succeed
	decrypted, err := crypto.Decrypt(masterKey, ciphertext, aad(userA, provider))
	if err != nil {
		t.Fatalf("decrypt with userA failed: %v", err)
	}
	if string(decrypted) != plainKey {
		t.Errorf("decrypted = %q, want %q", string(decrypted), plainKey)
	}

	// Decrypt with different user should fail (AAD mismatch)
	_, err = crypto.Decrypt(masterKey, ciphertext, aad(userB, provider))
	if err == nil {
		t.Fatal("expected error decrypting with wrong AAD (userB), got nil")
	}
}

func TestAIHandlers(t *testing.T) {
	mockStore := newMockAIStore()
	mockAuth := &mockAuthStore{
		user: auth.User{ID: "test-user-1", Name: "Test User", Email: "test@example.com"},
	}

	mux := http.NewServeMux()
	Register(mux, Deps{
		AuthStore: mockAuth,
		AIStore:   mockStore,
	})

	// 1. Set BYOK Key
	setBody := `{"api_key":"sk-test-openai-key-abc","label":"My OpenAI Key"}`
	req := httptest.NewRequest(http.MethodPut, "/ai/keys/openai", bytes.NewReader([]byte(setBody)))
	req.Header.Set("Authorization", "Bearer valid-token")
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("PUT /ai/keys/openai status = %d, want %d", w.Code, http.StatusOK)
	}

	// 2. Get BYOK Key - MUST NEVER RETURN KEY VALUE
	req = httptest.NewRequest(http.MethodGet, "/ai/keys/openai", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("GET /ai/keys/openai status = %d, want %d", w.Code, http.StatusOK)
	}
	respBody := w.Body.String()
	if bytes.Contains([]byte(respBody), []byte("sk-test-openai-key-abc")) {
		t.Fatalf("CRITICAL SECURITY LEAK: GET /ai/keys/openai returned plaintext key: %s", respBody)
	}

	var meta KeyMetadata
	if err := json.Unmarshal(w.Body.Bytes(), &meta); err != nil {
		t.Fatalf("decode key metadata: %v", err)
	}
	if meta.ProviderID != "openai" || meta.Label != "My OpenAI Key" {
		t.Errorf("unexpected metadata: %+v", meta)
	}

	// 3. Test BYOK Key
	req = httptest.NewRequest(http.MethodPost, "/ai/keys/openai/test", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("POST /ai/keys/openai/test status = %d, want %d", w.Code, http.StatusOK)
	}

	// 4. Set Project Model Pinning
	modelBody := `{"model_provider_id":"openai","model_id":"gpt-4o"}`
	req = httptest.NewRequest(http.MethodPut, "/projects/proj-123/model", bytes.NewReader([]byte(modelBody)))
	req.Header.Set("Authorization", "Bearer valid-token")
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("PUT /projects/proj-123/model status = %d, want %d", w.Code, http.StatusOK)
	}

	// 5. Get Project Model Pinning
	req = httptest.NewRequest(http.MethodGet, "/projects/proj-123/model", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("GET /projects/proj-123/model status = %d, want %d", w.Code, http.StatusOK)
	}
	var pModel ProjectModelConfig
	if err := json.Unmarshal(w.Body.Bytes(), &pModel); err != nil {
		t.Fatalf("decode project model: %v", err)
	}
	if pModel.ModelProviderID != "openai" || pModel.ModelID != "gpt-4o" {
		t.Errorf("unexpected project model: %+v", pModel)
	}

	// 6. Delete Key
	req = httptest.NewRequest(http.MethodDelete, "/ai/keys/openai", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("DELETE /ai/keys/openai status = %d, want %d", w.Code, http.StatusOK)
	}
}
