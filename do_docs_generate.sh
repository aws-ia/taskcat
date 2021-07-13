# Clean up docs
mkdir -p docs/apidocs
mkdir -p docs/schema
# Install docs tools
pip install portray
pip install pdocs

# Gererate API docs
portray as_html taskcat  -o docs/apidocs/ --overwrite

# Generate taskcat schema docs
python3 generate_schema.py
python3 generate_config_docs.py  >docs/schema/taskcat_schema.md

# Push to gh_pages
portray on_github_pages --overwrite
