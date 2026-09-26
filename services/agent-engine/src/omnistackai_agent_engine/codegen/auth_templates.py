"""The complete account flow, as emitted into every generated backend (R-591).

Register, login, me, logout, forgot-password and reset-password — one contract, three languages,
so a single web or mobile app works against a Python, Go or Node backend without knowing which.

What the contract promises, in every language:

* Passwords: PBKDF2-HMAC-SHA256, 100 000 iterations, random 32-byte salt, stored as
  "<hex_salt>:<hex_digest>". One format, so a user created by one backend can sign in through
  another and the seeded development admin works everywhere.
* Tokens: HS256 JWT signed with JWT_SECRET, 24 hours, carrying `role` and `roles` (the guard reads
  the list — R-566).
* Reset: a random one-time token; only its SHA-256 is stored, it expires after an hour and dies on
  use. The link is emailed through Resend when RESEND_API_KEY and EMAIL_FROM are set; with
  OMNISTACKAI_DEV_MODE=1 and no email configured it goes to the server log. It is never in an HTTP
  response, and forgot-password answers the same whether or not the address has an account.
* Errors: `{"detail": "<code>"}` — invalid_email, password_too_short, email_already_registered,
  invalid_credentials, unauthorized, invalid_token, invalid_or_expired_token.

Kept as plain templates rather than line-by-line string building so each file can be read as the
program it is.
"""

from __future__ import annotations

#: The account flow every generated backend implements identically.
AUTH_CONTRACT = {
    "register": ("POST", "/auth/register"),
    "login": ("POST", "/auth/login"),
    "me": ("GET", "/auth/me"),
    "logout": ("POST", "/auth/logout"),
    "forgot": ("POST", "/auth/forgot-password"),
    "reset": ("POST", "/auth/reset-password"),
}
MIN_PASSWORD_LENGTH = 8
RESET_TOKEN_TTL_MINUTES = 60

EMAIL_ENV_EXAMPLE = (
    "# Password-reset email (R-591). Leave empty to print reset links to the server log in dev mode.\n"
    "APP_BASE_URL=http://localhost:3000\n"
    "RESEND_API_KEY=\n"
    "EMAIL_FROM=\n"
)


