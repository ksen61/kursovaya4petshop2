document.addEventListener('DOMContentLoaded', async () => {
    const orderId = window.orderId;
    const orderEl = document.getElementById('order-detail');
    let userDateFormat = "%d.%m.%Y"; 

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

    try {
        await loadUserSettings();

        const res = await fetch(`/api/orders/${orderId}/`);
        if (!res.ok) {
            if (res.status === 403) throw new Error('Нет доступа к этому заказу');
            if (res.status === 404) throw new Error('Заказ не найден');
            throw new Error('Ошибка при загрузке заказа');
        }
        const order = await res.json();

        const formattedDate = formatDateByPattern(order.date_created, userDateFormat);

        orderEl.innerHTML = `
            <h2>Заказ №${order.id}</h2>
            <p><strong>Дата:</strong> ${formattedDate}</p>            
            <p><strong>Статус:</strong> ${order.status}</p>
            <p><strong>Пункт выдачи:</strong> ${order.pickup_point}</p>
            <p><strong>Итого:</strong> ${order.total_price} ₽</p>
            <h3 style="margin-top:20px;">Товары в заказе</h3>
            <ul>
                ${order.items.map(item => `
                <li>
                    <a href="/product/${item.product_id}/" style="color:#e9a630; text-decoration:none;">
                    ${item.product_name}
                    </a> — ${item.quantity} шт. (${item.price} ₽)
                </li>
                `).join('')}
            </ul>
        `;
    } catch (err) {
        console.error(err);
        orderEl.innerHTML = `<p style="color:red;">${err.message}</p>`;
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const toggleButton = document.getElementById('accessibility-toggle');
    if (!toggleButton) return;

    toggleButton.addEventListener('click', () => {
        document.body.classList.toggle('accessibility-mode');

        const icon = toggleButton.querySelector('i');
        if (document.body.classList.contains('accessibility-mode')) {
            icon.classList.replace('fa-eye', 'fa-low-vision');
            localStorage.setItem('accessibility', 'on');
        } else {
            icon.classList.replace('fa-low-vision', 'fa-eye');
            localStorage.setItem('accessibility', 'off');
        }
    });

    if (localStorage.getItem('accessibility') === 'on') {
        document.body.classList.add('accessibility-mode');
        const icon = toggleButton?.querySelector('i');
        if (icon) icon.classList.replace('fa-eye', 'fa-low-vision');
    }
});