#!/usr/bin/env python3
"""Non-invasive checks for the shipped theme, with optional installed Qt tools."""
import argparse
import configparser
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent


def ini(path):
    result = configparser.ConfigParser(interpolation=None)
    result.optionxform = str
    result.read_string(path.read_text())
    return result


def frame_geometry(path, attributes):
    parts = {}

    def visit(element, owner=''):
        owner = element.get('id', owner)
        values = tuple(element.get(key, '') for key in attributes)
        if any(key in element.attrib for key in attributes):
            parts.setdefault(owner, []).append((element.tag, values))
        for child in element:
            visit(child, owner)

    visit(ET.parse(path).getroot())
    return parts


def rgb(value):
    value = value.strip()
    if value.startswith('#'):
        return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(int(part) for part in value.split(',')[:3])


def contrast(first, second):
    """WCAG 2.x contrast ratio of two sRGB colours."""
    def luminance(color):
        channels = [c / 255 for c in color]
        channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def element_fill(path, ident):
    element = ET.parse(path).getroot().find(f".//*[@id='{ident}']")
    match = re.search(r'fill:(#[0-9a-fA-F]{6})', element.get('style', ''))
    assert match, f'{path}: {ident} has no solid fill'
    return rgb(match.group(1))


def subtree_text(path, ident):
    element = ET.parse(path).getroot().find(f".//*[@id='{ident}']")
    assert element is not None, f'{path}: missing {ident}'
    return ET.tostring(element, encoding='unicode')


def check_usability(theme, decoration, scheme):
    """Guard the accessibility fixes: contrast, focus and state distinctness."""
    aurorae = ROOT / 'aurorae/themes' / decoration
    rc = ini(aurorae / (decoration + 'rc'))
    svg = aurorae / 'decoration.svg'
    active, inactive = element_fill(svg, 'decoration-center'), element_fill(svg, 'decoration-inactive-center')
    assert active != inactive, f'{svg}: active and inactive frames are identical'
    for key, background in (('ActiveTextColor', active), ('InactiveTextColor', inactive)):
        ratio = contrast(rgb(rc['General'][key]), background)
        assert ratio >= 4.5, f'{decoration}: {key} contrast {ratio:.2f} < 4.5'
    for edge in ('Left', 'Right', 'Bottom'):
        assert int(rc['Layout']['Border' + edge]) >= 2, f'{decoration}: Border{edge} < 2'
    close = aurorae / 'close.svg'
    for state, red in (('active', False), ('inactive', False), ('deactivated', False),
                       ('hover', True), ('pressed', True)):
        text = subtree_text(close, state + '-center').lower()
        assert (('#da4453' in text) or ('#b52f3c' in text)) == red, f'{close}: {state} red={not red}'
    tasks = theme / 'widgets/tasks.svg'
    for prefix in ('', 'north-', 'east-', 'west-'):
        normal = re.sub(r'id="[^"]*"', '', subtree_text(tasks, prefix + 'normal-top'))
        minimized = re.sub(r'id="[^"]*"', '', subtree_text(tasks, prefix + 'minimized-top'))
        assert re.sub(r'y="[^"]*"', '', normal) != re.sub(r'y="[^"]*"', '', minimized), \
            f'{tasks}: {prefix}normal and minimized look identical'
    # Effective opacity of the task overlay (fill-opacity times group opacity),
    # blended over the scheme's window colour on a solid panel.
    def overlay(ident):
        text = subtree_text(tasks, ident)
        fill = float(re.search(r'fill-opacity:([0-9.]+)', text).group(1))
        group = re.match(r'<[^>]*style="opacity:([0-9.]+)', text)
        return fill * (float(group.group(1)) if group else 1)
    window = ini(ROOT / 'color-schemes' / (scheme + '.colors'))['Colors:Window']
    ink, panel = rgb(window['ForegroundNormal']), rgb(window['BackgroundNormal'])
    for prefix in ('', 'north-', 'east-', 'west-'):
        normal, hover = overlay(prefix + 'normal-center'), overlay(prefix + 'hover-top')
        assert normal < hover, f'{tasks}: {prefix}hover ({hover}) must exceed normal ({normal})'
        alpha = overlay(prefix + 'minimized-top')
        blended = tuple(round(p * (1 - alpha) + i * alpha) for p, i in zip(panel, ink))
        ratio = contrast(blended, panel)
        assert ratio >= 3, f'{tasks}: {prefix}minimized outline contrast {ratio:.2f} < 3'
    ids = {e.get('id') for e in ET.parse(theme / 'widgets/lineedit.svg').iter()}
    for prefix in ('hover', 'focus'):
        for part in ('center', 'top', 'bottom', 'left', 'right',
                     'topleft', 'topright', 'bottomleft', 'bottomright'):
            assert f'{prefix}-{part}' in ids, f'{theme}: lineedit {prefix}-{part}'
    button = theme / 'widgets/button.svg'
    assert subtree_text(button, 'focus-top') != subtree_text(button, 'hover-top').replace('hover', 'focus')
    assert 'url(' not in subtree_text(button, 'focus-top'), f'{button}: focus is a shadow, not a ring'
    ids = {e.get('id') for e in ET.parse(theme / 'widgets/radiobutton.svg').iter()}
    for element in ('normal', 'checked', 'hover', 'focus', 'symbol', 'shadow', 'hint-size'):
        assert element in ids, f'{theme}: radiobutton {element}'
    colors = ini(ROOT / 'color-schemes' / (scheme + '.colors'))
    for group in ('Colors:Window', 'Colors:View', 'Colors:Tooltip', 'Colors:Header',
                  'Colors:Header][Inactive', 'Colors:Complementary', 'Colors:Button'):
        background = rgb(colors[group]['BackgroundNormal'])
        for role in ('ForegroundNormal', 'ForegroundInactive', 'ForegroundLink', 'ForegroundVisited',
                     'ForegroundActive', 'ForegroundNegative', 'ForegroundNeutral', 'ForegroundPositive'):
            ratio = contrast(rgb(colors[group][role]), background)
            assert ratio >= 4.5, f'{scheme}: {group} {role} contrast {ratio:.2f} < 4.5'
        ratio = contrast(rgb(colors[group]['DecorationFocus']), background)
        assert ratio >= 3, f'{scheme}: {group} DecorationFocus contrast {ratio:.2f} < 3'
    wm = colors['WM']
    for state in ('active', 'inactive'):
        ratio = contrast(rgb(wm[state + 'Foreground']), rgb(wm[state + 'Background']))
        assert ratio >= 4.5, f'{scheme}: WM {state} title contrast {ratio:.2f} < 4.5'


