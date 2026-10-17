# Статус и спецификация темизации KDE Plasma 6.8 (kde-rounded-theme)

Дата ревизии: 2026-10-17
Целевое окружение: Arch Linux, KDE Plasma 6.8.0 (Wayland), Qt 6.12, KF6 (`libplasma` 6.8.0, `ksvg` 6.8.0, `libklookandfeel` 6.8.0, `union` 6.8.0, `aurorae` 6.8.0, `plasma-login-manager` 6.8.0).

---

## Часть 1. Архитектура стилизации KDE Plasma 6.8 (Полный справочник)

### 1.1. Глобальная тема (`Plasma/LookAndFeel` — `libklookandfeel`)
Пути: `/usr/share/plasma/look-and-feel/`, `~/.local/share/plasma/look-and-feel/`
Метаданные: `metadata.json` (`KPackageStructure: "Plasma/LookAndFeel"`).

- **Флаги `AppearanceSettings` (`contents/defaults`):**
  - `Colors`: `[kdeglobals][General] ColorScheme` (или вложенный файл `contents/colors`)
  - `WidgetStyle`: `[kdeglobals][KDE] widgetStyle`
  - `WindowDecoration`: `[kwinrc][org.kde.kdecoration2] library`, `theme`, `NoPlugin`
  - `BorderSize`: `[kwinrc][org.kde.kdecoration2] BorderSize`, `BorderlessMaximizedWindows`
  - `Icons`: `[kdeglobals][Icons] Theme`
  - `PlasmaTheme`: `[plasmarc][Theme] name`
  - `Cursors`: `[kcminputrc][Mouse] cursorTheme`
  - `Fonts`: `[kdeglobals][General]` (`font`, `fixed`, `smallestReadableFont`, `toolBarFont`, `menuFont`) и `[kdeglobals][WM]` (`activeFont`)
  - `WindowSwitcher`: `[kwinrc][TabBox] LayoutName`
  - `DesktopSwitcher`: `[kwinrc][TabBox] DesktopLayout`
  - `SplashScreen`: `[ksplashrc][KSplash] Theme`, `Engine`
  - `Wallpaper`: `[Wallpaper] Image`
- **Флаги `LayoutSettings`:**
  - `DesktopLayout`: `contents/layouts/org.kde.plasma.desktop-layout.js`, `contents/layouts/defaults`, `contents/plasmoidsetupscripts/*.js`
  - `TitlebarLayout`: `[kwinrc][org.kde.kdecoration2] ButtonsOnLeft`, `ButtonsOnRight`
  - `WindowPlacement`: `[kwinrc][Windows] Placement`
- **Встраиваемые QML/ресурсы (`contents/`):**
  - `splash/Splash.qml`, `logout/Logout.qml`, `windowswitcher/WindowSwitcher.qml`
  - `previews/` (`preview.png`, `fullscreenpreview.jpg`, `lockscreen.png`, `splash.png`, `windowswitcher.png`)
  - *Изменения 6.8:* Удалены интеграции `ShellPackage`, `VirtualKeyboardLoader` и Latte Dock. Экран блокировки и OSD обслуживаются пакетом оболочки `/usr/share/plasma/shells/org.kde.plasma.desktop/contents/{lockscreen,osd,logout,applet,configuration,explorer,activitymanager}`.

### 1.2. Оформление рабочего стола (`Plasma/Theme` — `libplasma` и `KSvg`)
Пути: `/usr/share/plasma/desktoptheme/`, `~/.local/share/plasma/desktoptheme/`
Метаданные и конфиг: `metadata.json` (`KPackageStructure: "Plasma/Theme"`), `plasmarc`, `colors` (опционально; без `colors` тема получает статус `FollowsColorTheme`).

- **Конфигурация в `plasmarc`:**
  - `[ContrastEffect]`: `enabled`, `contrast`, `intensity`, `saturation`
  - `[BlurBehindEffect]`: `enabled`
  - `[AdaptiveTransparency]`: `enabled`
  - `[Wallpaper]`: `defaultWallpaperTheme`, `defaultFileSuffix`, `defaultWidth`, `defaultHeight`
