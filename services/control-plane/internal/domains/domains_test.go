package domains

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
)

type fakeAuthStore struct {
	user auth.User
	err  error
}

func (f fakeAuthStore) CreateUser(context.Context, string, string, string, int64) (auth.User, error) {
	return f.user, f.err
}
func (f fakeAuthStore) FindUserByEmail(context.Context, string) (auth.User, string, error) {
	return f.user, "", f.err
}
func (f fakeAuthStore) FindUserByID(context.Context, string) (auth.User, error) {
	return f.user, f.err
}
func (f fakeAuthStore) CreateSession(context.Context, string, string, time.Time) error {
	return f.err
}
func (f fakeAuthStore) FindUserBySessionToken(context.Context, string) (auth.User, error) {
	if f.err != nil {
		return auth.User{}, f.err
	}
	return f.user, nil
}
func (f fakeAuthStore) DeleteSession(context.Context, string) error {
	return f.err
}

type fakeProjectStore struct {
	project projects.Project
	err     error
}

func (f fakeProjectStore) CreateProject(ctx context.Context, userID, name, description string) (projects.Project, error) {
	return f.project, f.err
}
func (f fakeProjectStore) ListProjects(ctx context.Context, userID, status string, limit int) ([]projects.Project, error) {
	return []projects.Project{f.project}, f.err
}
func (f fakeProjectStore) GetProject(ctx context.Context, id, userID string) (projects.Project, error) {
	if f.err != nil {
		return projects.Project{}, f.err
	}
	return f.project, nil
}
func (f fakeProjectStore) UpdateProject(ctx context.Context, id, userID string, name, description *string) (projects.Project, error) {
	return f.project, f.err
}
func (f fakeProjectStore) UpdateProjectBuildResult(ctx context.Context, id, userID string, name, prompt, commitSHA string, entities json.RawMessage, fileCount int, messageDelta int) error {
	return f.err
}
func (f fakeProjectStore) DebitProjectCredits(ctx context.Context, userID, projectID string, requested int64, reason string) (int64, int64, error) {
	return 0, 0, f.err
}
func (f fakeProjectStore) ArchiveProject(ctx context.Context, id, userID string) error {
	return f.err
}
func (f fakeProjectStore) DeleteProject(ctx context.Context, id, userID string) error {
	return f.err
}
func (f fakeProjectStore) TouchProjectOpened(ctx context.Context, id, userID string) error {
	return f.err
}

type memDomainStore struct {
	domains map[string]Domain // key: id
}

func newMemDomainStore() *memDomainStore {
	return &memDomainStore{domains: make(map[string]Domain)}
}

func (m *memDomainStore) ListProjectDomains(ctx context.Context, projectID string) ([]Domain, error) {
	var list []Domain
	for _, d := range m.domains {
		if d.ProjectID == projectID {
			list = append(list, d)
		}
	}
	return list, nil
}

func (m *memDomainStore) GetDomain(ctx context.Context, domainID string) (Domain, error) {
	d, ok := m.domains[domainID]
	if !ok {
		return Domain{}, ErrNotFound
	}
	return d, nil
}

func (m *memDomainStore) GetDomainByHostname(ctx context.Context, hostname string) (Domain, error) {
	for _, d := range m.domains {
		if d.Hostname == hostname {
			return d, nil
		}
	}
	return Domain{}, ErrNotFound
}

func (m *memDomainStore) CreateDomain(ctx context.Context, d Domain) (Domain, error) {
	d.ID = fmt.Sprintf("dom-%d", len(m.domains)+1)
	d.CreatedAt = time.Now().UTC()
	// If first domain, mark primary
	var count int
	for _, existing := range m.domains {
		if existing.ProjectID == d.ProjectID {
			count++
		}
	}
	if count == 0 {
		d.IsPrimary = true
	}
	m.domains[d.ID] = d
	return d, nil
}

