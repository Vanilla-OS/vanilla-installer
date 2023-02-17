pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
coredir = join_paths(pkgdatadir, 'vanilla_installer/core')

subdir('locales')

sources = [
  '__init__.py',
  'locale.py',
  'languages.py',
  'keymaps.py',
  'timezones.py',
  'disks.py',
  'system.py'
]

install_data(sources, install_dir: coredir)
