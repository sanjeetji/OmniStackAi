"""PC-108: the web app's list and detail pages, written for the people who use the app.

Every build uses template pages (model page design is optional), and the web app's list and detail
templates were the operator's: an admin table with density toggles, CSV/JSON export and bulk
selection; a detail page with an ID box, "Copy ID", "Export JSON" and prev/next buttons. Seen in the
PC-101 benchmark screenshots. The web app now gets:

- a list as a responsive grid of cards: the record's image (when it has one), its title, a short
  summary and up to three facts (status, a figure, a date); search, pages, loading placeholders, a
  real error with a retry, and an empty state that says what to do next;
- a detail page as a reading view: title, status and image first, then the formatted body and the
  other fields; edit, delete and the lifecycle's actions only where the API allows them; related
  records (a post's comments) listed below.

The admin app keeps the operator pages, and forms are unchanged. Only the plan's real hooks are
called, so nothing here can promise what the API does not do.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR, Entity, Field, FieldType, Screen
from .route_wiring import Op

_TITLE_NAMES = ("title", "name", "label", "headline", "subject", "full_name", "email")
_IMAGE_NAMES = ("image", "image_url", "photo", "photo_url", "picture", "cover", "cover_image",
                "thumbnail", "avatar", "logo", "banner")
_STATUS_NAMES = ("status", "state", "stage", "category", "type", "kind", "priority")
_MONEY_WORDS = ("price", "amount", "cost", "total", "fee", "salary", "budget", "revenue")
_SUMMARY_NAMES = ("summary", "excerpt", "description", "subtitle", "tagline", "bio", "intro")
_HIDDEN = ("id", "created_by", "owner_id", "user_id", "password", "password_hash")


def _pascal(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in value.replace("-", "_").split("_") if part)


def _plural_name(name: str) -> str:
    return name if name.endswith("s") else f"{name}s"


def _words(value: str) -> str:
    from .nextjs import _title_case

    return _title_case(value)


def _title_field(entity: Entity) -> str:
    names = {f.name: f for f in entity.fields}
    for name in _TITLE_NAMES:
        if name in names:
            return name
    text = next((f.name for f in entity.fields
                 if f.type in (FieldType.STRING, FieldType.TEXT) and f.name not in _HIDDEN), None)
    return text or "id"


def _is_person(entity: Entity) -> bool:
    names = {f.name for f in entity.fields}
    return "first_name" in names and "last_name" in names


def _title_js(entity: Entity, record: str) -> str:
    """The record's title as a JS expression: a person's full name, else the title field."""
    if _is_person(entity):
        return f'([{record}.first_name, {record}.last_name].filter(Boolean).join(" ") || "Unnamed")'
    return f'String({record}.{_title_field(entity)} ?? "Untitled")'


def _is_avatar(entity: Entity, image: Field | None) -> bool:
    """A person's photo is an avatar beside the name, not a banner."""
    return image is not None and (_is_person(entity) or image.name in ("avatar", "photo", "picture", "profile_photo"))


def _is_image_attachment(field: Field) -> bool:
    if field.type is not FieldType.ATTACHMENT:
        return False
    from .upload_policy import policy_for

    return any(ext in ("jpg", "jpeg", "png", "webp", "gif", "avif") for ext in policy_for(field).extensions)


def _image_field(entity: Entity) -> Field | None:
    attachment = next((f for f in entity.fields if _is_image_attachment(f)), None)
    if attachment is not None:
        return attachment
    return next((f for f in entity.fields if f.type is FieldType.STRING and f.name in _IMAGE_NAMES), None)


