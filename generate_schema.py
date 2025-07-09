#!/usr/bin/env python
"""
TaskCat Configuration Schema Generator

This script generates a JSON schema file for TaskCat configuration validation.
The schema is derived from the BaseConfig dataclass and is used to validate
TaskCat configuration files (.taskcat.yml) to ensure they conform to the
expected structure and contain valid values.

The generated schema file is used by:
- IDE extensions for configuration file validation and auto-completion
- TaskCat itself for runtime configuration validation
- Documentation generation tools
- CI/CD pipelines for configuration validation

Usage:
    python generate_schema.py

Output:
    Creates/updates ./taskcat/cfg/config_schema.json with the current schema
"""

import json

from taskcat._dataclasses import BaseConfig

if __name__ == "__main__":
    # Generate JSON schema from the BaseConfig dataclass
    # This uses the dataclasses-jsonschema library to automatically
    # create a comprehensive JSON schema based on the dataclass definitions
    schema = BaseConfig.json_schema()
    
    # Write the schema to the configuration directory
    # The schema file is used for validation and IDE support
    with open("./taskcat/cfg/config_schema.json", "w") as f:
        # Format the JSON with consistent indentation and sorting
        # This ensures the schema file is human-readable and diff-friendly
        f.write(json.dumps(
            schema, 
            sort_keys=True,      # Sort keys alphabetically for consistency
            indent=4,            # Use 4-space indentation for readability
            separators=(",", ": ")  # Clean separator formatting
        ))
        
        # Add final newline for POSIX compliance
        f.write("\n")
