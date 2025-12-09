# Chopsticks Documentation

This directory contains the documentation for Chopsticks, built using Sphinx with the Canonical theme and following the Diátaxis framework.

## 📚 Documentation Structure

The documentation is organized into four content types following [Diátaxis](https://diataxis.fr/):

- **Tutorial** (`tutorial/`) - Learning-oriented guides
- **How-to Guides** (`how-to/`) - Task-oriented instructions
- **Reference** (`reference/`) - Information-oriented technical details
- **Explanation** (`explanation/`) - Understanding-oriented conceptual discussions

## 🌐 Published Documentation

### Main Documentation
- **Production:** https://canonical-chopsticks.readthedocs-hosted.com

### Pull Request Previews
Every pull request automatically gets a preview build on Read the Docs:
- **Format:** `https://canonical-chopsticks--pr-<number>.readthedocs-hosted.com`
- **Example:** PR #11 → https://canonical-chopsticks--pr-11.readthedocs-hosted.com

RTD automatically:
- Builds documentation on PR creation/updates
- Publishes to a unique PR-specific URL
- Updates the PR with a comment containing the preview link
- Removes the preview when the PR is closed/merged

## 🛠️ Local Development

### Install Dependencies
```bash
cd docs
make install
```

### Build HTML
```bash
make html
```

Open `_build/index.html` in your browser to view.

### Live Preview
```bash
make run
```

Opens http://localhost:8000 with auto-reload on file changes.

## ✅ Quality Checks

### Run All Checks
```bash
make vale      # Style guide compliance
make woke      # Inclusive language check
make spelling  # Spell checking
make linkcheck # Verify all links
```

### Add Custom Terms
Edit `.custom_wordlist.txt` to add project-specific terms that should not be flagged as spelling errors.

## 📝 Writing Documentation

### File Format
- Use reStructuredText (`.rst`) for structured content
- MyST Markdown (`.md`) is also supported for simple pages

### Style Guidelines
- Follow the Canonical style guide (enforced by Vale)
- Use inclusive language (enforced by woke checks)
- Include code examples where relevant
- Add cross-references between related pages

### Document Structure
```rst
Page Title
==========

Brief introduction to the topic.

Section Heading
---------------

Content with examples:

.. code-block:: bash

   chopsticks run --config myconfig.yaml

Subsection
~~~~~~~~~~

More detailed content.
```

## 🔧 Configuration Files

- `.readthedocs.yaml` - Read the Docs build configuration
- `conf.py` - Sphinx configuration
- `requirements.txt` - Python dependencies
- `Makefile` - Build automation
- `.custom_wordlist.txt` - Custom vocabulary for spell checking

## 🤝 Contributing

When adding new documentation:

1. Choose the appropriate Diátaxis category
2. Follow existing file naming conventions
3. Add the new file to the appropriate `index.rst` toctree
4. Run quality checks locally before committing
5. Ensure CI checks pass

## 🐛 Troubleshooting

### Build Failures
```bash
# Clean build artifacts
make clean

# Rebuild from scratch
make html
```

### Vale/Woke Errors
- Check `.custom_wordlist.txt` for missing terms
- Review inclusive language alternatives
- Consult the Canonical style guide

## 📖 Resources

- [Diátaxis Framework](https://diataxis.fr/)
- [Canonical Documentation Starter Pack](https://github.com/canonical/sphinx-docs-starter-pack)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Read the Docs](https://docs.readthedocs.io/)
