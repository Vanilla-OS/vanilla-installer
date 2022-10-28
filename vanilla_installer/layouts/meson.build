pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
layoutsdir = join_paths(pkgdatadir, 'vanilla_installer/layouts')

sources = [
  '__init__.py',
  'preferences.py',
  'yes_no.py',
]

install_data(sources, install_dir: layoutsdir)