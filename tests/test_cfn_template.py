import unittest
from pathlib import Path

from taskcat import Config


class TestCfnTemplate(unittest.TestCase):
    def test_init(self):
        test_proj = (Path(__file__).parent / "./data/nested-fail").resolve()
        c = Config.create(
            project_config_path=test_proj / ".taskcat.yml", project_root=test_proj
        )
        templates = c.get_templates()
        template = templates["taskcat-json"]
        self.assertEqual(1, len(template.children))
        self.assertEqual(4, len(template.descendents))
