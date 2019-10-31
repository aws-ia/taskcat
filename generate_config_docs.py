# flake8: noqa
import json

if __name__ == "__main__":

    schema = json.load(open("./taskcat/cfg/config_schema.json", "r"))

    def resolve_ref(props):
        if "$ref" in props:
            ref = props["$ref"].split("/")[-1]
            del props["$ref"]
            props.update(schema["definitions"][ref])
        return props

    for k, v in schema["properties"].items():
        item_str = f"* `{k}` "
        v = resolve_ref(v)
        item_str += f"*type:* `{v['type']}` "
        if "description" in v:
            item_str += f'{v["description"]}'
        print(item_str)
        if "properties" in v:
            for ik, iv in v["properties"].items():
                item_str = f"  * `{ik}` "
                iv = resolve_ref(iv)
                item_str += f"*type:* `{iv['type']}` "
                if "description" in iv:
                    item_str += f'{iv["description"]}'
                print(item_str)
                if iv["type"] == "object":
                    if "properties" in iv:
                        for iik, iiv in iv["properties"].items():
                            item_str = f"  * `{iik}` "
                            iiv = resolve_ref(iiv)
                            item_str += f"*type:* `{iiv['type']}` "
                            if "description" in iiv:
                                item_str += f'{iiv["description"]}'
                    elif "additionalProperties" in iv:
                        name = ik[:-1] if ik.endswith("s") else ik
                        item_str = f"    * `<{name.upper()}_NAME>` "
                        props = resolve_ref(iv["additionalProperties"])
                        item_str += f"*type:* `{iv['type']}` "
                        if "description" in props:
                            item_str += f'{props["description"]}'
                    print(item_str)
        elif "additionalProperties" in v:
            name = k[:-1] if k.endswith("s") else k
            item_str = f"  * `<{name.upper()}_NAME>` "
            props = resolve_ref(v["additionalProperties"])
            item_str += f"*type:* `{v['type']}` "
            if "description" in props:
                item_str += f'{props["description"]}'
            if "properties" in props:
                for ik, iv in props["properties"].items():
                    item_str = f"  * `{ik}` "
                    iv = resolve_ref(iv)
                    item_str += f"*type:* `{iv['type']}` "
                    if "description" in iv:
                        item_str += f'{iv["description"]}'
                    print(item_str)
                    if iv["type"] == "object":
                        if "properties" in iv:
                            for iik, iiv in iv["properties"].items():
                                item_str = f"    * `{iik}` "
                                iiv = resolve_ref(iiv)
                                item_str += f"*type:* `{iiv['type']}` "
                                if "description" in iiv:
                                    item_str += f'{iiv["description"]}'
                        elif "additionalProperties" in iv:
                            name = ik[:-1] if ik.endswith("s") else ik
                            item_str = f"    * `<{name.upper()}_NAME>` "
                            iprops = resolve_ref(iv["additionalProperties"])
                            item_str += f"*type:* `{iv['type']}` "
                            if "description" in iprops:
                                item_str += f'{iprops["description"]}'
                        print(item_str)
        else:
            print(v)
