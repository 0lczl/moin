/* One interface preference across the welcome page and working areas. */
(function () {
  const key = 'moin-interface-language';
  let memory = null;
  function read() {
    if (memory) return memory;
    try {
      const value = localStorage.getItem(key);
      if (value === 'ar' || value === 'en') return value;
      // Carry forward a choice made before this shared control existed.
      const old = localStorage.getItem('moin-locale') || localStorage.getItem('moin-live-language');
      if (old === 'ar' || old === 'en') return old;
    } catch (_) { /* Storage can be disabled. */ }
    return navigator.language?.toLowerCase().startsWith('ar') ? 'ar' : 'en';
  }
  function save(value) {
    memory = value;
    try { localStorage.setItem(key, value); } catch (_) { /* Current page still switches. */ }
  }
  window.MoinLocale = { read, save };
})();