PYTHON_AUTH_ROUTER = r'''"""Account flow for the generated API (R-461, completed in R-591).

POST /auth/register, /auth/login, /auth/logout, /auth/forgot-password, /auth/reset-password and
GET /auth/me. Passwords: PBKDF2-SHA256, 100 000 iterations, random 32-byte salt, stored as
"<hex_salt>:<hex_digest>" (the same format the Go and Node backends use). Tokens: HS256 JWT signed
with JWT_SECRET from the environment.

Password reset sends a one-time link. Only a SHA-256 of the token is stored and it expires after
an hour. It is emailed through Resend when RESEND_API_KEY and EMAIL_FROM are set; with
OMNISTACKAI_DEV_MODE=1 and no email configured it is printed to the server log. It is never returned
in an HTTP response, and forgot-password answers the same whether or not the address has an
account, so the endpoint cannot be used to discover who is registered.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import secrets
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

JWT_ALGORITHM = "HS256"
DEFAULT_ROLE = "user"  # every self-registered account starts with this role
TOKEN_EXPIRE_HOURS = 24
MIN_PASSWORD_LENGTH = 8
RESET_TOKEN_TTL_MINUTES = 60

log = logging.getLogger("auth")
router = APIRouter(tags=["auth"])


def hash_password(plain: str) -> str:
    """Return "<hex_salt>:<hex_digest>" suitable for the password_hash column."""
    salt = secrets.token_bytes(32)
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 100_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(plain: str, stored: str) -> bool:
    """Return True when `plain` matches the stored PBKDF2 hash."""
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 100_000)
    return secrets.compare_digest(candidate, expected)


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _check_email(email: str) -> None:
    if "@" not in email or len(email) > 254 or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=400, detail="invalid_email")


def _check_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail="password_too_short")


def _jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="auth_not_configured")
    return secret


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    role: str = "user"  # accepted for compatibility and ignored: nobody signs up as an admin


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _user(row: Any) -> UserOut:
    return UserOut(id=row["id"], email=row["email"], full_name=row["full_name"], role=row["role"])


def _create_token(user: UserOut) -> str:
    # `roles` as a list beside `role`: the guard reads the list (R-566).
    data: dict[str, Any] = {
        "sub": user.id, "email": user.email, "role": user.role, "roles": [user.role],
        "full_name": user.full_name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(data, _jwt_secret(), algorithm=JWT_ALGORITHM)


def _reset_link(token: str) -> str:
    base = os.environ.get("APP_BASE_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/reset-password?token={token}"


def _send_via_resend(to: str, link: str) -> None:
    body = json.dumps({
        "from": os.environ["EMAIL_FROM"],
        "to": [to],
        "subject": "Reset your password",
        "text": (
            "Someone asked to reset the password for this account.\n\n"
            f"Choose a new password here (the link works once, for {RESET_TOKEN_TTL_MINUTES} minutes):\n{link}\n\n"
            "If it was not you, ignore this email; your password is unchanged."
        ),
    }).encode()
    request = urllib.request.Request(
        "https://api.resend.com/emails", data=body, method="POST",
        headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 (fixed https URL)
        response.read()


async def _deliver_reset_link(email: str, token: str) -> None:
    link = _reset_link(token)
    if os.environ.get("RESEND_API_KEY") and os.environ.get("EMAIL_FROM"):
        try:
            await asyncio.to_thread(_send_via_resend, email, link)
        except Exception:  # noqa: BLE001 - the caller must not learn whether sending failed
            log.exception("password reset email could not be sent")
    elif os.environ.get("OMNISTACKAI_DEV_MODE") == "1":
        log.warning("DEV MODE: password reset link for %s: %s", email, link)
    else:
        log.warning("password reset requested but email is not configured (set RESEND_API_KEY and EMAIL_FROM)")


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest) -> TokenResponse:
    """Register a new account with the default role and return a signed JWT."""
    from app.db import connect

    email = _normalize_email(body.email)
    _check_email(email)
    _check_password(body.password)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute('SELECT id FROM "users" WHERE email = %s', (email,))
        if await cur.fetchone():
            raise HTTPException(status_code=409, detail="email_already_registered")
        await cur.execute(
            'INSERT INTO "users" (email, password_hash, full_name, role) VALUES (%s, %s, %s, %s) '
            "RETURNING id::text AS id, email, full_name, role",
            (email, hash_password(body.password), body.full_name, DEFAULT_ROLE),
        )
        user = _user(await cur.fetchone())
    return TokenResponse(access_token=_create_token(user), user=user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """Authenticate with email + password and return a signed JWT."""
    from app.db import connect

    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(
            'SELECT id::text AS id, email, password_hash, full_name, role FROM "users" WHERE email = %s',
            (_normalize_email(body.email),),
        )
        row = await cur.fetchone()
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = _user(row)
    return TokenResponse(access_token=_create_token(user), user=user)


@router.get("/me", response_model=UserOut)
async def me(authorization: str | None = Header(default=None)) -> UserOut:
    """The signed-in user, read from the database (a deleted account stops working at once)."""
    from app.db import connect

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        claims = jwt.decode(authorization[len("Bearer "):], _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid_token") from exc
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(
            'SELECT id::text AS id, email, full_name, role FROM "users" WHERE id::text = %s',
            (str(claims.get("sub", "")),),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="invalid_token")
    return _user(row)


@router.post("/logout", status_code=204)
async def logout() -> Response:
    """Tokens are stateless; the client forgets its token."""
    return Response(status_code=204)


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest) -> dict[str, str]:
    """Send a one-time reset link if the account exists. The answer is the same either way."""
    from app.db import connect

    email = _normalize_email(body.email)
    token = secrets.token_hex(32)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(
            'UPDATE "users" SET reset_token_hash = %s, '
            "reset_token_expires_at = NOW() + make_interval(mins => %s) "
            "WHERE email = %s RETURNING id",
            (hashlib.sha256(token.encode()).hexdigest(), RESET_TOKEN_TTL_MINUTES, email),
        )
        found = await cur.fetchone()
    if found:
        await _deliver_reset_link(email, token)
    return {"status": "ok"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest) -> dict[str, str]:
    """Redeem a reset link: set the new password and make the link unusable."""
    from app.db import connect

    _check_password(body.new_password)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(
            'UPDATE "users" SET password_hash = %s, reset_token_hash = NULL, reset_token_expires_at = NULL '
            "WHERE reset_token_hash = %s AND reset_token_expires_at > NOW() RETURNING id",
            (hash_password(body.new_password), hashlib.sha256((body.token or "").encode()).hexdigest()),
        )
        updated = await cur.fetchone()
    if not updated:
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")
    return {"status": "ok"}
'''


