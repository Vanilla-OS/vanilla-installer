pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
defaults_disk_dir = join_paths(pkgdatadir, 'vanilla_installer/defaults/disks')

sources = [
  '__init__.py',
  'disk_widgets.py',
  'disk_default_page.py',
  'disk_manual_page.py',
]

install_data(sources, install_dir: defaults_disk_dir)
