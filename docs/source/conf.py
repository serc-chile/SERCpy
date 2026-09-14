# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'SERCpy'
copyright = '2026, SERC Chile'
author = 'Solar Energy Research Center (SERC) Chile'

release = '0.1'
version = '0.1.0'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'nbsphinx',
    'sphinx_new_tab_link',
]

# Make the compiler interpret backticks (`word`) as code-like text
default_role = "literal"

# -- Options for autodoc / napoleon
autodoc_class_signature = "separated"
autodoc_typehints = "description"

# Prevent Notebooks from being executed
nbsphinx_execute = 'never'

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_css_files = ['custom.css']

# -- Options for EPUB output
epub_show_urls = 'footnote'
