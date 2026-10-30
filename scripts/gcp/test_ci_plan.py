"""Safety checks for integrated change selection and reusable validation evidence."""

import unittest

import ci_plan


class CiPlanTests(unittest.TestCase):
    def setUp(self):
        self.sources = {name: char * 40 for name, char in zip(ci_plan.COMPONENTS, "abc")}
        self.baseline = {
            "integration_tag": "integration-1-1",
            "release": "release-" + "d" * 32,
            "root_sha": "e" * 40,
            "sources": dict(self.sources),
            "android_input_sha256": "f" * 64,
            "android_verified_mobile_sha": self.sources["mobile"],
        }
        self.android_key = "f" * 64

    def plan(self, root=(), backend=(), frontend=(), mobile=(), force=None):
        paths = {"backend": backend, "frontend": frontend, "mobile": mobile}
        return ci_plan.make_plan("1" * 40, self.sources, self.baseline, root, paths, self.android_key, force)

    def test_unknown_baseline_runs_everything(self):
        plan = self.plan(force="no complete integration baseline")
        self.assertEqual(plan["images"], list(ci_plan.SERVICES))
        self.assertTrue(plan["infrastructure"]["run"])
        self.assertTrue(plan["cloudsql"]["run"])
        self.assertTrue(all(job["run"] for job in plan["components"].values()))

    def test_documentation_only_change_skips_component_tests_and_images(self):
        plan = self.plan(frontend=("docs/architecture.md", "README.md"))
        self.assertFalse(any(job["run"] for job in plan["components"].values()))
        self.assertEqual(plan["images"], [])
        self.assertFalse(plan["publish_required"])

    def test_mobile_tests_change_does_not_rebuild_android_or_web_images(self):
        current = dict(self.sources, mobile="1" * 40)
        plan = ci_plan.make_plan("2" * 40, current, self.baseline, (),
                                 {"backend": (), "frontend": (), "mobile": ("tests/NexoRuta.Mobile.Api.Tests/ApiTests.cs",)},
                                 self.android_key)
        self.assertTrue(plan["components"]["mobile_portable"]["run"])
        self.assertFalse(plan["components"]["mobile_android"]["run"])
        self.assertIn("app-input digest", plan["components"]["mobile_android"]["reason"])
        self.assertEqual(plan["images"], [])

    def test_mobile_application_change_requires_android_and_no_container_images(self):
        current = dict(self.sources, mobile="1" * 40)
        plan = ci_plan.make_plan("2" * 40, current, self.baseline, (),
                                 {"backend": (), "frontend": (), "mobile": ("src/NexoRuta.Mobile/MainPage.xaml",)},
                                 "0" * 64)
        self.assertTrue(plan["components"]["mobile_portable"]["run"])
        self.assertTrue(plan["components"]["mobile_android"]["run"])
        self.assertEqual(plan["images"], [])

    def test_backend_contract_change_validates_consumers(self):
        plan = self.plan(backend=("src/NexoRuta.Api/Controllers/EnviosController.cs",))
        self.assertTrue(plan["components"]["backend"]["run"])
        self.assertTrue(plan["components"]["frontend"]["run"])
        self.assertTrue(plan["components"]["mobile_portable"]["run"])
        self.assertFalse(plan["components"]["mobile_android"]["run"])
        self.assertEqual(plan["images"], ["api", "worker"])

    def test_geojson_change_rebuilds_backoffice_asset_consumer(self):
        plan = self.plan(backend=("src/ZonasCobertura/Data/departamentos-uruguay.geojson",))
        self.assertTrue(plan["components"]["frontend"]["run"])
        self.assertEqual(plan["images"], ["api", "worker", "backoffice"])

    def test_frontend_source_change_builds_only_frontend_images(self):
        plan = self.plan(frontend=("src/NexoRuta.Admin/Pages/Index.razor",))
        self.assertTrue(plan["components"]["frontend"]["run"])
        self.assertEqual(plan["images"], ["admin", "backoffice", "commerce", "tracking"])
        self.assertFalse(plan["components"]["backend"]["run"])

    def test_root_pipeline_change_invalidates_all_inputs(self):
        plan = self.plan(root=(".github/workflows/ci.yml",))
        self.assertEqual(plan["images"], list(ci_plan.SERVICES))
        self.assertTrue(all(job["run"] for job in plan["components"].values()))
        self.assertTrue(plan["infrastructure"]["run"])
        self.assertTrue(plan["cloudsql"]["run"])


if __name__ == "__main__":
    unittest.main()
