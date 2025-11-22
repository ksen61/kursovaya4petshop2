document.addEventListener('DOMContentLoaded', async function() {
    const container = document.getElementById('checkout-container');
    const createOrderUrl = container.dataset.createOrderUrl;

    const orderItemsEl = document.getElementById('order-items');
    const totalPriceEl = document.getElementById('total-price');
    const pickupPointSelect = document.getElementById('pickup_point');
    const phoneInput = document.getElementById('phone');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    function ensurePlus7() {
        if (!phoneInput.value) phoneInput.value = '+7';
    }

    function validatePhone() {
        let numbers = phoneInput.value.replace(/\D/g, '');
        if (!numbers.startsWith('7')) numbers = '7' + numbers;
        phoneInput.value = '+' + numbers.slice(0, 11);
    }

    function handlePhoneKeydown(e) {
        if ((phoneInput.selectionStart <= 2) && (e.key === 'Backspace' || e.key === 'Delete')) {
            e.preventDefault();
        }
    }

    function handlePhoneClick() {
        if (phoneInput.selectionStart < 2) phoneInput.setSelectionRange(2, 2);
    }

    if (phoneInput) {
        ensurePlus7();
        phoneInput.addEventListener('input', validatePhone);
        phoneInput.addEventListener('keydown', handlePhoneKeydown);
        phoneInput.addEventListener('blur', ensurePlus7);
        phoneInput.addEventListener('click', handlePhoneClick);
    }

    async function loadUserProfile() {
        try {
            const res = await fetch('/api/profile/');
            if(!res.ok) return;
            const data = await res.json();
            if(data.first_name) document.getElementById('first_name').value = data.first_name;
            if(data.last_name) document.getElementById('last_name').value = data.last_name;
            if(data.email) document.getElementById('email').value = data.email;
            if(data.phone) {
                let phone = data.phone;
                if (!phone.startsWith('+7') && phone.startsWith('7')) {
                    phone = '+' + phone;
                }
                document.getElementById('phone').value = phone;
                ensurePlus7(); 
            }
        } catch(err) {
            console.error('Ошибка загрузки профиля:', err);
        }
    }

    async function loadCart() {
        try {
            const res = await fetch('/api/cart/');
            const data = await res.json();
            orderItemsEl.innerHTML = '';
            let total = 0;

            if(!data.items || data.items.length === 0){
                orderItemsEl.innerHTML = '<p>Корзина пуста.</p>';
                totalPriceEl.textContent = '0 ₽';
                return;
            }

            data.items.forEach(item => {
                const price = parseFloat(item.product.price) || 0;
                const totalItem = parseFloat(item.total) || (price * item.quantity);

                const li = document.createElement('li');
                li.className = 'order-item';
                li.innerHTML = `
                    <div class="item-image">
                        <img src="${item.product.image || '/static/img/default-product.png'}" alt="${item.product.name}">
                    </div>
                    <div class="item-details">
                        <h3>${item.product.name}</h3>
                        <div class="item-meta">
                            <span class="item-price">${price.toFixed(2)} ₽ × ${item.quantity}</span>
                            <span class="item-total">${totalItem.toFixed(2)} ₽</span>
                        </div>
                    </div>
                `;
                orderItemsEl.appendChild(li);
                total += totalItem;
            });
            totalPriceEl.textContent = total.toFixed(2) + ' ₽';
        } catch(err) {
            console.error(err);
            orderItemsEl.innerHTML = '<p style="color:red;">Ошибка загрузки корзины</p>';
            totalPriceEl.textContent = '0 ₽';
        }
    }

    async function loadPickupPoints() {
        try {
            const res = await fetch('/api/pickup_points/');
            const points = await res.json();
            pickupPointSelect.innerHTML = '';
            points.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name;
                pickupPointSelect.appendChild(opt);
            });
        } catch(err) {
            console.error('Ошибка загрузки пунктов выдачи:', err);
            pickupPointSelect.innerHTML = '<option value="">Ошибка загрузки пунктов</option>';
        }
    }

    await loadCart();
    await loadUserProfile();
    await loadPickupPoints();

    document.getElementById('order-form').addEventListener('submit', async e => {
        e.preventDefault();
        document.querySelectorAll('.form-error').forEach(el => el.textContent = '');

        validatePhone();
        const phoneValue = phoneInput.value;
        
        if (!phoneValue || phoneValue.length < 12) {
            document.getElementById('error-phone').textContent = 'Введите корректный номер телефона';
            return;
        }

        const payload = {
            first_name: document.getElementById('first_name').value,
            last_name: document.getElementById('last_name').value,
            email: document.getElementById('email').value,
            phone: phoneValue,
            pickup_point: document.getElementById('pickup_point').value,
        };

        try {
            const res = await fetch(createOrderUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });

            const text = await res.text(); 
            let data;
            try { data = JSON.parse(text); } 
            catch {
                console.error('Ответ не JSON:', text);
                alert('Ошибка на сервере: проверьте консоль');
                return;
            }

            if(res.ok){
                window.location.href = `/orders/${data.order_id}/`;
            } else if(data.errors){
                for(let field in data.errors){
                    const el = document.getElementById(`error-${field}`);
                    if(el) el.textContent = data.errors[field][0];
                }
            } else if(data.error){
                alert(data.error);
            } else {
                alert('Неизвестная ошибка при создании заказа');
            }

        } catch(err) {
            console.error(err);
            alert('Ошибка отправки запроса на сервер');
        }
    });
});