def _summary_field(entity: Entity, title: str) -> Field | None:
    if _is_person(entity):
        # The name is the title; the way to reach them is the summary.
        return next((f for f in entity.fields if "email" in f.name), None)
    named = next((f for f in entity.fields if f.name in _SUMMARY_NAMES
                  and f.type in (FieldType.STRING, FieldType.TEXT, FieldType.RICH_TEXT)), None)
    if named is not None:
        return named
    for kinds in ((FieldType.RICH_TEXT,), (FieldType.TEXT,), (FieldType.STRING,)):
        found = next((f for f in entity.fields if f.type in kinds and f.name not in (title, *_HIDDEN)
                      and f.name not in _IMAGE_NAMES and not f.name.endswith("_id")
                      and "email" not in f.name and "url" not in f.name), None)
        if found is not None:
            return found
    return None


def _is_status(field: Field) -> bool:
    from .field_validation import parse_field_rules

    return field.type is FieldType.BOOL or bool(parse_field_rules(field).enum) or (
        field.type is FieldType.STRING and field.name in _STATUS_NAMES)


def _fact_fields(entity: Entity, used: set[str]) -> list[Field]:
    """Up to three short facts for a card: statuses first, then a figure, then a date."""
    facts = [f for f in entity.fields if f.name not in used and _is_status(f)][:2]
    figure = next((f for f in entity.fields if f.name not in used and f.type in (FieldType.INT, FieldType.FLOAT)
                   and not f.name.endswith("_id")), None)
    if figure is not None:
        facts.append(figure)
    date = next((f for f in entity.fields if f.name not in used and f.type is FieldType.DATETIME
                 and f.name not in ("updated_at",)), None)
    if date is not None:
        facts.append(date)
    return facts[:3]


def _fact_jsx(field: Field, expr: str) -> str:
    """One fact as a small chip; nothing at all when the record has no value."""
    label = _words(field.name)
    if field.type is FieldType.BOOL:
        return (f'{{{expr} !== undefined && {expr} !== null && (<span className="rounded-full bg-muted px-2.5 py-0.5 '
                f'text-xs font-medium text-muted-foreground">{{{expr} ? "{label}" : "Not {label.lower()}"}}</span>)}}')
    if _is_status(field):
        return (f'{{{expr} ? (<span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium '
                f'text-primary">{{String({expr}).replace(/_/g, " ")}}</span>) : null}}')
    if field.type is FieldType.DATETIME:
        return (f'{{{expr} ? (<span className="text-xs text-muted-foreground">{{new Date({expr})'
                f'.toLocaleDateString(undefined, {{ day: "numeric", month: "short", year: "numeric" }})}}</span>) : null}}')
    money = any(word in field.name for word in _MONEY_WORDS)
    shown = (f"Number({expr}).toLocaleString(undefined, {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})"
             if money else f"Number({expr}).toLocaleString(undefined, {{ maximumFractionDigits: 2 }})")
    unit = "" if money else f' <span className="font-normal text-muted-foreground">{label.lower()}</span>'
    return (f'{{{expr} !== undefined && {expr} !== null ? (<span className="text-sm font-semibold text-foreground">'
            f"{{{shown}}}{unit}</span>) : null}}")


def _image_expr(field: Field, record: str) -> str:
    """A usable src for the record's image, or an empty string."""
    if field.type is FieldType.ATTACHMENT:
        return f'(fileKeys({record}.{field.name})[0] ? fileUrl(fileKeys({record}.{field.name})[0]) : "")'
    return f'(typeof {record}.{field.name} === "string" && /^https?:\\/\\//.test({record}.{field.name}) ? {record}.{field.name} : "")'


def _summary_expr(field: Field, record: str) -> str:
    if field.type is FieldType.RICH_TEXT:
        return f"plainText({record}.{field.name}, 160)"
    return f'String({record}.{field.name} ?? "")'


# ── the list ────────────────────────────────────────────────────────────────────────────────────

