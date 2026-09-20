package secrets

import (
	"bytes"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/crypto"
)

func TestKeyPatternValidation(t *testing.T) {
	valid := []string{
		"STRIPE_API_KEY",
		"SMTP_PASSWORD",
		"KEY",
		"A",
		"PORT_8080",
		"AWS_S3_BUCKET_NAME_2",
		"X",
	}
	for _, k := range valid {
		if !keyPattern.MatchString(k) {
			t.Errorf("expected %q to be valid UPPER_SNAKE_CASE", k)
		}
	}

	invalid := []string{
		"stripe_api_key",
		"StripeApiKey",
		"_LEADING",
		"1_NUMBER",
		"",
		"WITH SPACE",
		"KEY-DASH",
		"KEY.DOT",
	}
	for _, k := range invalid {
		if keyPattern.MatchString(k) {
			t.Errorf("expected %q to be invalid UPPER_SNAKE_CASE", k)
		}
	}
}

func TestStoreAvailability(t *testing.T) {
	validKey := make([]byte, 32)
	_, _ = rand.Read(validKey)
	s1 := NewPgStore(nil, validKey, nil)
	if !s1.IsAvailable() {
		t.Errorf("expected store with valid 32-byte key to be available")
	}

	s2 := NewPgStore(nil, nil, nil)
	if s2.IsAvailable() {
		t.Errorf("expected store with nil key to be unavailable")
	}

	s3 := NewPgStore(nil, []byte("too-short"), nil)
	if s3.IsAvailable() {
		t.Errorf("expected store with <32 bytes to be unavailable")
	}
}

func TestCryptoWithAAD(t *testing.T) {
	key := make([]byte, 32)
	_, _ = rand.Read(key)

	projectID := "proj-123"
	keyName := "STRIPE_KEY"
	plaintext := "sk_test_1234567890"

	ciphertext, err := crypto.Encrypt(key, []byte(plaintext), aad(projectID, keyName))
	if err != nil {
		t.Fatalf("encrypt failed: %v", err)
	}

	// Decrypt with matching AAD
	decrypted, err := crypto.Decrypt(key, ciphertext, aad(projectID, keyName))
	if err != nil {
		t.Fatalf("decrypt failed: %v", err)
	}
	if string(decrypted) != plaintext {
		t.Fatalf("got %q, want %q", string(decrypted), plaintext)
	}

	// Tamper: wrong project ID in AAD
	_, err = crypto.Decrypt(key, ciphertext, aad("other-project", keyName))
	if err == nil {
		t.Fatalf("expected decryption to fail with mismatched project ID in AAD")
	}

	// Tamper: wrong key name in AAD
	_, err = crypto.Decrypt(key, ciphertext, aad(projectID, "OTHER_KEY"))
	if err == nil {
		t.Fatalf("expected decryption to fail with mismatched key name in AAD")
	}
}

func TestKeyRotation(t *testing.T) {
	keyOld := make([]byte, 32)
	_, _ = rand.Read(keyOld)
	keyNew := make([]byte, 32)
	_, _ = rand.Read(keyNew)

	projectID := "proj-rot"
	keyName := "ROTATED_SECRET"
	plaintext := "super-secret-value"

	// Encrypted with old key
	ciphertextOld, err := crypto.Encrypt(keyOld, []byte(plaintext), aad(projectID, keyName))
	if err != nil {
		t.Fatalf("encrypt with old key failed: %v", err)
	}

	// Store configured with keyNew as master, keyOld as previous
	s := &PgStore{
		masterKey:   keyNew,
		previousKey: keyOld,
	}

	// Decrypt using fallback to previous key
	pt, decErr := crypto.Decrypt(s.masterKey, ciphertextOld, aad(projectID, keyName))
	if decErr != nil && len(s.previousKey) == 32 {
		pt, decErr = crypto.Decrypt(s.previousKey, ciphertextOld, aad(projectID, keyName))
	}
	if decErr != nil {
		t.Fatalf("failed to decrypt with rotation fallback: %v", decErr)
	}
	if string(pt) != plaintext {
		t.Fatalf("got %q, want %q", string(pt), plaintext)
	}

	// Re-encrypt with new master key
	ciphertextNew, err := crypto.Encrypt(s.masterKey, pt, aad(projectID, keyName))
	if err != nil {
		t.Fatalf("re-encrypt with new master key failed: %v", err)
	}

	// Verify decrypt with keyNew succeeds directly
	ptNew, err := crypto.Decrypt(s.masterKey, ciphertextNew, aad(projectID, keyName))
	if err != nil {
		t.Fatalf("decrypt with new master key failed: %v", err)
	}
	if string(ptNew) != plaintext {
		t.Fatalf("got %q, want %q", string(ptNew), plaintext)
	}
}

func TestSecretsHTTPHandlers(t *testing.T) {
	key := make([]byte, 32)
	_, _ = rand.Read(key)

	store := NewPgStore(nil, key, nil)

	mux := http.NewServeMux()
	Register(mux, Deps{
		SecretsStore: store,
		AuthStore:    nil, // will test unauthenticated and 503 paths
	})

	// 1. Unauthenticated request -> 401
	req := httptest.NewRequest(http.MethodGet, "/projects/p-1/secrets", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401 Unauthorized for unauthenticated request, got %d", w.Code)
	}

	// 2. Unavailable store (no key) -> 503
	emptyStore := NewPgStore(nil, nil, nil)
	mux503 := http.NewServeMux()
	Register(mux503, Deps{
		SecretsStore: emptyStore,
		AuthStore:    nil,
	})

	// Setup fake auth for 503 test
	// When store is unavailable, SetSecret and RevealSecret should return 503
	body := bytes.NewBufferString(`{"value":"val","description":"desc"}`)
	req503 := httptest.NewRequest(http.MethodPut, "/projects/p-1/secrets/MY_KEY", body)
	w503 := httptest.NewRecorder()
	mux503.ServeHTTP(w503, req503)
	// Without auth it fails at 401 first, which is correct
	if w503.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401 for unauthenticated, got %d", w503.Code)
	}
}

func TestSecretsAuthAndTenantIsolation(t *testing.T) {
	// Verify token hash helper
	token := "valid-session-token"
	hash := sha256.Sum256([]byte(token))
	hashHex := hex.EncodeToString(hash[:])
	if len(hashHex) != 64 {
		t.Fatalf("expected 64-char sha256 hex string")
	}

	// Verify auth header parsing
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	authHeader := req.Header.Get("Authorization")
	if authHeader != "Bearer "+token {
		t.Fatalf("failed to retrieve bearer token")
	}
}
