# ROUNDED

Rounded Plasma theme suite, migrated for the installed KDE Plasma 6.8 Wayland
environment. The original package IDs and artwork are preserved. This is not a
replacement desktop layout or an application style engine.

## Components

| Component | Light / palette-following | Fixed dark |
| --- | --- | --- |
| Global theme | `com.github.varlesh.rounded` | `com.github.varlesh.rounded-dark` |
| Plasma style | `ROUNDED-COLOR` | `ROUNDED-DARK` |
| Color scheme | `ROUNDED` | `ROUNDEDDARK` |
| Window decoration (global theme default) | Breeze | Aurorae `ROUNDED-DARK` |
| Aurorae decorations shipped | `ROUNDED` (manual choice) | `ROUNDED-DARK` |

Applications use Breeze, application icons use Breeze/Breeze Dark, and
cursors use `breeze_cursors`. Each Plasma style ships its own 101
monochrome panel and system-tray icons (`icons/`), described in
[docs/DESIGN.md](docs/DESIGN.md). COLOR follows the selected system palette. DARK deliberately
ships its own `colors` and does not follow external palette changes.
Aurorae colours are fixed in SVG, so the COLOR global theme selects the Breeze
decoration, which follows the palette; with a light palette you may pick the
light Aurorae `ROUNDED` manually. Pairing Aurorae `ROUNDED` with a dark palette
gives light titlebars over dark windows.
Konsole and Yakuake resources are optional. SDDM and `ROUNDED.layout.latte` are
legacy resources: neither is installed or covered by Plasma 6.8 compatibility.
Plasma Login Manager, lockscreen/OSD, wallpapers and application configuration
are not customized by the installer.

## Requirements

Plasma Workspace/Desktop, KWin, Aurorae, Breeze application style, Breeze icons
and Breeze cursors must be installed. Python 3 and a POSIX shell are required
for installation and static validation; `qmllint`, `kpackagetool6` and
`ksplashqml` enable additional checks. No build system or network downloads are
needed.

The checked local versions on 2026-10-17 were Plasma/KWin/libplasma/Aurorae
6.8.0, Qt Base 6.12.0 and KSvg 6.31.0. Plasma 5, other Plasma 6 versions and X11
have not been validated.

## Installation

Run commands from the repository root. Installation targets only
`${XDG_DATA_HOME:-$HOME/.local/share}` and never uses sudo.

```sh
sh scripts/check-theme.sh
sh scripts/install.sh install --dry-run
sh scripts/install.sh install
# Optional application resources, without selecting them in application settings:
sh scripts/install.sh install --update --with-konsole --with-yakuake
```

A base-theme update without optional flags preserves already installed
Konsole/Yakuake resources; pass their flags to update those components too.

Existing destinations are not silently overwritten. Use explicit `--update`
to replace them with backups. The installer stages the complete selected set,
records checksums and rolls back replacements on ordinary errors. Replacement
across multiple directories is not one atomic filesystem transaction. Keep
backups until the new installation has been checked. Forced termination or
power loss is not covered by the ordinary-error rollback; retain the installer
state and backups for recovery.

```sh
sh scripts/install.sh uninstall --dry-run
sh scripts/install.sh uninstall
sh scripts/install.sh restore --dry-run
sh scripts/install.sh restore
sh scripts/install.sh --help
```

Uninstall preserves modified and unowned files. Restoring an earlier resource
backup is a separate explicit action, not an automatic side effect of removal;
`restore` reverts the latest saved operation. To recover a pre-update resource
after uninstall, first restore the uninstall, then restore the update. Files
modified since the operation must not be overwritten. Backups and
ownership/checksums are stored in
`$XDG_DATA_HOME/.rounded-theme-installer` (under the default data directory when
the variable is unset or empty). The installer does not write
to `~/.config`, apply a theme, restart processes or clear caches.
Restore refuses the entire operation if a target has changed, retaining the
backup rather than performing a partial rollback. Mutating commands serialize
access with a filesystem lock. Uninstall can leave empty resource directories;
it deliberately keeps recovery records and backups.

