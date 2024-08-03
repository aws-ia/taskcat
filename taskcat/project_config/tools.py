from collections import OrderedDict


def _add_default_info(param_dict):
    """Method to to add default value"""
    return_str = ""
    if str(param_dict["Default"]) != "":
        return_str = param_dict["Default"]
    else:
        return_str = ""
    return return_str


def _add_region_info(param_name):
    """Method to to add region value"""
    return_str = ""
    if "region" in param_name.lower():
        return_str = "$[taskcat_current_region]"
    return return_str


def _add_pw_info():
    """Method to to add random password"""
    return_str = ""
    return_str = "$[taskcat_genpass_12]"
    return return_str


def _add_parameter_values(parameter_values):
    """Method to add default value to the parameter object"""
    parameter_dict = {}

    parameter_values = OrderedDict(sorted(parameter_values.items()))
    for parameter in parameter_values:
        # Set region info
        if "Region" in parameter_values[parameter].keys():
            parameter_dict[parameter] = _add_region_info(parameter)
            continue
        # Set password value
        if (
            "NoEcho" in parameter_values[parameter].keys()
            and parameter_values[parameter]["NoEcho"] == "true"
            and "password" in parameter.lower()
        ):
            parameter_dict[parameter] = _add_pw_info()
        else:
            parameter_dict[parameter] = ""

    return parameter_dict


def _get_parameter_stats(cfg_parameters):
    """Method to get parameter stats"""
    p_count = len(cfg_parameters)
    p_b_count = sum(cfg_parameters[p] == "" for p in cfg_parameters)
    return_text = (
        f"Parameter Count: {p_count}\r\n"
        f"Parameters with Blank values: {p_b_count}\r\n"
    )
    return return_text
