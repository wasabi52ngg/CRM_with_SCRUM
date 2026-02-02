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

  // Kanban task panel (details/checkpoints/chat)
  const taskPanel = document.getElementById('task-panel');
  if (taskPanel) {
    initKanbanTaskPanel(taskPanel);
  }

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

function initKanbanTaskPanel(panel) {
  const closeBtn = document.getElementById('tp-close');
  const titleEl = document.getElementById('tp-title');
  const metaEl = document.getElementById('tp-meta');
  const assigneeEl = document.getElementById('tp-assignee');
  const createdByEl = document.getElementById('tp-created-by');
  const dueEl = document.getElementById('tp-due');
  const spEl = document.getElementById('tp-sp');

  const tabBtns = document.querySelectorAll('.task-tab');
  const tabPanes = document.querySelectorAll('.task-tabpane');

  const cpAddBtn = document.getElementById('tp-cp-add');
  const cpList = document.getElementById('tp-cp-list');
  const chatList = document.getElementById('tp-chat-list');
  const chatForm = document.getElementById('tp-chat-form');
  const chatText = document.getElementById('tp-chat-text');

  let currentTaskId = null;
  let apiUrl = null;
  let checkpoints = [];
  let chat = [];

  function show() {
    panel.classList.remove('task-panel--hidden');
  }
  function hide() {
    panel.classList.add('task-panel--hidden');
    currentTaskId = null;
    apiUrl = null;
  }

  function setActiveTab(name) {
    tabBtns.forEach(b => b.classList.toggle('task-tab--active', b.getAttribute('data-tab') === name));
    tabPanes.forEach(p => p.classList.toggle('task-tabpane--active', p.getAttribute('data-tabpane') === name));
  }

  function renderCheckpoints() {
    if (!cpList) return;
    cpList.innerHTML = '';
    const sorted = checkpoints.slice().sort((a, b) => (a.order || 0) - (b.order || 0) || a.id - b.id);
    sorted.forEach(cp => {
      const item = document.createElement('div');
      item.className = 'tp-item';
      const top = document.createElement('div');
      top.className = 'tp-item__top';
      const title = document.createElement('div');
      title.textContent = cp.title || 'Без названия';
      const badge = document.createElement('span');
      badge.className = 'tp-badge' + (cp.is_done ? ' tp-badge--done' : '');
      badge.textContent = cp.is_done ? 'done' : 'todo';
      top.appendChild(title);
      top.appendChild(badge);
      item.appendChild(top);
      if (cp.comment) {
        const c = document.createElement('div');
        c.className = 'muted';
        c.style.marginTop = '6px';
        c.textContent = cp.comment;
        item.appendChild(c);
      }
      item.addEventListener('click', () => {
        // быстрый toggle done
        apiRequest({ action: 'checkpoint_update', id: cp.id, is_done: !cp.is_done })
          .then(resp => {
            if (!resp.ok) return;
            cp.is_done = !cp.is_done;
            renderCheckpoints();
          })
          .catch(() => {});
      });
      cpList.appendChild(item);
    });
  }

  function renderChat() {
    if (!chatList) return;
    chatList.innerHTML = '';
    chat.forEach(m => {
      const msg = document.createElement('div');
      msg.className = 'tp-msg';
      const meta = document.createElement('div');
      meta.className = 'tp-msg__meta';
      const author = document.createElement('div');
      author.textContent = m.author__username || 'user';
      const time = document.createElement('div');
      time.textContent = (m.created_at || '').toString().slice(0, 16).replace('T', ' ');
      meta.appendChild(author);
      meta.appendChild(time);
      const text = document.createElement('div');
      text.textContent = m.text;
      msg.appendChild(meta);
      msg.appendChild(text);
      chatList.appendChild(msg);
    });
  }

  function apiRequest(payload) {
    if (!apiUrl) return Promise.reject();
    return fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
      body: JSON.stringify(payload),
    }).then(r => r.json());
  }

  function loadTask(taskId) {
    currentTaskId = taskId;
    apiUrl = `/manager/tasks/${taskId}/panel/`;
    show();
    setActiveTab('checkpoints');
    return apiRequest({ action: 'detail' }).then(resp => {
      if (!resp.ok) return;
      const t = resp.task;
      if (titleEl) titleEl.textContent = t.title;
      if (metaEl) metaEl.textContent = `${t.task_type_label} • ${t.status_label}`;
      if (assigneeEl) assigneeEl.textContent = t.assignee || '—';
      if (createdByEl) createdByEl.textContent = t.created_by || '—';
      if (dueEl) dueEl.textContent = t.due_date || '—';
      if (spEl) spEl.textContent = String(t.story_points ?? 0);
      checkpoints = resp.checkpoints || [];
      chat = resp.chat || [];
      renderCheckpoints();
      renderChat();
    });
  }

  // click on kanban cards (ignore drag)
  document.querySelectorAll('[data-task]').forEach(card => {
    card.addEventListener('click', e => {
      if (card === window.__kanbanDragged) return;
      const id = parseInt(card.getAttribute('data-task') || '0', 10);
      if (!id) return;
      loadTask(id).catch(() => {});
    });
    card.addEventListener('dragstart', () => {
      window.__kanbanDragged = card;
      setTimeout(() => { window.__kanbanDragged = null; }, 50);
    });
  });

  if (closeBtn) closeBtn.addEventListener('click', () => hide());
  tabBtns.forEach(btn => btn.addEventListener('click', () => setActiveTab(btn.getAttribute('data-tab'))));

  if (cpAddBtn) {
    cpAddBtn.addEventListener('click', () => {
      const title = prompt('Название чекпоинта');
      if (!title) return;
      apiRequest({ action: 'checkpoint_create', title, comment: '' })
        .then(resp => {
          if (!resp.ok) return;
          checkpoints.push(resp.checkpoint);
          renderCheckpoints();
        })
        .catch(() => {});
    });
  }

  if (chatForm) {
    chatForm.addEventListener('submit', e => {
      e.preventDefault();
      const text = (chatText && chatText.value || '').trim();
      if (!text) return;
      apiRequest({ action: 'chat_add', text })
        .then(resp => {
          if (!resp.ok) return;
          chat.push(resp.message);
          if (chatText) chatText.value = '';
          renderChat();
        })
        .catch(() => {});
    });
  }
}

