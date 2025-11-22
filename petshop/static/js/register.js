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

function formatPhoneNumber(input) {
    let value = input.value.replace(/\D/g, '');
    
    if (value.startsWith('7') || value.startsWith('8')) {
        value = value.substring(1);
    }
    
    value = value.substring(0, 10);
    
    let formattedValue = '';
    if (value.length > 0) {
        formattedValue = '(' + value.substring(0, 3);
    }
    if (value.length > 3) {
        formattedValue += ') ' + value.substring(3, 6);
    }
    if (value.length > 6) {
        formattedValue += '-' + value.substring(6, 8);
    }
    if (value.length > 8) {
        formattedValue += '-' + value.substring(8, 10);
    }
    
    input.value = formattedValue;
}

function getCleanPhoneNumber(formattedPhone) {
    const digits = formattedPhone.replace(/\D/g, '');
    return '+7' + digits;
}

document.addEventListener('DOMContentLoaded', function() {
    const phoneInput = document.querySelector('input[name="phone"]');
    
    phoneInput.addEventListener('input', function(e) {
        formatPhoneNumber(e.target);
    });
    
    phoneInput.addEventListener('paste', function(e) {
        e.preventDefault();
        const pastedData = e.clipboardData.getData('text');
        this.value = pastedData;
        formatPhoneNumber(this);
    });
    
    phoneInput.addEventListener('keydown', function(e) {
        if ([8, 46, 9, 27, 13].includes(e.keyCode) || 
            (e.keyCode == 65 && e.ctrlKey === true) || 
            (e.keyCode == 67 && e.ctrlKey === true) ||
            (e.keyCode == 86 && e.ctrlKey === true) ||
            (e.keyCode == 88 && e.ctrlKey === true) ||
            (e.keyCode >= 35 && e.keyCode <= 39)) {
            return;
        }
        
        if ((e.keyCode < 48 || e.keyCode > 57) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    });
});

document.getElementById("register-form").addEventListener("submit", async function(e) {
    e.preventDefault();
    const form = e.target;

    const formattedPhone = form.phone.value;
    const cleanPhone = getCleanPhoneNumber(formattedPhone);

    const data = {
        email: form.email.value,
        first_name: form.first_name.value,
        last_name: form.last_name.value,
        phone: cleanPhone,
        password: form.password.value,
        date_of_birth: form.date_of_birth.value || null
    };

    const msgBox = document.getElementById("register-message");

    document.querySelectorAll(".error-message").forEach(el => el.textContent = "");
    msgBox.style.display = "block";

    try {
        const response = await fetch("/api/register/", {
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
            msgBox.textContent = result.message || "Регистрация успешна! Вы авторизованы.";
            form.reset();
            setTimeout(() => window.location.href = "/profile/", 1000);
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