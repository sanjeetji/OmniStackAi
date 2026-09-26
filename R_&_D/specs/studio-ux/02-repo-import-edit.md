# Spec: Existing Repo Import + Edit (Both Modes)

**Tracker ID:** R-628
**Phase:** 4 — Engineering Mode Hardening
**Priority:** P1
**Estimated Effort:** 6 weeks
**Dependencies:** Master Spec Section 5
**Status:** Draft

---

## Repo Intelligence Pipeline
```python
# services/agent-engine/src/omnistackai_agent_engine/repo_intel/

class RepoIntelligence:
    def analyze(self, repo_path: Path) -> RepoProfile:
        return RepoProfile(
            framework = self.detect_framework(repo_path),
            language = self.detect_language(repo_path),
            symbol_graph = self.build_symbol_graph(repo_path),  # Tree-sitter
            db_schema = self.extract_db_schema(repo_path),
            api_contracts = self.extract_api_contracts(repo_path),
            component_inventory = self.inventory_components(repo_path),
            test_coverage = self.analyze_tests(repo_path),
            ci_cd = self.parse_ci_cd(repo_path),
            dependencies = self.parse_dependencies(repo_path),
            git_history = self.analyze_git_history(repo_path),
        )

    def detect_framework(self, repo_path: Path) -> Framework:
        # package.json, pyproject.toml, go.mod, Cargo.toml
        # Returns: nextjs | react | vue | svelte | express | fastapi | nestjs | gin | etc.

    def build_symbol_graph(self, repo_path: Path) -> SymbolGraph:
        # Tree-sitter queries for each language
        # Nodes: functions, classes, components, hooks, types
        # Edges: imports, calls, renders, extends
        # Output: JSON graph for LLM context packing
```

## Edit Workflow (Both Modes)
```
# User: "Add Stripe payments to the checkout page"
# 1. Repo Intelligence loads context pack (relevant files only)
# 2. LLM proposes edit plan (max 12 files, bounded by impact engine)
# 3. Validator: only allowed imports, typechecks, no secrets
# 4. Apply in memory -> run verification (tsc + affected tests)
# 5. Repair loop (max 2) with real compiler errors
# 6. Commit to feature branch: "feat: add Stripe checkout integration"
# 7. PR description generated from acceptance criteria
```

## Mode Differences for Repo Edit
| Aspect | Vibe Mode | Engineering Mode |
|--------|-----------|------------------|
| Context Pack | Auto-selected (heuristic) | User-configurable (impact radius) |
| Verification | Typecheck only | Full: typecheck + build + test + security |
| Branch Strategy | Direct to main (solo) | Feature branch + PR (team) |
| Pack Awareness | Auto-detect applicable packs | Explicit pack selection/versioning |
| Rollback | One-click revert | Git revert + deployment rollback |

## Import Sources
- GitHub/GitLab/Bitbucket URL (public/private with token)
- Local zip upload
- Git clone via SSH/HTTPS

## Acceptance Criteria
- [ ] Tree-sitter parses TS/JS/Python/Go/Rust
- [ ] Symbol graph enables precise context packing
- [ ] Impact engine calculates blast radius for any change
- [ ] LLM proposes bounded edits (max 12 files)
- [ ] Verification runs in sandbox
- [ ] Repair loop fixes type errors
- [ ] Commit + PR created with description

## Files to Create
- services/agent-engine/src/omnistackai_agent_engine/repo_intel/analyzer.py
- services/agent-engine/src/omnistackai_agent_engine/repo_intel/tree_sitter.py
- services/agent-engine/src/omnistackai_agent_engine/repo_intel/impact_engine.py
- services/agent-engine/src/omnistackai_agent_engine/studio/repo_import.py
