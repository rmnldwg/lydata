# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import lydata

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "lyDATA"
copyright = "2024, Roman Ludwig"
author = "Roman Ludwig"
gh_username = "rmnldwg"
version = lydata.__version__
release = lydata.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "myst_parser",
]

source_suffix = [".rst", ".md"]
templates_path = ["_templates"]
exclude_patterns = []

# document classes and their constructors
autoclass_content = "class"

# sort members by source
autodoc_member_order = "bysource"

# show type hints
autodoc_typehints = "signature"

# create links to other projects
intersphinx_mapping = {
    "python": ("https://docs.python.org/3.10", None),
    "lymph": ("https://lymph-model.readthedocs.io/latest/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandera": ("https://pandera.readthedocs.io/en/stable/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

# -- MyST configuration ------------------------------------------------------
myst_enable_extensions = [
    "dollarmath",
    "linkify",
    "colon_fence",
]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_theme_options = {
    "repository_url": f"https://github.com/{gh_username}/{project}",
    "repository_branch": "main",
    "use_repository_button": True,
    "show_navbar_depth": 3,
    "home_page_in_toc": True,
}

html_static_path = ["_static"]
html_css_files = [
    "css/custom.css",
]
