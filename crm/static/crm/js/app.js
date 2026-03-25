// Main app initialization
document.addEventListener('DOMContentLoaded', () => {
  // Kanban drag & drop
  const cols = document.querySelectorAll('[data-col]');
  let dragged = null;

  document.querySelectorAll('.task[data-task]').forEach(card => {
    const isDraggable = card.getAttribute('draggable') === 'true';
    card.draggable = isDraggable;
    if (!isDraggable) return;
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
        body: JSON.stringify({
          id: taskId,
          status: newStatus,
          sprint:
            window.__boardSprintIdForMove != null && window.__boardSprintIdForMove !== ''
              ? window.__boardSprintIdForMove
              : window.__activeSprintId || null,
        })
      })
        .then(r => r.json())
        .then(resp => {
          if (!resp.ok && resp.error === 'dependency_not_done') {
            alert('Нельзя перевести задачу в статус «Готово», пока блокирующая задача не завершена.');
            // Откатываем визуальное перемещение
            window.location.reload();
          }
        })
        .catch(() => {});
    });
  });

  // Kanban task panel (details/checkpoints/chat) — выезжающая панель как «Планирование»
  if (document.getElementById('kanban-task-drawer')) {
    initKanbanTaskPanel();
  }

  // Kanban extras: create modal, filters, list view, inline edit
  if (document.querySelector('.kanban-wrap')) {
    initKanbanExtras();
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

  initNotifications();
});

function initNotifications() {
  const btn = document.getElementById('header-notify-btn');
  const badge = document.getElementById('header-notify-badge');
  const dropdown = document.getElementById('header-notify-dropdown');
  const listEl = document.getElementById('header-notify-list');
  const markAll = document.getElementById('header-notify-mark-all');
  const wrap = document.getElementById('header-notify-wrap');
  if (!btn || !badge || !dropdown || !listEl) return;

  function renderList(items) {
    listEl.innerHTML = '';
    if (!items || !items.length) {
      const li = document.createElement('li');
      li.className = 'header-notify-empty';
      li.textContent = 'Пока нет уведомлений';
      listEl.appendChild(li);
      return;
    }
    items.forEach(it => {
      const li = document.createElement('li');
      li.className = 'header-notify-item' + (it.read_at ? ' header-notify-item--read' : '');
      const a = document.createElement('a');
      a.className = 'header-notify-item__link';
      a.href = it.link_url || '#';
      const title = document.createElement('div');
      title.className = 'header-notify-item__title';
      title.textContent = it.title;
      a.appendChild(title);
      if (it.body) {
        const body = document.createElement('div');
        body.className = 'header-notify-item__body';
        body.textContent = it.body;
        a.appendChild(body);
      }
      li.appendChild(a);
      listEl.appendChild(li);
    });
  }

  async function refresh() {
    try {
      const r = await fetch('/notifications/api/?limit=20', { credentials: 'same-origin' });
      const d = await r.json();
      if (!d.ok) return;
      const n = d.unread_count || 0;
      badge.textContent = n > 99 ? '99+' : String(n);
      badge.hidden = n === 0;
      renderList(d.items || []);
    } catch (e) {
      /* ignore */
    }
  }

  btn.addEventListener('click', e => {
    e.stopPropagation();
    const open = dropdown.hidden;
    dropdown.hidden = !open;
    if (!dropdown.hidden) refresh();
  });
  if (markAll) {
    markAll.addEventListener('click', async e => {
      e.preventDefault();
      e.stopPropagation();
      try {
        await fetch('/notifications/api/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
          body: JSON.stringify({ action: 'mark_all_read' }),
          credentials: 'same-origin',
        });
      } catch (err) {
        /* ignore */
      }
      refresh();
    });
  }
  document.addEventListener('click', () => {
    dropdown.hidden = true;
  });
  if (wrap) {
    wrap.addEventListener('click', e => e.stopPropagation());
  }
  refresh();
  setInterval(refresh, 60000);
}