def visitor_list_page(screen: Screen, entity: Entity, ir: ApplicationIR, ops: set[Op],
                      detail: Screen | None, form: Screen | None) -> str:
    name = entity.name
    plural = _plural_name(name)
    heading = _words(_plural_name(entity.name))
    singular = _words(entity.name).lower()
    title = _title_field(entity)
    image = _image_field(entity)
    summary = _summary_field(entity, title)
    used = {title, "first_name", "last_name", *(f.name for f in (image, summary) if f is not None)}
    facts = _fact_fields(entity, used)
    can_create = Op.CREATE in ops and form is not None
    if detail is not None:
        href = f"`/{detail.id}?id=${{encodeURIComponent(String(item.id))}}`"
    elif form is not None and Op.UPDATE in ops:
        href = f"`/{form.id}?id=${{encodeURIComponent(String(item.id))}}`"
    else:
        href = None
    imports = ['import { useState } from "react";', 'import Link from "next/link";',
               'import { ChevronLeft, ChevronRight, Plus, RefreshCw, Search } from "lucide-react";',
               f'import {{ useList{plural} }} from "@/lib/hooks";']
    if image is not None and image.type is FieldType.ATTACHMENT:
        imports.append('import { fileKeys, fileUrl } from "@/components/file-uploader";')
    if summary is not None and summary.type is FieldType.RICH_TEXT:
        imports.append('import { plainText } from "@/components/rich-text";')
    new_button = (
        f'          <Link href="/{form.id}" className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 '
        f'text-sm font-medium text-primary-foreground shadow-sm transition-opacity hover:opacity-90">\n'
        f'            <Plus className="h-4 w-4" aria-hidden /> New {singular}\n'
        f"          </Link>\n" if can_create else ""
    )
    title_js = _title_js(entity, "item")
    avatar = _is_avatar(entity, image)
    initial = f"{{{title_js}.trim().charAt(0).toUpperCase()}}"
    image_block = ""
    avatar_block = ""
    if image is not None and avatar:
        src = _image_expr(image, "item")
        avatar_block = (
            f"                  {{{src} ? (\n"
            f'                    <img src={{{src}}} alt="" loading="lazy" className="h-12 w-12 shrink-0 rounded-full object-cover" />\n'
            f"                  ) : (\n"
            f'                    <span aria-hidden className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full '
            f'bg-primary/10 text-lg font-semibold text-primary">{initial}</span>\n'
            f"                  )}}\n"
        )
    elif image is not None:
        src = _image_expr(image, "item")
        image_block = (
            f"              {{{src} ? (\n"
            f'                <img src={{{src}}} alt="" loading="lazy" className="aspect-[16/10] w-full object-cover" />\n'
            f"              ) : (\n"
            f'                <div aria-hidden className="flex aspect-[16/10] w-full items-center justify-center bg-primary/10 '
            f'text-3xl font-semibold text-primary">{initial}</div>\n'
            f"              )}}\n"
        )
    summary_block = (
        f'                {{{_summary_expr(summary, "item")} ? (<p className="line-clamp-3 text-sm text-muted-foreground">'
        f'{{{_summary_expr(summary, "item")}}}</p>) : null}}\n' if summary is not None else ""
    )
    facts_block = ""
    if facts:
        facts_block = ('                <div className="mt-auto flex flex-wrap items-center gap-2 pt-2">\n'
                       + "".join(f"                  {_fact_jsx(f, f'item.{f.name}')}\n" for f in facts)
                       + "                </div>\n")
    heading_tag = f'<h2 className="line-clamp-2 text-base font-semibold text-foreground">{{{title_js}}}</h2>'
    if avatar:
        heading_block = ('                <div className="flex items-center gap-3">\n' + avatar_block
                         + f"                  {heading_tag}\n                </div>\n")
    else:
        heading_block = f"                {heading_tag}\n"
    card_inner = (
        image_block
        + '              <div className="flex flex-1 flex-col gap-2 p-5">\n'
        + heading_block
        + summary_block + facts_block
        + "              </div>\n"
    )
    card_class = ("group flex h-full flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm "
                  "transition-all hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-none "
                  "focus-visible:ring-2 focus-visible:ring-primary")
    if href is not None:
        card = (f'            <Link key={{String(item.id)}} href={{{href}}} className="{card_class}">\n'
                + card_inner + "            </Link>\n")
    else:
        card = (f'            <article key={{String(item.id)}} className="{card_class.replace(" hover:-translate-y-0.5 hover:shadow-md", "")}">\n'
                + card_inner + "            </article>\n")
    empty_action = (
        f'            <Link href="/{form.id}" className="mt-5 inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 '
        f'text-sm font-medium text-primary-foreground">\n'
        f'              <Plus className="h-4 w-4" aria-hidden /> Add the first {singular}\n'
        f"            </Link>\n" if can_create else ""
    )
    component = f"{_pascal(screen.id)}Page"
    return (
        '"use client";\n\n' + "\n".join(imports) + "\n\n"
        "// PC-108: the web app's list, for the people who use the app (the admin app keeps the table).\n"
        f"export default function {component}() {{\n"
        f"  const {{ data, total, loading, error, page, totalPages, setPage, setSearch, refetch }} = useList{plural}({{ limit: 12 }});\n"
        '  const [query, setQuery] = useState("");\n'
        "  const items = (data ?? []) as any[];\n\n"
        "  return (\n"
        '    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:py-12">\n'
        '      <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">\n'
        "        <div>\n"
        f'          <h1 className="text-3xl font-bold tracking-tight text-foreground">{heading}</h1>\n'
        '          <p className="mt-1 text-sm text-muted-foreground">\n'
        f'            {{loading && !data ? "Loading…" : `${{total}} ${{total === 1 ? "{singular}" : "{heading.lower()}"}}`}}\n'
        "          </p>\n"
        "        </div>\n"
        '        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">\n'
        "          <form role=\"search\" onSubmit={(e) => { e.preventDefault(); setSearch(query.trim()); }} className=\"relative\">\n"
        '            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />\n'
        f'            <label htmlFor="search" className="sr-only">Search {heading.lower()}</label>\n'
        f'            <input id="search" type="search" value={{query}} onChange={{(e) => setQuery(e.target.value)}} placeholder="Search {heading.lower()}"\n'
        '              className="h-10 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm text-foreground outline-none focus:ring-2 focus:ring-primary sm:w-64" />\n'
        "          </form>\n"
        + new_button +
        "        </div>\n"
        "      </header>\n\n"
        "      {error ? (\n"
        '        <div role="alert" className="flex flex-col items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-6">\n'
        f'          <p className="font-medium text-foreground">We could not load the {heading.lower()}.</p>\n'
        '          <p className="text-sm text-muted-foreground">{error.message}</p>\n'
        '          <button type="button" onClick={() => refetch()} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted">\n'
        '            <RefreshCw className="h-4 w-4" aria-hidden /> Try again\n'
        "          </button>\n"
        "        </div>\n"
        "      ) : loading && items.length === 0 ? (\n"
        '        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true" aria-label="Loading">\n'
        "          {Array.from({ length: 6 }, (_, i) => (\n"
        '            <div key={i} className="h-56 animate-pulse rounded-xl border border-border bg-muted" />\n'
        "          ))}\n"
        "        </div>\n"
        "      ) : items.length === 0 ? (\n"
        '        <div className="flex flex-col items-center rounded-xl border border-dashed border-border px-6 py-16 text-center">\n'
        f'          <p className="text-lg font-semibold text-foreground">{{query ? "Nothing matches your search" : "No {heading.lower()} yet"}}</p>\n'
        f'          <p className="mt-1 max-w-md text-sm text-muted-foreground">{{query ? "Try another word, or clear the search." : "When {heading.lower()} are added they appear here."}}</p>\n'
        + empty_action +
        "        </div>\n"
        "      ) : (\n"
        "        <>\n"
        '          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">\n'
        "          {items.map((item) => (\n"
        + card +
        "          ))}\n"
        "          </div>\n"
        "          {totalPages > 1 && (\n"
        '            <nav aria-label="Pages" className="mt-8 flex items-center justify-center gap-3 text-sm">\n'
        '              <button type="button" onClick={() => setPage(page - 1)} disabled={page <= 1} aria-label="Previous page"\n'
        '                className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-background text-foreground hover:bg-muted disabled:opacity-40">\n'
        '                <ChevronLeft className="h-4 w-4" aria-hidden />\n'
        "              </button>\n"
        '              <span className="text-muted-foreground">Page {page} of {totalPages}</span>\n'
        '              <button type="button" onClick={() => setPage(page + 1)} disabled={page >= totalPages} aria-label="Next page"\n'
        '                className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-background text-foreground hover:bg-muted disabled:opacity-40">\n'
        '                <ChevronRight className="h-4 w-4" aria-hidden />\n'
        "              </button>\n"
        "            </nav>\n"
        "          )}\n"
        "        </>\n"
        "      )}\n"
        "    </main>\n"
        "  );\n"
        "}\n"
    )


