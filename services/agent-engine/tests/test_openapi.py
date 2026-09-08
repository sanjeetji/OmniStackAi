"""Tests for OpenAPI 3.1 specification generation from Application IR [R-260]."""

import json
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
    RepoStrategy,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import (
    GoBackendAdapter,
    PythonBackendAdapter,
    assemble_project,
    render_openapi,
    render_openapi_json,
)


def _validation_ir() -> ApplicationIR:
    return ApplicationIR(
        name="Store API",
        description="Online store API",
        platforms=(Platform.BACKEND,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
            BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=(
            Entity(
                "Product",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING, validation=("max_length:100",)),
                    Field("category", FieldType.STRING, validation=("enum:electronics|clothing|food",)),
                    Field("price", FieldType.INT, validation=("min:1", "max:10000")),
                    Field("rating", FieldType.FLOAT, required=False, validation=("min:0.0", "max:5.0")),
                ),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/products", auth=False),
            ApiEndpoint(HttpMethod.POST, "/products", auth=True, required_roles=("admin",), request_schema="Product"),
            ApiEndpoint(HttpMethod.GET, "/products/{id}", auth=False, response_schema="Product"),
            ApiEndpoint(HttpMethod.PUT, "/products/{id}", auth=True, required_roles=("admin",), request_schema="Product"),
            ApiEndpoint(HttpMethod.DELETE, "/products/{id}", auth=True, required_roles=("admin",), response_schema="Product"),
        ),
    )


class OpenApiStructureTests(TestCase):
    def setUp(self) -> None:
        self.doc = render_openapi(example_ir("minimal-blog"))

    def test_openapi_version_and_info(self) -> None:
        self.assertEqual(self.doc["openapi"], "3.1.0")
        self.assertEqual(self.doc["info"]["title"], "Minimal Blog")
        self.assertIn("version", self.doc["info"])

    def test_security_schemes_declared(self) -> None:
        schemes = self.doc["components"]["securitySchemes"]
        self.assertIn("BearerAuth", schemes)
        self.assertEqual(schemes["BearerAuth"]["type"], "http")
        self.assertEqual(schemes["BearerAuth"]["scheme"], "bearer")
        self.assertEqual(schemes["BearerAuth"]["bearerFormat"], "JWT")

    def test_entities_become_schemas(self) -> None:
        schemas = self.doc["components"]["schemas"]
        self.assertIn("Post", schemas)
        self.assertIn("Comment", schemas)
        self.assertIn("ValidationError", schemas)
        self.assertIn("ValidationErrorResponse", schemas)
        self.assertIn("ErrorResponse", schemas)


class OpenApiFieldValidationTests(TestCase):
    def setUp(self) -> None:
        self.doc = render_openapi(_validation_ir())
        self.product_schema = self.doc["components"]["schemas"]["Product"]

    def test_string_length_and_enum_validation_mapped(self) -> None:
        props = self.product_schema["properties"]
        self.assertEqual(props["title"]["type"], "string")
        self.assertEqual(props["title"]["maxLength"], 100)

        self.assertEqual(props["category"]["type"], "string")
        self.assertEqual(props["category"]["enum"], ["electronics", "clothing", "food"])

    def test_numeric_min_max_validation_mapped(self) -> None:
        props = self.product_schema["properties"]
        self.assertEqual(props["price"]["type"], "integer")
        self.assertEqual(props["price"]["minimum"], 1)
        self.assertEqual(props["price"]["maximum"], 10000)

        self.assertEqual(props["rating"]["type"], "number")
        self.assertEqual(props["rating"]["minimum"], 0.0)
        self.assertEqual(props["rating"]["maximum"], 5.0)

    def test_required_fields_listed(self) -> None:
        req = self.product_schema["required"]
        self.assertIn("title", req)
        self.assertIn("category", req)
        self.assertIn("price", req)
        self.assertNotIn("rating", req)