- **Селекторы рендеринга (подпапки):** корень (по умолчанию), `translucent/`, `opaque/`, `solid/`.
- **Диалоги (`dialogs/`):** `background.svgz`, опционально `krunner.svgz`, `shutdowndialog.svgz`.
- **Виджеты (`widgets/` — 43 стандартных SVG в `default`):**
  `actionbutton`, `action-overlays`, `analog_meter`, `arrows`, `background`, `bar_meter_horizontal`, `bar_meter_vertical`, `branding`, `busywidget`, `button`, `calendar`, `checkmarks`, `clock`, `configuration-icons`, `containment-controls`, `dragger`, `frame`, `glowbar`, `line`, `lineedit`, `listitem`, `margins-highlight`, `media-delegate`, `menubaritem`, `monitor`, `notes`, `pager`, `panel-background` (префиксы `north/south/east/west`, `floating`, `mask`, `shadow`, `thick`, `hint-*-inset/margin`), `picker`, `plasmoidheading`, `plot-background`, `radiobutton`, `scrollbar`, `scrollwidget`, `slider`, `switch`, `tabbar`, `tasks`, `timer`, `toolbar`, `toolbox`, `tooltip`, `translucentbackground`, `viewitem`, плюс `extender-background` и `weather/wind-arrows`.
- **Системные иконки трея (`icons/` — 58 стандартных SVG в `default`):**
  `akonadi`, `akregator`, `amarok`, `applications`, `apport`, `audio`, `battery`, `bookmarks`, `cantata`, `computer`, `configure`, `device`, `disk`, `distribute`, `document`, `drive`, `edit`, `fcitx`, `go`, `ime`, `input`, `kalarm`, `kdeconnect`, `keyboard`, `kget`, `kgpg`, `kleopatra`, `klipper`, `kmail`, `konv_message`, `konversation`, `kopete`, `korgac`, `kpackagekit`, `kruler`, `kteatime`, `ktorrent`, `kup`, `list`, `mail`, `media`, `mobile`, `network`, `notification`, `osd`, `phone`, `plasmavault`, `plasmavault_error`, `preferences`, `printer`, `quassel`, `search`, `slc`, `software`, `start`, `system`, `touchpad`, `user`, `video`, `video-card`, `view`, `vlc`, `wallet`, `window`, `yakuake`, `zoom`.
- **CSS-классы динамической окраски SVG (`KSvg::Svg::StyleSheetColor`):**
  - Базовые: `ColorScheme-Text`, `Background`, `Highlight`, `HighlightedText`, `PositiveText`, `NeutralText`, `NegativeText`, `Frame`.
  - Наборы (`Button*`, `View*`, `Tooltip*`, `Complementary*`, `Header*`): `*Text`, `*Background`, `*Hover`, `*Focus`, `*HighlightedText`, `*PositiveText`, `*NeutralText`, `*NegativeText`.

### 1.3. Цветовые схемы (`*.colors`)
Пути: `/usr/share/color-schemes/`, `~/.local/share/color-schemes/`
- **Наборы (`ColorSet`):** `[Colors:View]`, `[Colors:Window]`, `[Colors:Button]`, `[Colors:Selection]`, `[Colors:Tooltip]`, `[Colors:Complementary]`, `[Colors:Header]`, `[Colors:Header][Inactive]`.
- **Роли в каждом наборе:** `BackgroundNormal`, `BackgroundAlternate`, `ForegroundNormal`, `ForegroundInactive`, `ForegroundActive`, `ForegroundLink`, `ForegroundVisited`, `ForegroundNegative`, `ForegroundNeutral`, `ForegroundPositive`, `DecorationFocus`, `DecorationHover`.
- **Прочие секции:** `[WM]` (`activeBackground`, `activeForeground`, `activeBlend`, `inactiveBackground`, `inactiveForeground`, `inactiveBlend`), `[ColorEffects:Disabled]`, `[ColorEffects:Inactive]`, `[KDE]` (`contrast`, `frameContrast`), `[General]` (`ColorScheme`, `Name`, `AccentColor`, `TintFactor`, `TitlebarIsAccentColored` / `accentActiveTitlebar`, `shadeSortColumn`).

