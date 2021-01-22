import unittest
from pathlib import Path

import yaml

from taskcat.testing import CFNTest


class TestRetain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cur_dir = Path(__file__).parent
        templates = Path("../../../tests/data/")
        cls.template_dir = cur_dir / templates / "retain-resources"

    def test_from_file(self):
        test = CFNTest.from_file(project_root=self.template_dir.resolve())

        with test as stacks:

            for stack in stacks:

                bucket_name = ""

                for output in stack.outputs:

                    if output.key == "LogsBucketName":
                        bucket_name = output.value
                        break

                assert "logs" in bucket_name

                assert stack.region.name in bucket_name

    def test_from_dict(self):
        taskcat_config = self.template_dir / ".taskcat.yml"

        with open(taskcat_config.resolve()) as f:
            config = yaml.load(f.read(), Loader=yaml.SafeLoader)

        config["tests"]["log-bucket"]["parameters"]["KeepBucket"] = "TRUE"

        test = CFNTest.from_dict(config, project_root=self.template_dir.resolve())

        with test as stacks:
            pass

        for stack in stacks:
            session = stack.region.session

            s3 = session.resource("s3")

            for output in stack.outputs:

                if output.key == "LogsBucketName":
                    bucket = s3.Bucket(output.value)
                    bucket.wait_until_exists()
                    bucket.delete()
                    bucket.wait_until_not_exists()
                    break
