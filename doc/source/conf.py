# -*- coding: utf-8 -*-
#
# Capsul documentation build configuration file, created by
# sphinx-quickstart on Wed Sep  4 12:18:01 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

from __future__ import print_function
import sys, os
import time
import shutil
import subprocess

# Doc generation depends on being able to import capsul
try:
    import capsul
except ImportError:
    raise RuntimeError('Cannot import CAPSUL, please investigate')

from distutils.version import LooseVersion
import sphinx
if LooseVersion(sphinx.__version__) < LooseVersion('1'):
    raise RuntimeError('Need sphinx >= 1 for autodoc to work correctly')

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0,os.path.abspath('sphinxext'))

# -- General configuration -----------------------------------------------------

# We load the release info into a dict by explicit execution
release_info = {}
finfo = os.path.join('..', '..', 'capsul', 'info.py')
with open(finfo) as f:
    exec(compile(f.read(), finfo, 'exec'), release_info)

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
try:
    # try napoleon which replaces numpydoc (and googledoc),
    # comes with sphinx 1.2
    import sphinx.ext.napoleon
    napoleon = 'sphinx.ext.napoleon'
except ImportError:
    # not available, fallback to numpydoc
    napoleon = 'numpy_ext.numpydoc'
extensions = [ 'sphinx.ext.autodoc',
               'sphinx.ext.doctest',
               'sphinx.ext.intersphinx',
               'sphinx.ext.todo',
               'sphinx.ext.coverage',
               #'sphinx.ext.imgmath',
               'sphinx.ext.ifconfig',
               'sphinx.ext.autosummary',
               'sphinx.ext.viewcode',
               napoleon,
               'sphinx.ext.extlinks',
               'sphinx.ext.ifconfig',
               'sphinx.ext.inheritance_diagram',
             ]

try:
    # nbsphinx converts ipython/jupyter notebooks to sphinx docs
    import nbsphinx
    if not shutil.which('pandoc'):
        print('Warning: pandoc is missing. Notebooks will not be included '
              'in the docs')
    else:
        nbsphinx_allow_errors = True
        extensions += ['nbsphinx',
                      'sphinx.ext.mathjax']
        # set this env variable to tell notebooks that we should not use
        # any GUI during notebooks execution
        os.environ['ALLOW_GUI'] = '0'
        print('-- nbsphinx should work. --')
except ImportError as e:
    nbsphinx = None
    print('Warning: nbsphinx could not be imported, the notebooks will not '
          'appear in the docs')
    #print(e)
    #import traceback
    #traceback.print_exc()

# inheritance_diagram config
inheritance_graph_attrs = dict(rankdir="LR", size='"13.0, 40.0"',
                               fontsize=14)  #, ratio='compress')
#inheritance_alias = {'subprocess32.Popen': 'Popen', 'subprocess.Popen': 'Popen', 'capsul.subprocess.fsl.Popen': 'fsl_Popen', 'capsul.subprocess.spm.Popen': 'spm_Popen'}
if not shutil.which('dot'):
    # dot is not installed, inheritance_diagram will not work
    import sphinx.ext.inheritance_diagram
    def null(*args, **kwargs):
        pass
    sphinx.ext.inheritance_diagram.render_dot_html = null
    sphinx.ext.inheritance_diagram.render_dot_latex = null
    sphinx.ext.inheritance_diagram.render_dot_texinfo = null

#

# Remove some numpy-linked warnings
numpydoc_show_class_members = False

# Generate autosummary even if no references
autosummary_generate = True

# Autodoc of class members
#autodoc_default_flags = ['members', 'inherited-members']
autodoc_default_flags = ['members']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'CAPSUL'
release_info['COPYRIGHT_YEAR'] = time.strftime('%Y')
copyright = u'%(COPYRIGHT_YEAR)s, %(AUTHOR)s <%(AUTHOR_EMAIL)s>' % release_info

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = release_info['__version__']
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_patterns = ['examples',
                    "_themes/scikit-learn/static/ML_MAPS_README.rst",
                    '_build',
                    '**.ipynb_checkpoints'] \
                   + templates_path

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------


# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
#html_theme = 'scikit-learn'
html_theme = 'default'
html_style = 'custom.css'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {'oldversion': False, 'collapsiblesidebar': True,
                      #'google_analytics': True, 'surveybanner': False,
                      #'sprintbanner': True}
html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "CAPSUL - Chain algorithm in pipelines and execute in many contexts"

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = "CAPSUL"

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = ""

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = { '**': ['localtoc.html', 'relations.html'],}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = True

# If false, no index is generated.
html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'capsul-doc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'capsul.tex', u'CAPSUL Documentation',
   u'CATI', 'manual'),
]

autoclass_content = "both"

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

#try:
    #from soma_workflow import info as swinfo
    #swf_version = '-%d.%d' % (swinfo.version_major, swinfo.version_minor)
#except ImportError:
    #swf_version = ''

try:
    from soma_workflow import version as swver
    somaworkflow_version = swver.shortVersion
except ImportError:
    somaworkflow_version = '2.9'
try:
    import soma.info
    somabase_version = '%d.%d' % (soma.info.version_major,
                                  soma.info.version_minor)
except ImportError:
    somabase_version = '4.6'

pyversion = '%d.%d' % sys.version_info[:2]

