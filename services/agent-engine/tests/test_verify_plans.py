from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import assembled_targets
from omnistackai_agent_engine.verify import (
    UnsupportedVerifyTargetError,
    VerifyPlan,
    VerifyStepKind,
    run_verify,
    supported_targets,
    verify_plan,
    verify_plans_for_ir,
)


class VerifyPlanTests(TestCase):
    def test_every_supported_target_has_a_plan(self) -> None:
        self.assertEqual(
            supported_targets(),
            ("backend-go", "backend-python", "nextjs-admin", "nextjs-web"),
        )
        for target in supported_targets():
            plan = verify_plan(target, "apps/web")
            self.assertIsInstance(plan, VerifyPlan)
            self.assertEqual(plan.target, target)

    def test_unknown_target_errors(self) -> None:
        with self.assertRaises(UnsupportedVerifyTargetError):
            verify_plan("flutter", "apps/mobile")

    def test_plan_steps_are_ladder_ordered(self) -> None:
        order = list(VerifyStepKind)
        for target in supported_targets():
            kinds = [step.kind for step in verify_plan(target, "d").steps]
            positions = [order.index(kind) for kind in kinds]
            self.assertEqual(positions, sorted(positions), target)

    def test_gate_classification(self) -> None:
        web = verify_plan("nextjs-web", "apps/web")
        self.assertEqual(web.gates(), (VerifyStepKind.INSTALL, VerifyStepKind.TYPECHECK, VerifyStepKind.LINT, VerifyStepKind.BUILD))
        self.assertEqual(web.steps[0].command.program, "pnpm")

        go = verify_plan("backend-go", "services/api")
        self.assertIn(VerifyStepKind.BUILD, go.gates())
        self.assertEqual(go.steps[-1].command.display(), "go build ./...")

        py = verify_plan("backend-python", "services/api")
        self.assertIn(VerifyStepKind.TEST, py.gates())
        self.assertEqual(py.steps[0].command.display(), "pip install -r requirements.txt")

    def test_display_lists_each_gate(self) -> None:
        text = verify_plan("backend-go", "services/api").display()
        self.assertIn("[lint] vet: go vet ./...", text)
        self.assertIn("[build]", text)


class IrMappingTests(TestCase):
    def test_rideshare_maps_web_and_go(self) -> None:
        ir = example_ir("rideshare-favourites")  # nextjs web + go backend
        plans = verify_plans_for_ir(ir)
        by_dir = {plan.app_dir: plan.target for plan in plans}
        self.assertEqual(by_dir, {"apps/web": "nextjs-web", "services/api": "backend-go"})

    def test_blog_maps_web_and_python(self) -> None:
        ir = example_ir("minimal-blog")  # nextjs web + python backend (+ admin, not assembled)
        plans = verify_plans_for_ir(ir)
        by_dir = {plan.app_dir: plan.target for plan in plans}
        self.assertEqual(by_dir, {"apps/web": "nextjs-web", "services/api": "backend-python"})

    def test_mapping_matches_assembled_targets(self) -> None:
        ir = example_ir("rideshare-favourites")
        assembled = {app.directory for app in assembled_targets(ir)}
        planned = {plan.app_dir for plan in verify_plans_for_ir(ir)}
        self.assertEqual(planned, assembled)


class PlanSafetyTests(TestCase):
    def test_no_control_characters_and_run_verify_is_callable(self) -> None:
        for target in supported_targets():
            for step in verify_plan(target, "d").steps:
                rendered = step.command.display()
                self.assertNotIn("\x00", rendered)
                self.assertNotIn("\n", rendered)
        self.assertTrue(callable(run_verify))  # executor exists; not run here
