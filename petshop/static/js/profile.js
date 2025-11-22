if (localStorage.getItem('darkTheme') === 'true') {
    document.documentElement.classList.add('dark-theme');
}

document.addEventListener('DOMContentLoaded', async function() {
    const form = document.getElementById('profile-form');
    const msgBox = document.getElementById('profile-message');
    const phoneInput = document.getElementById('phone');
    const dateInput = document.getElementById('date_of_birth');
    const dateFormatSelect = document.getElementById('date_format');
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    function ensurePlus7() {
        if (!phoneInput.value) phoneInput.value = '+7';
    }
    ensurePlus7();
    phoneInput.addEventListener('input', () => {
        let numbers = phoneInput.value.replace(/\D/g,'');
        if (!numbers.startsWith('7')) numbers='7'+numbers;
        phoneInput.value='+'+numbers.slice(0,11);
    });
    phoneInput.addEventListener('keydown', e => {
        if ((phoneInput.selectionStart<=2) && (e.key==='Backspace'||e.key==='Delete')) e.preventDefault();
    });
    phoneInput.addEventListener('blur', ensurePlus7);
    phoneInput.addEventListener('click', () => {
        if (phoneInput.selectionStart<2) phoneInput.setSelectionRange(2,2);
    });

    dateInput.addEventListener('input', () => {
        dateInput.value = dateInput.value.replace(/[^0-9.\/]/g, ''); 
    });

    function formatDateByPattern(dateString, format) {
        if (!dateString) return "";
        let year, month, day;

        if (dateString.includes('-')) [year, month, day] = dateString.split("-");
        else if (dateString.includes('.')) [day, month, year] = dateString.split(".");
        else if (dateString.includes('/')) [month, day, year] = dateString.split("/");

        if (!day || !month || !year) return "";

        switch (format) {
            case "%d.%m.%Y": return `${day}.${month}.${year}`;
            case "%Y.%m.%d": return `${year}.${month}.${day}`;
            case "%m/%d/%Y": return `${month}/${day}/${year}`;
            default: return `${day}.${month}.${year}`;
        }
    }

    function convertToISO(dateString, format) {
        if (!dateString) return null;
        let day, month, year;
        switch (format) {
            case "%d.%m.%Y": [day, month, year] = dateString.split("."); break;
            case "%Y.%m.%d": [year, month, day] = dateString.split("."); break;
            case "%m/%d/%Y": [month, day, year] = dateString.split("/"); break;
            default: return null;
        }
        if (!day || !month || !year) return null;
        return `${year}-${month.padStart(2,'0')}-${day.padStart(2,'0')}`;
    }
    function formatPlaceholder(format) {
        switch (format) {
            case "%d.%m.%Y": return "ДД.ММ.ГГГГ";
            case "%Y.%m.%d": return "ГГГГ.ММ.ДД";
            case "%m/%d/%Y": return "ММ/ДД/ГГГГ";
            default: return "ДД.ММ.ГГГГ";
        }
    }
    
    async function loadProfile() {
        try {
            const res = await fetch('/api/profile/', { headers: {'X-CSRFToken': csrftoken} });
            if (!res.ok) throw new Error('Не удалось загрузить профиль');
            const data = await res.json();

            document.getElementById('first_name').value = data.first_name || '';
            document.getElementById('last_name').value = data.last_name || '';
            document.getElementById('email').value = data.email || '';
            document.getElementById('phone').value = data.phone || '+7';
            document.getElementById('theme').checked = data.theme || false;

            const format = data.date_format || "%d.%m.%Y";
            dateFormatSelect.value = format;
            dateFormatSelect.dataset.prevFormat = format;
            dateInput.placeholder = formatPlaceholder(format);


            if (data.date_of_birth) {
                const formatted = formatDateByPattern(data.date_of_birth, format);
                dateInput.value = formatted;
            }

        } catch (err) {
            msgBox.style.color='red';
            msgBox.textContent = err;
        }
    }
    await loadProfile();

    dateFormatSelect.addEventListener('change', () => {
        const oldFormat = dateFormatSelect.dataset.prevFormat || "%d.%m.%Y";
        const iso = convertToISO(dateInput.value, oldFormat);
        const newFormat = dateFormatSelect.value;
        const formatted = iso ? formatDateByPattern(iso, newFormat) : "";
        dateInput.value = formatted; 
        dateInput.placeholder = formatPlaceholder(newFormat);
        dateFormatSelect.dataset.prevFormat = newFormat;
    });
    

    form.addEventListener('submit', async e => {
        e.preventDefault();
        document.querySelectorAll(".error-message").forEach(el => el.textContent = "");

        let isoDate = convertToISO(dateInput.value, dateFormatSelect.value);

        if (dateInput.value && !isoDate) {
            document.getElementById('error-date_of_birth').textContent = "Неверный формат даты";
            return; 
        }


        const data = {
            first_name: form.first_name.value,
            last_name: form.last_name.value,
            email: form.email.value,
            phone: form.phone.value,
            date_of_birth: isoDate,
            date_format: dateFormatSelect.value,
            theme: form.theme.checked
        };

        try {
            const res = await fetch('/api/profile/', {
                method: 'PUT',
                headers: {'Content-Type':'application/json','X-CSRFToken':csrftoken},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            msgBox.style.display='block';
            if (res.ok) {
                msgBox.style.color='green';
                msgBox.textContent = result.message || 'Профиль обновлён!';
            } else {
                msgBox.style.color='red';
                if (result.errors) {
                    for (let field in result.errors) {
                        const errorEl = document.getElementById(`error-${field}`);
                        if (errorEl) errorEl.textContent = result.errors[field].join(", ");
                    }
                    msgBox.textContent = "Исправьте ошибки в форме";
                } else if (result.Ошибка) {
                    msgBox.textContent = result.Ошибка;
                } else {
                    msgBox.textContent = JSON.stringify(result);
                }
            }
        } catch(err) {
            msgBox.style.display='block';
            msgBox.style.color='red';
            msgBox.textContent='Ошибка сети: '+err;
        }
    });

    document.getElementById('logout-btn').addEventListener('click', async () => {
        try {
            const res = await fetch('/api/logout/', {method:'POST', headers:{'X-CSRFToken':csrftoken}});
            if(res.ok) window.location.href='/login/';
            else alert('Не удалось выйти');
        } catch(err) { alert(err); }
    });

    document.getElementById('delete-btn').addEventListener('click', async () => {
        if(!confirm('Вы точно хотите удалить аккаунт?')) return;
        try {
            const res = await fetch('/api/profile/', {method:'DELETE', headers:{'X-CSRFToken':csrftoken}});
            if(res.ok) window.location.href='/';
            else alert('Не удалось удалить аккаунт');
        } catch(err) { alert(err); }
    });

});