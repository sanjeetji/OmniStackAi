"""PC-100: the generated admin console - a shell, a real-data dashboard, a page per entity.

Before this task the console was the web app's navbar over a dashboard of invented figures
("99.98%" health, "< 24ms" latency, a 72% bar on every card) and had no place to manage records.
The fixture is a real plan the planner wrote for "a sales analytics dashboard for a small online
shop" (PC-050's live proof), so the console is tested against full CRUD, relations and a nested
resource, not only the small built-in examples.
"""

import json
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, example_ir
from omnistackai_agent_engine.codegen import NextjsAdminAdapter, NextjsWebAdapter
from omnistackai_agent_engine.codegen.admin_console import dashboard_page, managed_entities
from omnistackai_agent_engine.codegen.llm_ui import clean_and_validate_jsx, invented_figure
from omnistackai_agent_engine.codegen.nextjs import DESIGN_SYSTEM_PRO, entity_api_functions
from omnistackai_agent_engine.codegen.route_wiring import Op

_SHOP = Path(__file__).parent / "fixtures" / "ir" / "shop_analytics.json"


def _shop() -> ApplicationIR:
    return ApplicationIR.from_dict(json.loads(_SHOP.read_text(encoding="utf-8")))


def _admin(ir: ApplicationIR):
    return NextjsAdminAdapter().generate(ir)


class TheConsoleOffersOnlyWhatTheApiHas(TestCase):
    def test_every_listable_entity_gets_a_management_page(self) -> None:
        project = _admin(_shop())
        pages = sorted(f.path for f in project.files() if f.path.startswith("app/manage/"))
        self.assertEqual(pages, ["app/manage/customers/page.tsx", "app/manage/orders/page.tsx",
                                 "app/manage/products/page.tsx"])
        # OrderItem is only reachable under an order (no list endpoint of its own): no page.
        self.assertNotIn("OrderItem", [entity.name for entity, _ in managed_entities(_shop())])

    def test_a_page_calls_exactly_the_functions_the_client_exports(self) -> None:
        project = _admin(_shop())
        api = project.get("lib/api.ts").content
        orders = project.get("app/manage/orders/page.tsx").content
        for name in ("listOrdersWithCount", "createOrder", "updateOrder", "deleteOrder", "listCustomersWithCount"):
            self.assertIn(name, orders)
            self.assertIn(f"export async function {name}(", api)

    def test_operations_the_plan_lacks_are_not_offered(self) -> None:
        # The minimal blog can list and create posts, but not edit or delete them.
        self.assertEqual(set(entity_api_functions(example_ir("minimal-blog"))["Post"]), {Op.LIST, Op.CREATE})
        posts = _admin(example_ir("minimal-blog")).get("app/manage/posts/page.tsx").content
        self.assertIn("create=", posts)
        self.assertNotIn("update=", posts)
        self.assertNotIn("remove=", posts)

    def test_the_form_follows_the_plan(self) -> None:
        orders = _admin(_shop()).get("app/manage/orders/page.tsx").content
        self.assertIn('{ name: "created_at", label: "Created At", kind: "datetime", required: false, editable: false', orders)
        self.assertIn('{ name: "total_amount", label: "Total Amount", kind: "float", required: true, editable: true', orders)
        # A related record is picked from its own list, labelled by a readable field.
        self.assertIn('name: "customer_id"', orders)
        self.assertIn('relation: { labelKey: "email"', orders)


class TheShellAndItsNavigation(TestCase):
    def test_the_admin_layout_uses_the_shell_and_the_web_app_keeps_its_navbar(self) -> None:
        admin_layout = _admin(_shop()).get("app/layout.tsx").content
        self.assertIn("<AdminShell>{children}</AdminShell>", admin_layout)
        self.assertNotIn("<Navbar />", admin_layout)
        web_layout = NextjsWebAdapter().generate(_shop()).get("app/layout.tsx").content
        self.assertIn("<Navbar />", web_layout)
        self.assertNotIn("AdminShell", web_layout)

    def test_navigation_lists_entities_pages_and_access_but_no_detail_screens(self) -> None:
        nav = _admin(_shop()).get("components/admin/nav.ts").content
        for href in ('"/manage/orders"', '"/order_list"', '"/revenue_dashboard"'):
            self.assertIn(href, nav)
        self.assertNotIn('"/order_detail"', nav, "a detail screen needs a record; it is reached from its list")
        self.assertIn('"label": "New order"', nav)

    def test_users_and_roles_stay_in_a_console_with_accounts(self) -> None:
        project = _admin(_shop())
        self.assertIn("app/users/page.tsx", {f.path for f in project.files()})
        self.assertIn('"/users"', project.get("components/admin/nav.ts").content)
        self.assertIn("useAuth", project.get("components/admin/admin-shell.tsx").content)