### 1.4. Стиль приложений (Application Style: KStyle, QQC2 и движок Union)
- **Классический стек:** `QStyle` плагины (`/usr/lib/qt6/plugins/styles/`, `/usr/share/kstyle/themes/*.themerc`), `qqc2-desktop-style`, синхронизация GTK3/GTK4 через `kde-gtk-config`.
- **Движок Union (новый в Plasma 6.8):** единый CSS-движок для QtWidgets (`UnionWidgetsStyle.so`), QtQuick Controls 2 (`/usr/lib/qt6/qml/org/kde/union/`, 50 контролов) и Kirigami (`org.kde.union`, 8 компонентов).
  - Пути тем: `/usr/share/union/styles/<name>/contents/{css,images}/`.
  - Файлы CSS: `variables.css`, `defaults.css`, `global.css`, `style.css`, `overrides.css`, `application.css`, `bars.css`, `button.css`, `calendar.css`, `check.css`, `delegate.css`, `kirigami.css`, `popup.css`, `tables.css`, `tabs.css`, `text.css`, `widgets.css`.

### 1.5. KWin, Курсоры, Иконки, Звуки, Экран входа, Мониторинг, Обои
- **Декорации окон (`KDecoration3` и `KWin/Aurorae`):**
  - Пути Aurorae: `/usr/share/aurorae/themes/`, `~/.local/share/aurorae/themes/`.
  - Элементы Aurorae: `decoration.svg`, кнопки (`close`, `minimize`, `maximize`, `restore`, `alldesktops`, `keepabove`, `keepbelow`, `shade`, `help`), конфиг `<theme>rc`, метаданные `metadata.json` (`KPackageStructure: "aurorae"`).
- **Переключатели и эффекты KWin:** `KWin/WindowSwitcher` (`tabbox`), `KWin/Effect`, `KWin/Script`.
- **Иконки и курсоры:** `/usr/share/icons/`, `~/.local/share/icons/` (включая `cursors_scalable/` для SVG-курсоров Wayland).
- **Системные звуки:** `/usr/share/sounds/`, `~/.local/share/sounds/`.
- **Экран входа:**
  - `plasmalogin` (Plasma Login Manager 6.8) — активен в системе, использует Wayland/KWin и синхронизирует тему Plasma, цветовую схему, курсоры, шрифты и плагины обоев напрямую из системных настроек.
  - `SDDM` (`/usr/share/sddm/themes/`) — устаревший альтернативный DM (в системе отключён).
- **Системный монитор:** `KSysguard/SensorFace` (`/usr/share/ksysguard/sensorfaces/`).
- **Обои:** `Wallpaper/Images` (с поддержкой `images/` и `images_dark/` для автопереключения день/ночь) и QML-плагины `Plasma/Wallpaper`.

---

## Часть 2. Состояние репозитория `kde-rounded-theme` и совместимость с Plasma 6.8

База репозитория: коммит `157d821` от 19.09.2022 (Plasma 5.25 / Qt 5).

### 2.1. Сломанные и несовместимые компоненты
1. **Глобальная тема (`plasma/look-and-feel/com.github.varlesh.rounded` и `rounded-dark`):**
   - Использует удалённый в KF6 формат `metadata.desktop` (отсутствует `metadata.json`). `kpackagetool6 --type Plasma/LookAndFeel` и KCM «Оформление рабочей среды» пакет не видят.
   - `contents/splash/Splash.qml` использует импорты Qt5 (`import QtQuick 2.5`, `import QtQuick.Window 2.2`).
