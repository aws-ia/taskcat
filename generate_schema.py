import json
import sys

from taskcat._dataclasses import BaseConfig

if __name__ == "__main__":
    if sys.version_info[0] == 3 and sys.version_info[1] == 7:
        schema = BaseConfig.json_schema()
        with open("./taskcat/cfg/config_schema.json", "w") as f:
            f.write(
                json.dumps(schema, sort_keys=True, indent=4, separators=(",", ": "))
            )

            f.write("\n")
