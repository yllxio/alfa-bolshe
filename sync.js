/* Optional DEMO shared-application sync. Never use with real personal data. */
(() => {
  'use strict';
  const endpoint = '/api/applications';
  let snapshots = new Map();
  let loading = true;
  let refreshing = false;
  let writing = false;
  const signature = a => JSON.stringify(a);
  const current = () => Array.isArray(state.apps) ? state.apps : [];
  const withoutActiveInput = () => !document.querySelector('#modalRoot .modal') &&
    !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);

  async function sendUpdates() {
    if (loading || writing) return;
    const altered = current().filter(a => signature(a) !== snapshots.get(a.id));
    if (!altered.length) return;
    writing = true;
    try {
      for (const app of altered) {
        const response = await fetch(endpoint, {
          method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(app)
        });
        if (!response.ok) throw Error('Не удалось синхронизировать заявку');
        snapshots.set(app.id, signature(app));
      }
    } catch (e) {
      console.warn('Демо-синхронизация отложена:', e.message);
    } finally { writing = false; }
  }

  async function refresh(initial = false) {
    if (refreshing || writing || (!initial && !withoutActiveInput())) return;
    refreshing = true;
    try {
      const response = await fetch(endpoint, {cache:'no-store'});
      if (!response.ok) throw Error('Сервер недоступен');
      const {applications} = await response.json();
      if (!Array.isArray(applications)) throw Error('Неверный ответ');
      let changed = false;
      const byId = new Map(current().map(a => [a.id, a]));
      for (const remote of applications) {
        const before = byId.get(remote.id);
        if (!before || signature(before) !== signature(remote)) {
          byId.set(remote.id, remote); changed = true;
        }
        snapshots.set(remote.id, signature(remote));
      }
      if (changed) {
        state.apps = Array.from(byId.values());
        // Do not interrupt an active form; only redraw read-only queue or tracker.
        const page = location.hash.slice(1);
        if (withoutActiveInput() && ['applications','manager','queue','dossier','analytics'].includes(page)) render();
      }
    } catch (e) {
      if (initial) console.info('Работаем в локальном режиме: синтетический сервер недоступен.');
    } finally {
      refreshing = false;
      if (initial) { loading = false; sendUpdates(); }
    }
  }

  const originalFlushSave = flushSave;
  flushSave = function() {
    originalFlushSave();
    void sendUpdates();
  };
  void refresh(true);
  setInterval(() => void refresh(false), 3500);
})();
