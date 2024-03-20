
def _add_qs_info(parameter):
    """Method to to add tcparameter for QS items"""
    return_text = ''
    match parameter.name.lower():
        case "qss3bucketname":
            return_text = (f'    {parameter.name}: $[taskcat_autobucket]'
                           f'\r\n')
        case "qss3bucketregion":
            return_text = (f'    {parameter.name}: $[taskcat_current_region]'
                           f'\r\n')
    return return_text


def _add_default_info(parameter):
    """Method to to add default value"""
    return_text = ''
    if str(parameter.Default) != '':
        return_text = f'    {parameter.name}: {str(parameter.Default)}\r\n'
    elif str(parameter.Default) == '' and parameter.Type == 'String':
        return_text = f'    {parameter.name}: ""\r\n'
    elif str(parameter.Default) == '' and parameter.Type == 'Number':
        return_text = f'    {parameter.name}:  \r\n'
    else:
        return_text = f'    {parameter.name}: OVERRIDE\r\n'
    return return_text


def _add_known_info(parameter, all_parameters):
    """Method to to add known items"""
    return_text = ''
    match parameter.name.lower():
        case "VPCCIDR":
            return_text = (f'    {parameter.name}: 10.0.0.0/16'
                           f'\r\n')
        case "PrivateSubnet1ACIDR" | "PrivateSubnet1CIDR":
            return_text = (f'    {parameter.name}: 10.0.0.0/19'
                           f'\r\n')
        case "PrivateSubnet1BCIDR":
            return_text = (f'    {parameter.name}: 10.0.192.0/21'
                           f'\r\n')
        case "PrivateSubnet2ACIDR" | "PrivateSubnet2CIDR":
            return_text = (f'    {parameter.name}: 10.0.32.0/19'
                           f'\r\n')
        case "PrivateSubnet2BCIDR":
            return_text = (f'    {parameter.name}: 10.0.200.0/2'
                           f'\r\n')
        case "PrivateSubnet3ACIDR" | "PrivateSubnet3CIDR":
            return_text = (f'    {parameter.name}: 10.0.64.0/19'
                           f'\r\n')
        case "PrivateSubnet3BCIDR":
            return_text = (f'    {parameter.name}: 10.0.208.0/21'
                           f'\r\n')
        case "PrivateSubnet4ACIDR" | "PrivateSubnet4CIDR":
            return_text = (f'    {parameter.name}: 10.0.96.0/19'
                           f'\r\n')
        case "PrivateSubnet4BCIDR":
            return_text = (f'    {parameter.name}: 10.0.216.0/21'
                           f'\r\n')
        case "PublicSubnet1CIDR":
            return_text += (f'    {parameter.name}: 10.0.128.0/20'
                            f'\r\n')
        case "PublicSubnet2CIDR":
            return_text = (f'    {parameter.name}: 10.0.144.0/20'
                           f'\r\n')
        case "PublicSubnet3CIDR":
            return_text = (f'    {parameter.name}: 10.0.160.0/20'
                           f'\r\n')
        case "PublicSubnet4CIDR":
            return_text = (f'    {parameter.name}: 10.0.176.0/20'
                           f'\r\n')
        case "keypair" | "keypairname":
            return_text = (f'    {parameter.name}: $[taskcat_getkeypair]'
                           f'\r\n')
        case "NumberOfAZs":
            return_text = (f'    {parameter.name}: {str(parameter.Default)}'
                           f'\r\n')
        case "availabilityzones" | "azs":
            naz = [
                parm for parm in all_parameters
                if parm.name.lower() == "numberofazs"
            ]
            if len(naz) != 0:
                return_text += (f'    {parameter.name}: $[taskcat_genaz_'
                                f'{getattr(naz[0], "Default")}\r\n')
            else:
                return_text += (f'    {parameter.name}: $[taskcat_genaz_2'
                                f'\r\n')
    return return_text


def _add_region_info(parameter):
    """Method to to add region value"""
    return_text = ''
    if "Region" in parameter.name:
        return_text = f'    {parameter.name}: $[taskcat_current_region]\r\n'
    return return_text


def _add_pw_info(parameter):
    """Method to to add random password"""
    return_text = f'    {parameter.name}: $[taskcat_genpass_12]\r\n'
    return return_text


def _add_allowed_value(parameter):
    """Method to to add allowed value"""
    return_text = (f'    {parameter.name}: '
                   f'{str(parameter.AllowedValues[0])}\r\n')
    return return_text


def _add_parameter_values(parameter_values):
    """Method to add default value to the parameter object"""
    parameter_help = ""
    parameter_text = ""
    parameter_override = ""

    parameter_values.sort(key=lambda x: x.name)
    for parameter in parameter_values:
        # if verbose_config:
        #     # Write help information
        #     parameter_help = add_help_info(parameter)
        # Set QS Parameters
        if (parameter.name.lower() == "qss3bucketname") \
                or (parameter.name.lower() == "qss3bucketregion"):
            parameter_text += (f'{parameter_help}{_add_qs_info(parameter)}')
            continue
        # Set Default value
        if hasattr(parameter, "Default"):
            default_info = _add_default_info(parameter)
            if 'OVERRIDE' in default_info:
                parameter_override += (f'{parameter_help}{default_info}')
            else:
                parameter_text += (f'{parameter_help}{default_info}')
            continue
        # Match any known parameter values
        known_info = _add_known_info(parameter, parameter_values)
        if known_info:
            parameter_text += (f'{parameter_help}'
                               f'{known_info}')
            continue
        # Set region info
        if "Region" in parameter.name:
            parameter_text += (f'{parameter_help}{_add_region_info(parameter)}')
            continue
        # Set password value
        if hasattr(parameter, "NoEcho") \
            and parameter.NoEcho == 'true' \
                and 'password' in parameter.name.lower():
            parameter_text += (f'{parameter_help}{_add_pw_info(parameter)}')
            continue
        # Choose the first alowable value if there is no default defined
        if hasattr(parameter, "AllowedValues"):
            parameter_text += (f'{parameter_help}'
                               f'{_add_allowed_value(parameter)}')
            continue
        # If nothing else can be identified mark as unknown.
        else:
            parameter_override += (f'{parameter_help}    {parameter.name}'
                                   f': OVERRIDE\r\n')
    # Position overriden parameters at the top
    parameter_override += parameter_text
    return parameter_override
