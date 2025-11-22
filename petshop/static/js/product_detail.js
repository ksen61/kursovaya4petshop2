document.addEventListener('DOMContentLoaded', () => {
    const productId = window.productId;
    const csrfToken = window.csrfToken;

    const imageEl = document.querySelector('.image-section img');
    const nameEl = document.querySelector('.info-section h1');
    const priceEl = document.querySelector('.price');
    const attributesEl = document.querySelector('.attributes');
    const descriptionEl = document.querySelector('.product-description p');
    const reviewsEl = document.querySelector('.reviews-list');
    const addForm = document.getElementById('add-to-cart-form');

    const reviewsPerPage = 5;
    let allReviews = [];
    let currentReviewPage = 1;

    let userDateFormat = "%d.%m.%Y"; 

    function setTextSafe(element, text) {
        if (element) element.textContent = text;
    }

    async function loadUserSettings() {
        try {
            const res = await fetch('/api/profile/');
            if (res.ok) {
                const data = await res.json();
                if (data.date_format) userDateFormat = data.date_format;
            }
        } catch (err) {
            console.warn('Не удалось загрузить настройки пользователя:', err);
        }
    }

    function formatDateByPattern(date, format) {
        if (!date) return 'Нет данных';
        const d = dayjs(date);
        switch (format) {
            case "%Y.%m.%d": return d.format("YYYY.MM.DD HH:mm");
            case "%m/%d/%Y": return d.format("MM/DD/YYYY HH:mm");
            default: return d.format("DD.MM.YYYY HH:mm");
        }
    }

    function renderReviewsPage(page) {
        if (!reviewsEl) return;

        if (allReviews.length === 0) {
            reviewsEl.innerHTML = '<p>Отзывов пока нет.</p>';
            document.querySelector('.pagination-reviews')?.remove();
            return;
        }

        reviewsEl.classList.add('dark-theme');

        const totalPages = Math.ceil(allReviews.length / reviewsPerPage);
        if (page < 1) page = 1;
        if (page > totalPages) page = totalPages;
        currentReviewPage = page;

        const start = (page - 1) * reviewsPerPage;
        const end = start + reviewsPerPage;
        const pageReviews = allReviews.slice(start, end);

        let html = '';
        pageReviews.forEach(r => {
            const formattedDate = formatDateByPattern(r.created_at, userDateFormat);
            html += `
                <div class="review-card">
                    <div class="review-header">
                        <span class="review-rating">⭐ ${r.rating}/5</span>
                        <span class="review-author"><strong>${r.user}</strong></span>
                    </div>
                    <p class="review-text">${r.text || 'Без текста'}</p>
                    <small class="review-date">${formattedDate}</small>
                </div>
            `;
        });
        reviewsEl.innerHTML = html;
        renderPagination(totalPages);
    }

    function renderPagination(totalPages) {
        if(!reviewsEl) return;
        let pagination = document.querySelector('.pagination-reviews');
        if(!pagination){
            pagination = document.createElement('div');
            pagination.className = 'pagination-reviews';
            pagination.style.textAlign = 'center';
            pagination.style.marginTop = '15px';
            reviewsEl.parentNode.appendChild(pagination);
        }

        let buttonsHtml = '';
        buttonsHtml += `<button class="page-btn" data-page="${currentReviewPage - 1}" ${currentReviewPage === 1 ? 'disabled' : ''}>Назад</button> `;
        for(let i=1; i <= totalPages; i++) {
            buttonsHtml += `<button class="page-btn ${i === currentReviewPage ? 'active' : ''}" data-page="${i}">${i}</button> `;
        }
        buttonsHtml += `<button class="page-btn" data-page="${currentReviewPage + 1}" ${currentReviewPage === totalPages ? 'disabled' : ''}>Вперед</button>`;
        pagination.innerHTML = buttonsHtml;

        pagination.querySelectorAll('.page-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = parseInt(btn.getAttribute('data-page'));
                if(page >= 1 && page <= totalPages){
                    renderReviewsPage(page);
                    reviewsEl.scrollIntoView({behavior: 'smooth', block: 'start'});
                }
            });
        });
    }

    async function loadProduct() {
        try {
            const res = await fetch(`/api/products/public/${productId}/`);
            if (!res.ok) throw new Error('Ошибка загрузки данных товара');
            const data = await res.json();

            if (imageEl) imageEl.src = data.image || '/static/img/default-product.png';
            setTextSafe(nameEl, data.name);
            setTextSafe(priceEl, data.price + ' ₽');

            let html = `<div><strong>Категория:</strong> ${data.category}</div>`;
            if(data.brand) html += `<div><strong>Бренд:</strong> ${data.brand}</div>`;
            if(data.age_category) html += `<div><strong>Возраст:</strong> ${data.age_category}</div>`;
            if(data.product_type) html += `<div><strong>Тип:</strong> ${data.product_type}</div>`;
            if(data.species) html += `<div><strong>Вид животного:</strong> ${data.species}</div>`;
            if(data.purposes?.length) html += `<div><strong>Назначение:</strong> ${data.purposes.join(', ')}</div>`;
            if(data.stocks?.length){
                html += `<div><strong>В наличии по пунктам:</strong><ul>`;
                data.stocks.forEach(s => html += `<li>${s.pickup_point}: ${s.quantity}</li>`);
                html += `</ul></div>`;
            }
            if(attributesEl) attributesEl.innerHTML = html;

            setTextSafe(descriptionEl, data.description || 'Описание отсутствует.');

            allReviews = (data.reviews || []).sort((a,b) => new Date(b.created_at) - new Date(a.created_at));
            renderReviewsPage(currentReviewPage);

            const reviewSection = document.getElementById('review-section');
            if(reviewSection){
                if(data.can_review > 0){
                    reviewSection.innerHTML = `
                        <a href="/reviews/add/${productId}/" class="btn-submit" style="margin: 0 50px;">Написать отзыв</a>
                        <span style="margin-left:10px;">Вы можете оставить ещё ${data.can_review} отзыв(ов)</span>
                    `;
                } else {
                    reviewSection.innerHTML = `<p>Вы можете оставить отзыв только после получения товара.</p>`;
                }
            }
        } catch(err) {
            console.error(err);
            alert('Ошибка загрузки товара');
        }
    }

    if (addForm) {
        addForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            let msgBox = addForm.querySelector('.max-quantity-message');
            if (!msgBox) {
                msgBox = document.createElement('div');
                msgBox.className = 'max-quantity-message';
                msgBox.style.display = 'none';
                addForm.appendChild(msgBox);
            }

            try {
                const quantity = parseInt(addForm.querySelector('input[name=quantity]').value) || 1;

                const res = await fetch(`/api/cart/add/${productId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ quantity })
                });

                const data = await res.json();

                if(res.ok){
                    alert(data.message || 'Товар добавлен в корзину!');
                } else {
                    msgBox.textContent = data.error || 'Невозможно добавить товар';
                    msgBox.style.display = 'block';
                }
            } catch(err){
                console.error(err);
                msgBox.textContent = 'Ошибка добавления товара в корзину';
                msgBox.style.display = 'block';
            }
        });
    }

    loadUserSettings();
    loadProduct();
});