# ── the detail page ─────────────────────────────────────────────────────────────────────────────

def _value_jsx(field: Field, expr: str) -> str:
    """A field's value on the record's page, readable for a person."""
    if field.type is FieldType.RICH_TEXT:
        return f"<RichText html={{{expr}}} />"
    if field.type is FieldType.ATTACHMENT:
        return f"<FileList value={{{expr}}} />"
    if field.type is FieldType.BOOL:
        return f'{{{expr} ? "Yes" : "No"}}'
    if field.type is FieldType.DATETIME:
        return (f'{{{expr} ? new Date({expr}).toLocaleString(undefined, {{ dateStyle: "medium", timeStyle: "short" }}) : "—"}}')
    if field.type in (FieldType.INT, FieldType.FLOAT):
        return f'{{{expr} !== undefined && {expr} !== null ? Number({expr}).toLocaleString() : "—"}}'
    if field.type is FieldType.JSON:
        return f'<pre className="whitespace-pre-wrap text-xs">{{{expr} ? JSON.stringify({expr}, null, 2) : "—"}}</pre>'
    if field.type is FieldType.STRING and ("url" in field.name or field.name in ("website", "link")):
        return (f'{{typeof {expr} === "string" && /^https?:\\/\\//.test({expr}) ? (<a href={{{expr}}} target="_blank" rel="noreferrer" '
                f'className="text-primary underline-offset-2 hover:underline">{{{expr}}}</a>) : ({expr} || "—")}}')
    if field.type is FieldType.STRING and "email" in field.name:
        return (f'{{{expr} ? (<a href={{`mailto:${{{expr}}}`}} className="text-primary underline-offset-2 hover:underline">'
                f'{{{expr}}}</a>) : "—"}}')
    return f'{{{expr} !== undefined && {expr} !== null && {expr} !== "" ? String({expr}) : "—"}}'