extlinks = {
  #'somabase': ('https://brainvisa.info/soma-base-' + somabase_version + '/sphinx/%s',
    #'somabase '),
  #'somaworkflow': ('https://brainvisa.info/soma-workflow-' + somaworkflow_version + '/sphinx/%s',
    #'somaworkflow '),
  'somabase': ('https://brainvisa.info/soma-base/sphinx/%s',
    'somabase '),
  'somaworkflow': ('https://brainvisa.info/soma-workflow/sphinx/%s',
    'somaworkflow '),
}

# Example configuration for intersphinx: refer to the Python standard library.
#intersphinx_mapping = {'https://docs.python.org/': None}

docpath = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(soma.__file__))), 'share', 'doc')

intersphinx_mapping = {
  'somabase': (os.environ.get('SOMABASE_INTERSPHINX_URL',
                              os.path.join(docpath, 'soma-base-' + somabase_version + '/sphinx')),
               None),
  'somaworkflow': (os.environ.get('SOMAWORKFLOW_INTERSPHINX_URL',
                                  os.path.join(docpath, 'soma-workflow-'
                                  + somaworkflow_version + '/sphinx')),
                   None),
  'python': ('https://docs.python.org/%s' % pyversion, None),
  'traits': ('https://docs.enthought.com/traits', None),
}

# init for Qt
try:
    from soma.qt_gui import qt_backend
    qt_backend.set_qt_backend(compatible_qt5=True)
    print('Using Qt backend:', qt_backend.get_qt_backend())
except Exception:
    print('Warning: Qt could not be loaded. GUI will not be documented.')

# Notebooks handling:
#
# Several problems are handled here:
# 1. nbsphinx 0.4 does not read (ignores) notebooks in _static/
#    For this reason we moved the NB to tutorial/
# 2. nbsphinx 0.4 does not allow direct links to the .ipynb (for download)
#    but replaces them with the converted HTML page.
#    For this reason we duplicate the NB into _static/ where NB are not
#    processed, and links not changed
# 3. notebooks include kernel information which does not necessarily match the
#    running/installed python and jupyter kernels.
#    For this reason we conbert them using pupyter nbconvert, forcing the
#    kernel to the current running python version.
# 4. sphinx does not copy image files not in _static/ into the build tree.
#    So we copy them into the build tree.
# 5. nbsphinx 0.4 messes up image links when the notebook is not in the root
#    of the sphinx tree. Typically in a notebook placed in tutorial/,
#    containing links to "images/something.jpg", the HTML page will contain
#    links to "tutorial/images/something.jpg".
#    To overcome this, we copy the images directory into
#    "tutorial/tutorial/images/" in the build tree.
#
# Thus, in git sources we have:
#
#     tutorial/capsul_tutorial.ipynb.in
#     tutorial/images/*.jpg
#
# After running this conf.py (run by sphinx actually), we have additionally,
# still in sources:
#
#     tutorial/capsul_tutorial.ipynb
#
# and in the build tree:
#
#     _static/tutorial/capsul_tutorial.ipynb
#     tutorial/tutorial/images/*.jpg
#
# Hack to copy files from sources to build dir
out_dir = sys.argv[-1]
src_dir = sys.argv[-2]
print('source:', src_dir)
print('dest:', out_dir)
print('cwd:', os.getcwd())
if not os.path.isabs(src_dir) and not os.path.exists(os.path.join(src_dir)):
    # this strange config appears in MAkefile builds
    src_dir = os.getcwd()
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(os.path.dirname(os.getcwd()), out_dir)
# nbsphinx 3/4 has a bug: it adds the 1st directory level to images paths.
# so we have to move it into a 2nd level of 'tutorial'. Probably nbsphinx
# is only working well for notebooks at the root of the source tree.
out_tuto_path = os.path.join(out_dir, 'tutorial')
out_tuto_img_path = os.path.join(out_tuto_path, 'tutorial')
if os.path.exists(out_tuto_img_path):
    shutil.rmtree(out_tuto_img_path)
if not os.path.exists(out_tuto_path):
    os.makedirs(out_tuto_path)
shutil.copytree(os.path.join(src_dir, 'tutorial/images'), out_tuto_img_path)

# convert notebook(s) with correct python kernel
in_nb = os.path.join(src_dir, 'tutorial/capsul_tutorial.ipynb.in')
out_nb = os.path.join(src_dir, 'tutorial/capsul_tutorial.ipynb')
args = [sys.executable, '-m', 'jupyter', 'nbconvert', '--to', 'notebook',
        # Comment execution until v3 API is finished and examples are fixed
        #'--execute',
        #'--ExecutePreprocessor.kernel_name=python%d' % sys.version_info[0],
        '--output', out_nb, in_nb]
print('exec:', *args)
subprocess.check_call(args)

#shutil.copy2(os.path.join(src_dir, 'tutorial/capsul_tutorial.ipynb.in'),
             #os.path.join(out_tuto_path, 'capsul_tutorial.ipynb.in'))
if not os.path.exists(os.path.join(out_dir, '_static/tutorial')):
    os.makedirs(os.path.join(out_dir, '_static/tutorial'))
shutil.copy2(os.path.join(src_dir, 'tutorial/capsul_tutorial.ipynb'),
             os.path.join(out_dir, '_static/tutorial/capsul_tutorial.ipynb'))
