"""Tests for React data-fetching & mutation hooks generation (lib/hooks.ts) [R-262]."""

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
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import NextjsWebAdapter, render_hooks

_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
    BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _crud_ir() -> ApplicationIR:
    return ApplicationIR(
        name="Blog App",
        description="A blogging app with posts and comments.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("user"),),
        entities=(
            Entity(
                name="Post",
                fields=(
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING),
                    Field("body", FieldType.TEXT),
                ),
                relations=(
                    Relation("comments", "Comment", RelationKind.ONE_TO_MANY),
                ),
            ),
            Entity(
                name="Comment",
                fields=(
                    Field("id", FieldType.UUID),
                    Field("post_id", FieldType.UUID),
                    Field("body", FieldType.TEXT),
                ),
                relations=(
                    Relation("post", "Post", RelationKind.MANY_TO_ONE),
                ),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
            ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
            ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"),
            ApiEndpoint(HttpMethod.PATCH, "/posts/{id}", request_schema="Post", response_schema="Post"),
            ApiEndpoint(HttpMethod.DELETE, "/posts/{id}", response_schema="Post"),
            ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", response_schema="Comment"),
            ApiEndpoint(HttpMethod.POST, "/comments", request_schema="Comment", response_schema="Comment"),
        ),
    )


class NextjsHooksUnitTests(TestCase):
    def setUp(self) -> None:
        self.ir = _crud_ir()
        self.hooks_content = render_hooks(self.ir)

    def test_hooks_file_emits_use_client_directive(self) -> None:
        self.assertTrue(self.hooks_content.startswith('"use client";'))

    def test_react_imports(self) -> None:
        self.assertIn('import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";', self.hooks_content)
        self.assertIn('import type { Comment, Post } from "./types";', self.hooks_content)
        self.assertIn('import { api, type ApiOptions } from "./api";', self.hooks_content)

    def test_shared_interfaces_emitted(self) -> None:
        self.assertIn("export interface UseListParams {", self.hooks_content)
        self.assertIn("  limit?: number;", self.hooks_content)
        self.assertIn("  offset?: number;", self.hooks_content)
        self.assertIn("  sort?: string;", self.hooks_content)
        self.assertIn('  order?: "asc" | "desc";', self.hooks_content)
        self.assertIn("  q?: string;", self.hooks_content)
        self.assertIn("export interface UseListState<T> {", self.hooks_content)
        self.assertIn("export interface UseDetailState<T> {", self.hooks_content)
        self.assertIn("export interface UseMutationState<TData, TResult = TData> {", self.hooks_content)

    def test_list_hook_generated_with_pagination_and_search(self) -> None:
        self.assertIn("export function useListPosts(", self.hooks_content)
        self.assertIn("const limit = params.limit ?? 100;", self.hooks_content)
        self.assertIn("const offset = params.offset ?? 0;", self.hooks_content)
        self.assertIn("const page = Math.floor(offset / limit) + 1;", self.hooks_content)
        self.assertIn("const pageSize = limit;", self.hooks_content)
        self.assertIn("const totalPages = Math.max(1, Math.ceil(total / limit));", self.hooks_content)
        self.assertIn("const setPage = useCallback((newPage: number) => {", self.hooks_content)
        self.assertIn("const setSearch = useCallback((q: string) => {", self.hooks_content)
        self.assertIn('const setSort = useCallback((sort: string, order?: "asc" | "desc") => {', self.hooks_content)
        self.assertIn("const res = await api.listPostsWithCount({ params, signal: controller.signal, ...options });", self.hooks_content)

    def test_get_detail_hook_generated(self) -> None:
        self.assertIn("export function usePost(", self.hooks_content)
        self.assertIn("id: string | null | undefined,", self.hooks_content)
        self.assertIn("const item = await api.getPost(id, options);", self.hooks_content)
        self.assertIn("setData(item);", self.hooks_content)

    def test_create_mutation_hook_generated(self) -> None:
        self.assertIn("export function useCreatePost() {", self.hooks_content)
        self.assertIn("return await api.createPost(data, options);", self.hooks_content)
        self.assertIn("return { create, mutate: create, loading, error, reset };", self.hooks_content)

    def test_update_mutation_hook_generated(self) -> None:
        self.assertIn("export function useUpdatePost() {", self.hooks_content)
        self.assertIn("return await api.updatePost(id, data, options);", self.hooks_content)
        self.assertIn("return { update, mutate: update, loading, error, reset };", self.hooks_content)

    def test_delete_mutation_hook_generated(self) -> None:
        self.assertIn("export function useDeletePost() {", self.hooks_content)
        self.assertIn("await api.deletePost(id, options);", self.hooks_content)
        self.assertIn("return { remove, mutate: remove, loading, error, reset };", self.hooks_content)

    def test_subcollection_list_hook_generated(self) -> None:
        self.assertIn("export function useListCommentsByPost(", self.hooks_content)
        self.assertIn("postId: string | null | undefined,", self.hooks_content)
        self.assertIn(
            "const res = await api.listCommentsByPostWithCount(postId, { params, ...options, signal: controller.signal });",
            self.hooks_content,
        )

    def test_hooks_object_exported(self) -> None:
        self.assertIn("export const hooks = {", self.hooks_content)
        self.assertIn("  useListPosts,", self.hooks_content)
        self.assertIn("  usePost,", self.hooks_content)
        self.assertIn("  useCreatePost,", self.hooks_content)
        self.assertIn("  useUpdatePost,", self.hooks_content)
        self.assertIn("  useDeletePost,", self.hooks_content)
        self.assertIn("  useListCommentsByPost,", self.hooks_content)
        self.assertIn("  useCreateComment,", self.hooks_content)

    def test_empty_ir_generates_empty_hooks_file(self) -> None:
        empty_ir = ApplicationIR(
            name="Empty",
            description="Empty app",
            platforms=(Platform.WEB,),
            project_strategy=_STRATEGY,
            entities=(),
            apis=(),
        )
        content = render_hooks(empty_ir)
        self.assertTrue(content.startswith('"use client";'))
        self.assertIn("export {};", content)
        self.assertNotIn("useList", content)

    def test_unwired_op_omits_missing_hooks(self) -> None:
        partial_ir = ApplicationIR(
            name="Partial",
            description="Only GET",
            platforms=(Platform.WEB,),
            project_strategy=_STRATEGY,
            entities=(
                Entity("Article", (Field("id", FieldType.UUID), Field("title", FieldType.STRING))),
            ),
            apis=(
                ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
            ),
        )
        content = render_hooks(partial_ir)
        self.assertIn("export function useArticle(", content)
        self.assertNotIn("useListArticles", content)
        self.assertNotIn("useCreateArticle", content)
        self.assertNotIn("useUpdateArticle", content)
        self.assertNotIn("useDeleteArticle", content)

    def test_nextjs_adapter_emits_lib_hooks(self) -> None:
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        paths = set(project.paths())
        self.assertIn("lib/hooks.ts", paths)
        hooks_file = project.get("lib/hooks.ts").content
        self.assertIn("useListPosts", hooks_file)

    def test_example_ir_rideshare_favourites(self) -> None:
        ir = example_ir("rideshare-favourites")
        content = render_hooks(ir)
        self.assertIn("useListDrivers", content)
        self.assertIn("useListFavouriteDrivers", content)
        self.assertNotIn("useDriver", content)
        self.assertNotIn("useCreateDriver", content)

    def test_example_ir_minimal_blog(self) -> None:
        ir = example_ir("minimal-blog")
        content = render_hooks(ir)
        self.assertIn("useListPosts", content)
        self.assertIn("useCreatePost", content)
        self.assertIn("useListCommentsByPost", content)
        self.assertNotIn("useUpdatePost", content)
        self.assertNotIn("useDeletePost", content)
