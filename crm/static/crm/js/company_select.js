(function() {
    const searchInput = document.getElementById('company-search');
    const sortButton = document.getElementById('sort-button');
    const companiesGrid = document.getElementById('companies-grid');
    const noResults = document.getElementById('no-results');
    
    if (!searchInput || !sortButton || !companiesGrid) return;
    
    const companyCards = Array.from(companiesGrid.querySelectorAll('.company-card'));
    let isAscending = false; // false = по убыванию (по умолчанию), true = по возрастанию
    
    sortButton.addEventListener('click', () => {
        isAscending = !isAscending; // Переключаем между убыванием и возрастанием
        
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
        
        let visible = companyCards.filter(card => {
            const name = card.dataset.name || '';
            const industry = card.dataset.industry || '';
            if (!searchTerm) return true;
            return name.includes(searchTerm) || industry.includes(searchTerm);
        });
        
        visible.sort((a, b) => {
            const nameA = a.dataset.name || '';
            const nameB = b.dataset.name || '';
            if (isAscending) {
                return nameA.localeCompare(nameB);
            } else {
                return nameB.localeCompare(nameA);
            }
        });
        
        companyCards.forEach(card => {
            if (visible.includes(card)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
        
        if (visible.length === 0) {
            noResults.classList.add('show');
            companiesGrid.style.display = 'none';
        } else {
            noResults.classList.remove('show');
            companiesGrid.style.display = 'grid';
            
            visible.forEach(card => {
                companiesGrid.appendChild(card);
            });
        }
    }
    
    searchInput.addEventListener('input', filterAndSort);
})();