func (m *memDomainStore) UpdateDomainStatus(ctx context.Context, id, status, tlsStatus, errorMsg string, verifiedAt *time.Time) error {
	d, ok := m.domains[id]
	if !ok {
		return ErrNotFound
	}
	d.Status = status
	d.TLSStatus = tlsStatus
	d.Error = errorMsg
	d.VerifiedAt = verifiedAt
	now := time.Now().UTC()
	d.LastCheckedAt = &now
	m.domains[id] = d
	return nil
}

func (m *memDomainStore) SetPrimaryDomain(ctx context.Context, projectID, domainID string) error {
	found := false
	for k, d := range m.domains {
		if d.ProjectID == projectID {
			d.IsPrimary = (d.ID == domainID)
			m.domains[k] = d
			if d.ID == domainID {
				found = true
			}
		}
	}
	if !found {
		return ErrNotFound
	}
	return nil
}

func (m *memDomainStore) DeleteDomain(ctx context.Context, domainID string) error {
	if _, ok := m.domains[domainID]; !ok {
		return ErrNotFound
	}
	delete(m.domains, domainID)
	return nil
}

type fakeDNSVerifier struct {
	cnameMap map[string]string
	ipMap    map[string][]net.IP
}

func (f fakeDNSVerifier) LookupCNAME(ctx context.Context, host string) (string, error) {
	if val, ok := f.cnameMap[host]; ok {
		return val, nil
	}
	return "", fmt.Errorf("cname not found")
}

func (f fakeDNSVerifier) LookupIP(ctx context.Context, network, host string) ([]net.IP, error) {
	if val, ok := f.ipMap[host]; ok {
		return val, nil
	}
	return nil, fmt.Errorf("ip not found")
}

func TestCleanAndValidateHostname(t *testing.T) {
	validCases := []struct {
		input string
		want  string
	}{
		{"App.Example.com.", "app.example.com"},
		{"shop.my-startup.io", "shop.my-startup.io"},
		{"dev.portal.company.co.uk", "dev.portal.company.co.uk"},
		{"MYDOMAIN.APP", "mydomain.app"},
	}

	for _, tc := range validCases {
		got, err := CleanAndValidateHostname(tc.input)
		if err != nil {
			t.Errorf("CleanAndValidateHostname(%q) unexpected error: %v", tc.input, err)
		}
		if got != tc.want {
			t.Errorf("CleanAndValidateHostname(%q) = %q, want %q", tc.input, got, tc.want)
		}
	}

	invalidCases := []struct {
		input string
		desc  string
	}{
		{"", "empty string"},
		{"192.168.1.1", "IPv4 address"},
		{"::1", "IPv6 address"},
		{"com", "bare TLD"},
		{"co.uk", "bare public suffix"},
		{"omnistackai.com", "reserved platform domain"},
		{"sub.omnistack.ai", "subdomain of reserved domain"},
		{"localhost", "localhost"},
		{"-bad-start.com", "invalid label start"},
		{"http://test.com", "URL scheme included"},
	}

	for _, tc := range invalidCases {
		_, err := CleanAndValidateHostname(tc.input)
		if err == nil {
			t.Errorf("CleanAndValidateHostname(%q) [%s] expected error, got nil", tc.input, tc.desc)
		}
	}
}

func TestIsApexDomain(t *testing.T) {
	if !IsApexDomain("example.com") {
		t.Errorf("example.com should be an apex domain")
	}
	if !IsApexDomain("mystore.co.uk") {
		t.Errorf("mystore.co.uk should be an apex domain")
	}
	if IsApexDomain("app.example.com") {
		t.Errorf("app.example.com should NOT be an apex domain")
	}
	if IsApexDomain("portal.mystore.co.uk") {
		t.Errorf("portal.mystore.co.uk should NOT be an apex domain")
	}
}

