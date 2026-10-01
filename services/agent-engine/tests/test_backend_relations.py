"""PC-100 / PC-103: every backend writes and reads a relation, and lets the database set timestamps.

Found live in PC-100 for the Python API (the default backend): a product created with a category_id
came back with none, and a plan that declared created_at made it required on every create. PC-103
found the same gap in the Go and Node backends (Go's Order struct had no CustomerId; Node's
z.object dropped the unknown key) and that the Node API failed `tsc` wherever it had accounts. All
of it was proven against Postgres with the generated servers (see the CHANGELOG); these tests keep
the generated code in that shape.
"""

import json
from dataclasses import replace
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR
from omnistackai_agent_engine.codegen.assembler import assemble_project

_SHOP = Path(__file__).parent / "fixtures" / "ir" / "shop_analytics.json"


def _project(backend: str):
    ir = ApplicationIR.from_dict(json.loads(_SHOP.read_text(encoding="utf-8")))
    return assemble_project(replace(ir, project_strategy=replace(ir.project_strategy, backend_strategy=backend)))


class GoWritesRelations(TestCase):
    def setUp(self) -> None:
        self.project = _project("go")

    def _file(self, suffix: str) -> str:
        return next(f.content for f in self.project.files() if f.path.endswith(suffix))

    def test_the_model_carries_the_foreign_key_and_optional_timestamps(self) -> None:
        models = self._file("models/models.go")
        order = models[models.index("type Order struct"):models.index("type OrderItem struct")]
        self.assertRegex(order, r'CustomerId\s+\*string\s+`json:"customer_id,omitempty"`')
        self.assertRegex(order, r'CreatedAt\s+\*time\.Time\s+`json:"created_at,omitempty"`')
        self.assertNotIn('validate:"required"`\n\tCreatedAt', order)

    def test_the_store_writes_and_reads_it(self) -> None:
        store = self._file("store/order.go")
        # R-570: and who created it, from the verified token.
        self.assertIn('INSERT INTO "order" ("order_date", "status", "total_amount", "customer_id", "created_by")', store)
        self.assertIn('"customer_id" = $4 WHERE', store)
        self.assertIn("&m.CustomerId", store)


class NodeWritesRelations(TestCase):
    def setUp(self) -> None:
        self.project = _project("node")

    def test_validation_keeps_the_foreign_key(self) -> None:
        validation = next(f.content for f in self.project.files() if f.path.endswith("validation.ts"))
        order = validation[validation.index("createOrderSchema"):]
        self.assertIn("customer_id: z.string().uuid().nullable().optional(),", order[:order.index("});")])

    def test_the_repository_writes_and_reads_it(self) -> None:
        repo = next(f.content for f in self.project.files() if f.path.endswith("OrderRepository.ts")
                    or f.path.endswith("order.repository.ts") or f.path.endswith("/order.ts") and "/db/" in f.path)
        self.assertIn('"customer_id"', repo)
        self.assertIn('const WRITABLE: string[] = ["order_date", "status", "total_amount", "customer_id"];', repo)

    def test_the_role_manager_type_checks(self) -> None:
        core = next(f.content for f in self.project.files() if f.path.endswith("auth/core.ts"))
        self.assertNotIn("if ('status' in claims)", core)
        self.assertIn("if (isFailure(claims)) return claims;", core)