def visitor_detail_page(screen: Screen, entity: Entity, ir: ApplicationIR, ops: set[Op],
                        collection: Screen | None, form: Screen | None) -> str:
    from ..application_ir.workflow import workflow_for_entity
    from .lifecycle_ui import lifecycle_component_name, lifecycle_component_path
    from .nextjs import _subcollections_for_parent

    name = entity.name
    plural = _plural_name(name)
    singular = _words(name).lower()
    heading_plural = _words(_plural_name(name))
    title = _title_field(entity)
    image = _image_field(entity)
    # A summary-like field is the lede under the title; the body is the longest other text.
    lede = None if _is_person(entity) else next(
        (f for f in entity.fields if f.name in _SUMMARY_NAMES
         and f.type in (FieldType.STRING, FieldType.TEXT, FieldType.RICH_TEXT)), None)
    lede_name = lede.name if lede is not None else None
    body = next((f for f in entity.fields if f.type is FieldType.RICH_TEXT and f.name != lede_name), None) or next(
        (f for f in entity.fields if f.type is FieldType.TEXT and f.name not in _HIDDEN and f.name != lede_name), None)
    statuses = [f for f in entity.fields if _is_status(f) and f.name != title][:3]
    used = {title, "first_name", "last_name", "id", "created_at", "updated_at",
            *(f.name for f in (image, body, lede) if f is not None), *(f.name for f in statuses)}
    others = [f for f in entity.fields if f.name not in used and f.name not in _HIDDEN]
    by_get = Op.GET in ops
    can_edit = Op.UPDATE in ops and form is not None
    can_delete = Op.DELETE in ops
    workflow = workflow_for_entity(ir, name) if by_get else None
    subcollections = _subcollections_for_parent(name, ir)  # listed by the parent's id, GET or not
    back = f"/{collection.id}" if collection is not None else "/"
    back_label = f"All {heading_plural.lower()}" if collection is not None else "Home"

    imports = ['import { Suspense } from "react";', 'import Link from "next/link";',
               'import { useRouter, useSearchParams } from "next/navigation";',
               'import { ArrowLeft, Pencil, RefreshCw, Trash2 } from "lucide-react";']
    hooks = [f"use{name}" if by_get else f"useList{plural}"]
    if can_delete:
        hooks.append(f"useDelete{name}")
    hooks += [s.hook_name for s in subcollections]
    imports.append(f'import {{ {", ".join(dict.fromkeys(hooks))} }} from "@/lib/hooks";')
    if can_delete:
        imports.append('import { ConfirmDialog, useConfirm } from "@/components/confirm-dialog";')
    shown_fields = [f for f in (body, *others) if f is not None]
    if any(f.type is FieldType.RICH_TEXT for f in shown_fields):
        imports.append('import { RichText } from "@/components/rich-text";')
    uploader = (["FileList"] if any(f.type is FieldType.ATTACHMENT for f in others) else []) + (
        ["fileKeys", "fileUrl"] if image is not None and image.type is FieldType.ATTACHMENT else [])
    if uploader:
        imports.append(f'import {{ {", ".join(uploader)} }} from "@/components/file-uploader";')
    if workflow is not None:
        imports.append(f'import {{ {lifecycle_component_name(workflow)} }} from "@/{lifecycle_component_path(workflow).removesuffix(".tsx")}";')

    lines = ['"use client";', "", *imports, "",
             "// PC-108: a record's page for the people who use the app (the admin app keeps the tools).",
             f"function {_pascal(screen.id)}View() {{",
             "  const params = useSearchParams();",
             '  const id = params.get("id");',
             "  const router = useRouter();"]
    if by_get:
        lines.append(f"  const {{ data, loading, error, refetch }} = use{name}(id);")
        lines.append("  const item = data as any;")
    else:
        # No read-by-id endpoint: the record is found in the list.
        lines.append(f"  const {{ data: list, loading, error, refetch }} = useList{plural}({{ limit: 100 }});")
        lines.append("  const item = ((list ?? []) as any[]).find((x) => String(x.id) === String(id)) ?? null;")
    if can_delete:
        lines += [f"  const {{ remove, loading: removing }} = useDelete{name}();",
                  "  const { confirmAsync, confirmProps } = useConfirm();",
                  "  const handleDelete = async () => {",
                  "    if (!id) return;",
                  f'    const ok = await confirmAsync("Delete this {singular}?", "This cannot be undone.");',
                  "    if (!ok) return;",
                  "    await remove(id);",
                  f'    router.push("{back}");',
                  "  };"]
    for index, sub in enumerate(subcollections):
        lines.append(f"  const related{index} = {sub.hook_name}(id);")
    lines += ["",
              "  if (!id) {",
              "    return (",
              '      <main className="mx-auto w-full max-w-3xl px-4 py-16 text-center sm:px-6">',
              f'        <p className="text-lg font-semibold text-foreground">Choose a {singular} to see it here.</p>',
              f'        <Link href="{back}" className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline">',
              f'          <ArrowLeft className="h-4 w-4" aria-hidden /> {back_label}',
              "        </Link>",
              "      </main>",
              "    );",
              "  }",
              "  if (loading && !item) {",
              "    return (",
              '      <main className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6" aria-busy="true" aria-label="Loading">',
              '        <div className="h-8 w-2/3 animate-pulse rounded bg-muted" />',
              '        <div className="mt-6 h-64 animate-pulse rounded-xl bg-muted" />',
              "      </main>",
              "    );",
              "  }",
              "  if (error || !item) {",
              "    return (",
              '      <main className="mx-auto w-full max-w-3xl px-4 py-16 text-center sm:px-6">',
              f'        <p className="text-lg font-semibold text-foreground">{{error ? "This {singular} could not be loaded." : "This {singular} was not found."}}</p>',
              '        <div className="mt-4 flex items-center justify-center gap-4 text-sm">',
              '          {error ? (<button type="button" onClick={() => refetch()} className="inline-flex items-center gap-2 font-medium text-primary hover:underline"><RefreshCw className="h-4 w-4" aria-hidden /> Try again</button>) : null}',
              f'          <Link href="{back}" className="inline-flex items-center gap-2 font-medium text-primary hover:underline"><ArrowLeft className="h-4 w-4" aria-hidden /> {back_label}</Link>',
              "        </div>",
              "      </main>",
              "    );",
              "  }",
              ""]
    if image is not None:
        lines.append(f"  const image = {_image_expr(image, 'item')};")
    lines += ["  return (",
              '    <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 lg:py-12">',
              f'      <Link href="{back}" className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">',
              f'        <ArrowLeft className="h-4 w-4" aria-hidden /> {back_label}',
              "      </Link>",
              '      <article className="mt-6">',
              '        <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">',
              "          <div>"]
    if statuses:
        lines.append('            <div className="mb-3 flex flex-wrap gap-2">')
        lines += [f"              {_fact_jsx(f, f'item.{f.name}')}" for f in statuses]
        lines.append("            </div>")
    heading = f'<h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">{{{_title_js(entity, "item")}}}</h1>'
    if _is_avatar(entity, image):
        lines += ['            <div className="flex items-center gap-4">',
                  '              {image ? (<img src={image} alt="" className="h-16 w-16 rounded-full object-cover" />) : null}',
                  f"              {heading}",
                  "            </div>"]
    else:
        lines.append(f"            {heading}")
    # The API returns created_at for every record (the data layer adds it).
    if lede is not None:
        words = f"plainText(item.{lede.name})" if lede.type is FieldType.RICH_TEXT else f'String(item.{lede.name} ?? "")'
        lines.append(f'            {{{words} ? (<p className="mt-3 text-lg leading-relaxed text-muted-foreground">{{{words}}}</p>) : null}}')
    lines.append('            {item.created_at ? (<p className="mt-2 text-sm text-muted-foreground">Added {new Date(item.created_at).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}</p>) : null}')
    lines.append("          </div>")
    if can_edit or can_delete:
        lines.append('          <div className="flex shrink-0 gap-2">')
        if can_edit:
            lines += [f'            <Link href={{`/{form.id}?id=${{encodeURIComponent(String(item.id))}}`}} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground hover:bg-muted">',
                      '              <Pencil className="h-4 w-4" aria-hidden /> Edit',
                      "            </Link>"]
        if can_delete:
            lines += ['            <button type="button" onClick={handleDelete} disabled={removing} className="inline-flex h-9 items-center gap-2 rounded-lg border border-destructive/40 px-3 text-sm font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50">',
                      '              <Trash2 className="h-4 w-4" aria-hidden /> Delete',
                      "            </button>"]
        lines.append("          </div>")
    lines.append("        </header>")
    if image is not None and not _is_avatar(entity, image):
        lines.append('        {image ? (<img src={image} alt="" className="mt-8 w-full rounded-xl border border-border object-cover" />) : null}')
    if workflow is not None:
        lines.append(f'        <div className="mt-8"><{lifecycle_component_name(workflow)} record={{item}} onChanged={{() => refetch()}} /></div>')
    if body is not None:
        if body.type is FieldType.RICH_TEXT:
            lines.append(f'        <div className="mt-8 text-base leading-relaxed text-foreground"><RichText html={{item.{body.name}}} /></div>')
        else:
            lines.append(f'        {{item.{body.name} ? (<p className="mt-8 whitespace-pre-line text-base leading-relaxed text-foreground">{{String(item.{body.name})}}</p>) : null}}')
    if others:
        # Only fields with a value; the box hides itself when none has one (empty:hidden).
        lines.append('        <dl className="mt-10 grid gap-x-8 gap-y-5 rounded-xl border border-border bg-card p-6 empty:hidden sm:grid-cols-2">')
        for f in others:
            has = (f"plainText(item.{f.name})" if f.type is FieldType.RICH_TEXT
                   else f'item.{f.name} !== null && item.{f.name} !== undefined && item.{f.name} !== ""')
            lines += [f"          {{{has} ? (",
                      "          <div>",
                      f'            <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{_words(f.name)}</dt>',
                      f'            <dd className="mt-1 break-words text-sm text-foreground">{_value_jsx(f, f"item.{f.name}")}</dd>',
                      "          </div>",
                      "          ) : null}"]
        lines.append("        </dl>")
    for index, sub in enumerate(subcollections):
        child_title = _title_field(sub.child_entity)
        child_summary = _summary_field(sub.child_entity, child_title)
        label = _words(_plural_name(sub.child_entity.name))
        text = (f"plainText(r.{child_summary.name}, 280)" if child_summary is not None and child_summary.type is FieldType.RICH_TEXT
                else f'String(r.{child_summary.name} ?? "")' if child_summary is not None else '""')
        lines += ['        <section className="mt-12">',
                  f'          <h2 className="text-lg font-semibold text-foreground">{label} <span className="text-sm font-normal text-muted-foreground">({{related{index}.total}})</span></h2>',
                  f"          {{(related{index}.data ?? []).length === 0 ? (",
                  f'            <p className="mt-3 text-sm text-muted-foreground">No {label.lower()} yet.</p>',
                  "          ) : (",
                  '            <ul className="mt-4 space-y-3">',
                  f"              {{((related{index}.data ?? []) as any[]).map((r) => (",
                  '                <li key={String(r.id)} className="rounded-lg border border-border bg-card p-4">',
                  (f'                  <p className="text-sm font-medium text-foreground">{{String(r.{child_title} ?? "")}}</p>'
                   if child_title != (child_summary.name if child_summary else None) and child_title != "id" else ""),
                  f'                  <p className="mt-1 whitespace-pre-line text-sm text-muted-foreground">{{{text}}}</p>',
                  "                </li>",
                  "              ))}",
                  "            </ul>",
                  "          )}",
                  "        </section>"]
    lines += ["      </article>"]
    if can_delete:
        lines.append("      <ConfirmDialog {...confirmProps} />")
    lines += ["    </main>",
              "  );",
              "}",
              "",
              "// useSearchParams needs a Suspense boundary in the App Router.",
              f"export default function {_pascal(screen.id)}Page() {{",
              "  return (",
              "    <Suspense fallback={null}>",
              f"      <{_pascal(screen.id)}View />",
              "    </Suspense>",
              "  );",
              "}",
              ""]
    source = "\n".join(line for line in lines if line != "")
    if "plainText(" in source:
        # Related records' words (a comment's formatted body) - merged into the rich-text import.
        if 'import { RichText } from "@/components/rich-text";' in source:
            source = source.replace('import { RichText } from "@/components/rich-text";',
                                    'import { RichText, plainText } from "@/components/rich-text";', 1)
        else:
            source = source.replace('import Link from "next/link";',
                                    'import Link from "next/link";\nimport { plainText } from "@/components/rich-text";', 1)
    return source