function initRequestTimeline(root) {
  const apiUrl = root.getAttribute('data-api-url');
  const scriptEl = document.getElementById('cp-data');
  let checkpoints = [];
  if (scriptEl) {
    try {
      checkpoints = JSON.parse(scriptEl.textContent);
    } catch (e) {
      checkpoints = [];
    }
  }

  const editor = document.getElementById('cp-editor');
  const form = document.getElementById('cp-editor-form');
  const addBtn = document.getElementById('cp-add-btn');
  const deleteBtn = document.getElementById('cp-delete-btn');
  const closeBtn = document.getElementById('cp-editor-close');
  const editToggle = document.getElementById('cp-edit-toggle');

  let isEditMode = false;

  function applyEditMode() {
    const actions = document.querySelector('.cp-editor-actions');
    if (!actions) return;
    // Поля всегда редактируемые, кнопки сохранения/удаления показываем только в режиме редактирования
    actions.style.display = isEditMode ? 'flex' : 'none';
  }

  function render() {
    root.innerHTML = '';
    const list = document.createElement('div');
    list.className = 'cp-points';

    const sorted = checkpoints.slice().sort(
      (a, b) => (a.order || 0) - (b.order || 0) || a.id - b.id,
    );

    sorted.forEach((cp, index) => {
      const item = document.createElement('div');
      item.className = 'cp-point';
      if (index === 0) {
        item.classList.add('cp-point--first');
      }
      item.setAttribute('data-id', cp.id);
      item.setAttribute('draggable', 'true');
      item.setAttribute('data-index', index);

      const dot = document.createElement('div');
      dot.className = 'cp-dot' + (cp.is_done ? ' cp-dot--done' : '');

      const label = document.createElement('div');
      label.className = 'cp-label';
      label.textContent = cp.title || `Этап ${index + 1}`;

      item.appendChild(dot);
      item.appendChild(label);
      list.appendChild(item);

      // клик по точке или тексту открывает редактор
      const openOnClick = (e) => {
        if (e.target.closest('.cp-editor')) return;
        e.stopPropagation();
        openEditor(cp, item);
        root.querySelectorAll('.cp-dot').forEach(d => d.classList.remove('cp-dot--active'));
        dot.classList.add('cp-dot--active');
      };
      item.addEventListener('click', openOnClick);
    });

    root.appendChild(list);

    // drag & drop reordering
    let dragSrc = null;
    let dragSrcIndex = -1;
    let draggedDot = null;

    list.querySelectorAll('.cp-point').forEach(el => {
      el.addEventListener('dragstart', e => {
        dragSrc = el;
        dragSrcIndex = parseInt(el.getAttribute('data-index') || '0', 10);
        draggedDot = el.querySelector('.cp-dot');
        if (draggedDot) draggedDot.classList.add('cp-dot--dragging');
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

        // Обновляем индексы и классы first/gap
        Array.from(list.children).forEach((child, idx) => {
          child.setAttribute('data-index', idx);
          child.classList.toggle('cp-point--first', idx === 0);
        });

        saveOrder(list);
      });

      el.addEventListener('dragend', () => {
        if (draggedDot) draggedDot.classList.remove('cp-dot--dragging');
        dragSrc = null;
        dragSrcIndex = -1;
        draggedDot = null;
        // На всякий случай обновим классы first после завершения
        Array.from(list.children).forEach((child, idx) => {
          child.classList.toggle('cp-point--first', idx === 0);
        });
      });
    });
  }

  function openEditor(cp, pointElement) {
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

    // при открытии существующего чекпоинта по умолчанию режим просмотра (без кнопок),
    // для нового сразу включаем редактирование
    isEditMode = !cp;
    applyEditMode();

    // позиционируем редактор справа от выбранного чекпоинта
    if (pointElement) {
      const rootRect = root.getBoundingClientRect();
      const pointRect = pointElement.getBoundingClientRect();
      const editorRect = editor.getBoundingClientRect();
      const timelineCard = root.closest('.timeline-card');
      if (timelineCard) {
        const cardRect = timelineCard.getBoundingClientRect();
        const top = pointRect.top - cardRect.top - 8;
        const right = cardRect.right - pointRect.right - 24;
        editor.style.top = `${Math.max(0, top)}px`;
        editor.style.right = `${Math.max(24, right)}px`;
        editor.style.left = 'auto';
      }
    } else {
      // для нового чекпоинта - внизу списка
      const points = root.querySelectorAll('.cp-point');
      if (points.length > 0) {
        const lastPoint = points[points.length - 1];
        const rootRect = root.getBoundingClientRect();
        const pointRect = lastPoint.getBoundingClientRect();
        const timelineCard = root.closest('.timeline-card');
        if (timelineCard) {
          const cardRect = timelineCard.getBoundingClientRect();
          const top = pointRect.top - cardRect.top - 8;
          editor.style.top = `${Math.max(0, top)}px`;
          editor.style.right = '24px';
          editor.style.left = 'auto';
        }
      }
    }
  }

  function closeEditor() {
    if (editor) {
      editor.classList.add('cp-editor--hidden');
    }
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
          render();
          const newPoint = root.querySelector(`[data-id="${resp.checkpoint.id}"]`);
          openEditor(resp.checkpoint, newPoint);
        } else if (payload.action === 'update' && id) {
          const cp = findCheckpoint(id);
          if (cp) {
            cp.title = title;
            cp.comment = comment;
            cp.is_done = isDone;
          }
          render();
          const updatedPoint = root.querySelector(`[data-id="${id}"]`);
          openEditor(cp || null, updatedPoint);
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
    const sorted = ids
      .map((id, idx) => {
        const cp = map.get(id);
        if (cp) cp.order = idx + 1;
        return cp;
      })
      .filter(Boolean);
    checkpoints = sorted;
    render();
  }

  if (addBtn) {
    addBtn.addEventListener('click', () => {
      openEditor(null, null);
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
          render();
          closeEditor();
        })
        .catch(() => {});
    });
  }

  if (editToggle) {
    editToggle.addEventListener('click', () => {
      isEditMode = !isEditMode;
      applyEditMode();
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