2. **Тема SDDM (`sddm/themes/ROUNDED-DARK`):**
   - В системе вместо SDDM работает `plasmalogin.service` (Plasma Login Manager), который не использует темы SDDM.
   - Код `Main.qml`, `RebootToolTip.qml`, `ShutdownToolTip.qml` импортирует удалённый в Qt6 модуль `QtGraphicalEffects 1.0` и `QtQuick.VirtualKeyboard 2.1` (не запустится в SDDM на Qt6 без портирования на `Qt5Compat.GraphicalEffects` / `MultiEffect`).
3. **Макет Latte Dock (`ROUNDED.layout.latte`):**
   - Полностью неактуален (Latte Dock не установлен и удалён из поддержки `libklookandfeel` в Plasma 6.8).

### 2.2. Частично работающие компоненты (требуют доработки)
1. **Plasma Style (`plasma/desktoptheme/ROUNDED-COLOR` и `ROUNDED-DARK`):**
   - Загружается через легаси-фоллбэк `libPlasma`, но требует замены `metadata.desktop` на `metadata.json`.
   - Секции `[ContrastEffect]` и `[AdaptiveTransparency]` записаны в `metadata.desktop` — в Plasma 6 они должны находиться в отдельном файле `plasmarc` (сейчас игнорируются).
   - В `panel-background.svg` отсутствуют элементы плавающей панели Plasma 6 (`floating-*`, `hint-*-inset`).
   - В `ROUNDED-COLOR` 131 SVG-файл размечен классами `ColorScheme-*` (поддерживает системную схему и акцентные цвета). В `ROUNDED-DARK` — 0 классов `ColorScheme-*`, цвета жёстко зашиты в SVG и файле `colors`.
2. **Декорации Aurorae (`aurorae/themes/ROUNDED` и `ROUNDED-DARK`):**
   - Загружаются плагином `org.kde.kwin.aurorae.so` через `metadata.desktop`, но для совместимости с `kpackagetool6` нужен `metadata.json`.
3. **Цветовые схемы (`color-schemes/ROUNDED.colors`, `ROUNDEDDARK.colors`):**
   - Работают, но не содержат секций `[Colors:Header]` и `[Colors:Header][Inactive]` для единых шапок окон KDE.
4. **Терминалы (`yakuake/skins/ROUNDED*`, `konsole/ROUNDED.colorscheme`):**
   - Полностью совместимы с текущими Yakuake 26.08.2 и Konsole 26.08.2.

---

## Часть 3. Покрытие компонентов текущей пользовательской системы

Сверка с активной конфигурацией рабочего стола (`~/.config/plasma-org.kde.plasma.desktop-appletsrc` и установленными пакетами):
- Экраны: 2 монитора (2560x1440 и 1920x1080), контейнер `org.kde.plasma.folder`.
- Панели: 4 панели `org.kde.panel` (2 верхние с треем, часами, погодой, разделителями; 2 нижние с `kickoff` и `icontasks`).

### 3.1. Что стилизовано в теме (в наличии)
- **Фоны (`dialogs/`, `widgets/`, `opaque/`, `solid/`):** `dialogs/background`, `widgets/panel-background`, `widgets/background`, `widgets/tooltip`.
- **Базовые виджеты Plasma (`widgets/` — 24 файла):** `arrows`, `background`, `bar_meter_horizontal`, `bar_meter_vertical`, `busywidget`, `button`, `checkmarks`, `clock`, `configuration-icons`, `containment-controls`, `glowbar`, `line`, `lineedit`, `listitem`, `menubaritem`, `notes`, `pager`, `panel-background`, `scrollbar`, `scrollwidget`, `slider`, `switch`, `tabbar`, `tasks`, `tooltip`, `viewitem`.
- **Иконки трея (`icons/` — 96 файлов), совпадающие с активными апплетами системы:**
  `start` (Kickoff), `audio` (volume), `network` (networkmanagement), `battery`, `klipper` (clipboard), `kdeconnect`, `plasmavault` / `plasmavault_error` (vault), `printer` (printmanager), `keyboard` и `input` (keyboardlayout / keyboardindicator), `device` и `disk` (devicenotifier), `media` (mediacontroller), `notification` и `osd`, `preferences`, `system`, `configure`, `kup` (kupapplet), `yakuake`.
  *(Также в теме есть 43 иконки сторонних/старых приложений, не используемых в трее: `antimicro`, `audacious`, `cadence`, `choqok`, `corectrl`, `elisa`, `jami`, `juk`, `kaffeine`, `krfb`, `krusader_*`, `lutris`, `manjaro`, `mellowplayer`, `nepomuk`, `nulloy`, `onboard`, `qbittorrent`, `sirikali`, `strawberry`, `TeamViewer`, `thunderbird`, `veracrypt` и др.)*
