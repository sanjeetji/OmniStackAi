"""R-538: the CareClinic template's API tests, seed reproducibility and app completeness, offline.

CareClinic's API is TypeScript that Node (>= 22.18) runs natively. Its unit tests import only pure
modules (the appointment state machine, tokens, passwords, money, slot generation, prescription
rules), so they need no dependencies installed and no database. The seed is written by a generator
script; the committed SQL must be exactly what the script produces, and it must be loadable — the
first cut of it was not, so the checks below pin the two ways it broke.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[3] / "templates" / "catalog"
TEMPLATE_CANDIDATES = [CATALOG / "care-clinic", CATALOG / "_care-clinic"]
TEMPLATE = next((path for path in TEMPLATE_CANDIDATES if path.is_dir()), TEMPLATE_CANDIDATES[0])
REPO = TEMPLATE / "repo"
API = REPO / "services" / "api"


def _node_supports_typescript() -> bool:
    node = shutil.which("node")
    if not node:
        return False
    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=False).stdout.strip()
    match = re.match(r"v(\d+)\.(\d+)", version)
    return bool(match) and (int(match.group(1)), int(match.group(2))) >= (22, 18)


_INSERT = re.compile(r"^INSERT INTO (\w+)", re.M)


def _tables_written(sql: str) -> list[str]:
    """The tables a seed writes, in order, collapsing consecutive runs of the same table."""
    tables: list[str] = []
    for table in _INSERT.findall(sql):
        if not tables or tables[-1] != table:
            tables.append(table)
    return tables


def _node(args: list[str], cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, check=False,
        env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")},
    )


@unittest.skipUnless(API.is_dir() and _node_supports_typescript(), "needs the CareClinic template and Node >= 22.18")
class CareClinicApiTests(unittest.TestCase):
    def test_unit_tests_pass(self) -> None:
        tests = sorted(str(p.relative_to(API)) for p in (API / "test").glob("*.test.ts"))
        self.assertGreaterEqual(len(tests), 4)
        result = _node(["node", "--test", *tests], API)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])
        passed = re.search(r"pass (\d+)", result.stdout)
        self.assertIsNotNone(passed)
        self.assertGreaterEqual(int(passed.group(1)), 15)

    def test_icd10_seed_matches_its_generator(self) -> None:
        result = subprocess.run(
            ["node", "scripts/generate-icd10.mjs"], cwd=str(API), capture_output=True, timeout=60, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode()[-2000:])
        committed = (API / "seed" / "002_icd10.sql").read_bytes()
        self.assertEqual(
            hashlib.sha256(result.stdout).hexdigest(),
            hashlib.sha256(committed).hexdigest(),
            "seed/002_icd10.sql is stale: run `node scripts/generate-icd10.mjs > seed/002_icd10.sql`",
        )

    def test_the_committed_seed_came_from_this_generator(self) -> None:
        """R-586: byte for byte, because the generator no longer reads a clock.

        This used to compare only the sequence of tables written, because every date came from
        `new Date()` and a weekday shift changed how many appointments landed in the window. That
        was not weak enough to survive: the comparison still failed the day after the seed was
        committed, so `task verify` broke every day. Dates are now anchored to a fixed Monday and
        moved onto today by the seed itself, which makes the file identical on every run and lets
        this gate be exact.
        """
        result = subprocess.run(
            ["node", "scripts/generate-seed.mjs"], cwd=str(API), capture_output=True, timeout=180, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode()[-2000:])
        committed = (API / "seed" / "001_demo.sql").read_bytes()
        self.assertEqual(
            hashlib.sha256(result.stdout).hexdigest(),
            hashlib.sha256(committed).hexdigest(),
            "seed/001_demo.sql is stale: run `node scripts/generate-seed.mjs > seed/001_demo.sql`",
        )

    def test_the_generator_reads_no_clock(self) -> None:
        """The property that makes the gate above possible, asserted at the source.

        A single reintroduced `new Date()` or `NOW()` would put the seed back to failing daily, and
        it would look like an unrelated template test breaking for no reason -- which is exactly how
        this cost a morning to diagnose.
        """
        source = (API / "scripts" / "generate-seed.mjs").read_text(encoding="utf-8")
        self.assertNotRegex(source, r"new Date\(\s*\)", "the generator must not read the clock")
        self.assertNotIn("NOW()", source, "emit an anchored timestamp instead of NOW()")
        self.assertNotRegex(
            source, r"\bd\.getDay\(\)", "use getUTCDay: mixing local and UTC made output timezone-dependent"
        )

    def test_every_generated_date_column_is_moved_onto_today(self) -> None:
        """A date column added later cannot be quietly left behind in 2026.

        The seed writes anchored literals and then shifts them onto the current date. Any column
        that receives a literal and is not in that shift block would stay frozen at the anchor while
        everything around it moved -- an invoice dated months before the appointment it belongs to.
        This reads the generated SQL rather than the generator, so it sees what is really written.
        """
        sql = (API / "seed" / "001_demo.sql").read_text(encoding="utf-8")
        shifted = set(re.findall(r"UPDATE (\w+) SET (.+?);", sql))
        moved: set[tuple[str, str]] = set()
        for table, sets in shifted:
            for column in re.findall(r"(\w+) = \1 ", sets):
                moved.add((table, column))

        written: set[tuple[str, str]] = set()
        for match in re.finditer(r"INSERT INTO (\w+) \(([^)]*)\) VALUES \((.*?)\);", sql, re.S):
            table, columns = match.group(1), [c.strip() for c in match.group(2).split(",")]
            values, depth, current = [], 0, ""
            for char in match.group(3):
                if char == "," and depth == 0:
                    values.append(current.strip())
                    current = ""
                    continue
                if char in "([":
                    depth += 1
                if char in ")]":
                    depth -= 1
                current += char
            values.append(current.strip())
            if len(values) != len(columns):
                continue
            for column, value in zip(columns, values):
                if re.match(r"'20\d\d-\d\d-\d\d", value):
                    written.add((table, column))

        # A date of birth is not part of the demo's timeline and must never move.
        written -= {("patient_profiles", "dob"), ("family_members", "dob")}
        self.assertEqual(
            written - moved,
            set(),
            "these columns receive a date but are never moved onto today; add them to the shift "
            "block in scripts/generate-seed.mjs",
        )

    def test_the_generator_is_deterministic(self) -> None:
        """Two runs in the same moment must be byte-identical; nothing random may leak in."""
        runs = [
            subprocess.run(
                ["node", "scripts/generate-seed.mjs"], cwd=str(API), capture_output=True, timeout=180, check=False,
            ).stdout
            for _ in range(2)
        ]
        self.assertEqual(hashlib.sha256(runs[0]).hexdigest(), hashlib.sha256(runs[1]).hexdigest())



@unittest.skipUnless(API.is_dir(), "needs the CareClinic template")
class CareClinicSeedTests(unittest.TestCase):
    """The seed must load into PostgreSQL. Its first cut did not, in two specific ways."""

    def setUp(self) -> None:
        self.seed = (API / "seed" / "001_demo.sql").read_text(encoding="utf-8")

    def test_every_time_of_day_is_valid(self) -> None:
        """Minutes were once added without carrying, producing '09:60:00', which PostgreSQL rejects."""
        bad = re.findall(r"'\d{2}:(?:6\d|[7-9]\d):\d{2}'", self.seed)
        self.assertEqual(bad, [], f"invalid times in the seed: {sorted(set(bad))[:5]}")

    def test_queue_status_uses_its_own_vocabulary(self) -> None:
        """queue_status was once copied from the appointment status; 'no_show' is not one of its values."""
        allowed = set(re.findall(r"queue_status IN \(([^)]*)\)", (API / "migrations" / "002_scheduling.sql").read_text(encoding="utf-8"))[0].replace("'", "").split(", "))
        self.assertTrue({"waiting", "called", "with_doctor", "done", "cancelled"} <= allowed)
        for statement in re.findall(r"INSERT INTO appointments \(([^)]*)\) VALUES \(([^;]*)\);", self.seed):
            columns = [c.strip() for c in statement[0].split(",")]
            if "queue_status" not in columns:
                continue
            values = re.findall(r"'([^']*)'|(\d+|TRUE|FALSE|NULL)", statement[1])
            flat = [a or b for a, b in values]
            self.assertIn(flat[columns.index("queue_status")], allowed)

    def test_every_table_the_apps_read_has_rows(self) -> None:
        """Nine tables were once never written, so whole screens had nothing to show."""
        for table in ("clinics", "users", "doctor_profiles", "patient_profiles", "family_members",
                      "medical_histories", "doctor_availability", "schedule_overrides", "appointments",
                      "consultations", "diagnoses", "prescriptions", "prescription_items",
                      "lab_test_catalog", "lab_orders", "lab_order_items", "vitals_records",
                      "invoices", "invoice_items", "refunds", "telehealth_sessions",
                      "chart_access_logs", "patient_reviews", "notifications"):
            self.assertIn(f"INSERT INTO {table} ", self.seed, f"the seed never writes {table}")

    def test_the_icd10_catalogue_is_seeded(self) -> None:
        """The diagnosis picker searches this table; an empty one makes SOAP coding impossible."""
        icd = (API / "seed" / "002_icd10.sql").read_text(encoding="utf-8")
        self.assertGreaterEqual(icd.count("INSERT INTO icd10_catalog"), 40)
        for code in ("'I10'", "'E11.9'", "'J45.909'"):
            self.assertIn(code, icd)

    def test_the_demo_patient_has_a_chart_worth_opening(self) -> None:
        demo = "50000000-0000-0000-0000-000000000001"
        prescriptions = [line for line in self.seed.splitlines() if line.startswith("INSERT INTO prescriptions ") and demo in line]
        self.assertGreaterEqual(len(prescriptions), 3, "the account the demo signs in with needs its own history")

    def test_demo_logins_are_in_the_seed(self) -> None:
        for login in ("ananya@careclinic.test", "dr.rajesh@careclinic.test", "admin@careclinic.test",
                      "suresh.gowda@careclinic.test"):
            self.assertIn(login, self.seed)


_ROUTE = re.compile(r"(\w+)Routes\.(?:get|post|patch|put|delete)\(\"([^\"]*)\"")
# A string literal in app code that names an API path, e.g. "/api/admin/rooms".
_API_LITERAL = re.compile(r"[\"`](/(?:api/(?:public|patient|doctor|admin)|auth|health)(?:/[^\"`?\s]*)?)(?:\?[^\"`]*)?[\"`]")


def _matches(path: str, routes: list[re.Pattern[str]]) -> bool:
    """`/api/x/${id}` becomes a path segment; a trailing `${qs}` is a query string, so try both."""
    concrete = re.sub(r"\$\{[^}]*\}", "x", path).rstrip("/")
    if any(r.match(concrete) for r in routes):
        return True
    trimmed = path[: path.index("${")].rstrip("/") if "${" in path else concrete
    return bool(trimmed) and any(r.match(trimmed) for r in routes)


def _api_routes() -> list[re.Pattern[str]]:
    patterns = []
    for source in (API / "src" / "routes").glob("*.ts"):
        for _group, path in _ROUTE.findall(source.read_text(encoding="utf-8")):
            full = path.rstrip("/") or "/"
            patterns.append(re.compile("^" + re.sub(r":\w+", "[^/]+", full) + "$"))
    # publicRoutes is mounted twice: at the root and under /api/public.
    patterns.append(re.compile(r"^/api/public/.*$"))
    return patterns


@unittest.skipUnless(REPO.is_dir(), "needs the CareClinic template")
class CareClinicAppsTests(unittest.TestCase):
    def test_patient_app_pages(self) -> None:
        patient = REPO / "apps" / "patient"
        for page in ("", "login", "doctors", "doctors/[id]", "book", "book/[doctorId]",
                     "checkout/[appointmentId]", "appointments", "appointments/[id]",
                     "appointments/[id]/confirmation", "telehealth/[appointmentId]", "prescriptions",
                     "prescriptions/[id]", "lab-reports", "lab-reports/[id]", "records", "family", "invoices"):
            self.assertTrue((patient / "app" / page / "page.tsx").is_file(), f"patient page missing: /{page}")

    def test_dynamic_segments_are_real_route_folders(self) -> None:
        """The folders were once URL-encoded ('%5Bid%5D'), so every detail page 404'd on a real id."""
        for app in ("patient", "doctor", "admin"):
            for path in (REPO / "apps" / app).rglob("*"):
                if not path.is_dir() or "node_modules" in path.parts or ".next" in path.parts:
                    continue
                self.assertNotIn("%5B", path.name, f"{path} is a URL-encoded dynamic segment")

    def test_doctor_app_pages(self) -> None:
        doctor = REPO / "apps" / "doctor"
        for page in ("", "login", "queue", "consult/[appointmentId]", "consult/[appointmentId]/soap",
                     "consult/[appointmentId]/prescription", "consult/[appointmentId]/labs", "patients",
                     "patients/[id]", "patients/[id]/history", "schedule", "schedule/rules", "earnings",
                     "reviews", "telehealth/[appointmentId]"):
            self.assertTrue((doctor / "app" / page / "page.tsx").is_file(), f"doctor page missing: /{page}")

    def test_ops_console_pages_and_staff_only_sign_in(self) -> None:
        admin = REPO / "apps" / "admin"
        for page in ("", "login", "front-desk", "check-in", "walk-in", "appointments", "appointments/[id]",
                     "doctors", "doctors/[id]/schedule", "rooms", "billing", "billing/[id]", "refunds",
                     "labs", "reports", "audit", "settings", "queue-display"):
            self.assertTrue((admin / "app" / page / "page.tsx").is_file(), f"ops page missing: /{page}")
        for extra in ("lib/session.tsx", "lib/use-api.ts", "lib/format.ts", "components/shell.tsx",
                      "components/ui.tsx", "components/charts.tsx"):
            self.assertTrue((admin / extra).is_file(), extra)
        session = (admin / "lib" / "session.tsx").read_text(encoding="utf-8")
        self.assertIn('login(email, password, "admin")', session, "the console must sign in as staff")
        self.assertIn('STAFF_ROLES = ["admin", "receptionist"]', session)

    def test_the_console_reads_the_api_rather_than_a_hard_coded_table(self) -> None:
        """Every ops page was once a static mock. Each one must now load from the API."""
        admin = REPO / "apps" / "admin" / "app"
        exempt = {"login", "queue-display"}
        for page in sorted(admin.rglob("page.tsx")):
            name = page.parent.relative_to(admin).as_posix()
            if name.split("/")[0] in exempt:
                continue
            source = page.read_text(encoding="utf-8")
            self.assertIn("defaultApiClient.", source, f"/{name} does not call the API")

    def test_the_workstation_reads_the_api_rather_than_a_hard_coded_table(self) -> None:
        """R-539: every doctor screen was a static mock. Each one must now load from the API."""
        doctor = REPO / "apps" / "doctor" / "app"
        exempt = {"login"}
        for page in sorted(doctor.rglob("page.tsx")):
            name = page.parent.relative_to(doctor).as_posix()
            if name.split("/")[0] in exempt:
                continue
            source = page.read_text(encoding="utf-8")
            self.assertIn("defaultApiClient.", source, f"/{name} does not call the API")

    def test_the_workstation_has_its_own_session_and_guard(self) -> None:
        doctor = REPO / "apps" / "doctor"
        for extra in ("lib/session.tsx", "lib/use-api.ts", "lib/format.ts", "components/shell.tsx",
                      "components/ui.tsx", "components/charts.tsx", "components/consult-frame.tsx"):
            self.assertTrue((doctor / extra).is_file(), extra)
        session = (doctor / "lib" / "session.tsx").read_text(encoding="utf-8")
        self.assertIn('login(email, password, "doctor")', session, "the workstation signs in as a doctor")
        self.assertIn('stored.role === "doctor"', session, "a stored non-doctor session must be dropped")

    def test_no_placeholder_ids_are_linked_anywhere(self) -> None:
        """Links once pointed at a hard-coded patient, so they 404'd for everyone."""
        for app in ("patient", "doctor", "admin"):
            for source in (REPO / "apps" / app).rglob("*.tsx"):
                if "node_modules" in source.parts or ".next" in source.parts:
                    continue
                text = source.read_text(encoding="utf-8")
                for placeholder in ('href={`/patients/pat-', 'href="/patients/pat-',
                                    'href={`/doctors/doc-', 'href="/doctors/doc-'):
                    self.assertNotIn(placeholder, text, f"{source.name} links to a placeholder id")

    def test_role_isolation_is_enforced_by_the_api(self) -> None:
        public = (API / "src" / "routes" / "public.ts").read_text(encoding="utf-8")
        self.assertIn("ROLE_GROUPS", public)
        self.assertIn('admin: ["admin", "receptionist"]', public)
        self.assertIn("ForbiddenError", public)

    def test_every_api_path_used_by_the_apps_exists(self) -> None:
        routes = _api_routes()
        self.assertGreater(len(routes), 50)
        checked = 0
        for app in ("patient", "doctor", "admin"):
            root = REPO / "apps" / app
            for source in [*root.rglob("*.ts"), *root.rglob("*.tsx")]:
                if "node_modules" in source.parts or ".next" in source.parts:
                    continue
                for path in _API_LITERAL.findall(source.read_text(encoding="utf-8")):
                    checked += 1
                    self.assertTrue(
                        _matches(path, routes),
                        f"{source.relative_to(root)} calls {path}, which the API does not define",
                    )
        for source in (REPO / "packages" / "shared" / "src").rglob("*.ts"):
            for path in _API_LITERAL.findall(source.read_text(encoding="utf-8")):
                checked += 1
                self.assertTrue(
                    _matches(path, routes),
                    f"shared/{source.name} calls {path}, which the API does not define",
                )
        self.assertGreater(checked, 60)


