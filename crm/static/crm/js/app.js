// Basic drag&drop for Kanban (HTML5 API)
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

  const cols = document.querySelectorAll('[data-col]');
  let dragged = null;

  document.querySelectorAll('[data-task]').forEach(card => {
    card.draggable = true;
    card.addEventListener('dragstart', e => { dragged = card; e.dataTransfer.effectAllowed = 'move'; });
    card.addEventListener('dragend', () => { dragged = null; });
  });

  cols.forEach(col => {
    col.addEventListener('dragover', e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; });
    col.addEventListener('drop', e => {
      e.preventDefault();
      if (!dragged) return;
      col.querySelector('[data-list]').appendChild(dragged);
      const taskId = dragged.getAttribute('data-task');
      const newStatus = col.getAttribute('data-col');
      // Sync to server
      fetch(`/kanban/move/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify({ id: taskId, status: newStatus })
      }).catch(() => {});
    });
  });
});

function getCsrfToken() {
  const name = 'csrftoken=';
  const parts = document.cookie.split(';');
  for (let c of parts) {
    c = c.trim();
    if (c.startsWith(name)) return c.substring(name.length);
  }
  return '';
}

window.addEventListener('DOMContentLoaded', () => {
  // MATRIX VISUAL ORNAMENTS
  const matrix = document.querySelector('.matrix-bg');
  if(matrix) {
    for(let i=0;i<7;++i){
      const d = document.createElement('div');
      d.className = 'matrix-dot';
      d.style.top = Math.random()*86+6+'%';
      d.style.left = Math.random()*88+2+'%';
      d.style.animationDelay = (Math.random()*8)+'s';
      matrix.appendChild(d);
    }
    for(let i=0;i<3;++i){
      const h = document.createElement('div');
      h.className = 'matrix-hex';
      h.style.top = Math.random()*88+1+'%';
      h.style.left = Math.random()*90+0.5+'%';
      h.style.animationDelay = (Math.random()*14)+'s';
      matrix.appendChild(h);
    }
  }
});


