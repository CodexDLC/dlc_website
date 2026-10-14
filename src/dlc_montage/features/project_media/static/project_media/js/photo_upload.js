/* Each request contains one photo; successful photos are never retried automatically. */
(() => {
  const form = document.querySelector('[data-photo-upload]');
  if (!form || !window.XMLHttpRequest || !window.FormData) return;
  const input = form.querySelector('input[type="file"]');
  const button = form.querySelector('button[type="submit"]');
  const panel = form.querySelector('[data-upload-progress]');
  const status = form.querySelector('[data-upload-status]');
  const progress = form.querySelector('[data-file-progress]');
  const errors = form.querySelector('[data-upload-errors]');
  const ru = form.dataset.language.startsWith('ru');
  let active = false;
  const text = ru ? {
    processing: 'Сохраняем фотографию…',
    failed: 'Не удалось сохранить фотографию.',
    uncertain: 'Связь прервана или получен неожиданный ответ. Фотография могла сохраниться: проверьте галерею перед повторной загрузкой.',
    finished: 'Загрузка завершена. Фотографии доступны в галерее; копии отправляются в Nextcloud в фоне.',
    stopped: 'Загрузка остановлена. Оставшиеся фотографии не отправлены. Проверьте галерею перед повторной загрузкой.',
  } : {
    processing: 'Foto wird gespeichert…',
    failed: 'Foto konnte nicht gespeichert werden.',
    uncertain: 'Verbindung unterbrochen oder unerwartete Antwort. Das Foto könnte gespeichert sein: Prüfen Sie vor einem erneuten Upload die Galerie.',
    finished: 'Upload abgeschlossen. Fotos sind in der Galerie verfügbar; Kopien werden im Hintergrund an Nextcloud gesendet.',
    stopped: 'Upload angehalten. Verbleibende Fotos wurden nicht gesendet. Prüfen Sie vor einem erneuten Upload die Galerie.',
  };
  const count = (done, total) => ru ? `Обработано ${done} из ${total}` : `${done} von ${total} verarbeitet`;
  function addError(name, message) {
    const li = document.createElement('li');
    li.textContent = `${name}: ${message}`;
    errors.appendChild(li);
  }
  function send(file) {
    return new Promise((resolve) => {
      const xhr = new XMLHttpRequest();
      const data = new FormData();
      data.append('csrfmiddlewaretoken', form.querySelector('[name="csrfmiddlewaretoken"]').value);
      data.append(input.name, file, file.name);
      xhr.open('POST', form.action || window.location.href);
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      xhr.timeout = 180000;
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) progress.value = Math.round(event.loaded / event.total * 100);
      };
      xhr.upload.onload = () => { progress.value = 100; };
      xhr.onload = () => {
        let payload;
        try { payload = JSON.parse(xhr.responseText); } catch (_) { resolve({ uncertain: true }); return; }
        if (!payload || !Array.isArray(payload.errors) ||
            (xhr.status >= 200 && xhr.status < 300 && !Array.isArray(payload.uploaded))) {
          resolve({ uncertain: true }); return;
        }
        if (xhr.status >= 500) { resolve({ uncertain: true }); return; }
        resolve({ payload, fatal: xhr.status === 401 || xhr.status === 403 });
      };
      xhr.onerror = xhr.ontimeout = xhr.onabort = () => resolve({ uncertain: true });
      xhr.send(data);
    });
  }
  window.addEventListener('beforeunload', (event) => {
    if (active) { event.preventDefault(); event.returnValue = ''; }
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (active || !input.files.length) return;
    const files = Array.from(input.files);
    active = true;
    input.disabled = button.disabled = true;
    panel.hidden = false;
    errors.replaceChildren();
    let completed = 0;
    let stopped = false;
    try {
      for (const file of files) {
        progress.value = 0;
        status.textContent = `${count(completed, files.length)} · ${file.name} · ${text.processing}`;
        const result = await send(file);
        if (result.uncertain) { addError(file.name, text.uncertain); stopped = true; break; }
        for (const error of result.payload.errors) addError(error.name || file.name, error.message || text.failed);
        completed += 1;
        if (result.fatal) { stopped = true; break; }
      }
    } catch (_) {
      addError(files[completed]?.name || '', text.uncertain);
      stopped = true;
    } finally {
      active = false;
      input.disabled = button.disabled = false;
      input.value = '';
      status.textContent = `${count(completed, files.length)}. ${stopped ? text.stopped : text.finished}`;
    }
  });
})();
