"""PC-109: the generated React Native screens read as a finished product.

The live proof ran the app on the Android emulator (14 checks): the home screen greets the signed-in
person and lists the app's sections; a customer reads "Asha Rao" with their email beneath; an order
reads "Order 60aa77d7" with its state as a badge, its total and date; delete sits in the card behind a
confirmation; the form has human labels, marks what is required and leaves out what the database keeps.
"""

import json
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR
from omnistackai_agent_engine.codegen.react_native import ReactNativeAdapter

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _files() -> dict[str, str]:
    data = json.loads(FIXTURE.read_text())
    customer = next(e for e in data["entities"] if e["name"] == "Customer")
    customer["fields"].append({"name": "vip", "type": "bool", "required": False})
    data["capabilities"] = [{"kind": "workflow", "name": "flow", "config": {"entity": "Order", "field": "status",
                             "states": ["pending", "shipped"], "initial": "pending", "transitions": []}}]
    return {f.path: f.content for f in ReactNativeAdapter().generate(ApplicationIR.from_dict(data)).files()}


class ListsReadByName(TestCase):
    def setUp(self) -> None:
        self.files = _files()

    def test_titles(self) -> None:
        customers = self.files["src/features/customer/ui/CustomerListScreen.tsx"]
        self.assertIn("[(item as any).first_name, (item as any).last_name].filter(Boolean).join(' ')", customers)
        orders = self.files["src/features/order/ui/OrderListScreen.tsx"]
        self.assertIn("const titleOf = (item: Order) => 'Order ' + item.id.slice(0, 8);", orders, "not its state")
        self.assertIn("String((item as any).name ?? '')", self.files["src/features/product/ui/ProductListScreen.tsx"])

    def test_details_badge_and_no_ids(self) -> None:
        orders = self.files["src/features/order/ui/OrderListScreen.tsx"]
        self.assertIn("'Total amount ' + (item as any).total_amount", orders)
        self.assertIn("<Badge label={String((item as any).status).replace(/_/g, ' ')}", orders)
        for path, content in self.files.items():
            if path.endswith("ListScreen.tsx"):
                with self.subTest(path=path):
                    self.assertNotIn("ID: {item.id}", content)
                    self.assertNotIn("Sync Status", content)
                    self.assertIn("This cannot be undone.", content, "delete asks first")

    def test_overview_is_the_users(self) -> None:
        overview = self.files["src/app/screens/OverviewScreen.tsx"]
        for builder_view in ("System Metrics", "Full CRUD", "OmniStackAI Mobile", "StatCard"):
            self.assertNotIn(builder_view, overview)
        self.assertIn("Welcome back, ", overview)
        self.assertIn(">Order Items</Text>", overview)

    def test_navigation_titles_and_safe_area(self) -> None:
        navigator = self.files["src/app/navigation/RootNavigator.tsx"]
        self.assertIn('options={{ title: "Order Items" }}', navigator)
        self.assertIn('options={{ title: "Order Item" }}', navigator)
        self.assertIn("edges={['left', 'right', 'bottom']}", self.files["src/design-system/components/ScreenContainer.tsx"])


class FormsAskForWhatAPersonTypes(TestCase):
    def setUp(self) -> None:
        self.form = _files()["src/features/customer/ui/CustomerDetailScreen.tsx"]

    def test_labels_and_keyboards(self) -> None:
        for fragment in ('label="First name *"', 'label="Email *"', 'keyboardType="email-address"', 'keyboardType="phone-pad"',
                         "<Switch value={vip} onValueChange={setVip} />", "'New customer'"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.form)

    def test_what_the_database_keeps_is_not_a_field(self) -> None:
        for gone in ('label="Created at', 'label="Resume', 'label="Photo'):
            self.assertNotIn(gone, self.form)