GO_AUTH_HANDLERS = r'''package handlers

// Account flow (R-591): register, login, me, logout, forgot-password and reset-password, with the
// same contract as the Python and Node backends so one web or mobile app works against any of them.
// Passwords use the shared "<hex_salt>:<hex_digest>" PBKDF2-SHA256 format; tokens are HS256 JWTs
// signed with JWT_SECRET. A reset link is emailed through Resend when RESEND_API_KEY and EMAIL_FROM
// are set, printed to the log in dev mode otherwise, and never returned in a response.

import (
	"bytes"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"database/sql"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

const (
	minPasswordLength = 8
	resetTokenMinutes = 60
	tokenTTL          = 24 * time.Hour
	pbkdf2Iterations  = 100000
	defaultRole       = "user"
)

type authUser struct {
	ID       string  `json:"id"`
	Email    string  `json:"email"`
	FullName *string `json:"full_name"`
	Role     string  `json:"role"`
}

type tokenResponse struct {
	AccessToken string   `json:"access_token"`
	TokenType   string   `json:"token_type"`
	User        authUser `json:"user"`
}

func authError(w http.ResponseWriter, status int, code string) {
	writeJSON(w, status, map[string]string{"detail": code})
}

func decodeAuthBody(w http.ResponseWriter, r *http.Request, v any) bool {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	if err := json.NewDecoder(r.Body).Decode(v); err != nil {
		authError(w, http.StatusBadRequest, "invalid_json")
		return false
	}
	return true
}

// pbkdf2SHA256 is RFC 8018 PBKDF2 with HMAC-SHA256. Written out because crypto/pbkdf2 arrived only
// in Go 1.24 and this module targets 1.22; it produces the same bytes as Python's hashlib.
func pbkdf2SHA256(password, salt []byte, iterations, keyLen int) []byte {
	prf := hmac.New(sha256.New, password)
	blocks := (keyLen + prf.Size() - 1) / prf.Size()
	out := make([]byte, 0, blocks*prf.Size())
	counter := make([]byte, 4)
	for block := 1; block <= blocks; block++ {
		prf.Reset()
		prf.Write(salt)
		binary.BigEndian.PutUint32(counter, uint32(block))
		prf.Write(counter)
		u := prf.Sum(nil)
		t := append([]byte(nil), u...)
		for i := 1; i < iterations; i++ {
			prf.Reset()
			prf.Write(u)
			u = prf.Sum(nil)
			for j := range t {
				t[j] ^= u[j]
			}
		}
		out = append(out, t...)
	}
	return out[:keyLen]
}

func hashPassword(plain string) (string, error) {
	salt := make([]byte, 32)
	if _, err := rand.Read(salt); err != nil {
		return "", err
	}
	digest := pbkdf2SHA256([]byte(plain), salt, pbkdf2Iterations, 32)
	return hex.EncodeToString(salt) + ":" + hex.EncodeToString(digest), nil
}

func verifyPassword(plain, stored string) bool {
	saltHex, digestHex, ok := strings.Cut(stored, ":")
	if !ok {
		return false
	}
	salt, errSalt := hex.DecodeString(saltHex)
	expected, errDigest := hex.DecodeString(digestHex)
	if errSalt != nil || errDigest != nil || len(expected) == 0 {
		return false
	}
	candidate := pbkdf2SHA256([]byte(plain), salt, pbkdf2Iterations, len(expected))
	return subtle.ConstantTimeCompare(candidate, expected) == 1
}

func normalizeEmail(email string) string {
	return strings.ToLower(strings.TrimSpace(email))
}

func validEmail(email string) bool {
	return strings.Contains(email, "@") && len(email) <= 254 &&
		!strings.HasPrefix(email, "@") && !strings.HasSuffix(email, "@")
}

func sha256Hex(value string) string {
	sum := sha256.Sum256([]byte(value))
	return hex.EncodeToString(sum[:])
}

func (h *Handlers) issueToken(w http.ResponseWriter, status int, u authUser) {
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		authError(w, http.StatusInternalServerError, "auth_not_configured")
		return
	}
	claims := jwt.MapClaims{
		"sub": u.ID, "email": u.Email, "role": u.Role, "roles": []string{u.Role},
		"exp": time.Now().Add(tokenTTL).Unix(),
	}
	if u.FullName != nil {
		claims["full_name"] = *u.FullName
	}
	signed, err := jwt.NewWithClaims(jwt.SigningMethodHS256, claims).SignedString([]byte(secret))
	if err != nil {
		authError(w, http.StatusInternalServerError, "internal_error")
		return
	}
	writeJSON(w, status, tokenResponse{AccessToken: signed, TokenType: "bearer", User: u})
}

// AuthRegister creates an account with the default role. A role in the request is ignored, so
// nobody can sign themselves up as an admin.
func (h *Handlers) AuthRegister(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Email    string  `json:"email"`
		Password string  `json:"password"`
		FullName *string `json:"full_name"`
	}
	if !decodeAuthBody(w, r, &body) {
		return
	}
	email := normalizeEmail(body.Email)
	if !validEmail(email) {
		authError(w, http.StatusBadRequest, "invalid_email")
		return
	}
	if len(body.Password) < minPasswordLength {
		authError(w, http.StatusBadRequest, "password_too_short")
		return
	}
	hash, err := hashPassword(body.Password)
	if err != nil {
		authError(w, http.StatusInternalServerError, "internal_error")
		return
	}
	var u authUser
	err = h.DB.QueryRowContext(r.Context(),
		`INSERT INTO "users" (email, password_hash, full_name, role) VALUES ($1, $2, $3, $4)
		 ON CONFLICT (email) DO NOTHING RETURNING id::text, email, full_name, role`,
		email, hash, body.FullName, defaultRole,
	).Scan(&u.ID, &u.Email, &u.FullName, &u.Role)
	if errors.Is(err, sql.ErrNoRows) {
		authError(w, http.StatusConflict, "email_already_registered")
		return
	}
	if err != nil {
		log.Printf("register: %v", err)
		authError(w, http.StatusInternalServerError, "internal_error")
		return
	}
	h.issueToken(w, http.StatusCreated, u)
}

// AuthLogin checks an email and password and returns a signed token.
func (h *Handlers) AuthLogin(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Email    string `json:"email"`
		Password string `json:"password"`
	}
	if !decodeAuthBody(w, r, &body) {
		return
	}
	var u authUser
	var stored string
	err := h.DB.QueryRowContext(r.Context(),
		`SELECT id::text, email, password_hash, full_name, role FROM "users" WHERE email = $1`,
		normalizeEmail(body.Email),
	).Scan(&u.ID, &u.Email, &stored, &u.FullName, &u.Role)
	if err != nil || !verifyPassword(body.Password, stored) {
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
			log.Printf("login: %v", err)
		}
		authError(w, http.StatusUnauthorized, "invalid_credentials")
		return
	}
	h.issueToken(w, http.StatusOK, u)
}

// AuthMe returns the signed-in user, read from the database so a deleted account stops at once.
func (h *Handlers) AuthMe(w http.ResponseWriter, r *http.Request) {
	if !strings.HasPrefix(r.Header.Get("Authorization"), "Bearer ") {
		authError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	claims, status, msg := verifyToken(r)
	if msg != "" {
		authError(w, status, msg)
		return
	}
	sub, _ := claims["sub"].(string)
	var u authUser
	err := h.DB.QueryRowContext(r.Context(),
		`SELECT id::text, email, full_name, role FROM "users" WHERE id::text = $1`, sub,
	).Scan(&u.ID, &u.Email, &u.FullName, &u.Role)
	if err != nil {
		authError(w, http.StatusUnauthorized, "invalid_token")
		return
	}
	writeJSON(w, http.StatusOK, u)
}

// AuthLogout is a no-op: tokens are stateless and the client forgets its own.
func (h *Handlers) AuthLogout(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusNoContent)
}

// AuthForgotPassword sends a one-time reset link if the account exists. The answer is the same
// either way, so the endpoint cannot be used to discover who is registered.
func (h *Handlers) AuthForgotPassword(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Email string `json:"email"`
	}
	if !decodeAuthBody(w, r, &body) {
		return
	}
	email := normalizeEmail(body.Email)
	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		authError(w, http.StatusInternalServerError, "internal_error")
		return
	}
	token := hex.EncodeToString(raw)
	var id string
	err := h.DB.QueryRowContext(r.Context(),
		`UPDATE "users" SET reset_token_hash = $1, reset_token_expires_at = NOW() + make_interval(mins => $2)
		 WHERE email = $3 RETURNING id::text`,
		sha256Hex(token), resetTokenMinutes, email,
	).Scan(&id)
	if err == nil {
		deliverResetLink(email, token)
	} else if !errors.Is(err, sql.ErrNoRows) {
		log.Printf("forgot-password: %v", err)
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// AuthResetPassword redeems a reset link: it sets the new password and makes the link unusable.
func (h *Handlers) AuthResetPassword(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Token       string `json:"token"`
		NewPassword string `json:"new_password"`
	}
	if !decodeAuthBody(w, r, &body) {
		return
	}
	if len(body.NewPassword) < minPasswordLength {
		authError(w, http.StatusBadRequest, "password_too_short")
		return
	}
	hash, err := hashPassword(body.NewPassword)
	if err != nil {
		authError(w, http.StatusInternalServerError, "internal_error")
		return
	}
	var id string
	err = h.DB.QueryRowContext(r.Context(),
		`UPDATE "users" SET password_hash = $1, reset_token_hash = NULL, reset_token_expires_at = NULL
		 WHERE reset_token_hash = $2 AND reset_token_expires_at > NOW() RETURNING id::text`,
		hash, sha256Hex(body.Token),
	).Scan(&id)
	if err != nil {
		authError(w, http.StatusBadRequest, "invalid_or_expired_token")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func deliverResetLink(email, token string) {
	base := strings.TrimRight(os.Getenv("APP_BASE_URL"), "/")
	if base == "" {
		base = "http://localhost:3000"
	}
	link := base + "/reset-password?token=" + token
	apiKey, from := os.Getenv("RESEND_API_KEY"), os.Getenv("EMAIL_FROM")
	switch {
	case apiKey != "" && from != "":
		if err := sendViaResend(apiKey, from, email, link); err != nil {
			log.Printf("password reset email could not be sent: %v", err)
		}
	case os.Getenv("OMNISTACKAI_DEV_MODE") == "1":
		log.Printf("DEV MODE: password reset link for %s: %s", email, link)
	default:
		log.Printf("password reset requested but email is not configured (set RESEND_API_KEY and EMAIL_FROM)")
	}
}

func sendViaResend(apiKey, from, to, link string) error {
	payload, err := json.Marshal(map[string]any{
		"from":    from,
		"to":      []string{to},
		"subject": "Reset your password",
		"text": fmt.Sprintf("Someone asked to reset the password for this account.\n\n"+
			"Choose a new password here (the link works once, for %d minutes):\n%s\n\n"+
			"If it was not you, ignore this email; your password is unchanged.", resetTokenMinutes, link),
	})
	if err != nil {
		return err
	}
	req, err := http.NewRequest(http.MethodPost, "https://api.resend.com/emails", bytes.NewReader(payload))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")
	resp, err := (&http.Client{Timeout: 10 * time.Second}).Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("resend answered %d", resp.StatusCode)
	}
	return nil
}
'''


