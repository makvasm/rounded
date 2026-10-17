# Статус миграции ROUNDED на KDE Plasma 6.8

Дата ревизии: 2026-10-17.

Документ описывает текущее рабочее дерево после реализации миграции, а не
только исходный коммит `157d821` (Plasma 5.25 / Qt 5).
Полная визуальная совместимость ещё не подтверждена.

## 1. Окружение и границы

Проверенное локальное окружение: Arch Linux, Wayland.

| Компонент | Проверенная версия |
| --- | --- |
| Plasma Workspace/Desktop, KWin, libplasma, Aurorae | 6.8.0 |
| Qt Base | 6.12.0 |
| KSvg | 6.31.0 |

KSvg имеет версию 6.31.0, а не 6.8.0. Версии подтверждались локальными
ресурсами/базой пакетов; `plasmashell --version` и `kwin_wayland --version`
сообщают 6.8.0. Поддержка Plasma 5, прочих версий Plasma 6 и X11 не проверена.

Ссылка `/etc/systemd/system/display-manager.service` указывает на
`plasmalogin.service`; это не является проверкой состояния процесса.
Менеджер входа и его настройки в ходе миграции не изменялись.

По исходной инвентаризации пользовательская раскладка включает два монитора
(2560x1440 и 1920x1080) и четыре панели. Тема к рабочей сессии не применялась,
раскладка не менялась; её сохранение после ручного применения ещё не проверено.

## 2. Состав и идентификаторы

| Компонент | Светлый / динамический вариант | Фиксированный тёмный вариант |
| --- | --- | --- |
| Глобальная тема | `com.github.varlesh.rounded` | `com.github.varlesh.rounded-dark` |
| Plasma Style | `ROUNDED-COLOR` | `ROUNDED-DARK` |
| Цветовая схема | `ROUNDED` (`ROUNDED.colors`) | `ROUNDEDDARK` (`ROUNDEDDARK.colors`) |
| Aurorae | `ROUNDED` | `ROUNDED-DARK` |

Все исходные ID и имена файлов схем сохранены. COLOR следует системной
палитре через классы `ColorScheme-*`. DARK сохраняет фиксированные SVG-цвета
и собственный `plasma/desktoptheme/ROUNDED-DARK/colors`.

Стиль приложений остаётся Breeze, иконки используют `breeze` / `breeze-dark`,
курсоры обоих вариантов используют `breeze_cursors`.

## 3. Выполненные изменения

### Метаданные и настройки

- В обоих глобальных пакетах `metadata.desktop` заменён на `metadata.json` с `KPackageStructure: Plasma/LookAndFeel`, авторством, лицензией и прежним ID.
- В обоих desktop-пакетах добавлен `metadata.json` с `KPackageStructure: Plasma/Theme`; заменённые `metadata.desktop` удалены.
- Явный `Plasma/Theme` оказался необходим установленному KPackage для обнаружения тем в списке: без него разбор по пути проходил, но список был пуст.
- `X-Plasma-API` desktop-тем оставлен `5.0` по установленному эталону. Версия Plasma сама по себе не требует API `6.0`.
- ContrastEffect и AdaptiveTransparency вынесены в `plasmarc` с исходными значениями: `enabled=false`, `contrast=0.2`, `intensity=0.4`, `saturation=1.7` для контраста; `enabled=true` для адаптивной прозрачности.
- Удалены устаревшие сетевые KNewStuff-зависимости; включённые ресурсы поставляются установщиком локально. Fallback глобальных тем Breeze/Breeze Dark сохранён.
- В defaults Volantes заменены на `breeze_cursors`; добавлен `[ksplashrc][KSplash] Theme` соответствующего пакета без назначения неподтверждённого Engine.
- Секция декораций остаётся `[kwinrc][org.kde.kdecoration2]`; ABI KDecoration не является основанием переименовывать группу настройки.

### Splash, панели, Aurorae и цвета

