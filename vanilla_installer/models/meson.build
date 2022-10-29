pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
modelsdir = join_paths(pkgdatadir, 'vanilla_installer/models')

subdir('locales')

sources = [
  '__init__.py',
  'locale.py',
  'keymaps.py',
  'timezones.py',
]

install_data(sources, install_dir: modelsdir)