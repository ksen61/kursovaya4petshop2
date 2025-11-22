document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('review-form');
    const productId = form.dataset.productId;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const errorBox = document.getElementById('form-error');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorBox.textContent = '';

        const rating = document.getElementById('rating').value;
        const text = document.getElementById('text').value;

        try {
            const res = await fetch(`/reviews/add/${productId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ rating, text })
            });

            const textResponse = await res.text();
            let data;
            try {
                data = JSON.parse(textResponse);
            } catch {
                console.error('Ответ не JSON:', textResponse);
                alert('Ошибка сервера, проверьте консоль');
                return;
            }

            if (res.ok) {
                alert("Отзыв отправлен!");
                window.location.href = `/product/${productId}/`;
            } else if (data.error) {
                errorBox.textContent = data.error;
            } else if (data.errors) {
                const firstField = Object.keys(data.errors)[0];
                errorBox.textContent = `${firstField}: ${data.errors[firstField][0]}`;
            } else {
                errorBox.textContent = "Неизвестная ошибка при отправке отзыва";
            }

        } catch (err) {
            console.error(err);
            errorBox.textContent = "Ошибка запроса к серверу";
        }
    });
});