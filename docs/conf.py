import datetime
import os

# Chopsticks Documentation Configuration

#######################
# Project information #
#######################

project = "Chopsticks"
author = "Canonical Ltd."
copyright = "%s Apache-2.0, %s" % (datetime.date.today().year, author)

html_title = project + " documentation"

# Documentation website URL
ogp_site_url = "https://canonical-chopsticks.readthedocs-hosted.com/"
ogp_site_name = project
ogp_image = "https://assets.ubuntu.com/v1/cc828679-docs_illustration.svg"

# HTML context for templates
html_context = {
    "product_page": "github.com/canonical/chopsticks",
    "discourse": "https://discourse.ubuntu.com",
    "github_url": "https://github.com/canonical/chopsticks",
    'repo_default_branch': 'main',
    "repo_folder": "/docs/",
    "display_contributors": True,
    'github_issues': 'enabled',
}

#######################
# Sitemap configuration
#######################

html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "/")

if 'READTHEDOCS_VERSION' in os.environ:
    version = os.environ["READTHEDOCS_VERSION"]
    sitemap_url_scheme = '{version}{link}'
else:
    sitemap_url_scheme = 'MANUAL/{link}'

sitemap_show_lastmod = True
sitemap_excludes = [
    '404/',
    'genindex/',
    'search/',
]

#############
# Redirects #
#############

redirects = {}

###########################
# Link checker exceptions #
###########################

linkcheck_ignore = [
    "http://127.0.0.1:8000",
    "http://10.240.47.47:80",  # Local test endpoints
    "http://localhost:8089",  # Locust web UI (local only)
    "http://controller-ip:8089",  # Placeholder for user's controller IP
]

linkcheck_anchors_ignore_for_url = [r"https://github\.com/.*"]
linkcheck_retries = 3

########################
# Configuration extras #
########################

extensions = [
    "canonical_sphinx",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

exclude_patterns = [
    "doc-cheat-sheet*",
    "README.md",
    ".sphinx",
]

rst_epilog = """
.. include:: /reuse/links.txt
"""

rst_prolog = """
.. role:: center
   :class: align-center
"""

# Workaround for https://github.com/canonical/canonical-sphinx/issues/34
if "discourse_prefix" not in html_context and "discourse" in html_context:
    html_context["discourse_prefix"] = html_context["discourse"] + "/t/"

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'locust': ('https://docs.locust.io/en/stable/', None),
}
