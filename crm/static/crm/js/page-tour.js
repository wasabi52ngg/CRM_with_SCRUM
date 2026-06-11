/**
 * Пошаговые подсказки по странице (затемнение + всплывающие подсказки).
 * Запуск: кнопка [data-page-tour="id"] или startPageTour('id').
 */
(function () {
  const TOURS = {
    kanban: [
      {
        selector: '#kanban-backlog',
        title: 'Беклог',
        text: 'Здесь задачи, которые ещё не в спринте. Перетащите карточку на доску, когда будете готовы взять её в работу.',
        placement: 'right',
      },
      {
        selector: '#kanban-board-scope',
        title: 'Область доски',
        text: 'Выберите, что показывать: весь проект, активный спринт или конкретную итерацию.',
        placement: 'bottom',
      },
      {
        selector: '#kanban-board',
        title: 'Колонки доски',
        text: 'Перетаскивайте карточки между стадиями. Нажмите на задачу, чтобы открыть описание, чек-лист и комментарии.',
        placement: 'top',
      },
      {
        selector: '.kanban-filters-card',
        title: 'Фильтры',
        text: 'Отфильтруйте задачи по исполнителю, типу работ, эпику или быстрым пресетам «Мои», «Без исполнителя», «Просрочено».',
        placement: 'bottom',
      },
      {
        selector: '#kanban-open-planning',
        title: 'Планирование',
        text: 'Здесь создают спринты, смотрят статистику и при необходимости настраивают колонки доски.',
        placement: 'bottom',
        optional: true,
      },
      {
        selector: '.kanban-view-btn[data-view="list"]',
        title: 'Вид списка',
        text: 'Переключитесь на табличный вид, если удобнее смотреть все задачи построчно.',
        placement: 'bottom',
      },
    ],
    request_list: [
      {
        selector: '.page-title',
        title: 'Список заявок',
        text: 'Все обращения клиентов компании. Новые заявки можно взять в работу прямо из таблицы.',
        placement: 'bottom',
      },
      {
        selector: '.request-list-table',
        title: 'Таблица заявок',
        text: 'Статус, тип проекта и ответственный менеджер. Название — ссылка на карточку заявки.',
        placement: 'top',
      },
      {
        selector: '.request-list-take-col',
        title: 'Взять заявку',
        text: 'Если заявка свободна, нажмите «Взять заявку» — вы станете ответственным и сможете вести клиента.',
        placement: 'left',
        optional: true,
      },
    ],
    request_detail: [
      {
        selector: '.request-meta-card',
        title: 'Карточка заявки',
        text: 'Контакты клиента, тип проекта и текущий статус. Отсюда переводите заявку в работу или завершаете её.',
        placement: 'bottom',
      },
      {
        selector: '.timeline-card',
        title: 'Этапы обработки',
        text: 'Отмечайте шаги по заявке на схеме: добавляйте чекпоинты, связывайте их и отмечайте выполнение.',
        placement: 'top',
      },
      {
        selector: '.request-chat-section',
        title: 'Чат с клиентом',
        text: 'Переписка видна клиенту в личном кабинете. Ответственный менеджер может отправлять сообщения здесь.',
        placement: 'top',
      },
    ],
    project_detail: [
      {
        selector: '.page-title',
        title: 'Проект',
        text: 'Название и контекст работ. На этой странице вы видите общую сводку и список задач.',
        placement: 'bottom',
      },
      {
        selector: '#project-progress-card',
        title: 'Статус задач',
        text: 'Сводка по задачам: сколько в состоянии «К выполнению», «В работе», «К проверке» и «Готово».',
        placement: 'top',
      },
      {
        selector: '#project-open-kanban',
        title: 'Доска задач',
        text: 'Открывает канбан-доску проекта: колонки статусов и карточки задач.',
        placement: 'left',
      },
      {
        selector: '#project-open-reports',
        title: 'Отчёты по спринтам',
        text: 'Сводки по скорости команды, диаграмма сгорания и ретроспектива для выбранного спринта.',
        placement: 'bottom',
      },
      {
        selector: '#project-tasks-table',
        title: 'Таблица задач',
        text: 'Короткий список задач проекта: название, тип, статус, постановщик, исполнитель, дедлайн, приоритет и трудоёмкость.',
        placement: 'top',
      },
      {
        selector: '#scrum-project-form',
        title: 'Scrum-настройки',
        text: 'Если у вас есть права: задайте Product Owner, Scrum Master и критерии готовности (DoD). Эти поля помогают команде ориентироваться.',
        placement: 'bottom',
        optional: true,
      },
      {
        selector: '#project-add-task-title',
        title: 'Добавить задачу',
        text: 'Создайте новую задачу проекта: название, комментарий постановщика, приоритет, оценку трудоёмкости в баллах, исполнителя, дедлайн и тип.',
        placement: 'bottom',
      },
    ],
  };

  class PageTour {
    constructor(tourId) {
      this.tourId = tourId;
      this.steps = (TOURS[tourId] || []).filter((s) => !s.optional || document.querySelector(s.selector));
      this.resolvedSteps = [];
      this.index = 0;
      this.popover = null;
      this.target = null;
      this.blocker = null;
      this.onKeyDown = this.onKeyDown.bind(this);
    }

    start() {
      this.resolvedSteps = this.steps.filter((s) => document.querySelector(s.selector));
      if (!this.resolvedSteps.length) return;

      this.popover = document.createElement('div');
      this.popover.className = 'page-tour-popover';
      this.popover.setAttribute('role', 'dialog');
      this.popover.setAttribute('aria-live', 'polite');
      document.body.appendChild(this.popover);

      this.blocker = document.createElement('div');
      this.blocker.className = 'page-tour-blocker';
      this.blocker.setAttribute('aria-hidden', 'true');
      document.body.appendChild(this.blocker);

      document.body.classList.add('page-tour-active');
      document.addEventListener('keydown', this.onKeyDown);
      this.showStep(0);
    }

    onKeyDown(e) {
      if (e.key === 'Escape') this.finish();
      if (e.key === 'ArrowRight') this.next();
      if (e.key === 'ArrowLeft') this.prev();
    }

    clearTarget() {
      if (this.target) {
        this.target.classList.remove('page-tour-target');
        this.target = null;
      }
    }

    finish() {
      this.clearTarget();
      document.body.classList.remove('page-tour-active');
      document.removeEventListener('keydown', this.onKeyDown);
      if (this.popover) {
        this.popover.remove();
        this.popover = null;
      }
      if (this.blocker) {
        this.blocker.remove();
        this.blocker = null;
      }
      try {
        localStorage.setItem(`page_tour_done_${this.tourId}`, '1');
      } catch (_) {}
    }

    showStep(i) {
      if (i < 0 || i >= this.resolvedSteps.length) {
        this.finish();
        return;
      }

      this.index = i;
      const step = this.resolvedSteps[i];
      const el = document.querySelector(step.selector);
      if (!el) {
        this.next();
        return;
      }

      this.clearTarget();
      this.target = el;
      el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      window.requestAnimationFrame(() => {
        el.classList.add('page-tour-target');
        this.renderPopover(step);
        this.positionPopover(el, step.placement || 'bottom');
      });
    }

    renderPopover(step) {
      const total = this.resolvedSteps.length;
      const isFirst = this.index === 0;
      const isLast = this.index === total - 1;

      this.popover.innerHTML = `
        <h3 class="page-tour-popover__title"></h3>
        <p class="page-tour-popover__text"></p>
        <div class="page-tour-popover__footer">
          <span class="page-tour-popover__step"></span>
          <div class="page-tour-popover__actions"></div>
        </div>
      `;

      this.popover.querySelector('.page-tour-popover__title').textContent = step.title;
      this.popover.querySelector('.page-tour-popover__text').textContent = step.text;
      this.popover.querySelector('.page-tour-popover__step').textContent = `${this.index + 1} / ${total}`;

      const actions = this.popover.querySelector('.page-tour-popover__actions');

      if (!isFirst) {
        const back = document.createElement('button');
        back.type = 'button';
        back.className = 'page-tour-btn';
        back.textContent = 'Назад';
        back.addEventListener('click', () => this.prev());
        actions.appendChild(back);
      }

      const close = document.createElement('button');
      close.type = 'button';
      close.className = 'page-tour-btn page-tour-btn--ghost';
      close.textContent = 'Закрыть';
      close.addEventListener('click', () => this.finish());
      actions.appendChild(close);

      const next = document.createElement('button');
      next.type = 'button';
      next.className = 'page-tour-btn page-tour-btn--primary';
      next.textContent = isLast ? 'Готово' : 'Далее';
      next.addEventListener('click', () => (isLast ? this.finish() : this.next()));
      actions.appendChild(next);
    }

    positionPopover(el, placement) {
      const rect = el.getBoundingClientRect();
      const pop = this.popover;
      const margin = 14;
      pop.style.visibility = 'hidden';
      pop.style.left = '0';
      pop.style.top = '0';
      pop.classList.remove(
        'page-tour-popover--top',
        'page-tour-popover--bottom',
        'page-tour-popover--left',
        'page-tour-popover--right'
      );

      const popRect = pop.getBoundingClientRect();
      let top = 0;
      let left = 0;
      let place = placement;

      const fits = {
        bottom: rect.bottom + margin + popRect.height <= window.innerHeight - 8,
        top: rect.top - margin - popRect.height >= 8,
        right: rect.right + margin + popRect.width <= window.innerWidth - 8,
        left: rect.left - margin - popRect.width >= 8,
      };

      if (placement === 'bottom' && !fits.bottom && fits.top) place = 'top';
      if (placement === 'top' && !fits.top && fits.bottom) place = 'bottom';
      if (placement === 'right' && !fits.right && fits.left) place = 'left';
      if (placement === 'left' && !fits.left && fits.right) place = 'right';

      if (place === 'bottom') {
        top = rect.bottom + margin;
        left = rect.left + rect.width / 2 - popRect.width / 2;
      } else if (place === 'top') {
        top = rect.top - margin - popRect.height;
        left = rect.left + rect.width / 2 - popRect.width / 2;
      } else if (place === 'right') {
        top = rect.top + rect.height / 2 - popRect.height / 2;
        left = rect.right + margin;
      } else {
        top = rect.top + rect.height / 2 - popRect.height / 2;
        left = rect.left - margin - popRect.width;
      }

      left = Math.max(12, Math.min(left, window.innerWidth - popRect.width - 12));
      top = Math.max(12, Math.min(top, window.innerHeight - popRect.height - 12));

      pop.style.top = `${top}px`;
      pop.style.left = `${left}px`;
      pop.classList.add(`page-tour-popover--${place}`);
      pop.style.visibility = 'visible';
    }

    next() {
      this.showStep(this.index + 1);
    }

    prev() {
      this.showStep(this.index - 1);
    }
  }

  function bindLaunchButtons() {
    document.querySelectorAll('[data-page-tour]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-page-tour');
        if (TOURS[id]) new PageTour(id).start();
      });
    });
  }

  function maybeAutoStart() {
    const meta = document.querySelector('meta[name="page-tour-auto"]');
    if (!meta) return;
    const id = meta.getAttribute('content');
    if (!id || !TOURS[id]) return;
    try {
      if (localStorage.getItem(`page_tour_done_${id}`)) return;
    } catch (_) {}
    window.setTimeout(() => new PageTour(id).start(), 600);
  }

  window.startPageTour = function (tourId) {
    if (TOURS[tourId]) new PageTour(tourId).start();
  };

  document.addEventListener('DOMContentLoaded', () => {
    bindLaunchButtons();
    maybeAutoStart();
  });
})();
