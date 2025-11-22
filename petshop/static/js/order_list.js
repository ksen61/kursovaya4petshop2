document.addEventListener('DOMContentLoaded', async () => {
    const ordersListEl = document.getElementById('orders-list');
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
        const d = dayjs(date);
        switch (format) {
            case "%Y.%m.%d": return d.format("YYYY.MM.DD HH:mm");
            case "%m/%d/%Y": return d.format("MM/DD/YYYY HH:mm");
            default: return d.format("DD.MM.YYYY HH:mm");
        }
    }

    try {
        await loadUserSettings();

        const res = await fetch('/api/orders/history/');
        if (!res.ok) throw new Error('Ошибка при загрузке заказов');
        const orders = await res.json();

        if (orders.length === 0) {
            ordersListEl.innerHTML = '<p>У вас пока нет заказов.</p>';
            return;
        }

        ordersListEl.innerHTML = '';
        orders.forEach(order => {
            const div = document.createElement('div');
            div.className = 'order-card';

            const formattedDate = formatDateByPattern(order.date_created, userDateFormat);

            div.innerHTML = `
                <h3>Заказ №${order.id}</h3>
                <p><strong>Дата заказа:</strong> ${formattedDate}</p>
                <p><strong>Статус:</strong> ${order.status}</p>
                <p><strong>Пункт выдачи:</strong> ${order.pickup_point}</p>
                <p><strong>Итого:</strong> ${order.total_price} ₽</p>
                <a href="/orders/${order.id}/" class="btn-submit" style="margin-top: 10px; display: inline-block;">Подробнее</a>
            `;
            ordersListEl.appendChild(div);
        });
    } catch (err) {
        console.error(err);
        ordersListEl.innerHTML = '<p style="color:red;">Ошибка загрузки заказов</p>';
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