NODE_AUTH_CORE = r'''// Generated by OmniStackAI: account flow core (R-591)
//
// register, login, me, forgot-password and reset-password with the same contract as the Python
// and Go backends, so one web or mobile app works against any of them. Framework-neutral: the
// Express and Hono routers are thin adapters over these functions.
//
// Passwords: PBKDF2-SHA256, 100 000 iterations, random 32-byte salt, "<hex_salt>:<hex_digest>".
// Tokens: HS256 JWT signed with JWT_SECRET; verification checks the algorithm, compares signatures
// in constant time and rejects expired tokens. A reset link is emailed through Resend when
// RESEND_API_KEY and EMAIL_FROM are set, printed to the log in dev mode otherwise, and never
// returned in a response.
import * as crypto from 'node:crypto';
import { pool } from '../db/pool.js';
import { config } from '../config.js';

export const MIN_PASSWORD_LENGTH = 8;
const RESET_TOKEN_MINUTES = 60;
const TOKEN_TTL_SECONDS = 24 * 60 * 60;
const ITERATIONS = 100000;
const DEFAULT_ROLE = 'user';

export interface AuthClaims {
  sub: string;
  email?: string;
  role?: string;
  roles?: string[];
  exp?: number;
  [key: string]: unknown;
}

export interface Result {
  status: number;
  body?: unknown;
}

interface UserRow {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
}

const fail = (status: number, detail: string): Result => ({ status, body: { detail } });

export function signToken(claims: Record<string, unknown>, secret: string): string {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify(claims)).toString('base64url');
  const signature = crypto.createHmac('sha256', secret).update(`${header}.${payload}`).digest('base64url');
  return `${header}.${payload}.${signature}`;
}

export function verifyToken(token: string, secret: string): AuthClaims | null {
  try {
    const [headerB64, payloadB64, signatureB64] = token.split('.');
    if (!headerB64 || !payloadB64 || !signatureB64 || !secret) return null;
    const header = JSON.parse(Buffer.from(headerB64, 'base64url').toString('utf-8'));
    if (header.alg !== 'HS256') return null;
    const expected = crypto.createHmac('sha256', secret).update(`${headerB64}.${payloadB64}`).digest();
    const given = Buffer.from(signatureB64, 'base64url');
    if (given.length !== expected.length || !crypto.timingSafeEqual(given, expected)) return null;
    const claims = JSON.parse(Buffer.from(payloadB64, 'base64url').toString('utf-8')) as AuthClaims;
    if (typeof claims.exp === 'number' && claims.exp * 1000 < Date.now()) return null;
    return claims;
  } catch {
    return null;
  }
}

export function hashPassword(plain: string): string {
  const salt = crypto.randomBytes(32);
  const digest = crypto.pbkdf2Sync(plain, salt, ITERATIONS, 32, 'sha256');
  return `${salt.toString('hex')}:${digest.toString('hex')}`;
}

export function verifyPassword(plain: string, stored: string): boolean {
  const [saltHex, digestHex] = (stored || '').split(':');
  if (!saltHex || !digestHex) return false;
  const expected = Buffer.from(digestHex, 'hex');
  if (expected.length === 0) return false;
  const candidate = crypto.pbkdf2Sync(plain, Buffer.from(saltHex, 'hex'), ITERATIONS, expected.length, 'sha256');
  return crypto.timingSafeEqual(candidate, expected);
}

const normalizeEmail = (email: unknown) => String(email ?? '').trim().toLowerCase();
const validEmail = (email: string) =>
  email.includes('@') && email.length <= 254 && !email.startsWith('@') && !email.endsWith('@');
const sha256Hex = (value: string) => crypto.createHash('sha256').update(value).digest('hex');

function issue(status: number, user: UserRow): Result {
  if (!config.jwtSecret) return fail(500, 'auth_not_configured');
  const token = signToken(
    {
      sub: user.id, email: user.email, role: user.role, roles: [user.role], full_name: user.full_name,
      exp: Math.floor(Date.now() / 1000) + TOKEN_TTL_SECONDS,
    },
    config.jwtSecret,
  );
  return { status, body: { access_token: token, token_type: 'bearer', user } };
}

export async function register(body: any): Promise<Result> {
  const email = normalizeEmail(body?.email);
  if (!validEmail(email)) return fail(400, 'invalid_email');
  const password = String(body?.password ?? '');
  if (password.length < MIN_PASSWORD_LENGTH) return fail(400, 'password_too_short');
  // A role in the request is ignored, so nobody can sign themselves up as an admin.
  const result = await pool.query(
    `INSERT INTO "users" (email, password_hash, full_name, role) VALUES ($1, $2, $3, $4)
     ON CONFLICT (email) DO NOTHING RETURNING id::text AS id, email, full_name, role`,
    [email, hashPassword(password), body?.full_name ?? null, DEFAULT_ROLE],
  );
  if (result.rows.length === 0) return fail(409, 'email_already_registered');
  return issue(201, result.rows[0] as UserRow);
}

export async function login(body: any): Promise<Result> {
  const result = await pool.query(
    'SELECT id::text AS id, email, password_hash, full_name, role FROM "users" WHERE email = $1',
    [normalizeEmail(body?.email)],
  );
  const row = result.rows[0];
  if (!row || !verifyPassword(String(body?.password ?? ''), row.password_hash)) {
    return fail(401, 'invalid_credentials');
  }
  const { password_hash: _ignored, ...user } = row;
  return issue(200, user as UserRow);
}

export async function me(authorization: string | undefined): Promise<Result> {
  if (!authorization || !authorization.startsWith('Bearer ')) return fail(401, 'unauthorized');
  const claims = verifyToken(authorization.slice(7).trim(), config.jwtSecret);
  if (!claims) return fail(401, 'invalid_token');
  const result = await pool.query(
    'SELECT id::text AS id, email, full_name, role FROM "users" WHERE id::text = $1',
    [String(claims.sub ?? '')],
  );
  if (result.rows.length === 0) return fail(401, 'invalid_token');
  return { status: 200, body: result.rows[0] };
}

export async function forgotPassword(body: any): Promise<Result> {
  const email = normalizeEmail(body?.email);
  const token = crypto.randomBytes(32).toString('hex');
  const result = await pool.query(
    `UPDATE "users" SET reset_token_hash = $1, reset_token_expires_at = NOW() + make_interval(mins => $2)
     WHERE email = $3 RETURNING id`,
    [sha256Hex(token), RESET_TOKEN_MINUTES, email],
  );
  if (result.rows.length > 0) await deliverResetLink(email, token);
  // The same answer either way, so this cannot be used to discover who is registered.
  return { status: 200, body: { status: 'ok' } };
}

export async function resetPassword(body: any): Promise<Result> {
  const password = String(body?.new_password ?? '');
  if (password.length < MIN_PASSWORD_LENGTH) return fail(400, 'password_too_short');
  const result = await pool.query(
    `UPDATE "users" SET password_hash = $1, reset_token_hash = NULL, reset_token_expires_at = NULL
     WHERE reset_token_hash = $2 AND reset_token_expires_at > NOW() RETURNING id`,
    [hashPassword(password), sha256Hex(String(body?.token ?? ''))],
  );
  if (result.rows.length === 0) return fail(400, 'invalid_or_expired_token');
  return { status: 200, body: { status: 'ok' } };
}

async function deliverResetLink(email: string, token: string): Promise<void> {
  const base = (process.env.APP_BASE_URL || 'http://localhost:3000').replace(/\/+$/, '');
  const link = `${base}/reset-password?token=${token}`;
  const apiKey = process.env.RESEND_API_KEY;
  const from = process.env.EMAIL_FROM;
  if (apiKey && from) {
    try {
      const res = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from,
          to: [email],
          subject: 'Reset your password',
          text:
            'Someone asked to reset the password for this account.\n\n' +
            `Choose a new password here (the link works once, for ${RESET_TOKEN_MINUTES} minutes):\n${link}\n\n` +
            'If it was not you, ignore this email; your password is unchanged.',
        }),
      });
      if (!res.ok) console.error(`password reset email could not be sent: resend answered ${res.status}`);
    } catch (err) {
      console.error('password reset email could not be sent', err);
    }
  } else if (process.env.OMNISTACKAI_DEV_MODE === '1') {
    console.warn(`DEV MODE: password reset link for ${email}: ${link}`);
  } else {
    console.warn('password reset requested but email is not configured (set RESEND_API_KEY and EMAIL_FROM)');
  }
}
'''

