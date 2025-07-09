# TaskCat Documentation Generation

This guide explains how to generate and maintain TaskCat's documentation using the automated `gendocs.sh` script.

## Quick Start

```bash
# 1. First-time setup (installs dependencies and creates structure)
./gendocs.sh --install

# 2. Preview documentation locally
./gendocs.sh --preview

# 3. Build for production
./gendocs.sh --build

# 4. Deploy to GitHub Pages
./gendocs.sh --deploy
```

## Script Options

| Option | Short | Description |
|--------|-------|-------------|
| `--install` | `-i` | Install dependencies and create documentation structure |
| `--preview` | `-p` | Start local development server at http://localhost:8000 |
| `--build` | `-b` | Build static documentation site |
| `--deploy` | `-d` | Deploy to GitHub Pages |
| `--clean` | `-c` | Clean build artifacts |
| `--help` | `-h` | Show help message |

## Documentation Structure

After running `--install`, the following structure is created:

```
docs/
├── index.md                    # Home page
├── installation.md             # Installation guide
├── quickstart.md              # Quick start guide
├── configuration.md           # Configuration reference
├── user-guide/               # User guides
│   ├── template-testing.md
│   ├── multi-region.md
│   └── parameter-overrides.md
├── examples/                 # Usage examples
│   ├── basic.md
│   └── advanced.md
├── reference/                # Auto-generated API docs
└── assets/                   # Images and static files
```

## Features

### Modern Design
- Material Design theme with dark/light mode toggle
- Responsive layout for mobile and desktop
- Professional appearance suitable for enterprise use

### Auto-Generated API Documentation
- Automatically extracts docstrings from Python code
- Generates comprehensive API reference
- Maintains links between related functions and classes

### Developer-Friendly
- Live reload during development
- Syntax highlighting for code blocks
- Tabbed content for multiple formats (YAML/JSON)
- Admonitions for tips, warnings, and notes

### GitHub Integration
- One-command deployment to GitHub Pages
- Automatic edit links to source files
- Social links and repository information

## Customization

### Adding Content
1. Create new `.md` files in the `docs/` directory
2. Update the `nav` section in `mkdocs.yml`
3. Use standard Markdown with Material extensions

### Styling
- Modify `mkdocs.yml` for theme customization
- Add custom CSS in `docs/assets/css/`
- Update colors, fonts, and layout options

### API Documentation
The API documentation is automatically generated from your Python docstrings. The script:
1. Scans all Python files in the `taskcat/` directory
2. Extracts Google-style docstrings
3. Creates cross-referenced documentation
4. Maintains source code links

## Deployment

### GitHub Pages Setup
1. Enable GitHub Pages in repository settings
2. Set source to "GitHub Actions" or "gh-pages branch"
3. Run `./gendocs.sh --deploy` to publish

### Continuous Integration
Add to your GitHub Actions workflow:

```yaml
- name: Generate Documentation
  run: |
    ./gendocs.sh --install
    ./gendocs.sh --build
    ./gendocs.sh --deploy
```

## Troubleshooting

### Common Issues

**Python/pip not found:**
```bash
# Install Python 3.8+ and pip
# On macOS: brew install python
# On Ubuntu: apt-get install python3 python3-pip
```

**MkDocs command not found:**
```bash
./gendocs.sh --install  # Reinstall dependencies
```

**Port 8000 already in use:**
```bash
# Kill existing process or use different port
mkdocs serve --dev-addr=localhost:8001
```

### Getting Help
- Run `./gendocs.sh --help` for usage information
- Check MkDocs documentation: https://www.mkdocs.org/
- Material theme docs: https://squidfunk.github.io/mkdocs-material/

## Best Practices

1. **Keep docstrings updated** - API docs are generated from code
2. **Use consistent formatting** - Follow Google docstring style
3. **Add examples** - Include code examples in documentation
4. **Test locally** - Always preview before deploying
5. **Version control** - Commit documentation changes with code changes

## Advanced Usage

### Custom Plugins
Add plugins to `mkdocs.yml`:
```yaml
plugins:
  - search
  - mkdocstrings
  - mermaid2  # For diagrams
  - pdf-export  # For PDF generation
```

### Multiple Versions
For version-specific documentation:
```bash
mike deploy --push --update-aliases 1.0 latest
mike set-default --push latest
```

This creates a professional documentation site that automatically stays in sync with your codebase and provides an excellent user experience for TaskCat users and contributors.
