// Main app initialization
document.addEventListener('DOMContentLoaded', () => {
  // Theme toggle
  const root = document.documentElement;
  const toggle = document.getElementById('theme-toggle');
  const saved = localStorage.getItem('theme');
  if (saved === 'light') root.classList.add('light');
  toggle && toggle.addEventListener('click', () => {
    root.classList.toggle('light');
    localStorage.setItem('theme', root.classList.contains('light') ? 'light' : 'dark');
  });

  // Kanban drag & drop
  const cols = document.querySelectorAll('[data-col]');
  let dragged = null;

  document.querySelectorAll('[data-task]').forEach(card => {
    card.draggable = true;
    card.addEventListener('dragstart', e => {
      dragged = card;
      e.dataTransfer.effectAllowed = 'move';
    });
    card.addEventListener('dragend', () => { dragged = null; });
  });

  cols.forEach(col => {
    col.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    });
    col.addEventListener('drop', e => {
      e.preventDefault();
      if (!dragged) return;
      col.querySelector('[data-list]').appendChild(dragged);
      const taskId = dragged.getAttribute('data-task');
      const newStatus = col.getAttribute('data-col');
      fetch(`/kanban/move/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify({ id: taskId, status: newStatus })
      }).catch(() => {});
    });
  });

  // Request checkpoints timeline (manager request detail)
  const timeline = document.getElementById('cp-timeline');
  if (timeline) {
    initRequestTimeline(timeline);
  }

  // Matrix visual ornaments (for landing page)
  const matrix = document.querySelector('.matrix-bg');
  if (matrix) {
    for (let i = 0; i < 7; i++) {
      const d = document.createElement('div');
      d.className = 'matrix-dot';
      d.style.top = Math.random() * 86 + 6 + '%';
      d.style.left = Math.random() * 88 + 2 + '%';
      d.style.animationDelay = (Math.random() * 8) + 's';
      matrix.appendChild(d);
    }
    for (let i = 0; i < 3; i++) {
      const h = document.createElement('div');
      h.className = 'matrix-hex';
      h.style.top = Math.random() * 88 + 1 + '%';
      h.style.left = Math.random() * 90 + 0.5 + '%';
      h.style.animationDelay = (Math.random() * 14) + 's';
      matrix.appendChild(h);
    }
  }
});

function initRequestTimeline(root) {
  const apiUrl = root.getAttribute('data-api-url');
  let dataRaw = root.getAttribute('data-checkpoints') || '[]';
  let checkpoints;
  try {
    checkpoints = JSON.parse(dataRaw.replace(/'/g, '"'));
  } catch (e) {
    checkpoints = [];
  }

  const editor = document.getElementById('cp-editor');
  const form = document.getElementById('cp-editor-form');
  const addBtn = document.getElementById('cp-add-btn');
  const deleteBtn = document.getElementById('cp-delete-btn');
  const closeBtn = document.getElementById('cp-editor-close');

  let activeId = null;

  function render() {
    root.innerHTML = '';
    const line = document.createElement('div');
    line.className = 'cp-line';
    const list = document.createElement('div');
    list.className = 'cp-points';

    checkpoints
      .slice()
      .sort((a, b) => (a.order || 0) - (b.order || 0) || a.id - b.id)
      .forEach((cp, index) => {
        const item = document.createElement('div');
        item.className = 'cp-point';
        item.setAttribute('data-id', cp.id);
        item.setAttribute('draggable', 'true');

        const dot = document.createElement('div');
        dot.className = 'cp-dot' + (cp.is_done ? ' cp-dot--done' : '');
        if (cp.id === activeId) {
          dot.classList.add('cp-dot--active');
        }

        const label = document.createElement('div');
        label.className = 'cp-label';
        label.textContent = cp.title || `Этап ${index + 1}`;

        item.appendChild(dot);
        item.appendChild(label);
        list.appendChild(item);

        item.addEventListener('click', () => {
          openEditor(cp);
        });
      });

    root.appendChild(line);
    root.appendChild(list);

    // drag & drop reordering
    let dragSrc = null;
    list.querySelectorAll('.cp-point').forEach(el => {
      el.addEventListener('dragstart', e => {
        dragSrc = el;
        e.dataTransfer.effectAllowed = 'move';
      });
      el.addEventListener('dragover', e => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
      });
      el.addEventListener('drop', e => {
        e.preventDefault();
        if (!dragSrc || dragSrc === el) return;
        const children = Array.from(list.children);
        const srcIndex = children.indexOf(dragSrc);
        const targetIndex = children.indexOf(el);
        if (srcIndex < targetIndex) {
          list.insertBefore(dragSrc, el.nextSibling);
        } else {
          list.insertBefore(dragSrc, el);
        }
        saveOrder(list);
      });
      el.addEventListener('dragend', () => {
        dragSrc = null;
      });
    });
  }

  function openEditor(cp) {
    activeId = cp ? cp.id : null;
    if (!editor) return;
    editor.classList.remove('cp-editor--hidden');
    const idEl = document.getElementById('cp-id');
    const titleEl = document.getElementById('cp-title');
    const commentEl = document.getElementById('cp-comment');
    const doneEl = document.getElementById('cp-is-done');
    if (!idEl || !titleEl || !commentEl || !doneEl) return;
    idEl.value = cp ? cp.id : '';
    titleEl.value = cp ? (cp.title || '') : '';
    commentEl.value = cp ? (cp.comment || '') : '';
    doneEl.checked = cp ? !!cp.is_done : false;
    render();
  }

  function closeEditor() {
    activeId = null;
    if (editor) {
      editor.classList.add('cp-editor--hidden');
    }
    render();
  }

  function findCheckpoint(id) {
    return checkpoints.find(c => c.id === id);
  }

  function updateFromForm() {
    const id = parseInt(document.getElementById('cp-id').value || '0', 10);
    const title = document.getElementById('cp-title').value.trim();
    const comment = document.getElementById('cp-comment').value.trim();
    const isDone = document.getElementById('cp-is-done').checked;

    const payload = {
      action: id ? 'update' : 'create',
      id: id || undefined,
      title,
      comment,
      is_done: isDone,
    };

    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify(payload),
    })
      .then(r => r.json())
      .then(resp => {
        if (!resp.ok) return;
        if (payload.action === 'create' && resp.checkpoint) {
          checkpoints.push(resp.checkpoint);
          openEditor(resp.checkpoint);
        } else if (payload.action === 'update' && id) {
          const cp = findCheckpoint(id);
          if (cp) {
            cp.title = title;
            cp.comment = comment;
            cp.is_done = isDone;
          }
          openEditor(cp || null);
        }
      })
      .catch(() => {});
  }

  function saveOrder(list) {
    const ids = Array.from(list.querySelectorAll('.cp-point')).map(el =>
      parseInt(el.getAttribute('data-id') || '0', 10),
    );
    if (!ids.length) return;
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ action: 'reorder', ids }),
    }).catch(() => {});

    // локально обновим порядок
    const map = new Map();
    checkpoints.forEach(c => map.set(c.id, c));
    checkpoints = ids
      .map((id, idx) => {
        const cp = map.get(id);
        if (cp) cp.order = idx + 1;
        return cp;
      })
      .filter(Boolean);
    render();
  }

  if (addBtn) {
    addBtn.addEventListener('click', () => {
      openEditor(null);
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      closeEditor();
    });
  }

  if (deleteBtn) {
    deleteBtn.addEventListener('click', () => {
      const id = parseInt(document.getElementById('cp-id').value || '0', 10);
      if (!id) {
        closeEditor();
        return;
      }
      fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ action: 'delete', id }),
      })
        .then(r => r.json())
        .then(resp => {
          if (!resp.ok) return;
          checkpoints = checkpoints.filter(c => c.id !== id);
          closeEditor();
        })
        .catch(() => {});
    });
  }

  if (form) {
    form.addEventListener('submit', e => {
      e.preventDefault();
      updateFromForm();
    });
  }

  render();
}

function getCsrfToken() {
  const name = 'csrftoken=';
  const parts = document.cookie.split(';');
  for (let c of parts) {
    c = c.trim();
    if (c.startsWith(name)) return c.substring(name.length);
  }
  return '';
}