NODE_AUTH_ROUTER_EXPRESS = r'''// Generated by OmniStackAI: account routes (R-591), Express adapter over ../auth/core
import { Router, Request, Response } from 'express';
import * as auth from '../auth/core.js';

export const router = Router();

function send(res: Response, result: auth.Result) {
  if (result.body === undefined) return res.status(result.status).end();
  return res.status(result.status).json(result.body);
}

function handle(fn: (req: Request) => Promise<auth.Result>) {
  return async (req: Request, res: Response) => {
    try {
      send(res, await fn(req));
    } catch (err) {
      console.error(err);
      res.status(500).json({ detail: 'internal_error' });
    }
  };
}

router.post('/register', handle((req) => auth.register(req.body)));
router.post('/login', handle((req) => auth.login(req.body)));
router.get('/me', handle((req) => auth.me(req.headers.authorization)));
router.post('/logout', handle(async () => ({ status: 204 })));
router.post('/forgot-password', handle((req) => auth.forgotPassword(req.body)));
router.post('/reset-password', handle((req) => auth.resetPassword(req.body)));
'''

NODE_AUTH_ROUTER_HONO = r'''// Generated by OmniStackAI: account routes (R-591), Hono adapter over ../auth/core
import { Hono, Context } from 'hono';
import * as auth from '../auth/core.js';

export const router = new Hono();

async function handle(c: Context, fn: () => Promise<auth.Result>) {
  try {
    const result = await fn();
    if (result.body === undefined) return c.body(null, result.status as any);
    return c.json(result.body as any, result.status as any);
  } catch (err) {
    console.error(err);
    return c.json({ detail: 'internal_error' }, 500);
  }
}

const body = async (c: Context) => c.req.json().catch(() => ({}));

router.post('/register', async (c) => handle(c, async () => auth.register(await body(c))));
router.post('/login', async (c) => handle(c, async () => auth.login(await body(c))));
router.get('/me', async (c) => handle(c, () => auth.me(c.req.header('Authorization'))));
router.post('/logout', async (c) => handle(c, async () => ({ status: 204 })));
router.post('/forgot-password', async (c) => handle(c, async () => auth.forgotPassword(await body(c))));
router.post('/reset-password', async (c) => handle(c, async () => auth.resetPassword(await body(c))));
'''


