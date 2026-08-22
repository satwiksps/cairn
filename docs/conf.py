"""Sphinx configuration for the Steadlith documentation."""

from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version

project = "Steadlith"
author = "Steadlith contributors"
copyright = "2026, Steadlith contributors"

try:
    release = version("steadlith")
except PackageNotFoundError:
    release = "1.0.0"
version = ".".join(release.split(".")[:2])

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
]

source_suffix = {".md": "markdown"}
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
nitpicky = True

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 4

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_format = "short"
autosummary_generate = False

copybutton_prompt_text = r">>> |\.\.\. |\$ |PS> "
copybutton_prompt_is_regexp = True
copybutton_only_copy_prompt_lines = True

html_theme = "furo"
html_title = "Steadlith documentation"
html_logo = "_static/steadlith-mark.svg"
html_favicon = "_static/steadlith-mark.svg"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")
html_last_updated_fmt = "%Y-%m-%d"
html_show_sourcelink = True

html_theme_options = {
    "source_repository": "https://github.com/satwiksps/steadlith/",
    "source_branch": "main",
    "source_directory": "docs/",
    "light_css_variables": {
        "color-brand-primary": "#176b4a",
        "color-brand-content": "#176b4a",
        "color-api-name": "#0f5132",
    },
    "dark_css_variables": {
        "color-brand-primary": "#8ce8b3",
        "color-brand-content": "#8ce8b3",
        "color-api-name": "#8ce8b3",
        "color-background-primary": "#0b0e0c",
        "color-background-secondary": "#111713",
    },
}

html_context = {
    "display_github": True,
    "github_user": "satwiksps",
    "github_repo": "steadlith",
    "github_version": "main",
    "conf_py_path": "/docs/",
}
