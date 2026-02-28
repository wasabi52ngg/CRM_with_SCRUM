// Main app initialization
document.addEventListener('DOMContentLoaded', () => {
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

function getCsrfToken() {
  const name = 'csrftoken=';
  const parts = document.cookie.split(';');
  for (let c of parts) {
    c = c.trim();
    if (c.startsWith(name)) return c.substring(name.length);
  }
  return '';
}


