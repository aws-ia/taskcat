import json

import boto3

ec2 = boto3.client("ec2")

local_zones = set()
regions = [x["RegionName"] for x in ec2.describe_regions()["Regions"]]

for rn in regions:
    e = boto3.client("ec2", region_name=rn)
    for zone in e.describe_availability_zones(AllAvailabilityZones=True)[
        "AvailabilityZones"
    ]:
        if zone["ZoneType"] in ["availability-zone", "local-zone"]:
            local_zones.add(zone["ZoneName"])

with open("./taskcat/local_zones.py", "w") as fh:
    fh.write(f"ZONES = {json.dumps(sorted(local_zones), indent=4)}\n\n")