class OpenApiPathsAndOperationsTests(TestCase):
    def setUp(self) -> None:
        self.doc = render_openapi(example_ir("minimal-blog"))
        self.paths = self.doc["paths"]

    def test_list_operation_has_query_params_and_x_total_count_header(self) -> None:
        get_posts = self.paths["/posts"]["get"]
        self.assertEqual(get_posts["operationId"], "listPosts")
        self.assertIn("Post", get_posts["tags"])

        param_names = [p["name"] for p in get_posts["parameters"]]
        self.assertIn("limit", param_names)
        self.assertIn("offset", param_names)
        self.assertIn("sort", param_names)
        self.assertIn("order", param_names)

        resp200 = get_posts["responses"]["200"]
        self.assertIn("X-Total-Count", resp200["headers"])
        self.assertEqual(resp200["headers"]["X-Total-Count"]["schema"]["type"], "integer")
        self.assertEqual(
            resp200["content"]["application/json"]["schema"]["items"]["$ref"],
            "#/components/schemas/Post",
        )

    def test_subcollection_list_operation_has_path_and_query_params(self) -> None:
        get_comments = self.paths["/posts/{postId}/comments"]["get"]
        param_names = [p["name"] for p in get_comments["parameters"]]
        self.assertIn("postId", param_names)
        self.assertIn("limit", param_names)
        self.assertIn("offset", param_names)

        resp200 = get_comments["responses"]["200"]
        self.assertIn("X-Total-Count", resp200["headers"])

    def test_auth_and_roles_mapped_to_security_and_responses(self) -> None:
        post_posts = self.paths["/posts"]["post"]
        self.assertIn("security", post_posts)
        self.assertEqual(post_posts["security"], [{"BearerAuth": []}])
        self.assertIn("401", post_posts["responses"])

        # Test required_roles
        val_doc = render_openapi(_validation_ir())
        val_post = val_doc["paths"]["/products"]["post"]
        self.assertEqual(val_post["security"], [{"BearerAuth": ["admin"]}])
        self.assertIn("403", val_post["responses"])

    def test_crud_request_bodies_and_status_codes(self) -> None:
        val_doc = render_openapi(_validation_ir())
        paths = val_doc["paths"]

        # POST /products -> 201
        self.assertIn("201", paths["/products"]["post"]["responses"])
        self.assertEqual(
            paths["/products"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/Product",
        )

        # PUT /products/{id} -> 200, 400, 404
        put_prod = paths["/products/{id}"]["put"]
        self.assertIn("200", put_prod["responses"])
        self.assertIn("400", put_prod["responses"])
        self.assertIn("404", put_prod["responses"])

        # DELETE /products/{id} -> 204, 404
        del_prod = paths["/products/{id}"]["delete"]
        self.assertIn("204", del_prod["responses"])
        self.assertIn("404", del_prod["responses"])


class OpenApiMonorepoAssemblerTests(TestCase):
    def test_assemble_project_emits_contracts_openapi(self) -> None:
        project = assemble_project(example_ir("minimal-blog"))
        paths = set(project.paths())
        self.assertIn("contracts/openapi.json", paths)

        content = project.get("contracts/openapi.json").content
        parsed = json.loads(content)
        self.assertEqual(parsed["openapi"], "3.1.0")
        self.assertEqual(parsed["info"]["title"], "Minimal Blog")

        readme = project.get("README.md").content
        self.assertIn("contracts/openapi.json", readme)


class OpenApiBackendAdapterTests(TestCase):
    def test_go_backend_emits_openapi_json(self) -> None:
        project = GoBackendAdapter().generate(example_ir("rideshare-favourites"))
        self.assertIn("openapi.json", set(project.paths()))
        parsed = json.loads(project.get("openapi.json").content)
        self.assertEqual(parsed["openapi"], "3.1.0")

    def test_python_backend_emits_openapi_json(self) -> None:
        project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        self.assertIn("openapi.json", set(project.paths()))
        parsed = json.loads(project.get("openapi.json").content)
        self.assertEqual(parsed["openapi"], "3.1.0")


class OpenApiDeterministicTests(TestCase):
    def test_json_output_is_deterministic(self) -> None:
        ir = example_ir("rideshare-favourites")
        out1 = render_openapi_json(ir)
        out2 = render_openapi_json(ir)
        self.assertEqual(out1, out2)
