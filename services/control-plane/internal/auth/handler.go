package auth

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/mail"
	"strings"
)

const (
	minPasswordLength = 8
	maxPasswordLength = 128
	maxNameLength     = 200
)

// Register mounts /auth/register, /auth/login, /auth/logout and /auth/me onto mux.
func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("POST /auth/register", handleRegister(deps))
	mux.HandleFunc("POST /auth/login", handleLogin(deps))
	mux.HandleFunc("POST /auth/logout", handleLogout(deps))
	mux.HandleFunc("GET /auth/me", handleMe(deps))
}

type registerRequest struct {
	Email    string `json:"email"`
	Name     string `json:"name"`
	Password string `json:"password"`
}

type loginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type userResponse struct {
	ID            string `json:"id"`
	Email         string `json:"email"`
	Name          string `json:"name"`
	Role          string `json:"role"`
	Plan          string `json:"plan"`
	BYOKEnabled   bool   `json:"byok_enabled"`
	CreditBalance int64  `json:"credit_balance"`
}

type authResponse struct {
	userResponse
	Token string `json:"token"`
}

func toUserResponse(user User) userResponse {
	return userResponse{
		ID:            user.ID,
		Email:         user.Email,
		Name:          user.Name,
		Role:          user.Role,
		Plan:          user.Plan,
		BYOKEnabled:   user.BYOKEnabled,
		CreditBalance: user.CreditBalance,
	}
}

func handleRegister(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req registerRequest
		if !decodeJSON(w, r, &req) {
			return
		}

		email, err := normalizeEmail(req.Email)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid email")
			return
		}
		name, err := validateName(req.Name)
		if err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
		if err := validatePassword(req.Password); err != nil {
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}

		hash, err := deps.Hasher.Hash(req.Password)
		if err != nil {
			deps.logger().Error("hash password", "error", err)
			writeError(w, http.StatusInternalServerError, "could not create account")
			return
		}

		user, err := deps.Store.CreateUser(r.Context(), email, hash, name, deps.SignupCredits)
		if err != nil {
			if errors.Is(err, ErrEmailTaken) {
				writeError(w, http.StatusConflict, "email already registered")
				return
			}
			deps.logger().Error("create user", "error", err)
			writeError(w, http.StatusInternalServerError, "could not create account")
			return
		}

		token, err := issueSession(r.Context(), deps, user.ID)
		if err != nil {
			deps.logger().Error("issue session", "error", err)
			writeError(w, http.StatusInternalServerError, "could not create session")
			return
		}

		writeJSON(w, http.StatusCreated, authResponse{userResponse: toUserResponse(user), Token: token})
	}
}

func handleLogin(deps Deps) http.HandlerFunc {
	// Computed once, when the handler is built, from whichever Hasher this Deps carries - not
	// per-request and not a package-level global. Used below to give the "email not found" path
	// roughly the same cost as a real password check (one Verify call), so a login response does
	// not leak, via timing, whether an email is registered. If it fails (only possible if
	// crypto/rand is broken), the mitigation is skipped rather than the server refusing to start
	// or a request panicking.
	dummyEncodedHash, dummyHashErr := deps.Hasher.Hash("dummy-password-for-constant-time-comparison")

	return func(w http.ResponseWriter, r *http.Request) {
		var req loginRequest
		if !decodeJSON(w, r, &req) {
			return
		}

		email, err := normalizeEmail(req.Email)
		if err != nil {
			writeError(w, http.StatusUnauthorized, "invalid email or password")
			return
		}

		user, hash, err := deps.Store.FindUserByEmail(r.Context(), email)
		if err != nil {
			if errors.Is(err, ErrUserNotFound) {
				if dummyHashErr == nil {
					_, _ = deps.Hasher.Verify(dummyEncodedHash, req.Password)
				}
				writeError(w, http.StatusUnauthorized, "invalid email or password")
				return
			}
			deps.logger().Error("find user by email", "error", err)
			writeError(w, http.StatusInternalServerError, "could not sign in")
			return
		}

		ok, err := deps.Hasher.Verify(hash, req.Password)
		if err != nil {
			deps.logger().Error("verify password", "error", err)
			writeError(w, http.StatusInternalServerError, "could not sign in")
			return
		}
		if !ok {
			writeError(w, http.StatusUnauthorized, "invalid email or password")
			return
		}

		token, err := issueSession(r.Context(), deps, user.ID)
		if err != nil {
			deps.logger().Error("issue session", "error", err)
			writeError(w, http.StatusInternalServerError, "could not create session")
			return
		}

		writeJSON(w, http.StatusOK, authResponse{userResponse: toUserResponse(user), Token: token})
	}
}

func handleLogout(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		token, ok := bearerToken(r)
		if !ok {
			writeError(w, http.StatusUnauthorized, "missing bearer token")
			return
		}
		// Logout is idempotent: deleting a token that doesn't exist is not an error.
		if err := deps.Store.DeleteSession(r.Context(), hashToken(token)); err != nil {
			deps.logger().Error("delete session", "error", err)
			writeError(w, http.StatusInternalServerError, "could not sign out")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	}
}

func handleMe(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		token, ok := bearerToken(r)
		if !ok {
			writeError(w, http.StatusUnauthorized, "missing bearer token")
			return
		}
		user, err := deps.Store.FindUserBySessionToken(r.Context(), hashToken(token))
		if err != nil {
			if errors.Is(err, ErrSessionNotFound) {
				writeError(w, http.StatusUnauthorized, "session not found or expired")
				return
			}
			deps.logger().Error("find user by session token", "error", err)
			writeError(w, http.StatusInternalServerError, "could not load account")
			return
		}
		writeJSON(w, http.StatusOK, toUserResponse(user))
	}
}

func issueSession(ctx context.Context, deps Deps, userID string) (string, error) {
	raw, hash, err := generateToken()
	if err != nil {
		return "", err
	}
	expiresAt := deps.now().Add(deps.SessionTTL)
	if err := deps.Store.CreateSession(ctx, hash, userID, expiresAt); err != nil {
		return "", err
	}
	return raw, nil
}

func bearerToken(r *http.Request) (string, bool) {
	const prefix = "Bearer "
	header := r.Header.Get("Authorization")
	if !strings.HasPrefix(header, prefix) {
		return "", false
	}
	token := strings.TrimSpace(strings.TrimPrefix(header, prefix))
	if token == "" {
		return "", false
	}
	return token, true
}

func normalizeEmail(email string) (string, error) {
	email = strings.ToLower(strings.TrimSpace(email))
	if email == "" {
		return "", errors.New("email is required")
	}
	if _, err := mail.ParseAddress(email); err != nil {
		return "", err
	}
	return email, nil
}

func validateName(name string) (string, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		return "", errors.New("name is required")
	}
	if len(name) > maxNameLength {
		return "", errors.New("name must be at most 200 characters")
	}
	return name, nil
}

func validatePassword(password string) error {
	if len(password) < minPasswordLength {
		return errors.New("password must be at least 8 characters")
	}
	if len(password) > maxPasswordLength {
		return errors.New("password must be at most 128 characters")
	}
	return nil
}

func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) bool {
	defer func() { _ = r.Body.Close() }()
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(dst); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return false
	}
	return true
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

type errorResponse struct {
	Error string `json:"error"`
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, errorResponse{Error: message})
}
