"""Changing an IR, not only adding to it (R-584).

`apply_app_delta` merged net-new entities, endpoints and screens by tuple concatenation, and the
parser raised on anything that already existed. So "rename Post to Article", "remove the published
field" and "add a notes field to each check-in" could not be done — and both ways of failing were
bad. A model that restated the entity got `AppDeltaError: proposed entity 'Post' already exists`; a
model that gave up proposed nothing, which parsed cleanly and reported "no file changes were
needed", an edit that silently did nothing. The platform's own smoke test asks for one of these.

These are pure functions over an IR. Each returns a new IR and never mutates its argument, because
an edit that half-applied and then failed validation would leave a project in a state nobody chose.

**The hard part is not the change, it is everything pointing at it.** An entity is named by its own
record, by relations in other entities, by the request and response schemas of endpoints, by
fixtures, and by the ids of screens generated from it. Renaming the entity alone produces an IR
that fails validation for a dangling reference — or worse, one that validates and quietly drops the
endpoints, which is how a rename becomes a deletion nobody asked for. Every function here moves the
references with the thing.
"""

from __future__ import annotations

import re
from dataclasses import replace

from ..application_ir import ApplicationIR, Entity, Field


def _snake(name: str) -> str:
    """`MenuItem` -> `menu_item`, matching how screen ids are generated from entity names."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def entity_names(ir: ApplicationIR) -> set[str]:
    return {entity.name for entity in ir.entities}


def add_field(ir: ApplicationIR, entity_name: str, field: Field) -> ApplicationIR:
    """Add one field to an existing entity.

    The most common edit there is — "add a notes field to each check-in" — and the one the delta
    could not express at all.
    """
    if entity_name not in entity_names(ir):
        raise ValueError(f"cannot add a field to unknown entity {entity_name!r}")
    updated = []
    for entity in ir.entities:
        if entity.name != entity_name:
            updated.append(entity)
            continue
        if any(existing.name == field.name for existing in entity.fields):
            raise ValueError(f"{entity_name} already has a field named {field.name!r}")
        updated.append(replace(entity, fields=entity.fields + (field,)))
    return replace(ir, entities=tuple(updated))


def remove_field(ir: ApplicationIR, entity_name: str, field_name: str) -> ApplicationIR:
    """Remove a field, and the values fixtures gave it.

    A fixture row keeping a key for a column that no longer exists would fail to load, so the rows
    lose the key with the field.
    """
    if field_name == "id":
        raise ValueError("the id field cannot be removed; an entity without one cannot be stored")
    entities = []
    found = False
    for entity in ir.entities:
        if entity.name != entity_name:
            entities.append(entity)
            continue
        kept = tuple(f for f in entity.fields if f.name != field_name)
        found = len(kept) != len(entity.fields)
        entities.append(replace(entity, fields=kept))
    if not found:
        raise ValueError(f"{entity_name} has no field named {field_name!r}")

    fixtures = tuple(
        fixture
        if fixture.entity != entity_name
        else replace(
            fixture,
            rows=tuple({k: v for k, v in row.items() if k != field_name} for row in fixture.rows),
        )
        for fixture in ir.fixtures
    )
    return replace(ir, entities=tuple(entities), fixtures=fixtures)


def rename_field(ir: ApplicationIR, entity_name: str, old: str, new: str) -> ApplicationIR:
    """Rename a field, carrying its fixture values across."""
    if old == "id":
        raise ValueError("the id field cannot be renamed")
    entities = []
    found = False
    for entity in ir.entities:
        if entity.name != entity_name:
            entities.append(entity)
            continue
        if any(f.name == new for f in entity.fields):
            raise ValueError(f"{entity_name} already has a field named {new!r}")
        fields = []
        for field in entity.fields:
            if field.name == old:
                found = True
                fields.append(replace(field, name=new))
            else:
                fields.append(field)
        entities.append(replace(entity, fields=tuple(fields)))
    if not found:
        raise ValueError(f"{entity_name} has no field named {old!r}")

    fixtures = tuple(
        fixture
        if fixture.entity != entity_name
        else replace(
            fixture,
            rows=tuple(
                {(new if k == old else k): v for k, v in row.items()} for row in fixture.rows
            ),
        )
        for fixture in ir.fixtures
    )
    return replace(ir, entities=tuple(entities), fixtures=fixtures)


def rename_entity(ir: ApplicationIR, old: str, new: str) -> ApplicationIR:
    """Rename an entity and everything that names it.

    Relations in other entities, the schemas of endpoints, the paths of those endpoints, fixtures
    and the ids of screens generated from it. Renaming the record alone leaves an IR that either
    fails validation or, worse, validates while its endpoints point at something gone.
    """
    if old not in entity_names(ir):
        raise ValueError(f"unknown entity {old!r}")
    if new in entity_names(ir):
        raise ValueError(f"an entity named {new!r} already exists")

    old_snake, new_snake = _snake(old), _snake(new)

    entities = tuple(
        replace(
            entity if entity.name != old else replace(entity, name=new),
            relations=tuple(
                relation if relation.target_entity != old else replace(relation, target_entity=new)
                for relation in entity.relations
            ),
        )
        for entity in ir.entities
    )

    def _path(path: str) -> str:
        # `/posts/{postId}/comments` -> `/articles/{articleId}/comments`: the plural segment and
        # the camelCase parameter both carry the entity's name.
        camel_old = old[0].lower() + old[1:]
        camel_new = new[0].lower() + new[1:]
        path = re.sub(rf"(?<=/){re.escape(old_snake)}s(?=/|$)", f"{new_snake}s", path)
        return re.sub(rf"\{{{re.escape(camel_old)}Id\}}", f"{{{camel_new}Id}}", path)

    apis = tuple(
        replace(
            api,
            path=_path(api.path),
            request_schema=new if api.request_schema == old else api.request_schema,
            response_schema=new if api.response_schema == old else api.response_schema,
            error_schema=new if api.error_schema == old else api.error_schema,
        )
        for api in ir.apis
    )

    screens = tuple(
        screen
        if not screen.id.startswith(f"{old_snake}_")
        else replace(screen, id=f"{new_snake}_{screen.id[len(old_snake) + 1:]}")
        for screen in ir.screens
    )
    renamed_screens = {
        screen.id: f"{new_snake}_{screen.id[len(old_snake) + 1:]}"
        for screen in ir.screens
        if screen.id.startswith(f"{old_snake}_")
    }
    screens = tuple(
        replace(
            screen,
            navigation=tuple(renamed_screens.get(target, target) for target in screen.navigation),
        )
        for screen in screens
    )

    fixtures = tuple(
        fixture if fixture.entity != old else replace(fixture, entity=new) for fixture in ir.fixtures
    )
    return replace(ir, entities=entities, apis=apis, screens=screens, fixtures=fixtures)


def remove_entity(ir: ApplicationIR, name: str) -> ApplicationIR:
    """Remove an entity, and everything that would be left pointing at nothing.

    Its endpoints, its screens, its fixtures, and relations other entities declared towards it. A
    removal that left any of those behind would produce an IR that fails validation, so the choice
    is not whether to cascade but whether to do it deliberately.
    """
    if name not in entity_names(ir):
        raise ValueError(f"unknown entity {name!r}")
    if len(ir.entities) == 1:
        raise ValueError("an application needs at least one entity")

    snake = _snake(name)
    entities = tuple(
        replace(
            entity,
            relations=tuple(r for r in entity.relations if r.target_entity != name),
        )
        for entity in ir.entities
        if entity.name != name
    )
    apis = tuple(
        api
        for api in ir.apis
        if api.request_schema != name
        and api.response_schema != name
        and api.error_schema != name
        and not re.search(rf"(?<=/){re.escape(snake)}s(?=/|$)", api.path)
    )
    removed_screen_ids = {s.id for s in ir.screens if s.id.startswith(f"{snake}_")}
    screens = tuple(
        replace(screen, navigation=tuple(t for t in screen.navigation if t not in removed_screen_ids))
        for screen in ir.screens
        if screen.id not in removed_screen_ids
    )
    fixtures = tuple(f for f in ir.fixtures if f.entity != name)
    return replace(ir, entities=entities, apis=apis, screens=screens, fixtures=fixtures)


def remove_api(ir: ApplicationIR, method: str, path: str) -> ApplicationIR:
    """Remove one endpoint."""
    method = (method or "").upper()
    kept = tuple(a for a in ir.apis if not (a.method.value == method and a.path == path))
    if len(kept) == len(ir.apis):
        raise ValueError(f"no endpoint {method} {path}")
    return replace(ir, apis=kept)


def remove_screen(ir: ApplicationIR, screen_id: str) -> ApplicationIR:
    """Remove one screen, and any navigation pointing at it."""
    kept = tuple(s for s in ir.screens if s.id != screen_id)
    if len(kept) == len(ir.screens):
        raise ValueError(f"no screen {screen_id!r}")
    kept = tuple(
        replace(screen, navigation=tuple(t for t in screen.navigation if t != screen_id))
        for screen in kept
    )
    return replace(ir, screens=kept)


#: Which operations destroy something a user may have data in. Used to say so rather than to
#: refuse: it is their project, and the answer to "remove the published field" is to remove it and
#: be clear about what that means.
DESTRUCTIVE = frozenset({"remove_entity", "remove_field", "remove_api", "remove_screen"})


def describes_data_loss(operations: list[str]) -> str:
    """One sentence naming what a set of operations will destroy, or empty when nothing is lost."""
    destructive = [op for op in operations if op in DESTRUCTIVE]
    if not destructive:
        return ""
    if "remove_entity" in destructive or "remove_field" in destructive:
        return (
            "This removes stored data: the affected columns and rows go with it, and the preview "
            "rebuilds its database from scratch. It cannot be undone by editing again."
        )
    return "This removes part of the API surface; anything calling it will stop working."
