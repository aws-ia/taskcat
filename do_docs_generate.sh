# Clean up docs
rm -rf docs; mkdir docs
# Install docs tools
pip install portray
pip install pdocs

# Create docs dir
mkdir docs/schema
mkdir docs/apidocs/
# Gererate API docs
pdocs as_html taskcat  -o docs/apidocs/

# Generate taskcat schema docs
python3 generate_schema.py
python3 generate_config_docs.py  >docs/schema/taskcat_schema.md