## Quick Application

After `install`, open System Settings and choose, without replacing the
desktop layout:

1. Colors & Themes → Global Theme → ROUNDED or ROUNDED-DARK, with only the
   appearance checkboxes enabled (leave "Desktop and window layout" off);
2. or set the parts individually: Plasma Style (`ROUNDED-COLOR` or
   `ROUNDED-DARK`), Colors (`ROUNDED` or `ROUNDEDDARK`) and Window
   Decorations (Breeze for COLOR, `ROUNDED-DARK` for DARK).

The section below describes the cautious path with configuration backups.

## Manual Application

Before applying, back up existing `kdeglobals`, `kwinrc`, `plasmarc`,
`kcminputrc`, `ksplashrc`, `kdedefaults` and
`plasma-org.kde.plasma.desktop-appletsrc` from the configuration directory.
Record missing files as missing rather than creating them.

In System Settings, inspect the Global Theme, Plasma Style and Window
Decorations entries. Apply only appearance components; **do not select desktop
layout replacement**. There are no layout scripts in these packages. The
existing two-monitor/four-panel arrangement must remain unchanged. Logging out
or testing a real login is a separate manual operation.

For rollback, first select Breeze in appearance settings, then explicitly
restore the resource backup. Restore configuration files selectively outside
the running session or with the relevant processes stopped, so KDE cannot
overwrite the restored settings. Do not restart or reconfigure the display
manager. A temporary `XDG_DATA_HOME` alone does not isolate a GUI test from the
current configuration and D-Bus session.

## Validation

```sh
sh scripts/check-theme.sh
sh scripts/check-theme.sh --runtime
python3 scripts/test-install.py
```

