from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GitHubWorkflowTests(unittest.TestCase):
    def test_scraper_runs_chrome_headless(self):
        source = (ROOT / "survias_scraper.py").read_text(encoding="utf-8")

        self.assertIn('chrome_options.add_argument("--headless=new")', source)
        self.assertNotIn(
            '# chrome_options.add_argument("--headless=new")',
            source,
        )

    def test_workflow_uses_chile_timezone_and_repository_secrets(self):
        workflow = (
            ROOT / ".github" / "workflows" / "survias-scraper.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("timezone: America/Santiago", workflow)
        self.assertIn("cron: '0 8 * * 1'", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("SURVIAS_RUT1: ${{ secrets.SURVIAS_RUT1 }}", workflow)
        self.assertIn(
            "SURVIAS_PASSWORD1: ${{ secrets.SURVIAS_PASSWORD1 }}",
            workflow,
        )
        self.assertIn("SURVIAS_RUT2: ${{ secrets.SURVIAS_RUT2 }}", workflow)
        self.assertIn(
            "SURVIAS_PASSWORD2: ${{ secrets.SURVIAS_PASSWORD2 }}",
            workflow,
        )
        self.assertIn("DATABASE_URL: ${{ secrets.DATABASE_URL }}", workflow)


if __name__ == "__main__":
    unittest.main()
