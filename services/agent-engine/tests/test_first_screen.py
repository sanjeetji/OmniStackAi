"""PC-006: the first screen of a generated app reads like the product that was asked for.

Seen live on 2026-09-26 with "A simple habit tracker with habits and daily check-ins":
* the home page was a blog's ("LATEST", "Start reading", "What we cover: the subjects this
  publication follows") because every CRUD app has `*_editor` screens and "editor" counted as
  publishing evidence;
* names were mangled: "Habitcategory", "+ New DailyCheckIn";
* the home cards listed table columns ("Id, Title, Description");
* the top bar listed every editor with a "user" badge, wrapped onto two lines, and on a phone
  overflowed so the whole page scrolled sideways.
"""

import dataclasses
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.application_ir.ir import Entity, Field, FieldType, Screen
from omnistackai_agent_engine.codegen.archetype import Archetype, detect_archetype
from omnistackai_agent_engine.codegen.nextjs import (
    _nav_label,
    _navbar_component,
    _public_home_page,
    _title_case,
)


def _habit_ir():
    base = example_ir("minimal-blog")
    fields = (Field(name="id", type=FieldType.UUID), Field(name="title", type=FieldType.STRING))
    entities = tuple(Entity(name=n, fields=fields) for n in ("Habit", "HabitCategory", "DailyCheckIn"))
    screens = tuple(
        Screen(id=i, role="reader", components=(c,), actions=(), navigation=())
        for i, c in (("habit_list", "list"), ("habit_editor", "form"), ("category_list", "list"),
                     ("category_editor", "form"), ("checkin_editor", "form"))
    )
    return dataclasses.replace(base, name="Simple Habit Tracker",
                               description="A simple habit tracker with habits and daily check-ins.",
                               entities=entities, screens=screens, apis=(), capabilities=())


class APersonalToolIsNotABlog(TestCase):
    def test_a_habit_tracker_is_a_tracker(self) -> None:
        self.assertEqual(detect_archetype(_habit_ir()), Archetype.TRACKER)

    def test_editor_screens_alone_are_not_publishing(self) -> None:
        ir = dataclasses.replace(_habit_ir(), entities=(), name="Thing", description="A thing.")
        self.assertNotEqual(detect_archetype(ir), Archetype.PUBLICATION)

    def test_a_blog_is_still_a_blog(self) -> None:
        self.assertEqual(detect_archetype(example_ir("minimal-blog")), Archetype.PUBLICATION)

    def test_the_home_page_speaks_to_it(self) -> None:
        page = _public_home_page(_habit_ir())
        for blog_words in ("Start reading", "What we cover", "publication"):
            self.assertNotIn(blog_words, page)
        self.assertIn("Get started", page)
        self.assertIn(">Habits</Link>", page)


class NamesReadLikeWords(TestCase):
    def test_camel_case(self) -> None:
        self.assertEqual(_title_case("HabitCategory"), "Habit Category")
        self.assertEqual(_title_case("DailyCheckIn"), "Daily Check In")
        self.assertEqual(_title_case("post_list"), "Post List")
        self.assertEqual(_title_case("SKU"), "SKU")

    def test_lists_are_named_for_what_they_list(self) -> None:
        self.assertEqual(_nav_label("habit_list"), "Habits")
        self.assertEqual(_nav_label("category_list"), "Categories")
        self.assertEqual(_nav_label("dashboard"), "Dashboard")

    def test_home_cards_say_what_you_can_do(self) -> None:
        from omnistackai_agent_engine.codegen.nextjs import Op, _offering_detail

        entity = _habit_ir().entities[1]
        self.assertEqual(_offering_detail(entity, {Op.CREATE, Op.LIST, Op.UPDATE}),
                         "Add, browse and update your habit categories.")
        self.assertEqual(_offering_detail(entity, {Op.LIST}), "Browse your habit categories.")
        blog = _public_home_page(example_ir("minimal-blog"))
        self.assertNotIn("Id, Title", blog)


class TheHeaderFitsEveryScreen(TestCase):
    def setUp(self) -> None:
        self.navbar = _navbar_component(_habit_ir())

    def test_the_top_bar_lists_what_people_browse(self) -> None:
        self.assertIn("Habits", self.navbar)
        self.assertNotIn(">reader</span>", self.navbar.split("Enterprise Collapsible Sidebar")[0])
        self.assertIn('whiteSpace: "nowrap"', self.navbar)

    def test_the_new_button_is_named_plainly(self) -> None:
        self.assertNotIn("+ New HabitCategory", self.navbar)
        self.assertNotIn("DailyCheckIn", self.navbar)

    def test_parts_step_aside_on_a_phone(self) -> None:
        for hidden in ("omni-topnav", "omni-shortcuts", "omni-create", "omni-brand-name"):
            self.assertIn(f'className="{hidden}"', self.navbar)
        self.assertIn("@media (max-width: 640px)", self.navbar)
