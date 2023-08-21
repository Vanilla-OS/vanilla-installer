pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'vanilla_installer')
gnome = import('gnome')

blueprints = custom_target('blueprints',
  input: files(
    'gtk/confirm.blp',
    'gtk/default-keyboard.blp',
    'gtk/default-language.blp',
    'gtk/default-theme.blp',
    'gtk/default-timezone.blp',
    'gtk/default-users.blp',
    'gtk/dialog-disk-confirm.blp',
    'gtk/dialog-disk.blp',
    'gtk/dialog-output.blp',
    'gtk/dialog.blp',
    'gtk/done.blp',
    'gtk/layout-preferences.blp',
    'gtk/layout-yes-no.blp',
    'gtk/progress.blp',
    'gtk/tour.blp',
    'gtk/widget-choice-expander.blp',
    'gtk/widget-choice.blp',
    'gtk/widget-disk.blp',
    'gtk/widget-partition-row.blp',
    'gtk/window.blp',
    'gtk/default-welcome.blp',
    'gtk/default-disk.blp',
    'gtk/default-encryption.blp',
    'gtk/default-nvidia.blp',
    'gtk/dialog-recovery.blp',
    'gtk/widget-partition.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

gnome.compile_resources('vanilla-installer',
  'vanilla-installer.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: blueprints,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'vanilla-installer.in',
  output: 'vanilla-installer',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

configure_file(
  input: 'vanilla-installer-processor.in',
  output: 'vanilla-installer-processor',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

subdir('defaults')
subdir('layouts')
subdir('core')
subdir('utils')
subdir('views')
subdir('windows')

vanilla_installer_sources = [
  '__init__.py',
  'main.py',
]

install_data(vanilla_installer_sources, install_dir: moduledir)