function initKanbanTaskPanel() {
  const drawer = document.getElementById('kanban-task-drawer');
  if (!drawer) return;

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
  const activityList = document.getElementById('tp-activity-list');

  let currentTaskId = null;
  let apiUrl = null;
  let checkpoints = [];
  let chat = [];
  let activity = [];

  function show() {
    const planning = document.getElementById('kanban-planning-drawer');
    if (planning && planning.classList.contains('kanban-drawer--open')) {
      planning.classList.remove('kanban-drawer--open');
      planning.setAttribute('aria-hidden', 'true');
    }
    drawer.classList.add('kanban-drawer--open');
    drawer.setAttribute('aria-hidden', 'false');
    document.body.classList.add('kanban-drawer-lock');
  }
  function hide() {
    drawer.classList.remove('kanban-drawer--open');
    drawer.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('kanban-drawer-lock');
    currentTaskId = null;
    apiUrl = null;
    if (typeof hideCpAddForm === 'function') hideCpAddForm();
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
      badge.textContent = cp.is_done ? 'готово' : 'не готово';
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
      const row = document.createElement('div');
      row.className = 'tp-msg';
      const avWrap = document.createElement('div');
      avWrap.className = 'tp-msg__avatar-wrap';
      if (m.author_photo_url) {
        const img = document.createElement('img');
        img.className = 'user-avatar user-avatar--img';
        img.src = m.author_photo_url;
        img.alt = '';
        img.width = 36;
        img.height = 36;
        avWrap.appendChild(img);
      } else {
        const ph = document.createElement('span');
        ph.className = 'user-avatar user-avatar--placeholder';
        ph.style.width = '36px';
        ph.style.height = '36px';
        ph.style.fontSize = '15px';
        ph.style.minWidth = '36px';
        ph.textContent = m.author_initial || (m.author__username || '?')[0].toUpperCase();
        avWrap.appendChild(ph);
      }
      const body = document.createElement('div');
      body.className = 'tp-msg__body';
      const meta = document.createElement('div');
      meta.className = 'tp-msg__meta';
      const author = document.createElement('div');
      author.textContent = m.author__username || 'user';
      const time = document.createElement('div');
      time.textContent = (m.created_at || '').toString().slice(0, 16).replace('T', ' ');
      meta.appendChild(author);
      meta.appendChild(time);
      const text = document.createElement('div');
      text.className = 'tp-msg__text';
      text.textContent = m.text;
      body.appendChild(meta);
      body.appendChild(text);
      row.appendChild(avWrap);
      row.appendChild(body);
      chatList.appendChild(row);
    });
  }

  function renderActivity() {
    if (!activityList) return;
    activityList.innerHTML = '';
    activity.forEach(a => {
      const item = document.createElement('div');
      item.className = 'tp-activity-item';
      const meta = document.createElement('div');
      meta.className = 'tp-activity-item__meta';
      const who = document.createElement('div');
      who.textContent = a.author__username || 'system';
      const when = document.createElement('div');
      when.textContent = (a.created_at || '').toString().slice(0, 16).replace('T', ' ');
      meta.appendChild(who);
      meta.appendChild(when);
      const text = document.createElement('div');
      text.className = 'tp-activity-item__text';
      text.textContent = a.text || '';
      item.appendChild(meta);
      item.appendChild(text);
      activityList.appendChild(item);
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
    hideCpAddForm();
    currentTaskId = taskId;
    apiUrl = `/manager/tasks/${taskId}/panel/`;
    show();
    setActiveTab('checkpoints');
    return apiRequest({ action: 'detail' }).then(resp => {
      if (!resp.ok) return;
      const t = resp.task;
      if (titleEl) titleEl.textContent = t.title;
      if (metaEl) metaEl.textContent = `${t.task_type_label} • ${t.status_label}${t.priority_label ? ' • ' + t.priority_label : ''}`;
      const issueEl = document.getElementById('tp-issue-key');
      const descPrev = document.getElementById('tp-desc-preview');
      if (issueEl) issueEl.textContent = t.issue_key ? `Ключ: ${t.issue_key}` : '';
      if (descPrev) {
        let block = '';
        if (t.description) block += t.description;
        if (t.acceptance_criteria) block += (block ? '\n\n' : '') + 'Критерии приёмки:\n' + t.acceptance_criteria;
        descPrev.textContent = block.trim();
      }
      if (assigneeEl) assigneeEl.textContent = t.assignee || '—';
      if (createdByEl) createdByEl.textContent = t.created_by || '—';
      if (dueEl) dueEl.textContent = t.due_date || '—';
      if (spEl) spEl.textContent = String(t.story_points ?? 0);
      const sprintEl = document.getElementById('tp-sprint');
      const statusEl = document.getElementById('tp-status');
      const assigneeSelect = document.getElementById('tp-assignee-select');
      const dueInput = document.getElementById('tp-due-input');
      const spInput = document.getElementById('tp-sp-input');
      const sprintSelect = document.getElementById('tp-sprint-select');
      if (sprintEl) sprintEl.textContent = t.sprint_name || 'Беклог';
      if (statusEl) statusEl.textContent = t.status_label || '';
      if (assigneeSelect) assigneeSelect.value = t.assignee_id ? String(t.assignee_id) : '';
      if (dueInput) dueInput.value = t.due_date || '';
      if (spInput) spInput.value = String(t.story_points ?? 0);
      if (sprintSelect) sprintSelect.value = t.sprint_id ? String(t.sprint_id) : '';
      const epicEl = document.getElementById('tp-epic');
      const epicSelect = document.getElementById('tp-epic-select');
      if (epicEl) epicEl.textContent = t.epic_title || '—';
      if (epicSelect) epicSelect.value = t.epic_id ? String(t.epic_id) : '';
      checkpoints = resp.checkpoints || [];
      chat = resp.chat || [];
      activity = resp.activity || [];
      renderCheckpoints();
      renderChat();
      renderActivity();
      const extraChat = document.getElementById('tp-chat-extra');
      if (extraChat && (resp.links || resp.children || resp.watchers)) {
        extraChat.innerHTML = '';
        if (resp.links && resp.links.length) {
          const h = document.createElement('div');
          h.className = 'muted';
          h.style.marginBottom = '8px';
          h.textContent = 'Связи:';
          extraChat.appendChild(h);
          resp.links.forEach(lk => {
            const d = document.createElement('div');
            d.textContent = `${lk.link_type} → ${lk.title} (#${lk.target_id})`;
            extraChat.appendChild(d);
          });
        }
        if (resp.children && resp.children.length) {
          const h2 = document.createElement('div');
          h2.className = 'muted';
          h2.style.margin = '8px 0 4px';
          h2.textContent = 'Подзадачи:';
          extraChat.appendChild(h2);
          resp.children.forEach(ch => {
            const d = document.createElement('div');
            d.textContent = `• ${ch.title}`;
            extraChat.appendChild(d);
          });
        }
        if (resp.watchers && resp.watchers.length) {
          const w = document.createElement('div');
          w.className = 'muted';
          w.style.marginTop = '8px';
          w.textContent = 'Наблюдают: ' + resp.watchers.join(', ');
          extraChat.appendChild(w);
        }
      }
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

  document.querySelectorAll('.task-row').forEach(row => {
    row.addEventListener('click', () => {
      const id = parseInt(row.getAttribute('data-task') || '0', 10);
      if (id) loadTask(id).catch(() => {});
    });
  });

  if (closeBtn) closeBtn.addEventListener('click', () => hide());
  const taskDrawerBackdrop = document.getElementById('kanban-task-backdrop');
  if (taskDrawerBackdrop) taskDrawerBackdrop.addEventListener('click', () => hide());
  tabBtns.forEach(btn => btn.addEventListener('click', () => setActiveTab(btn.getAttribute('data-tab'))));

  const cpAddForm = document.getElementById('tp-cp-add-form');
  const cpAddInput = document.getElementById('tp-cp-add-input');
  const cpAddSubmit = document.getElementById('tp-cp-add-submit');
  const cpAddCancel = document.getElementById('tp-cp-add-cancel');

  function showCpAddForm() {
    if (!cpAddForm || !cpAddInput) return;
    cpAddForm.classList.remove('tp-cp-add-form--hidden');
    cpAddInput.value = '';
    cpAddInput.focus();
  }

  function hideCpAddForm() {
    if (cpAddForm) cpAddForm.classList.add('tp-cp-add-form--hidden');
  }

  function submitCpAdd() {
    const title = (cpAddInput && cpAddInput.value || '').trim();
    if (!title) return;
    hideCpAddForm();
    apiRequest({ action: 'checkpoint_create', title, comment: '' })
      .then(resp => {
        if (!resp.ok) return;
        checkpoints.push(resp.checkpoint);
        renderCheckpoints();
      })
      .catch(() => {});
  }

  if (cpAddBtn) {
    cpAddBtn.addEventListener('click', () => {
      if (!apiUrl) return;
      showCpAddForm();
    });
  }

  if (cpAddSubmit) cpAddSubmit.addEventListener('click', submitCpAdd);
  if (cpAddCancel) cpAddCancel.addEventListener('click', hideCpAddForm);
  if (cpAddInput) {
    cpAddInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); submitCpAdd(); }
      if (e.key === 'Escape') { e.preventDefault(); hideCpAddForm(); }
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

  function saveTaskField(field, value) {
    if (!apiUrl || !currentTaskId) return;
    const payload = { action: 'task_update' };
    payload[field] = value;
    apiRequest(payload).then(resp => {
      if (!resp.ok && resp.error === 'dependency_not_done') {
        alert('Нельзя перевести задачу в статус «Готово», пока блокирующая задача не завершена.');
        return;
      }
      if (resp.ok) loadTask(currentTaskId);
    }).catch(() => {});
  }

  document.querySelectorAll('.task-panel__row--editable').forEach(row => {
    const field = row.getAttribute('data-field');
    const valueEl = row.querySelector('.tp-value');
    const inputEl = row.querySelector('.tp-edit-input, .tp-edit-select');
    if (!valueEl || !inputEl) return;
    row.addEventListener('click', (e) => {
      if (e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT') return;
      valueEl.style.display = 'none';
      inputEl.style.display = 'block';
      inputEl.focus();
    });
    const finishEdit = () => {
      valueEl.style.display = '';
      inputEl.style.display = 'none';
      if (field === 'assignee') {
        const v = inputEl.value;
        saveTaskField('assignee', v || null);
        const opt = inputEl.selectedOptions[0];
        valueEl.textContent = (opt && v) ? opt.text : '—';
      } else if (field === 'status') {
        const v = inputEl.value;
        saveTaskField('status', v || null);
        const opt = inputEl.selectedOptions[0];
        valueEl.textContent = (opt && v) ? opt.text : '';
      } else if (field === 'sprint') {
        const v = inputEl.value;
        saveTaskField('sprint', v || null);
        const opt = inputEl.selectedOptions[0];
        valueEl.textContent = (opt && v) ? opt.text : 'Беклог';
      } else if (field === 'epic_id') {
        const v = inputEl.value;
        saveTaskField('epic_id', v === '' ? null : parseInt(v, 10));
        const opt = inputEl.selectedOptions[0];
        valueEl.textContent = (opt && v) ? opt.text : '—';
      } else if (field === 'due_date') {
        saveTaskField('due_date', inputEl.value || null);
        valueEl.textContent = inputEl.value || '—';
      } else if (field === 'story_points') {
        saveTaskField('story_points', parseInt(inputEl.value, 10) || 0);
        valueEl.textContent = inputEl.value || '0';
      }
    };
    inputEl.addEventListener('change', finishEdit);
    inputEl.addEventListener('blur', finishEdit);
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); finishEdit(); }
      if (e.key === 'Escape') { valueEl.style.display = ''; inputEl.style.display = 'none'; }
    });
  });

  const params = new URLSearchParams(window.location.search);
  const openFromUrl = parseInt(params.get('task') || '0', 10);
  if (openFromUrl) {
    loadTask(openFromUrl).catch(() => {});
  }
}

