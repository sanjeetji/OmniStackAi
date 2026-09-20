package git

import (
	"bytes"
	"context"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

var (
	ErrGitHubNotConfigured = errors.New("git: GitHub App is not configured")
	ErrInvalidPrivateKey   = errors.New("git: invalid RSA private key PEM")
)

type GitHubRepo struct {
	FullName string `json:"full_name"`
	HTMLURL  string `json:"html_url"`
	CloneURL string `json:"clone_url"`
	Private  bool   `json:"private"`
}

type InstallationTokenResponse struct {
	Token     string    `json:"token"`
	ExpiresAt time.Time `json:"expires_at"`
}

// MintAppJWT creates an RS256 JWT for GitHub App authentication using Go standard library crypto.
func MintAppJWT(appID string, privateKeyPEM []byte, now time.Time) (string, error) {
	if appID == "" || len(privateKeyPEM) == 0 {
		return "", ErrGitHubNotConfigured
	}

	block, _ := pem.Decode(privateKeyPEM)
	if block == nil {
		return "", ErrInvalidPrivateKey
	}

	var privKey *rsa.PrivateKey
	if key, err := x509.ParsePKCS1PrivateKey(block.Bytes); err == nil {
		privKey = key
	} else if key, err := x509.ParsePKCS8PrivateKey(block.Bytes); err == nil {
		var ok bool
		privKey, ok = key.(*rsa.PrivateKey)
		if !ok {
			return "", ErrInvalidPrivateKey
		}
	} else {
		return "", fmt.Errorf("%w: failed to parse private key: %v", ErrInvalidPrivateKey, err)
	}

	headerJSON := `{"alg":"RS256","typ":"JWT"}`
	headerB64 := base64.RawURLEncoding.EncodeToString([]byte(headerJSON))

	claims := map[string]interface{}{
		"iat": now.Add(-60 * time.Second).Unix(),
		"exp": now.Add(9 * time.Minute).Unix(),
		"iss": appID,
	}
	claimsBytes, err := json.Marshal(claims)
	if err != nil {
		return "", fmt.Errorf("git: marshal jwt claims: %w", err)
	}
	claimsB64 := base64.RawURLEncoding.EncodeToString(claimsBytes)

	signingInput := headerB64 + "." + claimsB64
	hashed := sha256.Sum256([]byte(signingInput))

	sig, err := rsa.SignPKCS1v15(rand.Reader, privKey, crypto.SHA256, hashed[:])
	if err != nil {
		return "", fmt.Errorf("git: sign jwt: %w", err)
	}
	sigB64 := base64.RawURLEncoding.EncodeToString(sig)

	return signingInput + "." + sigB64, nil
}

// MintInstallationToken exchanges a GitHub App JWT for a short-lived installation access token.
func MintInstallationToken(ctx context.Context, client *http.Client, apiBaseURL, appJWT string, installationID int64) (string, time.Time, error) {
	if client == nil {
		client = http.DefaultClient
	}
	if apiBaseURL == "" {
		apiBaseURL = "https://api.github.com"
	}
	url := fmt.Sprintf("%s/app/installations/%d/access_tokens", strings.TrimRight(apiBaseURL, "/"), installationID)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader([]byte("{}")))
	if err != nil {
		return "", time.Time{}, err
	}
	req.Header.Set("Authorization", "Bearer "+appJWT)
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("User-Agent", "OmniStackAI-Control-Plane")

	resp, err := client.Do(req)
	if err != nil {
		return "", time.Time{}, fmt.Errorf("git: post installation token: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", time.Time{}, fmt.Errorf("git: read installation token response: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", time.Time{}, fmt.Errorf("git: installation token request returned %d: %s", resp.StatusCode, string(body))
	}

	var tokResp InstallationTokenResponse
	if err := json.Unmarshal(body, &tokResp); err != nil {
		return "", time.Time{}, fmt.Errorf("git: unmarshal installation token: %w", err)
	}

	return tokResp.Token, tokResp.ExpiresAt, nil
}

// CreateUserRepo creates a repository on GitHub using an installation access token.
func CreateUserRepo(ctx context.Context, client *http.Client, apiBaseURL, token, name, description string, isPrivate bool) (*GitHubRepo, error) {
	if client == nil {
		client = http.DefaultClient
	}
	if apiBaseURL == "" {
		apiBaseURL = "https://api.github.com"
	}
	url := fmt.Sprintf("%s/user/repos", strings.TrimRight(apiBaseURL, "/"))

	reqBody, _ := json.Marshal(map[string]interface{}{
		"name":        name,
		"description": description,
		"private":     isPrivate,
		"auto_init":   false,
	})

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(reqBody))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "OmniStackAI-Control-Plane")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("git: create repo request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("git: read create repo response: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("git: create repo returned %d: %s", resp.StatusCode, string(body))
	}

	var repo GitHubRepo
	if err := json.Unmarshal(body, &repo); err != nil {
		return nil, fmt.Errorf("git: unmarshal create repo response: %w", err)
	}

	return &repo, nil
}