The checker validates 290 Plasma/Aurorae SVG files, duplicate IDs and SVG
references, metadata, local defaults targets, panel frames and margin hints,
matching COLOR/DARK panel geometry, Aurorae restore states and header color
roles, plus definitions for used COLOR palette classes. It also guards the
usability fixes described in [Usability and Guidelines](#usability-and-guidelines). It runs `qmllint`
when available. `--runtime` additionally parses both
global and desktop-theme packages with the installed KPackage tool and runs
both splashes in the offscreen KSplash host, without applying the theme.
These checks passed on the versions above. Offscreen tests are not visual
acceptance tests. The installer regression suite also passes 18 isolated tests,
including collision backups, legacy metadata cleanup, ownership preservation,
rollback, restore validation, concurrent invocation locking, optional payloads,
dry-run and paths with spaces.
An isolated installation followed by KPackage listing discovers both global
and both desktop-theme IDs. Desktop packages explicitly declare
`KPackageStructure: Plasma/Theme`: without it, this installed package lister
did not discover them, despite successful parsing by path.

The migration corrects `thick-hint-right-margin` in all six panel variants,
retains original contrast/adaptive transparency values in `plasmarc`, adds
distinct Aurorae restore artwork, and preserves the working Aurorae desktop
metadata. The Aurorae SVG loader uses the legacy metadata path; successful
KPackage parsing is not used as an Aurorae rendering guarantee.

### Usability and Guidelines

Design decisions follow the KDE HIG
([Accessibility](https://develop.kde.org/hig/accessibility/),
[Communicating status changes](https://develop.kde.org/hig/status_changes/),
[Simple by default](https://develop.kde.org/hig/simple_by_default/)) and the
GNOME HIG ([UI styling](https://developer.gnome.org/hig/guidelines/ui-styling.html),
[Buttons](https://developer.gnome.org/hig/patterns/controls/buttons.html),
[Pointer and touch](https://developer.gnome.org/hig/guidelines/pointer-touch.html))
as principles. Neither HIG gives numeric contrast limits; WCAG 2.x AA
(4.5:1 for text, 3:1 for focus indicators) is this project's own measurable
criterion.

| Decision | Basis | Checked automatically |
| --- | --- | --- |
| Inactive Aurorae frames use a separate tone; title text ≥ 4.5:1 | Focus must be visibly distinct | Yes |
| 2px side/bottom Aurorae borders; 24px titlebar buttons | Targets large enough for different devices and abilities | Border width only |
| Close button is monochrome at rest, red only on hover/press | Red marks errors and dangerous actions; avoid competing colour | Yes |
| Minimized tasks: 1px outline (≥ 3:1 on a solid panel) instead of the normal fill; normal 0.14 < hover/focus 0.22 | Do not rely on colour alone; use shape; keep hierarchy | Yes |
| Accent focus ring on buttons, text fields and radio buttons | Everything keyboard-usable with visible focus | Yes |
| Colour-scheme text roles ≥ 4.5:1, DecorationFocus ≥ 3:1 | Readability, WCAG criterion | Yes |
| COLOR global theme uses Breeze decoration | Colours follow the user's scheme | Yes |
| Aurorae `Animation=0` kept | No evidence Aurorae honours the global animation setting | No |

Manual checks still required: keyboard-only navigation, system font size 14,
globally disabled animations, title text clipping, and translucent panels on
busy wallpapers with `ContrastEffect` disabled.

### Design Identity

The visual language (radius scale, colour roles, state ladder, window
decoration glyphs) and a pre-commit checklist for keeping the style are in
[docs/DESIGN.md](docs/DESIGN.md).

### Deliberate Fallbacks

The non-invasive resource inventory established these consumer contracts:

| Consumer | Requested resource / states | Migration decision |
| --- | --- | --- |
| Installed panel QML | `widgets/panel-background`, `solid/widgets/panel-background`; frame/mask, `thick-hint-*`, floating fallback | Correct right hint in root/opaque/solid; preserve geometry |
| Folder containment | `widgets/action-overlays`; add/remove/open, normal/hover/pressed | Use installed default fallback pending visual evidence |
| Aurorae maximize button | `restoreButtonPath`, falling back to maximize when empty | Add distinct restore with existing five button states |
| KSplash host | `contents/splash/Splash.qml`, `stage` property | Preserve animation and stage contract; unversioned QtQuick |

The installed default Plasma style supplies resources absent from ROUNDED:
`calendar`, `margins-highlight`, `action-overlays`,
`actionbutton`, `media-delegate`, `frame`, `toolbar`,
`translucentbackground`, `dragger` and `monitor`. ROUNDED ships its own
`radiobutton`. `plasmoidheading` is absent on purpose: `PlasmoidHeading.qml`
draws it only from the same image set as `dialogs/background`, so headings
stay flat instead of mixing in the default style. No Breeze artwork has been
bulk-copied. Auxiliary resources such as `analog_meter`, `branding`, `picker`,
`plot-background`, `timer` and `weather/wind-arrows` remain on the standard
fallback path, not individually visually verified. The installed folder
containment requests `widgets/toolbox`, but no matching installed style SVG was
found; no speculative replacement is supplied. Weather/IME/camera and other
icon names without a confirmed desktop-theme consumer remain untouched and
can use the icon theme. Root panel resources serve translucent panels; there
is no unnecessary `translucent/` copy.

### Not Yet Visually Verified

No theme was applied to the active session and no before/after screenshots
were captured. KCM discovery without duplicate cards, live Aurorae rendering,
active/inactive/hover/pressed/disabled states, floating/attached panels at all
four edges, maximization transitions, blur, popup clipping and widget visual
consistency still require an isolated test session. Also unverified are
100/125/150/200% scaling, mixed-scale dual monitors, preservation of the four
existing panels, COLOR under light/dark/accent palettes, fixed DARK under
external palette changes, and live-session journal regressions. Help/shade
buttons were not added without a confirmed supported action requirement.

Consequently, the repository is migrated and passes the listed automated
checks, but full visual compatibility is not yet certified. Do not interpret
fallback availability or offscreen smoke tests as completion of that matrix.
