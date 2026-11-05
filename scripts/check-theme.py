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
    print(f'PASS: {len(svgs)} SVGs, metadata, defaults, panels, Aurorae and color roles')
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
