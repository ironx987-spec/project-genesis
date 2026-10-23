// doom_notes.js — UI для вкладки Заметки / Напоминания / Дневник
(function () {
  "use strict";

  var NOTES_TYPES = ['notes', 'reminders', 'diary'];

  window.addNote = function (idx) {
    var type = NOTES_TYPES[idx];
    var textEl = document.getElementById('noteInput' + idx);
    if (!textEl) return;
    var text = textEl.value.trim();
    if (!text) return;

    var payload = { type: type, text: text };
    if (idx === 1) {
      var whenEl = document.getElementById('noteWhen1');
      if (whenEl) payload.when = whenEl.value.trim();
    }

    fetch('/api/notes/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d && d.ok) {
        textEl.value = '';
        if (idx === 1) {
          var wEl = document.getElementById('noteWhen1');
          if (wEl) wEl.value = '';
        }
        renderNotes();
      }
    })
    .catch(function (e) { console.warn('[NOTES] add', e); });
  };

  window.deleteNote = function (type, id) {
    fetch('/api/notes/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: type, id: id })
    })
    .then(function (r) { return r.json(); })
    .then(function () { renderNotes(); })
    .catch(function (e) { console.warn('[NOTES] del', e); });
  };

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderNotes() {
    fetch('/api/notes')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        ['notes', 'reminders', 'diary'].forEach(function (type, idx) {
          var list = document.getElementById('notesList' + idx);
          var empty = document.getElementById('notesEmpty' + idx);
          if (!list) return;
          var items = (data && data[type]) || [];

          if (!items.length) {
            list.innerHTML = '';
            if (empty) empty.style.display = '';
            return;
          }
          if (empty) empty.style.display = 'none';

          var html = '';
          items.forEach(function (it) {
            var meta = '';
            if (type === 'reminders' && it.when) meta = '⏰ ' + escapeHtml(it.when);
            if (type === 'diary' && it.date) meta = '📅 ' + escapeHtml(it.date);
            if (type === 'notes' && it.ts) meta = '🕐 ' + escapeHtml(it.ts);

            html += '<div class="notes-item">' +
              '<div class="notes-item-text">' + escapeHtml(it.text) +
                (meta ? '<span class="notes-item-meta">' + meta + '</span>' : '') +
              '</div>' +
              '<button class="notes-item-del" onclick="deleteNote(\'' + type + '\',' + it.id + ')">✕</button>' +
            '</div>';
          });
          list.innerHTML = html;
        });
      })
      .catch(function (e) { console.warn('[NOTES] render', e); });
  }

  // Экспорт — на случай внешнего вызова
  window.renderNotes = renderNotes;

  // Автообновление раз в 3 сек, если вкладка Заметки активна
  setInterval(function () {
    if (typeof state !== 'undefined' && state.tab === 3) {
      renderNotes();
    }
  }, 3000);

  // Первый рендер — через 500 мс после загрузки
  setTimeout(renderNotes, 500);
})();
