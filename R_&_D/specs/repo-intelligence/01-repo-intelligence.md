# Spec: Repo Intelligence — Import, Analyze, Edit Existing Projects

**Tracker ID:** R-820
**Phase:** 4 — Engineering Mode Hardening
**Priority:** P1
**Estimated Effort:** 6 weeks
**Dependencies:** R-628 (Studio UX), R-800 (Multi-App Architect), R-600 (Pack Manifest)
**Status:** Draft

---

## 1. Problem Statement

Users have existing projects on GitHub, GitLab, local disk, Vercel, Netlify, Supabase. Engineering Mode must **import → analyze → map to IR → enable pack-based enhancement** — not just "chat edit" but structural understanding enabling: add features, modernize UI, add mobile, full migration.

---

## 2. Competitive Analysis

| Feature | Cursor | GitHub Copilot | v0 | Lovable | Bolt | Emergent | **OmniStackAI Target** |
|---------|--------|----------------|-----|---------|------|----------|------------------------|
| Import GitHub repo | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ **Full analysis** |
| Extract IR (entities, API, UI) | ❌ | Partial | ❌ | ❌ | ❌ | ❌ | ✅ **Complete IR** |
| Map to domain packs | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Auto-detect** |
| Add feature via packs | ❌ | Chat-only | ❌ | ❌ | ❌ | ❌ | ✅ **Structured** |
| Modernize UI (shadcn + Motion) | Chat | Chat | ❌ | ❌ | ❌ | ❌ | ✅ **Component-by-component** |
| Add native mobile | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Role-app generator** |
| Full migration to OmniStackAI | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Regenerate with packs** |
| Multi-language (TS/JS/Python/Go/Rust) | TS/JS | TS/JS/Python | ❌ | ❌ | ❌ | ❌ | ✅ **All 5** |

---

## 3. Requirements

### 3.1 Repo Intelligence Pipeline

```python
# services/agent-engine/src/omnistackai_agent_engine/repo_intel/analyzer.py

class RepoIntelligence:
    def analyze(self, repo_path: Path, config: AnalysisConfig) -> RepoProfile:
        return RepoProfile(
            framework = self.detect_framework(repo_path),
            language = self.detect_language(repo_path),
            symbol_graph = self.build_symbol_graph(repo_path),
            db_schema = self.extract_db_schema(repo_path),
            api_contracts = self.extract_api_contracts(repo_path),
            component_inventory = self.inventory_components(repo_path),
            auth_config = self.extract_auth_config(repo_path),
            env_schema = self.extract_env_schema(repo_path),
            test_coverage = self.analyze_tests(repo_path),
            ci_cd = self.parse_ci_cd(repo_path),
            dependencies = self.parse_dependencies(repo_path),
            git_history = self.analyze_git_history(repo_path),
            pack_recommendations = self.recommend_packs(repo_path),
        )
```
### 3.2 Tree-sitter Queries per Language

```python
# services/agent-engine/src/omnistackai_agent_engine/repo_intel/tree_sitter_queries.py

TREE_SITTER_QUERIES = {
    'typescript': {
        'components': '''
            (export_statement
                (function_declaration
                    name: (identifier) @component.name
                    parameters: (formal_parameters) @component.props
                )
            )
            (jsx_element
                (jsx_opening_element
                    (jsx_identifier) @jsx.component
                )
            )
        ''',
        'api_routes': '''
            (export_statement
                (arrow_function
                    parameters: (formal_parameters
                        (required_parameter
                            pattern: (identifier) @req
                        )
                    )
                )
            )
        ''',
        'database_models': '''
            (call_expression
                function: (member_expression
                    property: (identifier) @model.method
                )
            )
        ''',
    },
    'python': {
        'fastapi_routes': '''
            (decorator
                (call_expression
                    function: (attribute
                        attribute: (identifier) @http_method
                    )
                )
            )
        ''',
        'sqlalchemy_models': '''
            (class_definition
                name: (identifier) @model.name
                bases: (argument_list
                    (attribute
                        attribute: (identifier) @base_model
                    )
                )
            )
        ''',
    },
    'go': {
        'structs': '''
            (type_declaration
                (type_spec
                    name: (type_identifier) @struct.name
                    type: (struct_type) @struct.fields
                )
            )
        ''',
    },
}
```

### 3.3 Context Packing for LLM

```python
# services/agent-engine/src/omnistackai_agent_engine/repo_intel/context_packer.py

class ContextPacker:
    def pack_for_edit(self, profile: RepoProfile, user_request: str, max_tokens: int = 50000) -> ContextPack:
        relevant_nodes = self.semantic_search(profile.symbol_graph, user_request)
        expanded = self.expand_dependencies(profile.symbol_graph, relevant_nodes)
        ranked = self.rank_by_importance(expanded)
        selected_files = self.select_files(ranked, max_tokens)
        
        return ContextPack(
            files = {f.path: f.content for f in selected_files},
            symbol_graph = self.subgraph(profile.symbol_graph, selected_files),
            api_contracts = self.filter_contracts(profile.api_contracts, selected_files),
            db_schema = self.filter_schema(profile.db_schema, selected_files),
            pack_recommendations = profile.pack_recommendations,
            edit_constraints = self.derive_constraints(profile, selected_files),
        )
```

### 3.4 Impact Engine (Blast Radius)

