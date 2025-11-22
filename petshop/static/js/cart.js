document.addEventListener('DOMContentLoaded', () => {
    const cartList = document.getElementById('cart-items-list');
    const cartSummary = document.getElementById('cart-summary');

    const body = document.body;
    const isDark = body.classList.contains('dark-theme');
    const isAccessible = body.classList.contains('accessibility-mode'); 

    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

    const cartContainer = document.querySelector('.cart-container');
    const productListUrl = cartContainer.dataset.productListUrl;
    const checkoutUrl = cartContainer.dataset.checkoutUrl;

    function updateSummary(data) {
        const totalQuantity = data.items.reduce((acc, i) => acc + i.quantity, 0);
        const totalPrice = data.items.reduce((acc, i) => acc + i.total, 0).toFixed(2);

        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'summary-card';
        if (isDark) summaryDiv.classList.add('dark-theme');
        if (isAccessible) summaryDiv.classList.add('accessibility-mode');

        summaryDiv.innerHTML = `
            <div class="summary-row">
                <span class="summary-label">Товаров:</span>
                <span class="summary-value">${totalQuantity} шт.</span>
            </div>
            <div class="summary-row">
                <span class="summary-label">Общая сумма:</span>
                <span class="summary-value">${totalPrice} ₽</span>
            </div>
            <div class="summary-buttons">
                <a href="${productListUrl}" class="btn btn-continue">
                    <i class="fas fa-arrow-left"></i> Продолжить покупки
                </a>
                <a href="${checkoutUrl}" class="btn btn-checkout">
                    Оформить заказ <i class="fas fa-arrow-right"></i>
                </a>
            </div>
        `;
        cartSummary.innerHTML = '';
        cartSummary.appendChild(summaryDiv);
    }

    async function loadCart() {
        try {
            const res = await fetch('/api/cart/');
            
            if (!res.ok) {
                cartList.innerHTML = `<p style="color:red;">Ошибка загрузки корзины: ${res.status}</p>`;
                cartSummary.innerHTML = '';
                return;
            }

            const data = await res.json();
            console.log('Cart data:', data);

            cartList.innerHTML = '';

            if (!data.items || data.items.length === 0) {
                cartList.innerHTML = `<p>Корзина пуста. Начните добавлять товары.</p>`;
                cartSummary.innerHTML = '';
                return;
            }

            data.items.forEach(item => {
                const product = item.product;
                const div = document.createElement('div');
                div.className = 'cart-item';
                if (isDark) div.classList.add('dark-theme');
                if (isAccessible) div.classList.add('accessibility-mode');

                div.innerHTML = `
                    <div class="item-product">
                        <img src="${product.image || '/static/img/default-product.png'}" alt="${product.name}">
                        <div class="product-info">
                            <span class="product-title">
                                <a href="/product/${product.id}/">${product.name}</a>
                            </span>
                        </div>
                    </div>
                    <div class="item-price">${parseFloat(product.price).toFixed(2)} ₽</div>
                    <div class="item-quantity">
                        <input type="number" value="${item.quantity}" min="1" class="quantity-input" data-id="${item.id}">
                        <div class="quantity-error" style="color:red; margin-top:5px;"></div>
                    </div>
                    <div class="item-total">${item.total.toFixed(2)} ₽</div>
                    <div class="item-actions">
                        <button class="remove-btn" data-id="${item.id}">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                `;
                cartList.appendChild(div);
            });

            updateSummary(data);
        } catch (err) {
            console.error('Ошибка при загрузке корзины:', err);
            cartList.innerHTML = `<p style="color:red;">Ошибка загрузки корзины</p>`;
            cartSummary.innerHTML = '';
        }
    }

    cartList.addEventListener('click', async (e) => {
        const btn = e.target.closest('.remove-btn');
        if (!btn) return;
        const id = btn.dataset.id;
        try {
            const res = await fetch(`/api/cart/remove/${id}/`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrfToken }
            });
            const data = await res.json();
            if (!res.ok) {
                alert(data.error || 'Ошибка удаления товара');
                return;
            }
            loadCart();
        } catch (err) {
            console.error('Ошибка удаления товара:', err);
            alert('Ошибка удаления товара');
        }
    });

    cartList.addEventListener('change', async (e) => {
        const input = e.target.closest('.quantity-input');
        if (!input) return;
        const id = input.dataset.id;
        let quantity = parseInt(input.value);
        if (quantity < 1) quantity = 1;

        const msgBox = input.parentElement.querySelector('.quantity-error');

        try {
            const res = await fetch(`/api/cart/update/${id}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ quantity })
            });

            const data = await res.json();
            if (res.ok) {
                loadCart();
            } else {
                msgBox.textContent = data.error || 'Невозможно установить такое количество';
                input.value = data.current_quantity || 1;
            }
        } catch (err) {
            console.error('Ошибка обновления количества:', err);
            msgBox.textContent = 'Ошибка обновления количества';
        }
    });

    loadCart();
});