func TestCalculateExpectedRecord(t *testing.T) {
	// Apex on Vercel
	rType, rName, rVal := CalculateExpectedRecord("example.com", "vercel", "site-123")
	if rType != "A" || rName != "@" || rVal != "76.76.21.21" {
		t.Errorf("Vercel apex record mismatch: %s, %s, %s", rType, rName, rVal)
	}

	// Subdomain on Vercel
	rType, rName, rVal = CalculateExpectedRecord("app.example.com", "vercel", "site-123")
	if rType != "CNAME" || rName != "app" || rVal != "cname.vercel-dns.com" {
		t.Errorf("Vercel subdomain record mismatch: %s, %s, %s", rType, rName, rVal)
	}

	// Apex on Netlify
	rType, rName, rVal = CalculateExpectedRecord("example.com", "netlify", "my-site")
	if rType != "A" || rName != "@" || rVal != "75.2.60.5" {
		t.Errorf("Netlify apex record mismatch: %s, %s, %s", rType, rName, rVal)
	}

	// Subdomain on Netlify
	rType, rName, rVal = CalculateExpectedRecord("portal.example.com", "netlify", "my-site")
	if rType != "CNAME" || rName != "portal" || rVal != "my-site" {
		t.Errorf("Netlify subdomain record mismatch: %s, %s, %s", rType, rName, rVal)
	}
}

func TestDomainEndpointsLifecycle(t *testing.T) {
	authStore := fakeAuthStore{
		user: auth.User{ID: "usr-123", Email: "founder@example.com"},
	}
	projectStore := fakeProjectStore{
		project: projects.Project{ID: "proj-123", UserID: "usr-123"},
	}
	domainStore := newMemDomainStore()
	dnsVerifier := fakeDNSVerifier{
		cnameMap: map[string]string{
			"app.testcompany.com": "cname.vercel-dns.com.",
		},
		ipMap: map[string][]net.IP{
			"testcompany.com": {net.ParseIP("76.76.21.21")},
		},
	}

	deps := Deps{
		AuthStore:    authStore,
		ProjectStore: projectStore,
		DomainStore:  domainStore,
		DNSVerifier:  dnsVerifier,
	}

	mux := http.NewServeMux()
	Register(mux, deps)

	// 1. Initially empty list
	req := httptest.NewRequest("GET", "/projects/proj-123/domains", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("GET /domains status = %d, want 200", w.Code)
	}

	// 2. Add domain (subdomain)
	body := bytes.NewReader([]byte(`{"hostname":"app.testcompany.com"}`))
	req = httptest.NewRequest("POST", "/projects/proj-123/domains", body)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("POST /domains status = %d, body = %s", w.Code, w.Body.String())
	}

	var created Domain
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal created domain: %v", err)
	}
	if created.Hostname != "app.testcompany.com" || created.RecordType != "CNAME" || !created.IsPrimary {
		t.Fatalf("unexpected created domain: %+v", created)
	}

	// 3. Anti-hijack test: attempting to add the same hostname to another project fails with 409
	req = httptest.NewRequest("POST", "/projects/proj-123/domains", bytes.NewReader([]byte(`{"hostname":"app.testcompany.com"}`)))
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusConflict {
		t.Fatalf("POST duplicate domain status = %d, want 409 Conflict", w.Code)
	}

	// 4. Verify domain -> DNS matches fake resolver -> status verified
	req = httptest.NewRequest("POST", fmt.Sprintf("/projects/proj-123/domains/%s/verify", created.ID), nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("POST /verify status = %d, body = %s", w.Code, w.Body.String())
	}

	var verified Domain
	if err := json.Unmarshal(w.Body.Bytes(), &verified); err != nil {
		t.Fatalf("unmarshal verified domain: %v", err)
	}
	if verified.Status != "verified" || verified.TLSStatus != "issued" {
		t.Fatalf("expected verified domain, got status=%s, tls=%s", verified.Status, verified.TLSStatus)
	}

	// 5. Delete domain
	req = httptest.NewRequest("DELETE", fmt.Sprintf("/projects/proj-123/domains/%s", created.ID), nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("DELETE domain status = %d", w.Code)
	}
}