- В обоих splash используется `import QtQuick` без версии; неиспользуемый QtQuick.Window удалён. Логотип, палитра, анимация и свойство `stage` сохранены.
- В шести panel SVG (COLOR/DARK, корень/opaque/solid) исправлено имя `thick-right-margin` на `thick-hint-right-margin`. Геометрия и цвета не менялись.
- Геометрия соответствующих COLOR/DARK панелей совпадает по проверяемым SVG-атрибутам и ID частей.
- Отдельный `translucent/` не добавлялся: установленный Panel.qml использует корневой `widgets/panel-background` для прозрачных и `solid/widgets/panel-background` для непрозрачных панелей.
- Floating-префикс допускает fallback на обычную рамку. Уже существующие `shadow-hint-*-inset` не подменяют обычные inset-hints; отсутствие отдельного floating-набора не объявляется само по себе дефектом.
- В обе Aurorae добавлен различимый `restore.svg` с состояниями active, inactive, hover, pressed и deactivated. Ранее загрузчик мог использовать maximize при отсутствии restore; кнопка восстановления не была из-за этого неработоспособной.
- Рабочие Aurorae `metadata.desktop` сохранены. Доступный тип пакетов называется `KWin/Aurorae`, а не `aurorae`; разбор KPackage не используется как гарантия работы SVG-декорации в KWin.
- В обе схемы и встроенную палитру DARK добавлены полные `[Colors:Header]` и `[Colors:Header][Inactive]`. Поля `[General] ColorScheme` исправлены на собственные имена схем.
- В `widgets/tasks.svg` обоих стилей прозрачные заглушки `normal-*`/`minimized-*` (все ориентации: без префикса, `north-`, `east-`, `west-`) заменены скруглённым фоном (r=3) с непрозрачностью 0.08; `hover-*`/`focus-*` получили такой же фон 0.14 под существующей градиентной/акцентной полосой. DARK использует `#eff0f1`, COLOR — `ColorScheme-Text` + `currentColor`. ID, bounding box частей, градиенты, `attention-*`, `progress-*`, `group-expander-*` и `hint-stretch-borders` не менялись. Добавлены `east-hover-bottomleft`/`bottomright` рядом с прежними ID через дефис, которые сохранены. Закрытый launcher по-прежнему должен оставаться без фона; это требует ручной проверки.
- `help.svg` и `shade.svg` не добавлялись без подтверждённого требования к доступным действиям текущего Wayland/KWin.

## 4. Ресурсы и сознательные fallback

В каждом корневом `widgets/` находится 26 SVG, а не 24. Всего автоматическая
проверка охватывает 288 SVG Plasma/Aurorae. Наличие любого ресурса Breeze не
означает, что ROUNDED обязан иметь собственную копию.

| Потребитель | Подтверждённый контракт | Решение |
| --- | --- | --- |
| Панели Plasma | `widgets/panel-background`, `solid/widgets/panel-background`, рамки/маски, `thick-hint-*` | Исправлено имя правого hint, остальной дизайн сохранён |
| Folder containment | `widgets/action-overlays`, add/remove/open, normal/hover/pressed | Оставлен установленный default fallback |
| Aurorae maximize button | `restoreButtonPath`, fallback на maximize | Добавлен отдельный restore |
| KSplash | `contents/splash/Splash.qml`, свойство `stage` | Контракт сохранён, offscreen smoke-test пройден |

Установленная default-тема предоставляет отсутствующие собственные ресурсы:
`plasmoidheading`, `calendar`, `margins-highlight`, `action-overlays`,
`actionbutton`, `media-delegate`, `radiobutton`, `frame`, `toolbar`,
`translucentbackground`, `dragger`, `monitor`. Их визуальное согласование с
ROUNDED ещё не проверено; массового копирования Breeze не выполнялось.

Вспомогательные `analog_meter`, `branding`, `picker`, `plot-background`, `timer`,
`weather/wind-arrows` оставлены на штатном fallback-пути без индивидуальной
визуальной приёмки. Folder containment запрашивает `widgets/toolbox`, но в
проверенных установленных desktop-темах подходящий SVG не найден; новый
ресурс без подтверждённого контракта не создавался.

ID апплета не равен имени desktoptheme SVG. Для IME, яркости, камеры,
dwellclicker, kclock и сторонней погоды не добавлялись предположительные SVG.
Потребитель может использовать Breeze icons, QtQuick Controls или Kirigami.
Отсутствие `mobile`, `search`, `software`, `video-card`, `kpackagekit` само по
себе не является блокером миграции.

## 5. Установка и восстановление

Добавлен `scripts/install.sh` (POSIX shell entry point, Python 3 stdlib).

```sh
sh scripts/install.sh install --dry-run
sh scripts/install.sh install
sh scripts/install.sh install --update --with-konsole --with-yakuake
sh scripts/install.sh uninstall --dry-run
sh scripts/install.sh uninstall
sh scripts/install.sh restore --dry-run
sh scripts/install.sh restore
```

- Устанавливается явный manifest в `${XDG_DATA_HOME:-$HOME/.local/share}`: глобальные/desktop-темы, Aurorae и цветовые схемы. Konsole/Yakuake включаются только опциями, их настройки не выбираются автоматически.
- Обновление базовой темы без опциональных флагов сохраняет ранее установленные Konsole/Yakuake; для их обновления нужны соответствующие флаги.
- Коллизии требуют `--update`; предсуществующие идентичные файлы не присваиваются установке. Устаревшие Plasma `metadata.desktop` удаляются с backup только по известным путям и при точном совпадении ID пакета.
- Используются staging, контрольные суммы, транзакционные backups и откат замен при обычной ошибке. Межкаталожная установка не является одной атомарной транзакцией; принудительное завершение и потеря питания требуют отдельного восстановления.
- Uninstall удаляет только неизменённые принадлежащие установке файлы, сохраняя пользовательские изменения и посторонние файлы. Пустые каталоги могут остаться.
- Restore отменяет последнюю сохранённую операцию. После uninstall для возврата к состоянию до обновления сначала восстанавливается удаление, затем обновление.
- При изменённых целях restore отказывается от всей операции и сохраняет backups. Проверяются ID транзакции, пути, ownership, хеши, режимы доступа и содержимое backup.
- Мутирующие команды сериализуются через `flock`. Dry-run не создаёт файлов. Относительный XDG_DATA_HOME и символьные ссылки отклоняются; пустая переменная использует стандартный путь.
- Состояние хранится в `.rounded-theme-installer` внутри каталога данных. Запись в `~/.config`, применение темы, перезапуск процессов и очистка кешей не выполняются.