function initRequestTimeline(root) {
  const apiUrl = root.getAttribute('data-api-url');
  const scriptEl = document.getElementById('cp-data');
  const edgesScriptEl = document.getElementById('cp-edges-data');
  let checkpoints = [];
  let edges = [];
  if (scriptEl) {
    try {
      checkpoints = JSON.parse(scriptEl.textContent);
    } catch (e) {
      checkpoints = [];
    }
  }
  if (edgesScriptEl) {
    try {
      edges = JSON.parse(edgesScriptEl.textContent);
    } catch (e) {
      edges = [];
    }
  }

  const isDiagram = root.classList.contains('cp-diagram');
  const editor = document.getElementById('cp-editor');
  const form = document.getElementById('cp-editor-form');
  const addBtn = document.getElementById('cp-add-btn');
  const deleteBtn = document.getElementById('cp-delete-btn');
  const closeBtn = document.getElementById('cp-editor-close');
  const editToggle = document.getElementById('cp-edit-toggle');

  let isEditMode = false;
  let selectedEdgeId = null;

  let diagramZoom = 1;
  let diagramPanX = 0;
  let diagramPanY = 0;

  const NODE_WIDTH = 200;
  const NODE_HEIGHT = 44;
  const ZOOM_MIN = 0.25;
  const ZOOM_MAX = 2;
  const ZOOM_STEP = 0.15;

  function applyEditMode() {
    const actions = document.querySelector('.cp-editor-actions');
    if (!actions) return;
    actions.style.display = isEditMode ? 'flex' : 'none';
  }

  function getNodeCenter(cp) {
    const x = typeof cp.x === 'number' ? cp.x : 0;
    const y = typeof cp.y === 'number' ? cp.y : 0;
    return { x: x + NODE_WIDTH / 2, y: y + NODE_HEIGHT / 2 };
  }

  function edgePathD(sourceCp, targetCp) {
    const s = getNodeCenter(sourceCp);
    const t = getNodeCenter(targetCp);
    const dx = t.x - s.x;
    const dy = t.y - s.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const curvature = Math.min(40, dist * 0.3);
    const cpx = (s.x + t.x) / 2 - (dy / dist) * curvature;
    const cpy = (s.y + t.y) / 2 + (dx / dist) * curvature;
    return `M ${s.x} ${s.y} Q ${cpx} ${cpy} ${t.x} ${t.y}`;
  }

  function redrawEdges() {
    const svg = root.querySelector('.cp-diagram__edges');
    if (!svg) return;
    const pathMap = new Map();
    checkpoints.forEach(c => pathMap.set(c.id, c));
    edges.forEach(edge => {
      const pathEl = svg.querySelector(`[data-edge-id="${edge.id}"]`);
      if (!pathEl) return;
      const src = pathMap.get(edge.source_id);
      const tgt = pathMap.get(edge.target_id);
      if (src && tgt) pathEl.setAttribute('d', edgePathD(src, tgt));
    });
  }

  function getDiagramViewport() {
    return root.querySelector('.cp-diagram__viewport');
  }

  function getDiagramTransformEl() {
    return root.querySelector('.cp-diagram__transform');
  }

  function getDiagramWrap() {
    return root.querySelector('.cp-diagram__wrap');
  }

  function applyDiagramTransform() {
    const el = getDiagramTransformEl();
    if (el) {
      el.style.transform = `translate(${diagramPanX}px, ${diagramPanY}px) scale(${diagramZoom})`;
    }
    const val = root.querySelector('.cp-diagram__zoom-value');
    if (val) val.textContent = Math.round(diagramZoom * 100) + '%';
  }

  function updateWrapSize() {
    const wrap = getDiagramWrap();
    const transformEl = getDiagramTransformEl();
    if (!wrap || !transformEl) return;
    let maxRight = 600, maxBottom = 280;
    checkpoints.forEach(cp => {
      const x = typeof cp.x === 'number' ? cp.x : 0;
      const y = typeof cp.y === 'number' ? cp.y : 0;
      if (x + NODE_WIDTH + 80 > maxRight) maxRight = x + NODE_WIDTH + 80;
      if (y + NODE_HEIGHT + 80 > maxBottom) maxBottom = y + NODE_HEIGHT + 80;
    });
    wrap.style.width = maxRight + 'px';
    wrap.style.height = maxBottom + 'px';
    wrap.style.minWidth = maxRight + 'px';
    wrap.style.minHeight = maxBottom + 'px';
    transformEl.style.width = maxRight + 'px';
    transformEl.style.height = maxBottom + 'px';
  }

  function diagramFitAll() {
    const viewport = getDiagramViewport();
    if (!viewport || checkpoints.length === 0) return;
    const rect = viewport.getBoundingClientRect();
    let minX = 0, minY = 0, maxX = 0, maxY = 0;
    checkpoints.forEach(cp => {
      const x = typeof cp.x === 'number' ? cp.x : 0;
      const y = typeof cp.y === 'number' ? cp.y : 0;
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x + NODE_WIDTH > maxX) maxX = x + NODE_WIDTH;
      if (y + NODE_HEIGHT > maxY) maxY = y + NODE_HEIGHT;
    });
    const pad = 40;
    const contentW = Math.max(maxX - minX + pad * 2, 200);
    const contentH = Math.max(maxY - minY + pad * 2, 200);
    diagramZoom = Math.min(rect.width / contentW, rect.height / contentH, ZOOM_MAX);
    diagramZoom = Math.max(diagramZoom, ZOOM_MIN);
    diagramPanX = pad - minX * diagramZoom;
    diagramPanY = pad - minY * diagramZoom;
    applyDiagramTransform();
    const val = root.querySelector('.cp-diagram__zoom-value');
    if (val) val.textContent = Math.round(diagramZoom * 100) + '%';
  }

  function renderDiagram() {
    root.innerHTML = '';

    const viewport = document.createElement('div');
    viewport.className = 'cp-diagram__viewport';

    const zoomPan = document.createElement('div');
    zoomPan.className = 'cp-diagram__zoom-pan cp-diagram__zoom-pan--grab';

    const transformEl = document.createElement('div');
    transformEl.className = 'cp-diagram__transform';

    const wrap = document.createElement('div');
    wrap.className = 'cp-diagram__wrap';

    const bg = document.createElement('div');
    bg.className = 'cp-diagram__bg';

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'cp-diagram__edges cp-diagram__edges--interactive');
    svg.setAttribute('aria-hidden', 'true');
    edges.forEach(edge => {
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      const src = checkpoints.find(c => c.id === edge.source_id);
      const tgt = checkpoints.find(c => c.id === edge.target_id);
      path.setAttribute('d', (src && tgt) ? edgePathD(src, tgt) : 'M 0 0');
      path.setAttribute('class', 'cp-edge-path');
      path.setAttribute('data-edge-id', edge.id);
      path.setAttribute('data-source-id', edge.source_id);
      path.setAttribute('data-target-id', edge.target_id);
      path.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedEdgeId = edge.id;
        root.querySelectorAll('.cp-edge-path').forEach(p => p.classList.remove('cp-edge-path--selected'));
        path.classList.add('cp-edge-path--selected');
        openEdgeEditor(edge);
      });
      svg.appendChild(path);
    });
    wrap.appendChild(svg);

    const nodesWrap = document.createElement('div');
    nodesWrap.className = 'cp-diagram__nodes';

    checkpoints.forEach((cp, index) => {
      let x = typeof cp.x === 'number' ? cp.x : index * (NODE_WIDTH + 40);
      let y = typeof cp.y === 'number' ? cp.y : index * (NODE_HEIGHT + 24);
      if (index > 0 && cp.x === 0 && cp.y === 0) {
        x = index * (NODE_WIDTH + 40);
        y = 0;
      }
      cp.x = x;
      cp.y = y;

      const node = document.createElement('div');
      node.className = 'cp-node' + (cp.is_done ? ' cp-node--done' : '');
      node.setAttribute('data-id', cp.id);
      node.style.left = cp.x + 'px';
      node.style.top = cp.y + 'px';

      const dot = document.createElement('div');
      dot.className = 'cp-dot';
      const label = document.createElement('div');
      label.className = 'cp-label';
      label.textContent = cp.title || `Этап ${index + 1}`;
      node.appendChild(dot);
      node.appendChild(label);
      nodesWrap.appendChild(node);

      node.addEventListener('click', (e) => {
        if (e.target.closest('.cp-editor')) return;
        e.stopPropagation();
        selectedEdgeId = null;
        root.querySelectorAll('.cp-edge-path').forEach(p => p.classList.remove('cp-edge-path--selected'));
        root.querySelectorAll('.cp-node').forEach(n => n.classList.remove('cp-node--active'));
        node.classList.add('cp-node--active');
        openEditor(cp, node);
      });

      node.addEventListener('mousedown', (e) => {
        if (e.button !== 0 || e.target.closest('a, button')) return;
        e.stopPropagation();
        const dragStartX = e.clientX;
        const dragStartY = e.clientY;
        const nodeStartX = cp.x;
        const nodeStartY = cp.y;
        const onMove = (e2) => {
          const screenDx = e2.clientX - dragStartX;
          const screenDy = e2.clientY - dragStartY;
          cp.x = Math.max(0, nodeStartX + screenDx / diagramZoom);
          cp.y = Math.max(0, nodeStartY + screenDy / diagramZoom);
          node.style.left = cp.x + 'px';
          node.style.top = cp.y + 'px';
          redrawEdges();
          updateWrapSize();
        };
        const onUp = () => {
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup', onUp);
          fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
            body: JSON.stringify({ action: 'position', id: cp.id, x: cp.x, y: cp.y }),
          }).catch(() => {});
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
      });
    });

    wrap.appendChild(nodesWrap);
    wrap.insertBefore(bg, wrap.firstChild);

    transformEl.appendChild(wrap);
    zoomPan.appendChild(transformEl);
    viewport.appendChild(zoomPan);

    const toolbar = document.createElement('div');
    toolbar.className = 'cp-diagram__zoom-toolbar';
    toolbar.innerHTML = '<button type="button" class="cp-zoom-out" title="Уменьшить">−</button><span class="cp-diagram__zoom-value">100%</span><button type="button" class="cp-zoom-in" title="Увеличить">+</button><button type="button" class="cp-zoom-fit" title="Вместить всё">⊡</button>';
    viewport.appendChild(toolbar);

    root.appendChild(viewport);

    updateWrapSize();
    applyDiagramTransform();

    zoomPan.addEventListener('wheel', (e) => {
      e.preventDefault();
      const vp = getDiagramViewport();
      if (!vp) return;
      const r = vp.getBoundingClientRect();
      const cx = e.clientX - r.left - diagramPanX;
      const cy = e.clientY - r.top - diagramPanY;
      const contentX = cx / diagramZoom;
      const contentY = cy / diagramZoom;
      const prevZoom = diagramZoom;
      if (e.deltaY < 0) diagramZoom = Math.min(ZOOM_MAX, diagramZoom + ZOOM_STEP);
      else diagramZoom = Math.max(ZOOM_MIN, diagramZoom - ZOOM_STEP);
      diagramPanX = e.clientX - r.left - contentX * diagramZoom;
      diagramPanY = e.clientY - r.top - contentY * diagramZoom;
      applyDiagramTransform();
    }, { passive: false });

    let panStartX = 0, panStartY = 0, panStartPanX = 0, panStartPanY = 0;
    function startPan(e) {
      if (e.button !== 0) return;
      if (e.target.closest('.cp-node') || e.target.closest('.cp-edge-path')) return;
      e.preventDefault();
      panStartX = e.clientX;
      panStartY = e.clientY;
      panStartPanX = diagramPanX;
      panStartPanY = diagramPanY;
      zoomPan.classList.remove('cp-diagram__zoom-pan--grab');
      zoomPan.classList.add('cp-diagram__zoom-pan--grabbing');
      const onMove = (e2) => {
        diagramPanX = panStartPanX + (e2.clientX - panStartX);
        diagramPanY = panStartPanY + (e2.clientY - panStartY);
        applyDiagramTransform();
      };
      const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        zoomPan.classList.remove('cp-diagram__zoom-pan--grabbing');
        zoomPan.classList.add('cp-diagram__zoom-pan--grab');
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    }
    bg.addEventListener('mousedown', startPan);
    zoomPan.addEventListener('mousedown', (e) => {
      if (e.target === zoomPan || e.target === transformEl || e.target === wrap || e.target === svg) startPan(e);
    });

    toolbar.querySelector('.cp-zoom-out').addEventListener('click', () => {
      diagramZoom = Math.max(ZOOM_MIN, diagramZoom - ZOOM_STEP);
      applyDiagramTransform();
    });
    toolbar.querySelector('.cp-zoom-in').addEventListener('click', () => {
      diagramZoom = Math.min(ZOOM_MAX, diagramZoom + ZOOM_STEP);
      applyDiagramTransform();
    });
    toolbar.querySelector('.cp-zoom-fit').addEventListener('click', () => diagramFitAll());
  }

  function openEdgeEditor(edge) {
    const el = document.getElementById('cp-edge-editor');
    if (!el) return;
    el.classList.remove('cp-editor--hidden');
    const src = checkpoints.find(c => c.id === edge.source_id);
    const tgt = checkpoints.find(c => c.id === edge.target_id);
    el.querySelector('.cp-edge-editor__text').textContent =
      `Связь: «${src ? src.title : '?'}» → «${tgt ? tgt.title : '?'}»`;
    el.querySelector('.cp-edge-editor__delete').dataset.edgeId = edge.id;
  }

  function renderLegacy() {
    root.innerHTML = '';
    const list = document.createElement('div');
    list.className = 'cp-points';
    const sorted = checkpoints.slice().sort(
      (a, b) => (a.order || 0) - (b.order || 0) || a.id - b.id,
    );
    sorted.forEach((cp, index) => {
      const item = document.createElement('div');
      item.className = 'cp-point' + (index === 0 ? ' cp-point--first' : '');
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
      item.addEventListener('click', (e) => {
        if (e.target.closest('.cp-editor')) return;
        e.stopPropagation();
        openEditor(cp, item);
        root.querySelectorAll('.cp-dot').forEach(d => d.classList.remove('cp-dot--active'));
        dot.classList.add('cp-dot--active');
      });
    });
    root.appendChild(list);
    let dragSrc = null;
    let draggedDot = null;
    list.querySelectorAll('.cp-point').forEach(el => {
      el.addEventListener('dragstart', (e) => {
        dragSrc = el;
        draggedDot = el.querySelector('.cp-dot');
        if (draggedDot) draggedDot.classList.add('cp-dot--dragging');
        e.dataTransfer.effectAllowed = 'move';
      });
      el.addEventListener('dragover', (e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; });
      el.addEventListener('drop', (e) => {
        e.preventDefault();
        if (!dragSrc || dragSrc === el) return;
        const children = Array.from(list.children);
        const srcIndex = children.indexOf(dragSrc);
        const targetIndex = children.indexOf(el);
        list.insertBefore(dragSrc, srcIndex < targetIndex ? el.nextSibling : el);
        Array.from(list.children).forEach((child, idx) => {
          child.setAttribute('data-index', idx);
          child.classList.toggle('cp-point--first', idx === 0);
        });
        saveOrder(list);
      });
      el.addEventListener('dragend', () => {
        if (draggedDot) draggedDot.classList.remove('cp-dot--dragging');
        dragSrc = null;
        draggedDot = null;
      });
    });
  }

  function render() {
    if (isDiagram) renderDiagram();
    else renderLegacy();
  }

  function setFieldsDisabled(disabled) {
    const titleEl = document.getElementById('cp-title');
    const commentEl = document.getElementById('cp-comment');
    const doneEl = document.getElementById('cp-is-done');
    if (titleEl) titleEl.disabled = disabled;
    if (commentEl) commentEl.disabled = disabled;
    if (doneEl) doneEl.disabled = disabled;
  }

  function openEditor(cp, pointElement) {
    if (!editor) return;
    document.getElementById('cp-edge-editor') && document.getElementById('cp-edge-editor').classList.add('cp-editor--hidden');
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

    const addEdgeBlock = document.getElementById('cp-add-edge-block');
    const edgeTargetSelect = document.getElementById('cp-edge-target');
    if (isDiagram && addEdgeBlock && edgeTargetSelect) {
      if (cp && checkpoints.length > 1) {
        addEdgeBlock.style.display = 'block';
        edgeTargetSelect.innerHTML = '<option value="">— выберите этап —</option>';
        const existingTargets = new Set(edges.filter(e => e.source_id === cp.id).map(e => e.target_id));
        checkpoints.forEach(c => {
          if (c.id === cp.id) return;
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.textContent = (c.title || 'Этап') + (existingTargets.has(c.id) ? ' (уже связан)' : '');
          opt.disabled = existingTargets.has(c.id);
          edgeTargetSelect.appendChild(opt);
        });
      } else {
        addEdgeBlock.style.display = 'none';
      }
    }

    isEditMode = !cp;
    if (cp && !isEditMode) {
      setFieldsDisabled(true);
    } else {
      setFieldsDisabled(false);
    }
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

  function defaultNewNodePosition() {
    if (checkpoints.length === 0) return { x: 40, y: 40 };
    let maxX = 0, maxY = 0;
    checkpoints.forEach(c => {
      const x = typeof c.x === 'number' ? c.x : 0;
      const y = typeof c.y === 'number' ? c.y : 0;
      if (x + NODE_WIDTH > maxX) maxX = x + NODE_WIDTH;
      if (y + NODE_HEIGHT > maxY) maxY = y + NODE_HEIGHT;
    });
    return { x: maxX + 30, y: 40 };
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
    if (!id && isDiagram) {
      const pos = defaultNewNodePosition();
      payload.x = pos.x;
      payload.y = pos.y;
    }

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
          isEditMode = false;
          setFieldsDisabled(true);
          applyEditMode();
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
          isEditMode = false;
          setFieldsDisabled(true);
          applyEditMode();
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
      setFieldsDisabled(!isEditMode);
      applyEditMode();
    });
  }

  if (form) {
    form.addEventListener('submit', e => {
      e.preventDefault();
      updateFromForm();
    });
  }

  const edgeEditorClose = document.getElementById('cp-edge-editor-close');
  const edgeDeleteBtn = document.getElementById('cp-edge-delete-btn');
  if (edgeEditorClose) {
    edgeEditorClose.addEventListener('click', () => {
      document.getElementById('cp-edge-editor').classList.add('cp-editor--hidden');
      selectedEdgeId = null;
      root.querySelectorAll('.cp-edge-path').forEach(p => p.classList.remove('cp-edge-path--selected'));
    });
  }
  if (edgeDeleteBtn) {
    edgeDeleteBtn.addEventListener('click', () => {
      const edgeId = edgeDeleteBtn.dataset.edgeId;
      if (!edgeId) return;
      fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify({ action: 'edge_delete', id: parseInt(edgeId, 10) }),
      })
        .then(r => r.json())
        .then(resp => {
          if (resp.ok) {
            edges = edges.filter(e => e.id !== parseInt(edgeId, 10));
            render();
            document.getElementById('cp-edge-editor').classList.add('cp-editor--hidden');
          }
        })
        .catch(() => {});
    });
  }

  const edgeCreateBtn = document.getElementById('cp-edge-create-btn');
  if (edgeCreateBtn) {
    edgeCreateBtn.addEventListener('click', () => {
      const idEl = document.getElementById('cp-id');
      const edgeTargetSelect = document.getElementById('cp-edge-target');
      const sourceId = idEl ? parseInt(idEl.value || '0', 10) : 0;
      const targetId = edgeTargetSelect ? parseInt(edgeTargetSelect.value || '0', 10) : 0;
      if (!sourceId || !targetId || sourceId === targetId) return;
      if (edges.some(e => e.source_id === sourceId && e.target_id === targetId)) return;
      fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify({ action: 'edge_create', source_id: sourceId, target_id: targetId }),
      })
        .then(r => r.json())
        .then(resp => {
          if (resp.ok && resp.edge) {
            edges.push(resp.edge);
            render();
            const cp = findCheckpoint(sourceId);
            const node = root.querySelector(`[data-id="${sourceId}"]`);
            openEditor(cp, node);
          }
        })
        .catch(() => {});
    });
  }

  render();
}

