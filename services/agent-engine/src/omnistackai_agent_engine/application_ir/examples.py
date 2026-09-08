"""Realistic, construction-valid example Application IRs.

Used to drive the codegen adapters in demos and tests, and as reference specs. Each example passes
`validate_ir` with no errors. Pure/offline; no I/O.
"""

from __future__ import annotations

from .errors import InvalidIRError
from .ir import (
    AdminStrategy,
    ApiEndpoint,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    Fixture,
    HttpMethod,
    MobileProfile,
    Platform,
    ProjectStrategy,
    Relation,
    RelationKind,
    RepoStrategy,
    Role,
    Screen,
    AcceptanceCriterion,
    WebStrategy,
)


def rideshare_favourites() -> ApplicationIR:
    return ApplicationIR(
        name="Rideshare Favourites",
        description="Customers can favourite drivers and manage their list.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
            BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("customer", ("read", "write")), Role("admin", ("read",))),
        entities=(
            Entity("Driver", (Field("id", FieldType.UUID), Field("name", FieldType.STRING),
                              Field("rating", FieldType.FLOAT, required=False))),
            Entity(
                "FavouriteDriver",
                (Field("id", FieldType.UUID), Field("created_at", FieldType.DATETIME, required=False)),
                relations=(Relation("driver", "Driver", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/favourites/drivers", auth=True, response_schema="FavouriteDriver"),
            ApiEndpoint(HttpMethod.POST, "/favourites/drivers/{driverId}", auth=True, response_schema="FavouriteDriver"),
            ApiEndpoint(HttpMethod.DELETE, "/favourites/drivers/{driverId}", auth=True),
            ApiEndpoint(HttpMethod.GET, "/drivers", auth=False, response_schema="Driver"),
        ),
        screens=(Screen("favourites", "customer", components=("list", "empty-state"), actions=("add", "remove")),),
        acceptance_criteria=(
            AcceptanceCriterion("fav_add_remove_idempotent", "adding or removing a favourite is idempotent"),
            AcceptanceCriterion("fav_auth_required", "unauthenticated access is rejected"),
        ),
    )


def minimal_blog() -> ApplicationIR:
    return ApplicationIR(
        name="Minimal Blog",
        description="A tiny blog with posts and comments.",
        platforms=(Platform.WEB, Platform.ADMIN, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NEXTJS,
            BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("author", ("read", "write")), Role("reader", ("read",))),
        entities=(
            Entity("Post", (Field("id", FieldType.UUID), Field("title", FieldType.STRING),
                            Field("body", FieldType.TEXT), Field("published", FieldType.BOOL))),
            Entity(
                "Comment",
                (Field("id", FieldType.UUID), Field("body", FieldType.TEXT)),
                relations=(Relation("post", "Post", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/posts", auth=False, response_schema="Post"),
            ApiEndpoint(HttpMethod.POST, "/posts", auth=True, request_schema="Post", response_schema="Post"),
            ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", auth=False, response_schema="Comment"),
        ),
        screens=(
            Screen("post_list", "reader", components=("list",), actions=("open",)),
            Screen("post_editor", "author", components=("form",), actions=("save", "publish")),
        ),
        acceptance_criteria=(
            AcceptanceCriterion("post_publish_toggle", "an author can publish and unpublish a post"),
        ),
        fixtures=(
            Fixture(
                "Post",
                (
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "title": "Hello, world",
                        "body": "The first post.",
                        "published": True,
                    },
                    {
                        "id": "22222222-2222-2222-2222-222222222222",
                        "title": "Draft ideas",
                        "body": "Work in progress — don't ship yet.",
                        "published": False,
                    },
                ),
            ),
            Fixture(
                "Comment",
                (
                    {
                        "id": "33333333-3333-3333-3333-333333333333",
                        "body": "Nice first post!",
                        "post_id": "11111111-1111-1111-1111-111111111111",
                    },
                ),
            ),
        ),
    )


EXAMPLES = {
    "rideshare-favourites": rideshare_favourites,
    "minimal-blog": minimal_blog,
}


def example_ir(name: str) -> ApplicationIR:
    try:
        builder = EXAMPLES[name]
    except KeyError as error:
        raise InvalidIRError(
            f"unknown example {name!r}; known: {', '.join(sorted(EXAMPLES))}"
        ) from error
    return builder()
