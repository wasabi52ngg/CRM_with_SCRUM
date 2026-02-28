(function() {
    const searchInput = document.getElementById('company-search');
    const filterCheckbox = document.getElementById('filter-user-companies');
    const sortButton = document.getElementById('sort-button');
    const companiesList = document.getElementById('companies-list');
    const noResults = document.getElementById('no-results');
    const requestForm = document.getElementById('request-form');
    const selectedCompanyInput = document.getElementById('selected-company');
    
    if (!companiesList) return;
    
    const companyItems = Array.from(companiesList.querySelectorAll('.company-item'));
    let isAscending = false; // false = по убыванию (по умолчанию), true = по возрастанию
    
    // Обработка выбора компании
    companyItems.forEach(item => {
        const radio = item.querySelector('input[type="radio"]');
        
        item.addEventListener('click', (e) => {
            // Не срабатывает если кликнули на radio (он скрыт)
            if (e.target.type === 'radio') return;
            
            companyItems.forEach(i => i.classList.remove('selected'));
            item.classList.add('selected');
            if (radio) {
                radio.checked = true;
            }
            if (selectedCompanyInput) {
                selectedCompanyInput.value = radio ? radio.value : '';
            }
        });
    });
    
    // Сортировка - только 2 состояния
    if (sortButton) {
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
            
            filterAndSearch();
        });
    }
    
    function filterAndSearch() {
        const searchTerm = (searchInput?.value || '').toLowerCase().trim();
        const filterUserCompanies = filterCheckbox?.checked || false;
        
        let visible = companyItems.filter(item => {
            const name = item.dataset.name || '';
            const industry = item.dataset.industry || '';
            const isUserCompany = item.dataset.userCompany === 'true';
            
            let matches = true;
            
            // Поиск
            if (searchTerm && !name.includes(searchTerm) && !industry.includes(searchTerm)) {
                matches = false;
            }
            
            // Фильтр по компаниям, куда уже отправлял
            if (filterUserCompanies && !isUserCompany) {
                matches = false;
            }
            
            return matches;
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
        companyItems.forEach(item => {
            if (visible.includes(item)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
        
        // Переставляем видимые элементы в правильном порядке
        visible.forEach(item => {
            companiesList.appendChild(item);
        });
        
        // Показываем сообщение "не найдено"
        if (visible.length === 0) {
            if (noResults) {
                noResults.classList.add('show');
            }
            if (companiesList) {
                companiesList.style.display = 'none';
            }
        } else {
            if (noResults) {
                noResults.classList.remove('show');
            }
            if (companiesList) {
                companiesList.style.display = 'block';
            }
        }
    }
    
    if (searchInput) {
        searchInput.addEventListener('input', filterAndSearch);
    }
    
    if (filterCheckbox) {
        filterCheckbox.addEventListener('change', filterAndSearch);
    }
    
    // Инициализация фильтрации при загрузке
    filterAndSearch();
})();
