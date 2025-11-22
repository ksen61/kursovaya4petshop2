document.addEventListener('DOMContentLoaded', function() {
    console.log('Quiz script loaded');
    
    let currentStep = 0;
    const steps = document.querySelectorAll('.quiz-step');
    const prevBtn = document.getElementById('prevStep');
    const totalSteps = steps.length;
    const formData = {};
    const grid = document.getElementById('products-grid');

    let currentPage = 0;
    const pageSize = 3;
    let allProducts = [];

    const paginationWrapper = document.createElement('div');
    paginationWrapper.style.display = 'flex';
    paginationWrapper.style.justifyContent = 'center';
    paginationWrapper.style.marginTop = '20px';
    paginationWrapper.style.gap = '10px';

    const prevPageBtn = document.createElement('button');
    prevPageBtn.textContent = '← Назад';
    prevPageBtn.className = 'nav-btn';
    prevPageBtn.disabled = true;

    const nextPageBtn = document.createElement('button');
    nextPageBtn.textContent = 'Вперед →';
    nextPageBtn.className = 'nav-btn';
    nextPageBtn.disabled = true;

    paginationWrapper.appendChild(prevPageBtn);
    paginationWrapper.appendChild(nextPageBtn);
    grid.insertAdjacentElement('afterend', paginationWrapper);

    function updateStepDisplay() {
        steps.forEach((step, index) => {
            step.style.display = index === currentStep ? 'block' : 'none';
        });
        prevBtn.style.display = currentStep > 0 ? 'inline-block' : 'none';
    }

    function showProductsSection() {
        if (grid) {
            grid.style.display = 'grid';
            grid.style.marginTop = '30px';
            setTimeout(() => {
                grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 300);
        }
    }

    function hideProductsSection() {
        if (grid) {
            grid.style.display = 'none';
        }
        paginationWrapper.style.display = 'none';
    }

    function renderPage(page) {
        if (!allProducts || allProducts.length === 0) {
            grid.innerHTML = `
                <div class="no-products" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                    <h3>Товары не найдены</h3>
                    <p>Попробуйте изменить критерии поиска</p>
                    <button class="nav-btn restart-btn" onclick="resetQuiz()" style="margin-top: 15px;">Начать заново</button>
                </div>
            `;
            paginationWrapper.style.display = 'none';
            return;
        }

        paginationWrapper.style.display = 'flex';
        const start = page * pageSize;
        const end = start + pageSize;
        const pageProducts = allProducts.slice(start, end);

        grid.innerHTML = '';
        pageProducts.forEach(product => {
            const card = document.createElement('div');
            card.className = 'product-card';
            card.style.border = '1px solid #ddd';
            card.style.borderRadius = '8px';
            card.style.padding = '15px';
            card.style.textAlign = 'center';

            const description = product.description 
                ? (product.description.length > 50 
                    ? product.description.substring(0, 50) + '...' 
                    : product.description)
                : 'Описание отсутствует';

            card.innerHTML = `
                <img src="${product.image || '/static/img/default-product.png'}" 
                     alt="${product.name}" 
                     style="max-width: 100%; height: 150px; object-fit: cover; border-radius: 4px;"
                     onerror="this.src='/static/img/default-product.png'">
                <h3 style="margin: 10px 0;"><a href="/product/${product.id}/">${product.name}</a></h3>
                <p style="font-size: 14px;">${description}</p>
                <div class="price" style="font-weight: bold; font-size: 18px; margin-top: 10px;">
                    ${product.price} ₽
                </div>
            `;
            grid.appendChild(card);
        });

        prevPageBtn.disabled = page === 0;
        nextPageBtn.disabled = end >= allProducts.length;
    }

    prevPageBtn.addEventListener('click', () => {
        if (currentPage > 0) {
            currentPage--;
            renderPage(currentPage);
        }
    });

    nextPageBtn.addEventListener('click', () => {
        if ((currentPage + 1) * pageSize < allProducts.length) {
            currentPage++;
            renderPage(currentPage);
        }
    });

    function fetchProducts() {
        if (!grid) return;

        grid.innerHTML = `
            <div class="loading" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <h3>Загружаем подходящие товары...</h3>
                <p>Пожалуйста, подождите</p>
            </div>
        `;
        
        showProductsSection();

        const params = new URLSearchParams();

        if (formData.species) params.append('species', formData.species);
        if (formData.age) params.append('age', formData.age);
        if (formData.category) params.append('category', formData.category);
        if (formData.type) params.append('type', formData.type);
        if (formData.purpose) params.append('purpose', formData.purpose);

        const apiUrl = `/api/products/public/${params.toString() ? '?' + params.toString() : ''}`;

        fetch(apiUrl)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                allProducts = data;
                currentPage = 0;
                renderPage(currentPage);
                addRestartButton();
            })
            .catch(error => {
                grid.innerHTML = `
                    <div class="error" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                        <h3>Ошибка загрузки товаров</h3>
                        <p>${error.message}</p>
                        <button class="btn" onclick="resetQuiz()" style="margin-top: 15px;">Попробовать снова</button>
                    </div>
                `;
                paginationWrapper.style.display = 'none';
            });
    }

    function addRestartButton() {
        const quizNavigation = document.querySelector('.quiz-navigation');
        if (!quizNavigation) return;

        const existingBtn = quizNavigation.querySelector('.restart-btn');
        if (existingBtn) existingBtn.remove();

        const restartBtn = document.createElement('button');
        restartBtn.textContent = 'Начать заново';
        restartBtn.className = 'nav-btn restart-btn';
        restartBtn.type = 'button';
        restartBtn.style.marginLeft = '10px';
        restartBtn.addEventListener('click', resetQuiz);

        quizNavigation.appendChild(restartBtn);
    }

    function resetQuiz() {
        console.log('Resetting quiz');

        currentStep = 0;
        Object.keys(formData).forEach(key => delete formData[key]);

        document.querySelectorAll('.option-btn').forEach(btn => btn.classList.remove('selected'));

        const restartBtn = document.querySelector('.restart-btn');
        if (restartBtn) restartBtn.remove();

        hideProductsSection();
        updateStepDisplay();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    window.resetQuiz = resetQuiz;

    steps.forEach((step, stepIndex) => {
        const optionButtons = step.querySelectorAll('.option-btn');
        optionButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();

                const dataName = this.getAttribute('data-name');
                const dataValue = this.getAttribute('data-value');

                optionButtons.forEach(button => button.classList.remove('selected'));
                this.classList.add('selected');

                formData[dataName] = dataValue;
                
                if (stepIndex < totalSteps - 1) {
                    currentStep++;
                    updateStepDisplay();
                } else {
                    fetchProducts();
                }
            });
        });
    });

    prevBtn.addEventListener('click', () => {
        if (currentStep > 0) {
            currentStep--;
            updateStepDisplay();
            hideProductsSection();

            const restartBtn = document.querySelector('.restart-btn');
            if (restartBtn) restartBtn.remove();
        }
    });

    updateStepDisplay();
    hideProductsSection();

    console.log('Quiz initialized successfully');
    console.log('Found steps:', steps.length);
    console.log('Found grid:', !!grid);
});

const themeToggle = document.getElementById('themeToggle');
themeToggle.addEventListener('change', () => {
    document.body.classList.toggle('dark-theme', themeToggle.checked);

    fetch('/api/user/theme/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}'},
        body: JSON.stringify({theme: themeToggle.checked})
    });
});