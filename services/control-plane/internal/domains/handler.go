package domains

import (
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/deploy"
	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/projects"
)

type Deps struct {
	AuthStore    auth.Store
	ProjectStore projects.Store
	DomainStore  Store
	DeployStore  deploy.Store
	Vercel       deploy.DeployProvider
	Netlify      deploy.DeployProvider
	DNSVerifier  DNSVerifier
	Logger       *slog.Logger
	HTTPClient   *http.Client
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

func (d Deps) httpClient() *http.Client {
	if d.HTTPClient != nil {
		return d.HTTPClient
	}
	return &http.Client{Timeout: 30 * time.Second}
}

func (d Deps) getProvider(name string) (deploy.DeployProvider, error) {
	switch strings.ToLower(strings.TrimSpace(name)) {
	case "vercel":
		if d.Vercel != nil {
			return d.Vercel, nil
		}
		return deploy.NewVercelProvider("", d.httpClient()), nil
	case "netlify":
		if d.Netlify != nil {
			return d.Netlify, nil
		}
		return deploy.NewNetlifyProvider("", d.httpClient()), nil
	default:
		return nil, errors.New("unsupported provider: " + name)
	}
}

func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /projects/{id}/domains", handleListDomains(deps))
	mux.HandleFunc("POST /projects/{id}/domains", handleAddDomain(deps))
	mux.HandleFunc("POST /projects/{id}/domains/{domainId}/verify", handleVerifyDomain(deps))
	mux.HandleFunc("PUT /projects/{id}/domains/{domainId}/primary", handleSetPrimaryDomain(deps))
	mux.HandleFunc("DELETE /projects/{id}/domains/{domainId}", handleDeleteDomain(deps))
}

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func authenticate(r *http.Request, authStore auth.Store) (auth.User, error) {
	return auth.RequireUser(r.Context(), authStore, r)
}

func checkProjectAccess(r *http.Request, deps Deps, projectID string) (auth.User, projects.Project, error) {
	user, err := authenticate(r, deps.AuthStore)
	if err != nil {
		return auth.User{}, projects.Project{}, err
	}
	proj, err := deps.ProjectStore.GetProject(r.Context(), projectID, user.ID)
	if err != nil {
		return user, projects.Project{}, err
	}
	return user, proj, nil
}

func handleListDomains(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		if _, _, err := checkProjectAccess(r, deps, projectID); err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		doms, err := deps.DomainStore.ListProjectDomains(r.Context(), projectID)
		if err != nil {
			deps.logger().Error("failed to list project domains", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to list domains")
			return
		}
		if doms == nil {
			doms = []Domain{}
		}

		writeJSON(w, http.StatusOK, map[string]any{"domains": doms})
	}
}

