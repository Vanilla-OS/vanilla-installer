import os
import glob
import importlib
import inspect

path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
files = glob.glob(os.path.join(path, "*.py"))
files.remove(os.path.join(path, "__init__.py"))

all_locales_categorized = {}
for file in files:
    module = importlib.import_module("vanilla_installer.models.locales." + os.path.basename(file)[:-3])
    all_locales_categorized[module.name] = module.locales

all_locales = []
for category in all_locales_categorized:
    for locale in all_locales_categorized[category]:
        all_locales.append(locale)

all_locales.sort(key=lambda locale: locale.location)