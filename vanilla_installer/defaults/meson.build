pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
defaultsdir = join_paths(pkgdatadir, 'vanilla_installer/defaults')

sources = [
  '__init__.py',
  'welcome.py',
  'language.py',
  'keyboard.py',
  'timezone.py',
  'disk.py',
  'encryption.py',
  'image.py',
  'nvidia.py',
  'vm.py',
  'conn_check.py',
  'network.py',
]

install_data(sources, install_dir: defaultsdir)
