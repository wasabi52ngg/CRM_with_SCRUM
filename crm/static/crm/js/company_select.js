(function() {
    const searchInput = document.getElementById('company-search');
    const sortButton = document.getElementById('sort-button');
    const companiesGrid = document.getElementById('companies-grid');
    const noResults = document.getElementById('no-results');
    
    if (!searchInput || !sortButton || !companiesGrid) return;
    
    const companyCards = Array.from(companiesGrid.querySelectorAll('.company-card'));
    let isAscending = false; // false = по убыванию (по умолчанию), true = по возрастанию
    
    // Сортировка - только 2 состояния
    sortButton.addEventListener('click', () => {
        isAscending = !isAscending; // Переключаем между убыванием и возрастанием
        
        // Обновляем иконку
        const arrow = sortButton.querySelector('.sort-arrow');
        if (arrow) {
            if (isAscending) {
                arrow.textContent = '↑';
                sortButton.classList.add('active');
            } else {
                arrow.textContent = '↓';
                sortButton.classList.remove('active');
            }
        }
        
        filterAndSort();
    });
    
    function filterAndSort() {
        const searchTerm = searchInput.value.toLowerCase().trim();
        
        // Фильтрация
        let visible = companyCards.filter(card => {
            const name = card.dataset.name || '';
            const industry = card.dataset.industry || '';
            if (!searchTerm) return true;
            return name.includes(searchTerm) || industry.includes(searchTerm);
        });
        
        // Сортировка - только по названию, 2 направления
        visible.sort((a, b) => {
            const nameA = a.dataset.name || '';
            const nameB = b.dataset.name || '';
            if (isAscending) {
                return nameA.localeCompare(nameB);
            } else {
                return nameB.localeCompare(nameA);
            }
        });
        
        // Показываем/скрываем карточки
        companyCards.forEach(card => {
            if (visible.includes(card)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
        
        // Показываем сообщение "не найдено"
        if (visible.length === 0) {
            noResults.classList.add('show');
            companiesGrid.style.display = 'none';
        } else {
            noResults.classList.remove('show');
            companiesGrid.style.display = 'grid';
            
            // Переставляем видимые карточки в правильном порядке
            visible.forEach(card => {
                companiesGrid.appendChild(card);
            });
        }
    }
    
    searchInput.addEventListener('input', filterAndSort);
})();
