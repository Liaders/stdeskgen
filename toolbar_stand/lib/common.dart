String translate(String key) =>
    const {
      'Assign organization': 'Назначить организацию',
      'Expand toolbar': 'Развернуть панель',
    }[key] ??
    key;
