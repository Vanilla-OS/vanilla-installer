pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
localesdir = join_paths(pkgdatadir, 'vanilla_installer/models/locales')

sources = [
    '__init__.py',
    'africa.py',
    'america.py',
    'antarctica.py',
    'arctic.py',
    'asia.py',
    'atlantic.py',
    'australia.py',
    'brazil.py',
    'canada.py',
    'chile.py',
    'europe.py',
    'indian.py',
    'mexico.py',
    'pacific.py',
]

install_data(sources, install_dir: localesdir)