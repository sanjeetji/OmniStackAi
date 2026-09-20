package skills

import (
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"

	"github.com/sanjeetji/OmniStackAi/services/control-plane/internal/auth"
)

type Deps struct {
	AuthStore  auth.Store
	SkillStore Store
	Logger     *slog.Logger
}

func (d Deps) logger() *slog.Logger {
	if d.Logger != nil {
		return d.Logger
	}
	return slog.Default()
}

func Register(mux *http.ServeMux, deps Deps) {
	mux.HandleFunc("GET /skills", handleListSkills(deps))
	mux.HandleFunc("POST /skills", handleCreateSkill(deps))
	mux.HandleFunc("GET /skills/{id}", handleGetSkill(deps))
	mux.HandleFunc("PATCH /skills/{id}", handleUpdateSkill(deps))
	mux.HandleFunc("DELETE /skills/{id}", handleDeleteSkill(deps))

	mux.HandleFunc("GET /projects/{id}/knowledge", handleGetProjectKnowledge(deps))
	mux.HandleFunc("PUT /projects/{id}/knowledge", handleUpdateProjectKnowledge(deps))
	mux.HandleFunc("GET /projects/{id}/skills", handleListProjectSkills(deps))
	mux.HandleFunc("PUT /projects/{id}/skills/{skillId}", handleAttachProjectSkill(deps))
	mux.HandleFunc("DELETE /projects/{id}/skills/{skillId}", handleDetachProjectSkill(deps))
}

func requireUser(deps Deps, r *http.Request) (*auth.User, int, string) {
	user, err := auth.RequireUser(r.Context(), deps.AuthStore, r)
	if err != nil {
		if errors.Is(err, auth.ErrUnauthenticated) {
			return nil, http.StatusUnauthorized, "session expired or invalid"
		}
		deps.logger().Error("lookup user by token", "error", err)
		return nil, http.StatusInternalServerError, "database error"
	}
	return &user, http.StatusOK, ""
}

func jsonResponse(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func jsonError(w http.ResponseWriter, status int, message string) {
	jsonResponse(w, status, map[string]string{"error": message})
}

func handleListSkills(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, status, errStr := requireUser(deps, r)
		if user == nil {
			jsonError(w, status, errStr)
			return
		}

		skillsList, err := deps.SkillStore.ListSkills(r.Context(), user.ID)
		if err != nil {
			deps.logger().Error("list skills failed", "error", err, "user_id", user.ID)
			jsonError(w, http.StatusInternalServerError, "failed to list skills")
			return
		}

		jsonResponse(w, http.StatusOK, skillsList)
	}
}

type CreateSkillRequest struct {
	Name        string `json:"name"`
	Title       string `json:"title"`
	Description string `json:"description"`
	Body        string `json:"body"`
	IsDefault   bool   `json:"is_default"`
}

func handleCreateSkill(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, status, errStr := requireUser(deps, r)
		if user == nil {
			jsonError(w, status, errStr)
			return
		}

		var req CreateSkillRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			jsonError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		sk, err := deps.SkillStore.CreateSkill(
			r.Context(), user.ID, req.Name, req.Title, req.Description, req.Body, req.IsDefault,
		)
		if err != nil {
			if errors.Is(err, ErrInvalidSkillName) || errors.Is(err, ErrEmptySkillTitle) || errors.Is(err, ErrSkillBodyTooLarge) {
				jsonError(w, http.StatusBadRequest, err.Error())
				return
			}
			if errors.Is(err, ErrSkillAlreadyExists) {
				jsonError(w, http.StatusConflict, err.Error())
				return
			}
			deps.logger().Error("create skill failed", "error", err, "user_id", user.ID)
			jsonError(w, http.StatusInternalServerError, "failed to create skill")
			return
		}

		jsonResponse(w, http.StatusCreated, sk)
	}
}

func handleGetSkill(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, status, errStr := requireUser(deps, r)
		if user == nil {
			jsonError(w, status, errStr)
			return
		}

		skillID := r.PathValue("id")
		sk, err := deps.SkillStore.GetSkill(r.Context(), user.ID, skillID)
		if err != nil {
			if errors.Is(err, ErrSkillNotFound) {
				jsonError(w, http.StatusNotFound, "skill not found")
				return
			}
			deps.logger().Error("get skill failed", "error", err, "skill_id", skillID)
			jsonError(w, http.StatusInternalServerError, "failed to get skill")
			return
		}

		jsonResponse(w, http.StatusOK, sk)
	}
}

type UpdateSkillRequest struct {
	Title       string `json:"title"`
	Description string `json:"description"`
	Body        string `json:"body"`
	IsDefault   bool   `json:"is_default"`
}

func handleUpdateSkill(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, status, errStr := requireUser(deps, r)
		if user == nil {
			jsonError(w, status, errStr)
			return
		}

		skillID := r.PathValue("id")
		var req UpdateSkillRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			jsonError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		sk, err := deps.SkillStore.UpdateSkill(
			r.Context(), user.ID, skillID, req.Title, req.Description, req.Body, req.IsDefault,
		)
		if err != nil {
			if errors.Is(err, ErrSkillNotFound) {
				jsonError(w, http.StatusNotFound, "skill not found")
				return
			}
			if errors.Is(err, ErrEmptySkillTitle) || errors.Is(err, ErrSkillBodyTooLarge) {
				jsonError(w, http.StatusBadRequest, err.Error())
				return
			}
			deps.logger().Error("update skill failed", "error", err, "skill_id", skillID)
			jsonError(w, http.StatusInternalServerError, "failed to update skill")
			return
		}

		jsonResponse(w, http.StatusOK, sk)
	}
}