def is_account_route(path: str) -> bool:
    """True for a path the generated account flow owns.

    Models often put their own `/auth/login` in a plan. With the account flow generated, that
    endpoint would be emitted twice: Go's ServeMux panics at start-up on a duplicate pattern, and
    the Python and Node backends would write two `auth` modules over each other. The account flow
    is the complete, tested implementation, so it wins and the plan's copy is left out.
    """
    return path == "/auth" or path.startswith("/auth/")


RN_AUTH_CONTEXT = r'''// Generated by OmniStackAI: session state for the mobile app (R-591)
//
// The session survives an app restart: the token lives in the Keychain (iOS) or Keystore (Android)
// through expo-secure-store, never in plain storage. Sign-in, sign-up and password recovery call
// the backend's /auth routes, which every generated backend implements identically.
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import * as SecureStore from 'expo-secure-store';
import { apiClient, setAuthToken } from '../api/client';

const TOKEN_KEY = 'omnistack.session';

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string | null;
  role?: string;
}

interface TokenResponse {
  access_token: string;
  user: UserProfile;
}

interface AuthContextValue {
  user: UserProfile | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const clear = useCallback(async () => {
    setToken(null);
    setUser(null);
    setAuthToken(null);
    await SecureStore.deleteItemAsync(TOKEN_KEY).catch(() => undefined);
  }, []);

  // Restore the session on launch; an expired or revoked token signs the user out quietly.
  useEffect(() => {
    (async () => {
      try {
        const stored = await SecureStore.getItemAsync(TOKEN_KEY);
        if (stored) {
          setAuthToken(stored);
          const me = await apiClient.get<UserProfile>('/auth/me');
          setToken(stored);
          setUser(me);
        }
      } catch {
        await clear();
      } finally {
        setLoading(false);
      }
    })();
  }, [clear]);

  const start = useCallback(async (data: TokenResponse) => {
    await SecureStore.setItemAsync(TOKEN_KEY, data.access_token);
    setAuthToken(data.access_token);
    setToken(data.access_token);
    setUser(data.user);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await start(await apiClient.post<TokenResponse>('/auth/login', { email, password }));
  }, [start]);

  const register = useCallback(async (fullName: string, email: string, password: string) => {
    await start(await apiClient.post<TokenResponse>('/auth/register', { full_name: fullName, email, password }));
  }, [start]);

  const forgotPassword = useCallback(async (email: string) => {
    await apiClient.post<{ status: string }>('/auth/forgot-password', { email });
  }, []);

  const logout = useCallback(async () => {
    await apiClient.post('/auth/logout', {}).catch(() => undefined);
    await clear();
  }, [clear]);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, forgotPassword, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>');
  return value;
};
'''

