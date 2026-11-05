(() => {
    const el = id => document.getElementById(id);
    const raw = el('id_ui_profile');
    const enabled = el('ui-enabled');
    const controls = el('ui-controls');
    const status = el('ui-status');
    const defaults = {accent: '#0071FF', button: '#2C8CFF'};
    let rawError = '';
    const allowed = ['schema_version', 'accent', 'button', 'navigation', 'group_width', 'address_book_width', 'device_names', 'resizable_panels', 'colleagues'];
    const supported = () => ['windows', 'linux', 'macos'].includes(el('id_platform').value) && el('id_version').value === '1.5.0';

    function validate(profile) {
        if (!profile || Array.isArray(profile) || typeof profile !== 'object' || profile.schema_version !== 1)
            throw Error('Expected a JSON profile with schema_version: 1.');
        if (Object.keys(profile).some(key => !allowed.includes(key))) throw Error('The profile contains unsupported settings. It has not been changed.');
        for (const key of ['accent', 'button']) {
            if (key in profile && (typeof profile[key] !== 'string' || !/^#[0-9a-f]{6}$/i.test(profile[key])))
                throw Error('Colors must use #RRGGBB, for example #6750A4.');
        }
        for (const key of ['group_width', 'address_book_width']) {
            if (key in profile && (!Number.isInteger(profile[key]) || profile[key] < 150 || profile[key] > 480))
                throw Error('Panel widths must be whole numbers between 150 and 480.');
        }
        if ('navigation' in profile && !['icons', 'text'].includes(profile.navigation)) throw Error('Navigation must be icons or text.');
        if ('device_names' in profile && typeof profile.device_names !== 'boolean') throw Error('device_names must be true or false.');
        if ('colleagues' in profile && typeof profile.colleagues !== 'boolean') throw Error('colleagues must be true or false.');
        if ('resizable_panels' in profile && typeof profile.resizable_panels !== 'boolean') throw Error('resizable_panels must be true or false.');
        return profile;
    }

    function updateControls() {
        controls.disabled = !enabled.checked || !!rawError;
        for (const key of ['accent', 'button']) {
            const disabled = !enabled.checked || !el(`ui-${key}-enabled`).checked || !!rawError;
            el(`ui-${key}`).disabled = disabled;
            el(`ui-${key}-hex`).disabled = disabled;
        }
    }

    function readControls() {
        const profile = {schema_version: 1, navigation: el('ui-navigation').value, device_names: el('ui-device-names').checked, colleagues: el('ui-colleagues').checked, resizable_panels: el('ui-resizable-panels').checked};
        for (const key of ['accent', 'button']) {
            if (el(`ui-${key}-enabled`).checked) profile[key] = el(`ui-${key}-hex`).value.trim();
        }
        for (const [id, key] of [['ui-group-width', 'group_width'], ['ui-address-width', 'address_book_width']]) {
            if (el(id).value !== '') profile[key] = Number(el(id).value);
            else if (el(id).validity.badInput) throw Error('Enter a whole number for the panel width.');
        }
        return validate(profile);
    }

    function prepare(forBuild = true) {
        updateControls();
        try {
            if (enabled.checked && rawError) throw Error(rawError);
            raw.value = enabled.checked ? JSON.stringify(readControls()) : '';
            if (enabled.checked && !supported()) {
                status.textContent = 'Appearance customization supports Windows x64, Linux and macOS / RustDesk 1.5.0. Windows x86 uses Sciter: turn appearance customization off for this target. Your settings are preserved.';
                return !forBuild;
            }
            status.textContent = enabled.checked ? 'Appearance settings will be applied to the client.' : 'The original client appearance will be used.';
            return true;
        } catch (error) {
            status.textContent = error.message;
            return false;
        }
    }

    function hydrate(value) {
        rawError = '';
        raw.value = typeof value === 'object' && value !== null ? JSON.stringify(value) : (value || '');
        enabled.checked = !!raw.value;
        try {
            const profile = raw.value ? validate(JSON.parse(raw.value)) : {};
            for (const key of ['accent', 'button']) {
                el(`ui-${key}-enabled`).checked = key in profile;
                el(`ui-${key}-hex`).value = profile[key] || defaults[key];
                el(`ui-${key}`).value = profile[key] || defaults[key];
            }
            el('ui-navigation').value = profile.navigation || 'icons';
            el('ui-colleagues').checked = profile.colleagues || false;
            el('ui-device-names').checked = profile.device_names || false;
            el('ui-resizable-panels').checked = profile.resizable_panels || false;
            el('ui-group-width').value = profile.group_width ?? '';
            el('ui-address-width').value = profile.address_book_width ?? '';
        } catch (error) {
            rawError = error.message;
        }
        updateControls();
        // Preserve the loaded JSON exactly until a control is edited.
        status.textContent = rawError || (enabled.checked && !supported()
            ? 'This profile requires Windows x64, Linux or macOS / RustDesk 1.5.0. Windows x86 uses Sciter. Settings are preserved.'
            : (enabled.checked ? 'Appearance profile loaded.' : 'The original client appearance will be used.'));
    }

    controls.addEventListener('input', event => {
        for (const key of ['accent', 'button']) {
            if (event.target === el(`ui-${key}`)) el(`ui-${key}-hex`).value = event.target.value.toUpperCase();
            if (event.target === el(`ui-${key}-hex`) && /^#[0-9a-f]{6}$/i.test(event.target.value)) el(`ui-${key}`).value = event.target.value;
        }
        prepare(false);
    });
    controls.addEventListener('change', () => prepare(false));
    enabled.addEventListener('change', () => {
        if (!enabled.checked) rawError = '';
        prepare(false);
    });
    raw.addEventListener('input', () => hydrate(raw.value));
    el('ui-reset').addEventListener('click', () => hydrate(''));
    for (const id of ['id_platform', 'id_version']) el(id).addEventListener('change', () => prepare(false));
    el('myForm').addEventListener('submit', event => {
        if (!prepare()) {
            event.preventDefault();
            el('ui-customization').scrollIntoView({behavior: 'smooth'});
        }
    });
    window.rdgenUI = {prepare, loadConfig: config => hydrate(config.ui_profile ?? '')};
    hydrate(raw.value);
})();