@unittest.skipUnless((CATALOG / "care-clinic").is_dir(), "needs the published CareClinic template")
class CareClinicCatalogTests(unittest.TestCase):
    """R-538: what the marketplace lists."""

    def setUp(self) -> None:
        self.published = CATALOG / "care-clinic"
        self.manifest = json.loads((self.published / "template.json").read_text(encoding="utf-8"))

    def test_manifest_is_listable(self) -> None:
        self.assertEqual(self.manifest["slug"], "care-clinic")
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(self.manifest["category"], "healthcare")
        self.assertEqual({app["id"] for app in self.manifest["apps"]}, {"patient", "doctor", "admin", "api"})

    def test_every_screen_has_an_image_on_disk(self) -> None:
        screens = self.manifest["screens"]
        self.assertEqual(len(screens), 48)
        by_app: dict[str, int] = {}
        for screen in screens:
            self.assertTrue((self.published / screen["image"]).is_file(), screen["image"])
            for key in ("app", "title", "description", "route"):
                self.assertTrue(screen[key].strip(), f"{screen['image']} has no {key}")
            by_app[screen["app"]] = by_app.get(screen["app"], 0) + 1
        self.assertEqual(by_app, {"patient": 16, "doctor": 14, "admin": 18})
        self.assertTrue((self.published / self.manifest["cover"]).is_file())

    def test_demo_users_match_the_seed(self) -> None:
        seed = (self.published / "repo" / "services" / "api" / "seed" / "001_demo.sql").read_text(encoding="utf-8")
        for user in self.manifest["demo_users"]:
            self.assertIn(user["email"], seed, f"{user['email']} is advertised but not seeded")

    def test_no_build_output_or_dependencies_are_published(self) -> None:
        for path in (self.published / "repo").rglob("*"):
            self.assertNotIn(path.name, {"node_modules", ".next", ".turbo"}, f"{path} must not be published")


if __name__ == "__main__":
    unittest.main()