RN_AUTH_SCREENS = r'''// Generated by OmniStackAI: sign-in, sign-up and password recovery screens (R-591)
import React, { useState } from 'react';
import { Text, TouchableOpacity, StyleSheet, View } from 'react-native';
import { ScreenContainer } from '../../design-system/components/ScreenContainer';
import { Input } from '../../design-system/components/Input';
import { Button } from '../../design-system/components/Button';
import { tokens } from '../../design-system/tokens';
import { useAuth } from '../../shared/auth/AuthContext';

const MIN_PASSWORD_LENGTH = 8;

const MESSAGES: Record<string, string> = {
  invalid_credentials: 'That email and password do not match.',
  email_already_registered: 'An account with this email already exists. Try signing in.',
  invalid_email: 'Enter a valid email address.',
  password_too_short: `Use at least ${MIN_PASSWORD_LENGTH} characters.`,
};

const explain = (err: unknown) => {
  const code = err instanceof Error ? err.message : '';
  return MESSAGES[code] || code || 'Something went wrong. Please try again.';
};

export const LoginScreen: React.FC<{ navigation: any }> = ({ navigation }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password);
      navigation.goBack();
    } catch (err) {
      setError(explain(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScreenContainer>
      <Text style={styles.title}>Welcome back</Text>
      <Text style={styles.subtitle}>Sign in to continue.</Text>
      {error && <Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
      <Input label="Email" value={email} onChangeText={setEmail} autoCapitalize="none"
        autoComplete="email" keyboardType="email-address" textContentType="emailAddress" />
      <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry
        autoComplete="password" textContentType="password" onSubmitEditing={submit} />
      <Button title="Sign in" onPress={submit} loading={busy} disabled={!email || !password} />
      <TouchableOpacity onPress={() => navigation.navigate('ForgotPassword')} style={styles.link}>
        <Text style={styles.linkText}>Forgot your password?</Text>
      </TouchableOpacity>
      <View style={styles.row}>
        <Text style={styles.muted}>New here? </Text>
        <TouchableOpacity onPress={() => navigation.replace('Register')}>
          <Text style={styles.linkText}>Create an account</Text>
        </TouchableOpacity>
      </View>
    </ScreenContainer>
  );
};

export const RegisterScreen: React.FC<{ navigation: any }> = ({ navigation }) => {
  const { register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError(null);
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(MESSAGES.password_too_short);
      return;
    }
    setBusy(true);
    try {
      await register(fullName.trim(), email.trim(), password);
      navigation.goBack();
    } catch (err) {
      setError(explain(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScreenContainer>
      <Text style={styles.title}>Create your account</Text>
      <Text style={styles.subtitle}>It takes less than a minute.</Text>
      {error && <Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
      <Input label="Full name" value={fullName} onChangeText={setFullName} autoComplete="name" textContentType="name" />
      <Input label="Email" value={email} onChangeText={setEmail} autoCapitalize="none"
        autoComplete="email" keyboardType="email-address" textContentType="emailAddress" />
      <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry
        autoComplete="password-new" textContentType="newPassword"
        placeholder={`At least ${MIN_PASSWORD_LENGTH} characters`} />
      <Button title="Create account" onPress={submit} loading={busy} disabled={!email || !password} />
      <View style={styles.row}>
        <Text style={styles.muted}>Already have an account? </Text>
        <TouchableOpacity onPress={() => navigation.replace('Login')}>
          <Text style={styles.linkText}>Sign in</Text>
        </TouchableOpacity>
      </View>
    </ScreenContainer>
  );
};

export const ForgotPasswordScreen: React.FC<{ navigation: any }> = ({ navigation }) => {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError(null);
    setBusy(true);
    try {
      await forgotPassword(email.trim());
      setSent(true);
    } catch (err) {
      setError(explain(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScreenContainer>
      <Text style={styles.title}>Reset your password</Text>
      {sent ? (
        <>
          <Text style={styles.subtitle}>
            If an account exists for {email.trim()}, we have emailed a link to choose a new password.
            It works once, for one hour.
          </Text>
          <Button title="Back to sign in" onPress={() => navigation.navigate('Login')} />
        </>
      ) : (
        <>
          <Text style={styles.subtitle}>Enter your email and we will send you a reset link.</Text>
          {error && <Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
          <Input label="Email" value={email} onChangeText={setEmail} autoCapitalize="none"
            autoComplete="email" keyboardType="email-address" textContentType="emailAddress"
            onSubmitEditing={submit} />
          <Button title="Send reset link" onPress={submit} loading={busy} disabled={!email} />
        </>
      )}
    </ScreenContainer>
  );
};

/** Sign in / sign out, shown in the home screen header. */
export const AuthHeaderButton: React.FC<{ navigation: any }> = ({ navigation }) => {
  const { user, logout, loading } = useAuth();
  if (loading) return null;
  return user ? (
    <TouchableOpacity accessibilityRole="button" onPress={logout}>
      <Text style={styles.linkText}>Sign out</Text>
    </TouchableOpacity>
  ) : (
    <TouchableOpacity accessibilityRole="button" onPress={() => navigation.navigate('Login')}>
      <Text style={styles.linkText}>Sign in</Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  title: {
    fontSize: tokens.fontSize.xxl,
    fontWeight: '800',
    color: tokens.colors.text,
    marginTop: tokens.spacing.lg,
  },
  subtitle: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textMuted,
    marginTop: tokens.spacing.xs,
    marginBottom: tokens.spacing.lg,
    lineHeight: 20,
  },
  error: {
    color: tokens.colors.danger,
    fontSize: tokens.fontSize.sm,
    marginBottom: tokens.spacing.md,
  },
  link: { marginTop: tokens.spacing.md, alignSelf: 'center' },
  linkText: { color: tokens.colors.primary, fontWeight: '600', fontSize: tokens.fontSize.sm },
  row: { flexDirection: 'row', justifyContent: 'center', marginTop: tokens.spacing.lg },
  muted: { color: tokens.colors.textMuted, fontSize: tokens.fontSize.sm },
});
'''