func handleAddDomain(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		var body struct {
			Hostname string `json:"hostname"`
			Provider string `json:"provider"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		cleanHost, err := CleanAndValidateHostname(body.Hostname)
		if err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}

		// Anti-hijack: Check if hostname is already registered across ANY project
		existing, err := deps.DomainStore.GetDomainByHostname(r.Context(), cleanHost)
		if err == nil {
			if existing.ProjectID == projectID {
				writeError(w, http.StatusConflict, "domain is already attached to this project")
				return
			}
			writeError(w, http.StatusConflict, "hostname already registered by another project")
			return
		}

		providerName := strings.ToLower(strings.TrimSpace(body.Provider))
		var deployExtID string
		if deps.DeployStore != nil {
			p, ext, _, err := deps.DeployStore.GetProjectDeployMeta(r.Context(), projectID)
			if err == nil && p != "" {
				if providerName == "" {
					providerName = strings.ToLower(p)
				}
				deployExtID = ext
			}
		}
		if providerName == "" {
			providerName = "vercel"
		}

		// Calculate record defaults
		recordType, recordName, recordValue := CalculateExpectedRecord(cleanHost, providerName, deployExtID)
		status := "pending"
		tlsStatus := "pending"

		// If user has connected this deploy provider, also attach at provider
		if deps.DeployStore != nil && deployExtID != "" {
			if _, token, err := deps.DeployStore.GetConnection(r.Context(), user.ID, providerName); err == nil && token != "" {
				if prov, err := deps.getProvider(providerName); err == nil {
					pRecordType, pRecordName, pRecordValue, pVerified, pErr := prov.AddDomain(r.Context(), token, deployExtID, cleanHost)
					if pErr == nil {
						if pRecordType != "" {
							recordType = pRecordType
						}
						if pRecordName != "" {
							recordName = pRecordName
						}
						if pRecordValue != "" {
							recordValue = pRecordValue
						}
						if pVerified {
							status = "verified"
							tlsStatus = "issued"
						}
					} else {
						deps.logger().Warn("provider AddDomain call returned warning", "error", pErr)
					}
				}
			}
		}

		dom := Domain{
			ProjectID:   projectID,
			Hostname:    cleanHost,
			Provider:    providerName,
			RecordType:  recordType,
			RecordName:  recordName,
			RecordValue: recordValue,
			Status:      status,
			TLSStatus:   tlsStatus,
		}

		created, err := deps.DomainStore.CreateDomain(r.Context(), dom)
		if err != nil {
			deps.logger().Error("failed to create domain record", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to create domain")
			return
		}

		writeJSON(w, http.StatusCreated, created)
	}
}

func handleVerifyDomain(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		domainID := r.PathValue("domainId")
		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		dom, err := deps.DomainStore.GetDomain(r.Context(), domainID)
		if err != nil {
			writeError(w, http.StatusNotFound, "domain not found")
			return
		}
		if dom.ProjectID != projectID {
			writeError(w, http.StatusNotFound, "domain not found for project")
			return
		}

		var deployExtID string
		if deps.DeployStore != nil {
			_, ext, _, _ := deps.DeployStore.GetProjectDeployMeta(r.Context(), projectID)
			deployExtID = ext
		}

		// 1. DNS Resolution check
		dnsResolved, dnsDetail := VerifyDNS(r.Context(), deps.DNSVerifier, dom.Hostname, dom.RecordType, dom.RecordValue)

		// 2. Provider verification check
		providerVerified := false
		tlsIssued := false
		var providerError string

		if deps.DeployStore != nil && deployExtID != "" {
			if _, token, err := deps.DeployStore.GetConnection(r.Context(), user.ID, dom.Provider); err == nil && token != "" {
				if prov, err := deps.getProvider(dom.Provider); err == nil {
					pDns, pTls, pErrStr, pErr := prov.VerifyDomain(r.Context(), token, deployExtID, dom.Hostname)
					if pErr == nil {
						providerVerified = pDns
						tlsIssued = pTls
						providerError = pErrStr
					}
				}
			}
		}

		newStatus := "pending"
		newTLSStatus := "pending"
		var errorMsg string
		var verifiedAt *time.Time

		// Two-phase rule: both standard DNS resolution AND provider verification must agree
		// Or if provider is not configured yet (e.g. mock or local testing without token), standard DNS resolution sets it verified
		hasProviderToken := false
		if deps.DeployStore != nil && deployExtID != "" {
			if _, token, err := deps.DeployStore.GetConnection(r.Context(), user.ID, dom.Provider); err == nil && token != "" {
				hasProviderToken = true
			}
		}

		if dnsResolved && (providerVerified || !hasProviderToken) {
			newStatus = "verified"
			if tlsIssued || !hasProviderToken {
				newTLSStatus = "issued"
			} else {
				newTLSStatus = "pending"
			}
			now := time.Now().UTC()
			verifiedAt = &now
		} else if dnsResolved {
			newStatus = "verifying"
			newTLSStatus = "pending"
			if providerError != "" {
				errorMsg = providerError
			} else {
				errorMsg = "DNS is resolving; waiting for hosting provider certificate issuance"
			}
		} else {
			newStatus = "pending"
			newTLSStatus = "pending"
			errorMsg = dnsDetail
		}

		if err := deps.DomainStore.UpdateDomainStatus(r.Context(), domainID, newStatus, newTLSStatus, errorMsg, verifiedAt); err != nil {
			deps.logger().Error("failed to update domain status", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to update domain status")
			return
		}

		updated, err := deps.DomainStore.GetDomain(r.Context(), domainID)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to fetch updated domain")
			return
		}

		writeJSON(w, http.StatusOK, updated)
	}
}

func handleSetPrimaryDomain(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		domainID := r.PathValue("domainId")
		if _, _, err := checkProjectAccess(r, deps, projectID); err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		if err := deps.DomainStore.SetPrimaryDomain(r.Context(), projectID, domainID); err != nil {
			deps.logger().Error("failed to set primary domain", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to set primary domain")
			return
		}

		updated, err := deps.DomainStore.GetDomain(r.Context(), domainID)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to get domain")
			return
		}

		writeJSON(w, http.StatusOK, updated)
	}
}

func handleDeleteDomain(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		projectID := r.PathValue("id")
		domainID := r.PathValue("domainId")
		user, _, err := checkProjectAccess(r, deps, projectID)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "unauthorized or project not found")
			return
		}

		dom, err := deps.DomainStore.GetDomain(r.Context(), domainID)
		if err != nil {
			writeError(w, http.StatusNotFound, "domain not found")
			return
		}

		// Remove from provider if token available
		if deps.DeployStore != nil {
			_, ext, _, _ := deps.DeployStore.GetProjectDeployMeta(r.Context(), projectID)
			if ext != "" {
				if _, token, err := deps.DeployStore.GetConnection(r.Context(), user.ID, dom.Provider); err == nil && token != "" {
					if prov, err := deps.getProvider(dom.Provider); err == nil {
						_ = prov.RemoveDomain(r.Context(), token, ext, dom.Hostname)
					}
				}
			}
		}

		if err := deps.DomainStore.DeleteDomain(r.Context(), domainID); err != nil {
			deps.logger().Error("failed to delete domain", "error", err)
			writeError(w, http.StatusInternalServerError, "failed to delete domain")
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{"deleted": true})
	}
}