## 6. Выполненные проверки

```sh
sh scripts/check-theme.sh
sh scripts/check-theme.sh --runtime
python3 scripts/test-install.py
sh -n scripts/install.sh scripts/check-theme.sh
git diff --check
```

| Проверка | Результат |
| --- | --- |
| JSON, XML/SVG, уникальность ID, href-ссылки | Пройдено для проверяемых ресурсов, 288 SVG |
| FrameSvg рамки/маски панелей и thick-margin hints | Пройдено |
| Геометрия COLOR/DARK панелей, используемые COLOR CSS-классы | Пройдено |
| Defaults, собственные ID, Header-роли и соответствие встроенного DARK | Пройдено |
| qmllint обоих Splash.qml | Пройдено |
| Разбор четырёх пакетов установленным kpackagetool6 по пути | Пройдено |
| Оба splash в ksplashqml --test --window --nofork с QT_QPA_PLATFORM=offscreen | Пройдено, без вывода ошибок |
| Установка в изолированные временные XDG-каталоги | Пройдено, применён 321 файл базового набора |
| Plasma/LookAndFeel --list и Plasma/Theme --list после изолированной установки | Обнаружены все четыре ID |
| 18 тестов установщика | Пройдено |
| Shell-синтаксис и git diff --check | Пройдено |

Тесты установщика включают пути с пробелами, повторную установку, коллизии,
обновление legacy-метаданных, сохранение ownership и опциональных компонентов,
rollback, проверку restore и backup, блокировку параллельных запусков,
dry-run, отклонение symlink и некорректного XDG-пути.

Временные каталоги удалены после тестирования. Проверки не применяли тему к
основной сессии. Offscreen-запуск не заменяет визуальную приёмку.

## 7. Непроверенные сценарии и исключения

- KCM: карточки обеих глобальных/desktop-тем и Aurorae без дубликатов, корректное ручное применение компонентов.
- Живой рендеринг Aurorae: все состояния кнопок, максимизация/восстановление, hit areas, размеры и читаемость заголовка.
- Фоны задач в менеджере задач: четыре края панели, launcher без фона, свёрнутое/фоновое/hover/активное/attention, швы 4px-сегментов при 125/150%, восприятие полосы поверх фона.
- Floating/non-floating панели: четыре края, разные высоты, переходы при максимизации, маски, тени, blur и adaptive transparency.
- Kickoff, календарь, tray, сеть, звук, буфер обмена, уведомления, медиаконтроллер, folder selection, KRunner, tooltips и popups у края экрана.
- COLOR со светлой, тёмной и контрастной акцентной схемой; фиксированный DARK при смене внешней схемы; шапки QtWidgets/Kirigami.
- Масштабы 100/125/150/200%, смешанный масштаб двух мониторов, сохранение четырёх панелей после ручного применения.
- Скриншоты до/после и отсутствие новых воспроизводимых ошибок в журнале живой сессии.
- Konsole/Yakuake: проверена установка опциональных ресурсов, но полная runtime/визуальная совместимость приложений не заявляется.

SDDM и `ROUNDED.layout.latte` сохранены как legacy, исключены из установки и
заявленной совместимости. Union/Kvantum, Kitty, собственные иконки/курсоры,
обои, lockscreen/OSD и Plasma Login Manager в объём миграции не входят.

Перед ручным применением следует сохранить существующие `kdeglobals`,
`kwinrc`, `plasmarc`, `kcminputrc`, `ksplashrc`, состояние `kdedefaults` и
`plasma-org.kde.plasma.desktop-appletsrc`; отсутствующие файлы отмечать как
отсутствующие. Выбирать только оформление без замены desktop layout.
Восстанавливать настройки адресно вне сессии/при остановленных процессах.
Один временный XDG_DATA_HOME не изолирует GUI от текущих D-Bus и конфигурации.

**Итог:** кодовая миграция и перечисленные автоматические проверки выполнены.
Полная визуальная приёмка Plasma 6.8 Wayland остаётся открытой; отсутствие
собственного SVG или успешный smoke-test не доказывают визуальную совместимость.
