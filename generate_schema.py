import json
import sys

from taskcat._dataclasses import BaseConfig

SUPPORTED_VERSIONS = [(3, 6), (3, 7), (3, 8)]

if __name__ == "__main__":
    if (sys.version_info.major, sys.version_info.minor) not in SUPPORTED_VERSIONS:
        raise Exception("unsupported python version")
    schema = BaseConfig.json_schema()
    with open("./taskcat/cfg/config_schema.json", "w") as f:
        f.write(json.dumps(schema, sort_keys=True, indent=4, separators=(",", ": ")))
        f.write("\n")