class EveryFigureIsReal(TestCase):
    def test_the_dashboard_reads_the_api_and_invents_nothing(self) -> None:
        page = dashboard_page(_shop())
        self.assertEqual(invented_figure(page), "")
        for invented in ("99.98%", "24ms", "72%", "System Operational"):
            self.assertNotIn(invented, page)
        self.assertIn("listOrdersWithCount({ params: { limit: 100, sort: \"created_at\", order: \"desc\" as const } })", page)
        self.assertIn('href: "/manage/orders"', page)

    def test_the_admin_home_is_the_dashboard_without_a_model(self) -> None:
        self.assertEqual(_admin(_shop()).get("app/page.tsx").content, dashboard_page(_shop()))

    def test_a_model_page_with_an_invented_figure_is_refused(self) -> None:
        page = ('"use client";\nexport default function Home() {\n'
                '  return <p className="text-xs">+12.5% from last month</p>;\n}\n')
        ok, _code, reason = clean_and_validate_jsx(page)
        self.assertFalse(ok)
        self.assertIn("Invented figure '+12.5%'", reason)

    def test_computed_numbers_and_ordinary_css_pass(self) -> None:
        for fine in ('{growth.toFixed(1)}% vs last month', 'transform: "translate(-50%, -50%)"',
                     'transition: "all 300ms ease"', '<p>Uptime</p><p>{uptime}%</p>', 'width: "100%"',
                     'className="w-[calc(100%+2px)]"'):
            self.assertEqual(invented_figure(fine), "", fine)
        for made_up in ('<p>+12% from last month</p>', '<h3>System Health</h3><p>99.98%</p>',
                        'Latency: &lt; 24ms', '3 vs last week', 'const mockOrders = [1]'):
            self.assertNotEqual(invented_figure(made_up), "", made_up)


class MapsForRecordsWithCoordinates(TestCase):
    def test_an_entity_with_latitude_and_longitude_gets_a_map_view(self) -> None:
        from dataclasses import replace

        from omnistackai_agent_engine.application_ir.ir import Field, FieldType

        ir = _shop()
        stores = [replace(e, fields=(*e.fields, Field("latitude", FieldType.FLOAT, required=False),
                                     Field("longitude", FieldType.FLOAT, required=False)))
                  if e.name == "Customer" else e for e in ir.entities]
        customers = _admin(replace(ir, entities=tuple(stores))).get("app/manage/customers/page.tsx").content
        self.assertIn('coordinates={{ lat: "latitude", lng: "longitude" }}', customers)
        self.assertNotIn("coordinates=", _admin(_shop()).get("app/manage/orders/page.tsx").content)
        self.assertEqual(DESIGN_SYSTEM_PRO["maplibre-gl"], "6.11.2")


class FoundLiveInTheGeneratedApi(TestCase):
    """The console's live proof hit three bugs in the generated Python API (the default backend)."""

    def _api(self):
        from omnistackai_agent_engine.codegen.assembler import assemble_project

        return assemble_project(_shop())

    def test_an_entity_called_order_can_be_listed(self) -> None:
        # `from app.repositories import order` was shadowed by the handler's `order` (sort
        # direction) parameter: GET /orders answered 500 in every app with an Order.
        router = self._api().get("services/api/app/routers/orders.py").content
        self.assertIn("from app.repositories import order as order_repo", router)
        self.assertIn("await order_repo.count_order(", router)
        self.assertNotIn("await order.", router)
        compile(router, "orders.py", "exec")

    def test_a_relation_can_be_set_through_the_api(self) -> None:
        project = self._api()
        models = project.get("services/api/app/models.py").content
        order_model = models[models.index("class Order("):models.index("class OrderItem(")]
        self.assertIn("customer_id: Optional[str] = None", order_model)
        repository = project.get("services/api/app/repositories/order.py").content
        self.assertIn("'customer_id'] if c in data]", repository)
        self.assertIn('"customer_id" = %s', repository)

    def test_the_database_sets_the_timestamps_a_plan_declares(self) -> None:
        models = self._api().get("services/api/app/models.py").content
        order_model = models[models.index("class Order("):models.index("class OrderItem(")]
        self.assertIn("created_at: Optional[datetime] = None", order_model)
        self.assertNotIn("created_at: datetime\n", order_model)


class TheDashboardTitle(TestCase):
    def test_a_name_that_already_says_admin_is_not_repeated(self) -> None:
        from dataclasses import replace

        self.assertIn('const TITLE = "Store Admin";', dashboard_page(replace(_shop(), name="Store Admin")))
        self.assertIn('const TITLE = "Shop Sales Analytics admin";', dashboard_page(_shop()))
