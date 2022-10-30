pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
utilsdir = join_paths(pkgdatadir, 'vanilla_installer/utils')

sources = [
  '__init__.py',
  'run_async.py',
  'processor.py',
  'recipe.py',
  'builder.py',
]

install_data(sources, install_dir: utilsdir)