from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    ApiEndpoint,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    MobileProfile,
    Platform,
    ProjectStrategy,
    Relation,
    RelationKind,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
)
from omnistackai_agent_engine.codegen import (
    GoBackendAdapter,
    NextjsWebAdapter,
    PythonBackendAdapter,
)


def _crud_ir() -> ApplicationIR:
    return ApplicationIR(
        name="Fleet Manager",
        description="Fleet and driver management.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
            BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("admin"),),
        entities=(
            Entity(
                "Company",
                (Field("id", FieldType.UUID), Field("name", FieldType.STRING)),
            ),
            Entity(
                "Driver",
                (
                    Field("id", FieldType.UUID),
                    Field("name", FieldType.STRING),
                    Field("company_id", FieldType.UUID),
                ),
                relations=(Relation("company", "Company", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/drivers", auth=True, response_schema="Driver"),
            ApiEndpoint(HttpMethod.GET, "/drivers/{id}", auth=True, response_schema="Driver"),
            ApiEndpoint(HttpMethod.POST, "/drivers", auth=True, request_schema="Driver", response_schema="Driver"),
            ApiEndpoint(HttpMethod.PUT, "/drivers/{id}", auth=True, request_schema="Driver", response_schema="Driver"),
            ApiEndpoint(HttpMethod.PATCH, "/drivers/{id}", auth=True, request_schema="Driver", response_schema="Driver"),
            ApiEndpoint(HttpMethod.DELETE, "/drivers/{id}", auth=True, response_schema="Driver"),
            ApiEndpoint(HttpMethod.GET, "/companies/{companyId}/drivers", auth=True, response_schema="Driver"),
            ApiEndpoint(HttpMethod.POST, "/custom/action/{actionId}", auth=False),
        ),
        screens=(Screen("drivers", "admin", components=("list",), actions=("create",)),),
    )


class NextjsApiClientTests(TestCase):
    def setUp(self) -> None:
        self.project = NextjsWebAdapter().generate(_crud_ir())
        self.api_ts = self.project.get("lib/api.ts").content

    def test_client_file_present_and_has_base_helpers(self) -> None:
        self.assertIn("lib/api.ts", set(self.project.paths()))
        self.assertIn('const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";', self.api_ts)
        self.assertIn("export interface ApiOptions", self.api_ts)
        self.assertIn("token?: string;", self.api_ts)
        self.assertIn("export class ApiError extends Error", self.api_ts)
        self.assertIn("async function request<T>", self.api_ts)
        self.assertIn('headers["Authorization"] = `Bearer ${token}`;', self.api_ts)

    def test_client_imports_entities(self) -> None:
        self.assertIn('import type { Company, Driver } from "./types";', self.api_ts)

    def test_crud_endpoints_typed(self) -> None:
        # LIST drivers with pagination params
        self.assertIn("export async function listDrivers(", self.api_ts)
        self.assertIn('options?: ApiOptions & { params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc" } }', self.api_ts)
        self.assertIn("Promise<Driver[]>", self.api_ts)

        # GET driver by id
        self.assertIn("export async function getDriver(id: string, options?: ApiOptions): Promise<Driver>", self.api_ts)
        self.assertIn("request<Driver>(`/drivers/${encodeURIComponent(id)}`", self.api_ts)

        # CREATE driver
        self.assertIn("export async function createDriver(data: Partial<Driver>, options?: ApiOptions): Promise<Driver>", self.api_ts)
        self.assertIn('request<Driver>("/drivers", { method: "POST", ...options }, data)', self.api_ts)

        # UPDATE driver (PUT /drivers/{id})
        self.assertIn("export async function updateDriver(id: string, data: Partial<Driver>, options?: ApiOptions): Promise<Driver>", self.api_ts)
        self.assertIn('request<Driver>(`/drivers/${encodeURIComponent(id)}`, { method: "PUT", ...options }, data)', self.api_ts)

        # PATCH update driver (fallback unique name)
        self.assertIn("patchDriversId(id: string, data: Partial<Driver>, options?: ApiOptions): Promise<Driver>", self.api_ts)

        # DELETE driver
        self.assertIn("export async function deleteDriver(id: string, options?: ApiOptions): Promise<void>", self.api_ts)
        self.assertIn('request<void>(`/drivers/${encodeURIComponent(id)}`, { method: "DELETE", ...options })', self.api_ts)

    def test_subcollection_list_by_typed(self) -> None:
        # GET /companies/{companyId}/drivers -> listDriversByCompany
        self.assertIn("export async function listDriversByCompany(companyId: string,", self.api_ts)
        self.assertIn('options?: ApiOptions & { params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc" } }', self.api_ts)
        self.assertIn("Promise<Driver[]>", self.api_ts)
        self.assertIn("`/companies/${encodeURIComponent(companyId)}/drivers`", self.api_ts)

    def test_unwired_custom_endpoint(self) -> None:
        # POST /custom/action/{actionId}
        self.assertIn("postCustomActionActionId(actionId: string, data?: unknown, options?: ApiOptions): Promise<unknown>", self.api_ts)

    def test_api_namespace_exported(self) -> None:
        self.assertIn("export const api = {", self.api_ts)
        self.assertIn("  listDrivers,", self.api_ts)
        self.assertIn("  getDriver,", self.api_ts)
        self.assertIn("  createDriver,", self.api_ts)
        self.assertIn("  updateDriver,", self.api_ts)
        self.assertIn("  deleteDriver,", self.api_ts)
        self.assertIn("  listDriversByCompany,", self.api_ts)

    def test_empty_ir_generates_valid_scaffold(self) -> None:
        empty_ir = ApplicationIR(
            name="Empty App",
            description="No entities or APIs",
            platforms=(Platform.WEB,),
            project_strategy=ProjectStrategy(
                MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
                BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
            ),
        )
        empty_project = NextjsWebAdapter().generate(empty_ir)
        content = empty_project.get("lib/api.ts").content
        self.assertIn("export interface ApiOptions", content)
        self.assertNotIn("import type", content)
        self.assertIn("export const api = {\n};", content)


class BackendCorsTests(TestCase):
    def test_go_backend_cors_middleware(self) -> None:
        project = GoBackendAdapter().generate(_crud_ir())
        main = project.get("main.go").content
        self.assertIn('"os"', main)
        self.assertIn("func corsMiddleware(next http.Handler) http.Handler", main)
        self.assertIn("Access-Control-Allow-Origin", main)
        self.assertIn("Access-Control-Allow-Methods", main)
        self.assertIn("Access-Control-Allow-Headers", main)
        self.assertIn("http.MethodOptions", main)
        self.assertIn("http.StatusNoContent", main)
        self.assertIn("corsMiddleware(mux)", main)

        env = project.get(".env.example").content
        self.assertIn("CORS_ALLOWED_ORIGIN=*", env)

    def test_python_backend_cors_middleware(self) -> None:
        ir = ApplicationIR(
            name="Fleet Manager",
            description="Fleet and driver management.",
            platforms=(Platform.BACKEND,),
            project_strategy=ProjectStrategy(
                MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
                BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
            ),
            entities=_crud_ir().entities,
            apis=_crud_ir().apis,
        )
        project = PythonBackendAdapter().generate(ir)
        main = project.get("app/main.py").content
        self.assertIn("from fastapi.middleware.cors import CORSMiddleware", main)
        self.assertIn("app.add_middleware(", main)
        self.assertIn("CORSMiddleware,", main)
        self.assertIn("allow_origins=", main)
        self.assertIn("allow_methods=", main)
        self.assertIn("allow_headers=", main)

        env = project.get(".env.example").content
        self.assertIn("CORS_ALLOWED_ORIGIN=*", env)
