function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

document.getElementById("login-form").addEventListener("submit", async function(e) {
    e.preventDefault();
    const form = e.target;
    const data = {
        email: form.email.value,
        password: form.password.value
    };

    const msgBox = document.getElementById("login-message");
    msgBox.style.display = "block";

    document.querySelectorAll(".error-message").forEach(el => el.textContent = "");

    try {
        const response = await fetch("/api/login/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrftoken
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            msgBox.style.color = "green";
            msgBox.textContent = result.message || "Вы вошли!";
            setTimeout(() => { window.location.href = "/profile/"; }, 1000);
        } else {
            msgBox.style.color = "red";

            if (result.errors) {
                for (let field in result.errors) {
                    const errorEl = document.getElementById(`error-${field}`);
                    if (errorEl) {
                        errorEl.textContent = result.errors[field].join(", ");
                    }
                }
                msgBox.textContent = "Исправьте ошибки в форме";
            } else if (result.Ошибка) {
                msgBox.textContent = result.Ошибка;
            }
        }
    } catch (err) {
        msgBox.style.color = "red";
        msgBox.textContent = "Ошибка сети: " + err;
        console.error(err);
    }
});