```python
# services/agent-engine/src/omnistackai_agent_engine/repo_intel/impact_engine.py

class ImpactEngine:
    def calculate_impact(self, profile: RepoProfile, proposed_changes: list[FileEdit]) -> ImpactReport:
        affected_symbols = set()
        for edit in proposed_changes:
            symbols = self.symbols_in_file(profile.symbol_graph, edit.file_path)
            affected_symbols.update(symbols)
        
        blast_radius = self.transitive_closure(profile.symbol_graph, affected_symbols)
        
        return ImpactReport(
            directly_modified = list(affected_symbols),
            potentially_affected = list(blast_radius - affected_symbols),
            test_files_to_run = self.find_related_tests(profile, blast_radius),
            build_targets = self.find_build_targets(profile, blast_radius),
            deployment_risk = self.assess_risk(blast_radius, profile),
            suggested_verification = self.suggest_verification(blast_radius),
        )
### 3.5 Edit Workflow (Both Modes)

```python
# services/agent-engine/src/omnistackai_agent_engine/repo_intel/edit_workflow.py

class RepoEditWorkflow:
    def execute_edit(self, repo: RepoProfile, user_request: str, mode: 'vibe' | 'engineering') -> EditResult:
        context = self.context_packer.pack_for_edit(repo, user_request)
        edit_plan = self.llm.propose_edits(context, user_request, mode)
        validation = self.validator.validate(edit_plan, repo)
        
        if mode == 'vibe':
            verification = self.verify_typecheck_only(edit_plan)
        else:
            verification = self.verify_full(edit_plan)
        
        for attempt in range(2):
            if verification.passed:
                break
            edit_plan = self.llm.repair(edit_plan, verification.errors)
            verification = self.verifier(edit_plan)
        
        branch = self.git.create_branch(f"feat/{slugify(user_request)}")
        self.git.apply_edits(edit_plan)
        self.git.commit(f"feat: {user_request}")
        
        pr_description = self.generate_pr_description(edit_plan, verification)
        
        return EditResult(branch=branch, pr_description=pr_description, verification=verification)
```

---

## 4. Import Sources

| Source | Auth Method | Analysis Depth |
|--------|-------------|----------------|
| GitHub/GitLab/Bitbucket | PAT / OAuth / SSH | Full clone + analyze |
| Local folder | Drag-drop / file picker | In-place analysis |
| Vercel/Netlify project | API token | Fetch source + config |
| Supabase project | Project ref + token | Introspect schema + Edge Functions |
| Docker image | Registry auth | Extract + analyze |

---

## 5. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-01 | Tree-sitter parses TS/JS/Python/Go/Rust | Unit tests per language |
| AC-02 | Symbol graph enables precise context packing | Context relevance > 90% |
| AC-03 | Impact engine calculates blast radius for any change | Manual verification |
| AC-04 | LLM proposes bounded edits (max 12 files) | Edit plan size test |
| AC-05 | Verification runs in sandbox (typecheck/build/test) | Integration test |
| AC-06 | Repair loop fixes type errors in ≤2 attempts | Error injection test |
| AC-07 | Commit + PR created with generated description | Git history check |
| AC-08 | Pack recommendations > 80% accurate | Manual audit on 20 repos |

---

## 6. Implementation Tasks

| Task ID | Description | Owner | Estimate |
|---------|-------------|-------|----------|
| R-820.1 | Tree-sitter integration + queries for 5 languages | Platform | 10 days |
| R-820.2 | Repo analyzer (framework, DB, API, components, auth) | AI Engineer | 10 days |
| R-820.3 | Symbol graph builder + JSON export | Platform | 5 days |
| R-820.4 | Context packer (semantic search, dependency expansion) | AI Engineer | 10 days |
| R-820.5 | Impact engine (transitive closure, risk assessment) | Platform | 5 days |
| R-820.6 | Edit workflow (propose → validate → apply → verify → repair → commit) | AI Engineer | 10 days |
| R-820.7 | Import adapters (GitHub, GitLab, Vercel, Netlify, Supabase, local) | Platform | 10 days |
| R-820.8 | Studio UI for import + edit (both modes) | Frontend | 5 days |

---

## 7. Files to Create

- `services/agent-engine/src/omnistackai_agent_engine/repo_intel/analyzer.py`
- `services/agent-engine/src/omnistackai_agent_engine/repo_intel/tree_sitter_queries.py`
- `services/agent-engine/src/omnistackai_agent_engine/repo_intel/context_packer.py`
- `services/agent-engine/src/omnistackai_agent_engine/repo_intel/impact_engine.py`
- `services/agent-engine/src/omnistackai_agent_engine/repo_intel/edit_workflow.py`
- `services/agent-engine/src/omnistackai_agent_engine/repo_intel/import_adapters/`
- `apps/console-web/app/studio/import-repo.tsx`
- `apps/console-web/app/studio/repo-edit-workspace.tsx`

---

## 8. Definition of Done

- [ ] Tree-sitter queries extract symbols for all 5 languages
- [ ] Repo analyzer produces complete RepoProfile
- [ ] Context packer fits within token budget with >90% relevance
- [ ] Impact engine correctly identifies blast radius
- [ ] Edit workflow works in both Vibe + Engineering modes
- [ ] All 6 import sources functional
- [ ] Studio UI integrates seamlessly
- [ ] Documentation: query patterns, context packing, impact assessment
```