(() => {
    const ru = {
        'Organizations tab (accessible device groups only)':'Вкладка «Организации» (только доступные группы устройств)',
        'organizations must be true or false.':'Параметр organizations должен быть true или false.',

        'Include compact interface (Slim UI)':'Добавить компактный интерфейс (Slim UI)',
        'If enabled, users can switch between normal and compact layouts in the client settings. If disabled, Slim UI is not included in the build.':'При включении пользователь сможет переключать обычный и компактный вид в настройках клиента. При отключении Slim UI не включается в сборку.',
        'slim_ui must be true or false.':'Параметр slim_ui должен быть true или false.',

        'Application logo: light theme (PNG)':'Логотип: светлая тема (PNG)',
        'Application logo: dark theme (PNG)':'Логотип: тёмная тема (PNG)',
        'Logo above Your Desktop. Select images for the light and dark themes. Windows x86 uses the light logo.':'Логотип над текстом «Ваш рабочий стол». Выберите изображения для светлой и тёмной темы. Windows x86 использует светлый логотип.',
        'Clear':'Очистить',
        'StatusDesk updates':'Обновления StatusDesk',
        'Update channel configuration (JSON; leave empty to disable)':'Конфигурация канала обновлений (JSON; пусто — выключено)',
        'Installed Windows x64/x86 clients only. Increase the revision for each release.':'Только установленные клиенты Windows x64/x86. Повышайте ревизию при каждом выпуске.',
        'Example configuration':'Пример конфигурации',
        'Colleagues tab (server-visible users)':'Вкладка «Коллеги» (пользователи, доступные через сервер)',
        'RustDesk Custom Client Builder':'Конструктор клиента RustDesk',
        'Save/Load Configuration':'Сохранение и загрузка конфигурации','Save Configuration':'Сохранить конфигурацию','Load Configuration':'Загрузить конфигурацию',
        'Select Platform':'Платформа','Windows 64Bit':'Windows 64 бита','Windows 32Bit':'Windows 32 бита','Rustdesk Version:':'Версия RustDesk:','nightly':'Тестовая (nightly)',
        'Fix connection delay when using third-party API':'Исправить задержку подключения при использовании стороннего API','General':'Основные настройки',
        'Name of the configuration (no spaces or special characters, English characters only):':'Имя конфигурации (латиницей, без пробелов и специальных символов):',
        'Custom Application Name (leave blank to use default):':'Название приложения (пустое поле — стандартное):','Connection Type:':'Направление подключений:',
        'Incoming Only':'Только входящие','Outgoing Only':'Только исходящие','Bidirectional':'В обоих направлениях','Disable Installation:':'Отключить установку:',
        'No, enable installation':'Нет, разрешить установку','Yes, DISABLE installation':'Да, отключить установку','Disable Settings:':'Отключить настройки:',
        'No, enable settings':'Нет, разрешить настройки','Yes, DISABLE settings':'Да, отключить настройки',
        "Custom Android App ID (replaces 'com.carriez.flutter_hbb', leave blank to use default):":'Идентификатор Android-приложения (пустое поле — стандартный):',
        'Custom Server':'Свой сервер','Host:':'Адрес сервера:','Port:':'Порт:','Key:':'Ключ:','API:':'Адрес API:',
        'Custom URL for links (replaces https://rustdesk.com):':'Ссылка на сайт (вместо https://rustdesk.com):',
        'Custom URL for downloading updates (replaces https://rustdesk.com/download):':'Ссылка для скачивания обновлений:',
        'Company name for copyright (replaces Purslane Tech Pte. Ltd.):':'Название компании для сведений об авторских правах:',
        'Security':'Безопасность','Password Approve mode:':'Подтверждение подключения:','Accept sessions via password':'По паролю','Accept sessions via click':'По нажатию кнопки','Accepts sessions via both':'По паролю или нажатию кнопки',
        'To use the hide connection window feature, please set a permanent password.':'Для скрытия окна подключения задайте постоянный пароль.',
        'Set Permanent Password:':'Постоянный пароль:','*The password is used as default, but can be changed by the client':'*Пароль задаётся по умолчанию, пользователь клиента может его изменить',
        'Deny LAN discovery':'Запретить обнаружение в локальной сети','Enable direct IP access':'Разрешить подключение по IP','Automatically close incoming sessions on user inactivity':'Завершать входящие сеансы при бездействии',
        'Allow hiding the connection window from remote screen.':'Разрешить скрытие окна подключения на удалённом экране.',
        'Visual':'Оформление','Custom App Icon (in .png format)':'Иконка приложения (PNG)','Custom App Logo (in .png format)':'Логотип приложения (PNG)','Custom Privacy Screen (in .png format)':'Изображение экрана приватности (PNG)',
        'Theme:':'Тема:','Light':'Светлая','Dark':'Тёмная','Follow System':'Как в системе','Default':'По умолчанию','Override':'Принудительно',
        '*Default sets the theme but allows the client to change it, Override sets the theme permanently.':'*«По умолчанию» позволяет менять тему в клиенте. «Принудительно» фиксирует её.',
        'Client appearance':'Оформление клиента','Customize client appearance':'Изменить оформление клиента','Custom accent color':'Свой акцентный цвет','Custom button color':'Свой цвет кнопок',
        'Main navigation':'Навигация главной страницы','Icons':'Иконки','Text tabs':'Текстовые вкладки','Accessible devices: users / groups panel width':'Доступные устройства: ширина панели пользователей и групп',
        '150–480 logical pixels. Leave blank for the original width.':'150–480 логических пикселей. Пустое поле — исходная ширина.','Address book panel width':'Ширина панели адресной книги',
        'Friendly names in accessible devices':'Псевдонимы доступных устройств','Use the server alias when available, then a local alias, the original device name, or its ID. Local aliases are stored on the client.':'Приоритет: серверный псевдоним → локальный → исходное имя → ID. Локальные имена хранятся на компьютере с клиентом.',
        'Advanced: JSON profile':'Дополнительно: профиль JSON','Existing profiles can also be pasted here.':'Сюда также можно вставить ранее сохранённый профиль.','Reset appearance':'Сбросить оформление',
        'Permissions':'Разрешения','The following Permissions can be set as default (the user can change the settings) or override (the settings cannot be changed).':'Разрешения можно задать по умолчанию (пользователь сможет их изменить) или принудительно (изменение запрещено).',
        'Permission type:':'Режим доступа:','Custom':'Настраиваемый','Full Access':'Полный доступ','Screen share':'Просмотр экрана','Enable keyboard/mouse':'Управление клавиатурой и мышью',
        'Enable clipboard':'Буфер обмена','Enable file transfer':'Передача файлов','Enable audio':'Передача звука','Enable TCP tunneling':'TCP-туннели','Enable remote restart':'Удалённая перезагрузка',
        'Enable recording session':'Запись сеанса','Enable blocking user input':'Блокировка ввода пользователя','Enable remote configuration modification':'Изменение удалённых настроек','Enable remote printer':'Удалённая печать','Enable remote camera':'Удалённая камера','Enable remote terminal':'Удалённый терминал',
        'Code Changes':'Дополнительные изменения','Display an X for offline devices in the addressbook.':'Отмечать недоступные устройства крестиком в адресной книге.','Remove notification for new versions.':'Убрать уведомления о новых версиях.',
        'Other':'Прочее','Remove wallpaper during incoming sessions':'Убирать обои во время входящих сеансов','Click here for a list of Default/Override settings':'Список настроек по умолчанию и принудительных настроек',
        'Default settings':'Настройки по умолчанию','Override settings':'Принудительные настройки','Generate Custom Client':'Собрать клиент','Source Code on Github':'Исходный код на GitHub','Donate':'Поддержать автора',
        'Appearance settings will be applied to the client.':'Настройки оформления будут применены к клиенту.','The original client appearance will be used.':'Будет использовано стандартное оформление клиента.','Appearance profile loaded.':'Профиль оформления загружен.',
        'Colors must use #RRGGBB, for example #6750A4.':'Укажите цвет в формате #RRGGBB, например #6750A4.','Panel widths must be whole numbers between 150 and 480.':'Ширина панели должна быть целым числом от 150 до 480.',
        'Recent GitHub builds':'Последние сборки на GitHub','Client build on GitHub':'Сборка клиента на GitHub','GitHub build':'Сборка на GitHub',
        'The configuration was sent to GitHub Actions. This computer does not need to be accessible from the internet.':'Конфигурация отправлена в GitHub Actions. Доступ к этому компьютеру из интернета не требуется.',
        'Waiting for GitHub to start the build…':'Ожидание запуска сборки на GitHub…','Open build and download artifacts on GitHub':'Открыть сборку и скачать результат на GitHub','Back to constructor':'Вернуться в конструктор',
        'After a successful build, download':'После успешной сборки скачайте','in the Artifacts section. You can close this page; the build continues on GitHub. Keep it open to automatically remove temporary transfer data after completion.':'в разделе Artifacts. Сборка продолжится, даже если закрыть эту страницу. Оставьте её открытой для автоматической очистки временных данных после завершения.',
        'Default: 150':'По умолчанию: 150','Default: 200':'По умолчанию: 200','Accent color':'Акцентный цвет','Accent color HEX':'Акцентный цвет HEX','Button color':'Цвет кнопок','Button color HEX':'Цвет кнопок HEX',
        'Filename is required.':'Укажите имя конфигурации.','Expected a JSON profile with schema_version: 1.':'Нужен профиль JSON с schema_version: 1.',
        'Currently available for RustDesk 1.5.0, Windows 64-bit. Other platforms will be added later.':'Сейчас доступно для RustDesk 1.5.0, Windows 64 бита. Остальные платформы подключаются.',
        'queued':'в очереди','in_progress':'выполняется','completed':'завершена','success':'успешно','failure':'ошибка','cancelled':'отменена',
        'Build completed:':'Сборка завершена:','Temporary transfer data removed.':'Временные данные удалены.','Transfer cleanup pending; keep this page open.':'Ожидание очистки временных данных; оставьте страницу открытой.',
    };
    Object.assign(ru, {
        'RustDesk 1.5.0: Windows x64, Linux and macOS. Windows x86 uses a legacy Sciter interface; appearance customization is unavailable.':'RustDesk 1.5.0: Windows x64, Linux и macOS. В Windows x86 используется старый интерфейс Sciter; эти настройки оформления для него пока недоступны.',
        'Appearance customization supports Windows x64, Linux and macOS / RustDesk 1.5.0. Windows x86 uses Sciter: turn appearance customization off for this target. Your settings are preserved.':'Оформление поддерживается для Windows x64, Linux и macOS / RustDesk 1.5.0. Для Windows x86 (Sciter) отключите настройку оформления. Профиль сохранён.',
        'This profile requires Windows x64, Linux or macOS / RustDesk 1.5.0. Windows x86 uses Sciter. Settings are preserved.':'Этот профиль рассчитан на Windows x64, Linux или macOS / RustDesk 1.5.0. В Windows x86 используется Sciter. Профиль сохранён.',
        'Windows x86 uses Sciter: custom logo and privacy images are not supported. The app icon is supported.':'Windows x86 использует Sciter: свой логотип и экран приватности не поддерживаются. Иконку приложения можно изменить.',
        'Local GitHub builds support Windows, Linux and macOS with RustDesk 1.5.0.':'Локальная сборка через GitHub поддерживает Windows, Linux и macOS на базе RustDesk 1.5.0.',
        'Expected a JSON profile with schema_version: 1.':'Нужен профиль JSON с schema_version: 1.',
        'Appearance profile loaded.':'Профиль оформления загружен.',
        'This field is required.':'Обязательное поле.',
        'The profile contains unsupported settings. It has not been changed.':'Профиль содержит неподдерживаемые настройки и оставлен без изменений.',
        'Enter a whole number for the panel width.':'Введите целое число для ширины панели.'
    });
    Object.assign(ru, {
        'Allow resizing panels by dragging':'Разрешить изменение ширины панелей мышью',
        'Widths above are initial values. Each client remembers dragged widths separately for the two panels. Double-click the divider to restore the initial width.':'Ширины выше задают начальные значения. Клиент отдельно запоминает размер каждой панели. Двойной щелчок по разделителю возвращает начальную ширину.',
        'resizable_panels must be true or false.':'Параметр resizable_panels должен быть true или false.'
    });
    const nodes = new WeakMap();
    const attributes = new WeakMap();
    const selector = document.getElementById('constructor-language');
    let language;
    try { language = localStorage.getItem('stdeskgen-language') || 'ru'; } catch { language = 'ru'; }
    function translate(text) {
        if (ru[text]) return ru[text];
        if (/^—\s*(queued|in_progress|completed)$/.test(text)) return text.replace(/queued|in_progress|completed/g, word => ru[word]);
        if (text.startsWith('GitHub build: ')) return 'Сборка на GitHub: ' + (ru[text.slice(14)] || text.slice(14));
        if (text.startsWith('Build completed: ')) return text.replace('Build completed:', 'Сборка завершена:').replace('success', 'успешно').replace('failure','ошибка').replace('cancelled','отменена').replace('Temporary transfer data removed.','Временные данные удалены.').replace('Transfer cleanup pending; keep this page open.','Ожидание очистки временных данных; оставьте страницу открытой.');
        return text;
    }
    const observer = new MutationObserver(apply);
    function apply() {
        observer.disconnect();
        document.documentElement.lang = language;
        selector.value = language;
        const walker=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        for (let node=walker.nextNode(); node; node=walker.nextNode()) {
            if (node.parentElement.closest('script,style,textarea,[data-no-translate]')) continue;
            const previous=nodes.get(node);
            if (!previous || (node.data!==previous.source && node.data!==previous.output)) nodes.set(node,{source:node.data});
            const saved=nodes.get(node);
            const source=saved.source;
            const clean=source.trim();
            const output=language==='ru' ? source.replace(clean,translate(clean)) : source;
            if(node.data!==output) node.data=output;
            saved.output=output;
        }
        for(const element of document.querySelectorAll('[placeholder],[aria-label]')) {
            if(!attributes.has(element)) attributes.set(element, {placeholder:element.getAttribute('placeholder'), 'aria-label':element.getAttribute('aria-label')});
            for(const [name,source] of Object.entries(attributes.get(element))) if(source!==null) element.setAttribute(name, language==='ru'?translate(source):source);
        }
        observer.observe(document.body,{subtree:true,childList:true,characterData:true});
    }
    selector.addEventListener('change',()=>{language=selector.value;try{localStorage.setItem('stdeskgen-language',language);}catch{}apply();});
    apply();
})();
