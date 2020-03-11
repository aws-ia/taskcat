#!/usr/bin/env python
# because something like https://github.com/boto/boto3/issues/1868 doesn't exist

import json

import requests

ENDPOINT_JSON = (
    "https://raw.githubusercontent.com/boto/botocore/master/botocore/"
    "data/endpoints.json"
)

if __name__ == "__main__":
    resp = requests.get(ENDPOINT_JSON)
    if resp.status_code != 200:
        raise Exception(f"{resp.status_code} {resp.reason}")
    endpoints = resp.json()
    partitions = {}
    regions = {}
    for p in endpoints["partitions"]:
        partitions[p["partition"]] = list(p["regions"])
        for r in p["regions"]:
            regions[r] = p["partition"]
    with open("./taskcat/regions_to_partitions.py", "w") as fh:
        fh.write(f"REGIONS = {json.dumps(regions, indent=4)}\n\n")
        fh.write(f"PARTITIONS = {json.dumps(partitions, indent=4)}\n")
