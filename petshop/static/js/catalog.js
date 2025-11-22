document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('products-grid');
    const form = document.getElementById('filters-form');
    const resetBtn = document.getElementById('reset-filters');
    const sortSelect = document.getElementById('sort-by');
    const searchInput = document.getElementById('search_name');
    
    const SEARCH_HISTORY_KEY = 'search_history';
    let searchHistory = [];

    function loadSearchHistory() {
        const saved = localStorage.getItem(SEARCH_HISTORY_KEY);
        if (saved) {
            searchHistory = JSON.parse(saved);
        }
    }

    function saveToSearchHistory() {
        const searchQuery = searchInput.value.trim();
        if (!searchQuery) return;
        
        const selectedFilters = {};
        const formData = new FormData(form);
        
        formData.forEach((value, key) => {
            if (key !== 'csrfmiddlewaretoken' && key !== 'search_name' && value) {
                if (!selectedFilters[key]) {
                    selectedFilters[key] = [value];
                } else {
                    selectedFilters[key].push(value);
                }
            }
        });
        
        const filterLabels = [];
        
        if (selectedFilters.category) {
            selectedFilters.category.forEach(catId => {
                const label = document.querySelector(`[name="category"][value="${catId}"] + label`);
                if (label) filterLabels.push(label.textContent.trim());
            });
        }
        
        if (selectedFilters.brand) {
            selectedFilters.brand.forEach(brandId => {
                const label = document.querySelector(`[name="brand"][value="${brandId}"] + label`);
                if (label) filterLabels.push(label.textContent.trim());
            });
        }
        
        if (selectedFilters.age) {
            selectedFilters.age.forEach(ageId => {
                const label = document.querySelector(`[name="age"][value="${ageId}"] + label`);
                if (label) filterLabels.push(label.textContent.trim());
            });
        }
        
        if (selectedFilters.species) {
            selectedFilters.species.forEach(speciesId => {
                const label = document.querySelector(`[name="species"][value="${speciesId}"] + label`);
                if (label) filterLabels.push(label.textContent.trim());
            });
        }
        
        if (selectedFilters.type) {
            selectedFilters.type.forEach(typeId => {
                const label = document.querySelector(`[name="type"][value="${typeId}"] + label`);
                if (label) filterLabels.push(label.textContent.trim());
            });
        }
        
        if (selectedFilters.purpose) {
            selectedFilters.purpose.forEach(purposeId => {
                const label = document.querySelector(`[name="purpose"][value="${purposeId}"] + label`);
                if (label) filterLabels.push(label.textContent.trim());
            });
        }
        
        if (selectedFilters.price_min) {
            filterLabels.push(`Цена от: ${selectedFilters.price_min[0]} ₽`);
        }
        if (selectedFilters.price_max) {
            filterLabels.push(`Цена до: ${selectedFilters.price_max[0]} ₽`);
        }
        
        if (sortSelect.value) {
            const sortText = sortSelect.options[sortSelect.selectedIndex].text;
            filterLabels.push(`Сортировка: ${sortText}`);
        }
        
        const historyItem = {
            query: searchQuery,
            filters: selectedFilters,
            filterLabels: filterLabels,
            sort: sortSelect.value,
            timestamp: new Date().toISOString()
        };
        
        searchHistory = searchHistory.filter(item => 
            !(item.query === historyItem.query && 
              JSON.stringify(item.filters) === JSON.stringify(historyItem.filters) &&
              item.sort === historyItem.sort)
        );
        
        searchHistory.unshift(historyItem);
        
        if (searchHistory.length > 10) {
            searchHistory = searchHistory.slice(0, 10);
        }
        
        localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(searchHistory));
    }

    function applySavedFilters(filters, sort) {
        form.reset();
        
        searchInput.value = filters.query || '';
        
        Object.keys(filters.filters || {}).forEach(key => {
            filters.filters[key].forEach(value => {
                const element = document.querySelector(`[name="${key}"][value="${value}"]`);
                if (element) element.checked = true;
            });
        });
        
        if (sort) {
            sortSelect.value = sort;
        }
    }

    function showSearchHistory() {
        if (searchHistory.length === 0) return;
        
        const existingList = document.getElementById('search-history-list');
        if (existingList) {
            existingList.remove();
        }
        
        const historyList = document.createElement('div');
        historyList.id = 'search-history-list';
        historyList.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
            max-height: 300px;
            overflow-y: auto;
        `;
        
        searchHistory.forEach((item, index) => {
            const historyItem = document.createElement('div');
            historyItem.style.cssText = `
                padding: 10px 12px;
                cursor: pointer;
                border-bottom: 1px solid #f0f0f0;
                transition: background-color 0.2s;
            `;
            
            const mainQuery = document.createElement('div');
            mainQuery.style.cssText = `
                font-weight: 600;
                margin-bottom: 4px;
                color: #333;
            `;
            mainQuery.textContent = item.query;
            
            const filtersText = document.createElement('div');
            filtersText.style.cssText = `
                font-size: 0.85em;
                color: #666;
                display: flex;
                flex-wrap: wrap;
                gap: 4px;
            `;
            
            if (item.filterLabels && item.filterLabels.length > 0) {
                item.filterLabels.forEach(filter => {
                    const filterBadge = document.createElement('span');
                    filterBadge.style.cssText = `
                        background: #f0f0f0;
                        padding: 2px 6px;
                        border-radius: 12px;
                        font-size: 0.8em;
                    `;
                    filterBadge.textContent = filter;
                    filtersText.appendChild(filterBadge);
                });
            } else {
                filtersText.textContent = 'Без фильтров';
                filtersText.style.fontStyle = 'italic';
            }
            
            historyItem.appendChild(mainQuery);
            historyItem.appendChild(filtersText);
            
            historyItem.addEventListener('mouseenter', () => {
                historyItem.style.backgroundColor = '#f8f9fa';
            });
            
            historyItem.addEventListener('mouseleave', () => {
                historyItem.style.backgroundColor = '';
            });
            
            historyItem.addEventListener('click', () => {
                applySavedFilters(item, item.sort);
                historyList.remove();
                loadProducts();
            });
            
            historyList.appendChild(historyItem);
        });
        
        searchInput.parentNode.style.position = 'relative';
        searchInput.parentNode.appendChild(historyList);
    }

    function hideSearchHistory() {
        setTimeout(() => {
            const historyList = document.getElementById('search-history-list');
            if (historyList) {
                historyList.remove();
            }
        }, 200);
    }

    async function loadProducts() {
        const formData = new FormData(form);
        const params = new URLSearchParams();

        formData.forEach((v,k) => {
            if (k !== 'csrfmiddlewaretoken' && v) {
                params.append(k,v);
            }
        });
        
        saveToSearchHistory();
        
        if (sortSelect.value) {
            params.append('sort', sortSelect.value);
        }

        try {
            const res = await fetch('/api/products/public/?' + params.toString());
            const data = await res.json();

            grid.innerHTML = '';

            if (!res.ok) {
                grid.innerHTML = `<p style="color:red;">Ошибка: ${data.error || 'Некорректный запрос'}</p>`;
                return;
            }

            if (!Array.isArray(data) || data.length === 0) {
                grid.innerHTML = '<p>Товары не найдены.</p>';
                return;
            }

            data.forEach(product => {
                const card = document.createElement('div');
                card.className = 'product-card';
                card.innerHTML = `
                    <img src="${product.image || '/static/img/default-product.png'}" alt="${product.name}" class="product-image">
                    <h3 class="product-title"><a href="/product/${product.id}/">${product.name}</a></h3>
                    <p class="product-description">${product.description.slice(0,50)}${product.description.length>50?'...':''}</p>
                    <div class="product-price"><span>${Math.round(product.price)} ₽</span></div>
                    <form class="add-to-cart-form">
                        <input type="hidden" name="quantity" value="1">
                        <button type="submit" class="btn add-to-cart-btn">
                            <i class="fas fa-shopping-basket"></i> В корзину
                        </button>
                        <div class="max-quantity-message"></div>
                    </form>
                `;
                grid.appendChild(card);

                const addForm = card.querySelector('.add-to-cart-form');
                const msgBox = addForm.querySelector('.max-quantity-message');

                addForm.addEventListener('submit', async e => {
                    e.preventDefault();
                    msgBox.style.display = 'none';

                    try {
                        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                        const quantity = parseInt(addForm.querySelector('input[name=quantity]').value) || 1;

                        const res = await fetch(`/api/cart/add/${product.id}/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': csrfToken
                            },
                            body: JSON.stringify({ quantity })
                        });

                        const data = await res.json();

                        if(res.ok) {
                            alert(data.message || 'Товар добавлен в корзину!');
                        } else {
                            msgBox.textContent = data.error || 'Ошибка добавления';
                            msgBox.style.display = 'block';
                        }

                    } catch(err) {
                        console.error(err);
                        msgBox.textContent = 'Ошибка добавления товара в корзину';
                        msgBox.style.display = 'block';
                    }
                });
            });
        } catch(err) {
            grid.innerHTML = '<p style="color:red;">Ошибка загрузки товаров</p>';
            console.error(err);
        }
    }

    searchInput.addEventListener('focus', showSearchHistory);
    searchInput.addEventListener('blur', hideSearchHistory);
    
    form.addEventListener('submit', e => { 
        e.preventDefault(); 
        loadProducts(); 
    });
    
    resetBtn.addEventListener('click', () => { 
        form.reset(); 
        sortSelect.value = '';
        loadProducts(); 
    });
    
    sortSelect.addEventListener('change', loadProducts);

    loadSearchHistory();
    loadProducts();
});