def check(runtime=False):
    svgs = list(ROOT.glob('plasma/**/*.svg')) + list(ROOT.glob('aurorae/**/*.svg'))
    for path in svgs:
        tree = ET.parse(path)
        ids = [e.attrib['id'] for e in tree.iter() if 'id' in e.attrib]
        assert len(ids) == len(set(ids)), f'Duplicate SVG IDs: {path}'
        if 'ROUNDED-COLOR' in path.parts:
            classes = {name for element in tree.iter()
                       for name in element.get('class', '').split()
                       if name.startswith('ColorScheme-')}
            if classes:
                styles = '\n'.join(element.text or '' for element in tree.iter()
                                   if element.get('id') == 'current-color-scheme')
                for name in classes:
                    assert re.search(r'\.' + re.escape(name) + r'\s*\{', styles), \
                        f'Missing dynamic color definition: {path}: {name}'
        for element in tree.iter():
            for key, value in element.attrib.items():
                if key in ('href', '{http://www.w3.org/1999/xlink}href') and value:
                    if value.startswith('#'):
                        assert value[1:] in ids, f'Broken SVG reference: {path}: {value}'
                    elif not value.startswith('data:'):
                        assert (path.parent / value).is_file(), f'External SVG resource: {path}: {value}'
    for suffix, desktop, scheme, decoration in (
        ('', 'ROUNDED-COLOR', 'ROUNDED', 'ROUNDED'),
        ('-dark', 'ROUNDED-DARK', 'ROUNDEDDARK', 'ROUNDED-DARK'),
    ):
        name = 'com.github.varlesh.rounded' + suffix
        package = ROOT / 'plasma/look-and-feel' / name
        theme = ROOT / 'plasma/desktoptheme' / desktop
        metadata = json.loads((package / 'metadata.json').read_text())
        assert metadata['KPlugin']['Id'] == name
        assert metadata['KPackageStructure'] == 'Plasma/LookAndFeel'
        assert not metadata.get('X-KPackage-Dependencies'), 'Unexpected network dependencies'
        metadata = json.loads((theme / 'metadata.json').read_text())
        assert metadata['KPlugin']['Id'] == desktop
        assert metadata['KPackageStructure'] == 'Plasma/Theme'
        assert metadata['X-Plasma-API'] == '5.0'
        assert not (theme / 'metadata.desktop').exists()
        assert not (package / 'metadata.desktop').exists()
        defaults = ini(package / 'contents/defaults')
        assert defaults['kdeglobals][General']['ColorScheme'] == scheme
        assert defaults['plasmarc][Theme']['name'] == desktop
        kdecoration = defaults['kwinrc][org.kde.kdecoration2']
        if suffix:
            assert kdecoration['library'] == 'org.kde.kwin.aurorae'
            assert kdecoration['theme'] == '__aurorae__svg__' + decoration
        else:
            # COLOR follows the user's palette; fixed-colour Aurorae cannot.
            assert kdecoration['library'] == 'org.kde.breeze'
            assert kdecoration['theme'] == 'Breeze'
        assert defaults['kcminputrc][Mouse']['cursorTheme'] == 'breeze_cursors'
        assert defaults['ksplashrc][KSplash']['Theme'] == name
        assert defaults['kdeglobals][KDE']['widgetStyle'] == 'Breeze'
        assert defaults['kdeglobals][Icons']['Theme'] == ('breeze-dark' if suffix else 'breeze')
        assert (package / 'contents/splash/images/logo.svg').is_file()
        effects = ini(theme / 'plasmarc')
        assert effects.has_section('ContrastEffect')
        assert effects.has_section('AdaptiveTransparency')
        for variant in ('', 'opaque', 'solid'):
            panel = theme / variant / 'widgets/panel-background.svg'
            ids = {e.get('id') for e in ET.parse(panel).iter()}
            for prefix in ('', 'mask-'):
                for part in ('center', 'top', 'bottom', 'left', 'right',
                             'topleft', 'topright', 'bottomleft', 'bottomright'):
                    assert prefix + part in ids, f'{panel}: {prefix}{part}'
            for edge in ('top', 'bottom', 'left', 'right'):
                assert f'thick-hint-{edge}-margin' in ids, str(panel)
        aurorae = ROOT / 'aurorae/themes' / decoration
        assert (aurorae / 'metadata.desktop').is_file()
        for button in ('maximize', 'restore'):
            ids = {e.get('id') for e in ET.parse(aurorae / (button + '.svg')).iter()}
            for state in ('active', 'inactive', 'hover', 'pressed', 'deactivated'):
                assert state + '-center' in ids, str(aurorae)
        check_usability(theme, decoration, scheme)
        colors = ini(ROOT / 'color-schemes' / (scheme + '.colors'))
        assert colors['General']['ColorScheme'] == scheme
        for section in ('Colors:Header', 'Colors:Header][Inactive'):
            assert set(colors['Colors:Window']) <= set(colors[section])
        if suffix:
            embedded = ini(theme / 'colors')
            for section in ('Colors:Header', 'Colors:Header][Inactive'):
                assert dict(embedded[section]) == dict(colors[section])
        qml = package / 'contents/splash/Splash.qml'
        tool = shutil.which('qmllint') or shutil.which('qmllint6')
        if tool:
            subprocess.run([tool, str(qml)], check=True)
        else:
            print('SKIP: qmllint is unavailable')
        if runtime:
            subprocess.run(['kpackagetool6', '--type', 'Plasma/LookAndFeel',
                            '--show', str(package)], check=True)
            subprocess.run(['kpackagetool6', '--type', 'Plasma/Theme',
                            '--show', str(theme)], check=True)
            subprocess.run(['ksplashqml', '--test', '--window', '--nofork', str(package)],
                           env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                           check=True, timeout=30)
    assert not (ROOT / 'plasma/desktoptheme/ROUNDED-COLOR/colors').exists()
    assert (ROOT / 'plasma/desktoptheme/ROUNDED-DARK/colors').is_file()
    geometry = ('d', 'x', 'y', 'width', 'height', 'rx', 'ry', 'transform',
                'cx', 'cy', 'r', 'points')
    for variant in ('', 'opaque', 'solid'):
        panels = []
        for name in ('ROUNDED-COLOR', 'ROUNDED-DARK'):
            path = ROOT / 'plasma/desktoptheme' / name / variant / 'widgets/panel-background.svg'
            panels.append(frame_geometry(path, geometry))
        assert panels[0] == panels[1], f'COLOR/DARK panel geometry differs: {variant}'
    print(f'PASS: {len(svgs)} SVGs, metadata, defaults, panels, Aurorae, color roles and usability guards')
    if runtime:
        print('PASS: installed KPackage parsers and offscreen KSplash host')
    print('NOT TESTED: KCM discovery, visual rendering and multi-monitor/scale matrix')


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--runtime', action='store_true',
                            help='also run installed KPackage parsers and offscreen KSplash')
        check(parser.parse_args().runtime)
    except (AssertionError, ValueError, KeyError, OSError, ET.ParseError, configparser.Error,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
