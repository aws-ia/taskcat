# Clean up docs
mkdir -p docs/apidocs
mkdir -p docs/schema
# Install docs tools
pip install portray pdocs json-schema-for-humans

# Gererate API docs
portray as_html taskcat  -o docs/apidocs/ --overwrite

# Generate taskcat schema docs
python3 generate_schema.py
generate-schema-doc --config expand_buttons=true taskcat/cfg/config_schema.json docs/schema/taskcat_schema.md

printf "\n\nReformatting schema files to specifications. Ignore the end-of-file-fixer error.\n\n"
pre-commit run --all-files

# Push to gh_pages
portray on_github_pages --overwrite