function initKanbanExtras() {
  const projectId = window.__kanbanProjectId;
  if (!projectId) return;

  const board = document.getElementById('kanban-board');
  const listView = document.getElementById('kanban-list-view');
  const filterAssignee = document.getElementById('kanban-filter-assignee');
  const filterType = document.getElementById('kanban-filter-type');
  const viewBtns = document.querySelectorAll('.kanban-view-btn');
  const modal = document.getElementById('task-create-modal');
  const modalClose = modal && modal.querySelector('.modal__close');
  const modalCancel = modal && modal.querySelector('.modal__cancel');
  const modalBackdrop = modal && modal.querySelector('.modal__backdrop');
  const createForm = document.getElementById('task-create-form');
  const statusInput = document.getElementById('task-create-status');
  const presetSelect = document.getElementById('kanban-preset-select');
  const savePresetBtn = document.getElementById('kanban-save-preset');
  const configToggleBtn = document.getElementById('kanban-config-toggle');
  const configPanel = document.getElementById('kanban-config-panel');

  let quickAssigneeFilter = null; // 'my' | 'unassigned' | null
  let quickOverdueFilter = false;

  function updateQuickFilterButtons() {
    document.querySelectorAll('.kanban-quick-filter').forEach(b => {
      const type = b.getAttribute('data-qf');
      const active =
        (type === 'my' && quickAssigneeFilter === 'my') ||
        (type === 'unassigned' && quickAssigneeFilter === 'unassigned') ||
        (type === 'overdue' && quickOverdueFilter);
      b.classList.toggle('kanban-quick-filter--active', active);
    });
  }

  function applyFilters() {
    const assigneeVal = filterAssignee ? filterAssignee.value : '';
    const typeVal = filterType ? filterType.value : '';
    const currentUserId = window.__currentUserId ? String(window.__currentUserId) : '';
    const now = new Date().toISOString().slice(0, 10);
    const cards = document.querySelectorAll('.task[data-task]');
    const rows = document.querySelectorAll('.task-row');

    cards.forEach(card => {
      const a = card.getAttribute('data-assignee') || '';
      const t = card.getAttribute('data-task-type') || '';
      const due = card.getAttribute('data-due') || '';
      let matchA = !assigneeVal || a === assigneeVal;
      let matchT = !typeVal || t === typeVal;

      // Быстрые фильтры по исполнителю
      if (quickAssigneeFilter === 'my' && currentUserId) {
        matchA = a === currentUserId;
      } else if (quickAssigneeFilter === 'unassigned') {
        matchA = !a;
      }

      // Быстрый фильтр просроченных
      if (quickOverdueFilter) {
        if (due) {
          matchT = matchT && due < now;
        } else {
          matchT = false;
        }
      }

      card.style.display = matchA && matchT ? '' : 'none';
    });

    // Те же правила для строк в списочном представлении
    rows.forEach(row => {
      const a = row.getAttribute('data-assignee') || '';
      const t = row.getAttribute('data-task-type') || '';
      // В списочном виде дедлайн берём из текста ячейки сложнее, поэтому учитываем только тип/исполнителя + быстрые по исполнителю
      let matchA = !assigneeVal || a === assigneeVal;
      let matchT = !typeVal || t === typeVal;

      if (quickAssigneeFilter === 'my' && currentUserId) {
        matchA = a === currentUserId;
      } else if (quickAssigneeFilter === 'unassigned') {
        matchA = !a;
      }

      // Просроченность в табличном виде не проверяем, чтобы не разбирать дату из HTML
      row.style.display = matchA && matchT ? '' : 'none';
    });
  }

  function updateCounts() {
    if (!board) return;
    board.querySelectorAll('.col').forEach(col => {
      const status = col.getAttribute('data-col');
      const list = col.querySelector('[data-list]');
      if (!list || !status) return;
      const tasks = Array.from(list.querySelectorAll('.task'));
      const visible = tasks.filter(t => t.style.display !== 'none').length;
      const spSum = tasks
        .filter(t => t.style.display !== 'none')
        .reduce((acc, t) => {
          const spe = t.querySelector('.task-sp');
          const n = spe ? parseInt(spe.textContent.replace(/\D/g, ''), 10) : 0;
          return acc + (Number.isFinite(n) ? n : 0);
        }, 0);
      const countEl = col.querySelector('.col-count');
      const spSumEl = col.querySelector('.col-sp');
      if (countEl) countEl.textContent = visible;
      if (spSumEl) spSumEl.textContent = `Σ SP ${spSum}`;

      const wipLimit = parseInt(col.getAttribute('data-wip') || '0', 10);
      if (wipLimit > 0 && visible > wipLimit) {
        col.classList.add('col--wip-over');
      } else {
        col.classList.remove('col--wip-over');
      }
    });
  }

  if (filterAssignee) filterAssignee.addEventListener('change', () => { applyFilters(); updateCounts(); });
  if (filterType) filterType.addEventListener('change', () => { applyFilters(); updateCounts(); });

  // Быстрые фильтры
  document.querySelectorAll('.kanban-quick-filter').forEach(btn => {
    btn.addEventListener('click', () => {
      const val = btn.getAttribute('data-qf');
      if (val === 'my') {
        quickAssigneeFilter = quickAssigneeFilter === 'my' ? null : 'my';
      } else if (val === 'unassigned') {
        quickAssigneeFilter = quickAssigneeFilter === 'unassigned' ? null : 'unassigned';
      } else if (val === 'overdue') {
        quickOverdueFilter = !quickOverdueFilter;
      }
      updateQuickFilterButtons();
      applyFilters();
      updateCounts();
    });
  });

  // Инициализируем подсчёты и WIP-подсветку при загрузке.
  applyFilters();
  updateCounts();

  // Применение сохранённого пресета
  if (presetSelect) {
    presetSelect.addEventListener('change', () => {
      const opt = presetSelect.selectedOptions[0];
      if (!opt) return;
      const a = opt.getAttribute('data-assignee') || '';
      const t = opt.getAttribute('data-type') || '';
      if (filterAssignee) filterAssignee.value = a;
      if (filterType) filterType.value = t;
      const currentUserId = window.__currentUserId ? String(window.__currentUserId) : '';
      // Восстанавливаем "Мои задачи", если пресет сохранён с текущим пользователем
      if (a && currentUserId && a === currentUserId) {
        quickAssigneeFilter = 'my';
      } else {
        quickAssigneeFilter = null;
      }
      // Пресеты сейчас не хранят отдельный флаг "просроченные", поэтому не восстанавливаем его
      quickOverdueFilter = false;
      updateQuickFilterButtons();
      applyFilters();
      updateCounts();
    });
  }

  // Сохранение текущего фильтра как пресета
  if (savePresetBtn) {
    savePresetBtn.addEventListener('click', () => {
      const name = window.prompt('Название фильтра:');
      if (!name) return;
      const assigneeVal = filterAssignee ? filterAssignee.value : '';
      const typeVal = filterType ? filterType.value : '';
      const body = new URLSearchParams();
      body.append('action', 'save_filter_preset');
      body.append('name', name);
      body.append('assignee', assigneeVal);
      body.append('task_type', typeVal);
      fetch(window.location.pathname, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': getCsrfToken(),
        },
        body: body.toString(),
      })
        .then(r => r.json())
        .then(resp => {
          if (resp.ok) {
            window.location.reload();
          }
        })
        .catch(() => {});
    });
  }

  // Тоггл панели настроек канбана
  if (configToggleBtn && configPanel) {
    configToggleBtn.addEventListener('click', () => {
      const hidden = configPanel.classList.contains('kanban-config--hidden');
      if (hidden) {
        configPanel.classList.remove('kanban-config--hidden');
      } else {
        configPanel.classList.add('kanban-config--hidden');
      }
    });
  }

  viewBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.getAttribute('data-view');
      viewBtns.forEach(b => b.classList.remove('kanban-view-btn--active'));
      btn.classList.add('kanban-view-btn--active');
      if (view === 'list') {
        if (board) board.style.display = 'none';
        if (listView) listView.style.display = 'block';
      } else {
        if (board) board.style.display = '';
        if (listView) listView.style.display = 'none';
      }
    });
  });

  function openCreateModal(status) {
    if (!modal) return;
    if (statusInput) statusInput.value = status || 'todo';
    modal.classList.remove('modal--hidden');
  }

  function closeCreateModal() {
    if (modal) modal.classList.add('modal--hidden');
  }

  const backlogAddBtn = document.querySelector('.backlog-add-btn');
  if (backlogAddBtn) {
    backlogAddBtn.addEventListener('click', () => {
      openCreateModal('todo');
    });
  }

  if (modalClose) modalClose.addEventListener('click', closeCreateModal);
  if (modalCancel) modalCancel.addEventListener('click', closeCreateModal);
  if (modalBackdrop) modalBackdrop.addEventListener('click', closeCreateModal);

  if (createForm) {
    createForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const status = statusInput ? statusInput.value : 'todo';
      const title = (document.getElementById('task-create-title')?.value || '').trim();
      const description = (document.getElementById('task-create-description')?.value || '').trim();
      const taskType = document.getElementById('task-create-type')?.value || 'fullstack';
      const assignee = document.getElementById('task-create-assignee')?.value || null;
      const dueDate = document.getElementById('task-create-due')?.value || null;
      const sp = parseInt(document.getElementById('task-create-sp')?.value || '0', 10);
      if (!title) return;
      const boardScopeEl = document.getElementById('kanban-board-scope');
      const scopeVal = boardScopeEl ? boardScopeEl.value : 'all';
      const sprintForCreate =
        scopeVal === 'active' && window.__activeSprintId ? window.__activeSprintId : undefined;
      fetch('/kanban/create/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify({
          project_id: projectId,
          status,
          title,
          description,
          task_type: taskType,
          assignee: assignee || undefined,
          due_date: dueDate || undefined,
          story_points: sp,
          sprint: sprintForCreate,
        }),
      })
        .then(r => r.json())
        .then(resp => {
          if (!resp.ok) return;
          closeCreateModal();
          createForm.reset();
          window.location.reload();
        })
        .catch(() => {});
    });
  }

  const boardScopeSelect = document.getElementById('kanban-board-scope');
  if (boardScopeSelect) {
    boardScopeSelect.addEventListener('change', () => {
      const u = new URL(window.location.href);
      u.searchParams.set('board', boardScopeSelect.value);
      window.location.href = u.toString();
    });
  }

  const epicFilterEl = document.getElementById('kanban-filter-epic');
  if (epicFilterEl) {
    epicFilterEl.addEventListener('change', () => {
      const u = new URL(window.location.href);
      const v = epicFilterEl.value;
      if (v) u.searchParams.set('epic', v);
      else u.searchParams.delete('epic');
      window.location.href = u.toString();
    });
  }

  function scrumApi(payload) {
    return fetch('/scrum/api/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
      body: JSON.stringify({ project_id: projectId, ...payload }),
    }).then(r => r.json());
  }

  const scrCreate = document.getElementById('scrum-create-sprint');
  if (scrCreate && window.__canEditSprints) {
    scrCreate.addEventListener('click', () => {
      const name = (document.getElementById('scrum-new-sprint-name')?.value || '').trim();
      if (!name) return;
      scrumApi({
        action: 'sprint_create',
        name,
        goal: (document.getElementById('scrum-new-sprint-goal')?.value || '').trim(),
        start_date: document.getElementById('scrum-new-sprint-start')?.value || null,
        end_date: document.getElementById('scrum-new-sprint-end')?.value || null,
      }).then(resp => {
        if (resp.ok) window.location.reload();
      }).catch(() => {});
    });
  }
  const scrAct = document.getElementById('scrum-activate-sprint');
  if (scrAct && window.__canEditSprints) {
    scrAct.addEventListener('click', () => {
      const sid = parseInt(document.getElementById('scrum-pick-sprint')?.value || '0', 10);
      if (!sid) return;
      scrumApi({ action: 'sprint_activate', sprint_id: sid }).then(resp => {
        if (resp.ok) window.location.reload();
      }).catch(() => {});
    });
  }
  const scrDone = document.getElementById('scrum-complete-sprint');
  if (scrDone && window.__canEditSprints) {
    scrDone.addEventListener('click', () => {
      const sid = parseInt(document.getElementById('scrum-pick-sprint')?.value || '0', 10);
      if (!sid) return;
      if (!window.confirm('Завершить спринт? Незавершённые задачи вернутся в беклог.')) return;
      scrumApi({ action: 'sprint_complete', sprint_id: sid }).then(resp => {
        if (resp.ok) window.location.reload();
      }).catch(() => {});
    });
  }
  const epicBtn = document.getElementById('scrum-create-epic');
  if (epicBtn && window.__canEditEpics) {
    epicBtn.addEventListener('click', () => {
      const title = (document.getElementById('scrum-new-epic-title')?.value || '').trim();
      if (!title) return;
      scrumApi({ action: 'epic_create', title }).then(resp => {
        if (resp.ok) window.location.reload();
      }).catch(() => {});
    });
  }

  const backlogList = document.querySelector('.backlog-list');
  if (backlogList && window.__canEditEpics) {
    let draggedBk = null;
    backlogList.querySelectorAll('.backlog-task').forEach(el => {
      el.addEventListener('dragstart', e => {
        draggedBk = el;
        e.dataTransfer.effectAllowed = 'move';
      });
      el.addEventListener('dragend', () => {
        if (!draggedBk) return;
        const ids = Array.from(backlogList.querySelectorAll('.backlog-task')).map(x =>
          parseInt(x.getAttribute('data-task'), 10)
        );
        scrumApi({ action: 'backlog_reorder', task_ids: ids }).catch(() => {});
        draggedBk = null;
      });
    });
    backlogList.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    });
    backlogList.addEventListener('drop', e => {
      e.preventDefault();
      if (!draggedBk) return;
      const after = e.target.closest('.backlog-task');
      if (!after || after === draggedBk) return;
      const rect = after.getBoundingClientRect();
      const mid = rect.top + rect.height / 2;
      if (e.clientY < mid) {
        backlogList.insertBefore(draggedBk, after);
      } else {
        backlogList.insertBefore(draggedBk, after.nextSibling);
      }
    });
  }

  const planningDrawer = document.getElementById('kanban-planning-drawer');
  const openPlanningBtn = document.getElementById('kanban-open-planning');
  const closePlanningBtn = document.getElementById('kanban-close-planning');
  const planningBackdrop = document.getElementById('kanban-planning-backdrop');
  function setPlanningDrawer(open) {
    if (!planningDrawer) return;
    if (open) {
      const taskDrawer = document.getElementById('kanban-task-drawer');
      if (taskDrawer && taskDrawer.classList.contains('kanban-drawer--open')) {
        taskDrawer.classList.remove('kanban-drawer--open');
        taskDrawer.setAttribute('aria-hidden', 'true');
      }
    }
    planningDrawer.classList.toggle('kanban-drawer--open', open);
    planningDrawer.setAttribute('aria-hidden', open ? 'false' : 'true');
    document.body.classList.toggle('kanban-drawer-lock', open);
  }
  if (openPlanningBtn) {
    openPlanningBtn.addEventListener('click', () => setPlanningDrawer(true));
  }
  if (closePlanningBtn) {
    closePlanningBtn.addEventListener('click', () => setPlanningDrawer(false));
  }
  if (planningBackdrop) {
    planningBackdrop.addEventListener('click', () => setPlanningDrawer(false));
  }
  document.querySelectorAll('[data-drawer-tab]').forEach(tab => {
    tab.addEventListener('click', () => {
      const name = tab.getAttribute('data-drawer-tab');
      document.querySelectorAll('[data-drawer-tab]').forEach(t => {
        t.classList.toggle('kanban-drawer__tab--active', t.getAttribute('data-drawer-tab') === name);
      });
      document.querySelectorAll('[data-drawer-pane]').forEach(p => {
        const show = p.getAttribute('data-drawer-pane') === name;
        p.classList.toggle('kanban-drawer__pane--hidden', !show);
      });
    });
  });

  const backlogAside = document.getElementById('kanban-backlog');
  const backlogToggleBtn = document.getElementById('kanban-backlog-toggle');
  const mainWrapEl = document.getElementById('kanban-main-wrap');
  if (backlogToggleBtn && backlogAside && mainWrapEl) {
    backlogToggleBtn.addEventListener('click', () => {
      const collapsed = mainWrapEl.classList.toggle('kanban-wrap--backlog-collapsed');
      backlogToggleBtn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      backlogToggleBtn.title = collapsed ? 'Показать беклог слева' : 'Скрыть беклог слева';
      backlogToggleBtn.classList.toggle('kanban-backlog-toggle-btn--collapsed', collapsed);
    });
  }
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