- **Оконные декорации Aurorae:** `decoration.svg`, `close.svg`, `maximize.svg`, `minimize.svg`, `alldesktops.svg`, `keepabove.svg`, `keepbelow.svg`.
- **Прочее:** цветовые схемы (`ROUNDED.colors`, `ROUNDEDDARK.colors`), скины Yakuake, палитра Konsole.

### 3.2. Чего не хватает в теме (берётся из дефолтного Breeze или отсутствует)
1. **Недостающие виджеты `desktoptheme/widgets/` (19 стандартных компонентов):**
   - Высокий приоритет (активно задействованы на рабочем столе):
     - `plasmoidheading.svg` — шапки и подвалы всех всплывающих окон (Kickoff, трей, часы, звук, сеть, уведомления).
     - `calendar.svg` — сетка календаря (используется в `digitalclock` на обоих мониторах).
     - `margins-highlight.svg` — индикация для используемых на верхних панелях `org.kde.plasma.marginsseparator`.
     - `action-overlays.svg` — оверлеи выделения/открытия значков на рабочем столе (`org.kde.plasma.folder`).
     - `actionbutton.svg` и `media-delegate.svg` — кнопки и обложки в `org.kde.plasma.mediacontroller` и на экране блокировки.
     - `radiobutton.svg`, `frame.svg`, `toolbar.svg`, `toolbox.svg`, `translucentbackground.svg`, `dragger.svg`.
     - `monitor.svg` — используется апплетом `org.kde.kscreen` в трее.
   - Низкий приоритет (вспомогательные): `analog_meter.svg`, `branding.svg`, `picker.svg`, `plot-background.svg`, `timer.svg`, `weather/wind-arrows.svg`.
   - Подкаталог `translucent/` (для KWin Blur).
2. **Недостающие иконки трея `desktoptheme/icons/`:**
   - Из стандартного набора Plasma 6.8 (6 шт.): `ime` (активен апплет `org.kde.plasma.manage-inputmethod`), `mobile`, `search`, `software`, `video-card`, `kpackagekit`.
   - Под активные апплеты в трее пользователя: `org.kde.plasma.brightness` (яркость), `org.kde.plasma.cameraindicator` (индикатор камеры), `org.kde.plasma.dwellclicker`, `org.kde.plasma.kclock_1x2`, `org.kde.plasma.advanced-weather-widget`.
3. **Недостающие кнопки декораций окон `aurorae/themes/ROUNDED*`:**
   - `restore.svg` (кнопка восстановления распахнутого окна — критично при максимизации), `shade.svg`, `help.svg`.
4. **Недостающие внешние компоненты и зависимости:**
   - **Курсоры:** `contents/defaults` ссылается на `volantes_cursors` / `volantes_light_cursors`, которые отсутствуют и в репозитории, и в системе (в системе установлены `breeze_cursors`, `Eden`, `Tela`, `Adwaita`, `Oxygen`).
   - **Стиль приложений:** нет темы для нового движка `Union` (`/usr/share/union/styles/`) или `KStyle`/Kvantum; используется дефолтный `Breeze`.
   - **Терминал Kitty:** основной терминал пользователя (`kitty.desktop` на панели `icontasks`) не имеет цветовой схемы в репозитории.
   - **Обои и иконки:** нет каталога `wallpapers/` и собственной темы иконок.
   - **Экран входа:** нет конфигурации/обоев для активного `plasmalogin`.
