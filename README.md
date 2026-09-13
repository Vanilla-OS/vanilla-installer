<div align="center">
    <img src="data/icons/hicolor/scalable/apps/org.vanillaos.Installer.svg" height="64">
    <h1>Vanilla OS Installer</h1>
    <p>A frontend in GTK 4 and Libadwaita for Albius.</p>
    <hr />
    <a href="https://hosted.weblate.org/engage/vanilla-os/">
<img src="https://hosted.weblate.org/widgets/vanilla-os/-/first-setup/svg-badge.svg" alt="Stato traduzione" />
</a>
    <br />
    <img src="data/screenshot.png">
</div>

## Build

### Dependencies

- build-essential
- meson
- libadwaita-1-dev
- gettext
- desktop-file-utils
- libgnome-desktop-4-dev
- libgweather-4-dev
- python3-requests
- gir1.2-vte-3.91
- libnma-dev
- libnma-gtk4-dev
- mutter-common
- x11-xkb-utils

### Build

```bash
meson build
ninja -C build
```

### Install

```bash
sudo ninja -C build install
```

## Run

```bash
vanilla-installer
```

### Using custom recipes

Place a new recipe in `/etc/vanilla-installer/recipe.json` or launch the
utility with the `VANILLA_CUSTOM_RECIPE` environment variable set to the path
of the recipe.

## Use of Generative AI

Maintainers may use generative AI tools as assistants while working on vanilla-installer. Non-trivial assisted commits disclose the tool, model, and scope of the work.

AI tools may assist with code comments, documentation, repetitive code, and issue triage. Maintainers make project decisions and review every assisted change before it is merged.

Use these trailers for non-trivial assisted commits:

```plain
Assisted-by: <tool>:<model-version>
AI-Scope: <what the tool generated and the prompt or a short prompt summary>
```

Single-line completions, renames, and formatting changes do not need trailers.

Coding agents must also follow [AGENTS.md](AGENTS.md) before changing files,
creating commits, or opening pull requests.