func handleDeleteSkill(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, status, errStr := requireUser(deps, r)
		if user == nil {
			jsonError(w, status, errStr)
			return
		}

		skillID := r.PathValue("id")
		if err := deps.SkillStore.DeleteSkill(r.Context(), user.ID, skillID); err != nil {
			if errors.Is(err, ErrSkillNotFound) {
				jsonError(w, http.StatusNotFound, "skill not found")
				return
			}
			deps.logger().Error("delete skill failed", "error", err, "skill_id", skillID)
			jsonError(w, http.StatusInternalServerError, "failed to delete skill")
			return
		}

		jsonResponse(w, http.StatusOK, map[string]bool{"deleted": true})
	}
}

func handleGetProjectKnowledge(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, status, errStr := requireUser(deps, r)
		if user == nil {
			jsonError(w, status, errStr)
			return
		}

		projectID := r.PathValue("id")
		pk, err := deps.SkillStore.GetProjectKnowledge(r.Context(), user.ID, projectID)
		if err != nil {
			if errors.Is(err, ErrProjectNotFound) {
				jsonError(w, http.StatusNotFound, "project not found")
				return
			}
			deps.logger().Error("get project knowledge failed", "error", err, "project_id", projectID)
			jsonError(w, http.StatusInternalServerError, "failed to get project knowledge")
			return
		}

		jsonResponse(w, http.StatusOK, pk)
	}
}

type UpdateKnowledgeRequest struct {
	Knowledge string `json:"knowledge"`
}

func handleUpdateProjectKnowledge(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, status, errStr := requireUser(deps, r)
		if user == nil {
			jsonError(w, status, errStr)
			return
		}

		projectID := r.PathValue("id")
		var req UpdateKnowledgeRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			jsonError(w, http.StatusBadRequest, "invalid request body")
			return
		}

		pk, err := deps.SkillStore.UpdateProjectKnowledge(r.Context(), user.ID, projectID, req.Knowledge)
		if err != nil {
			if errors.Is(err, ErrProjectNotFound) {
				jsonError(w, http.StatusNotFound, "project not found")
				return
			}
			if errors.Is(err, ErrKnowledgeTooLarge) {
				jsonError(w, http.StatusBadRequest, err.Error())
				return
			}
			deps.logger().Error("update project knowledge failed", "error", err, "project_id", projectID)
			jsonError(w, http.StatusInternalServerError, "failed to update project knowledge")
			return
		}

		jsonResponse(w, http.StatusOK, pk)
	}
}

func handleListProjectSkills(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, status, errStr := requireUser(deps, r)
		if user == nil {
			jsonError(w, status, errStr)
			return
		}

		projectID := r.PathValue("id")
		skillsList, err := deps.SkillStore.ListProjectSkills(r.Context(), user.ID, projectID)
		if err != nil {
			if errors.Is(err, ErrProjectNotFound) {
				jsonError(w, http.StatusNotFound, "project not found")
				return
			}
			deps.logger().Error("list project skills failed", "error", err, "project_id", projectID)
			jsonError(w, http.StatusInternalServerError, "failed to list project skills")
			return
		}

		jsonResponse(w, http.StatusOK, skillsList)
	}
}

func handleAttachProjectSkill(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, status, errStr := requireUser(deps, r)
		if user == nil {
			jsonError(w, status, errStr)
			return
		}

		projectID := r.PathValue("id")
		skillID := r.PathValue("skillId")
		err := deps.SkillStore.AttachProjectSkill(r.Context(), user.ID, projectID, skillID)
		if err != nil {
			if errors.Is(err, ErrProjectNotFound) {
				jsonError(w, http.StatusNotFound, "project not found")
				return
			}
			if errors.Is(err, ErrSkillNotFound) {
				jsonError(w, http.StatusNotFound, "skill not found")
				return
			}
			deps.logger().Error("attach project skill failed", "error", err, "project_id", projectID, "skill_id", skillID)
			jsonError(w, http.StatusInternalServerError, "failed to attach skill")
			return
		}

		jsonResponse(w, http.StatusOK, map[string]bool{"attached": true})
	}
}

func handleDetachProjectSkill(deps Deps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, status, errStr := requireUser(deps, r)
		if user == nil {
			jsonError(w, status, errStr)
			return
		}

		projectID := r.PathValue("id")
		skillID := r.PathValue("skillId")
		err := deps.SkillStore.DetachProjectSkill(r.Context(), user.ID, projectID, skillID)
		if err != nil {
			if errors.Is(err, ErrProjectNotFound) {
				jsonError(w, http.StatusNotFound, "project not found")
				return
			}
			deps.logger().Error("detach project skill failed", "error", err, "project_id", projectID, "skill_id", skillID)
			jsonError(w, http.StatusInternalServerError, "failed to detach skill")
			return
		}

		jsonResponse(w, http.StatusOK, map[string]bool{"detached": true})
	}
}
