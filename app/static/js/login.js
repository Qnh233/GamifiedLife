async function submitAuth(action) {
    const username = (document.getElementById('username').value || '').trim();
    const password = document.getElementById('password').value || '';
    const errorBox = document.getElementById('auth-error');

    errorBox.classList.add('d-none');
    errorBox.textContent = '';

    if (!username || !password) {
        errorBox.textContent = '用户名和密码不能为空';
        errorBox.classList.remove('d-none');
        return;
    }

    const endpoint = action === 'register' ? '/api/auth/register' : '/api/auth/login';

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();
        if (!res.ok) {
            errorBox.textContent = data.error || '认证失败，请重试';
            errorBox.classList.remove('d-none');
            return;
        }

        window.location.href = '/';
    } catch (error) {
        errorBox.textContent = '网络异常，请稍后再试';
        errorBox.classList.remove('d-none');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const onEnter = (event) => {
        if (event.key === 'Enter') {
            submitAuth('login');
        }
    };
    document.getElementById('username').addEventListener('keypress', onEnter);
    document.getElementById('password').addEventListener('keypress', onEnter);
});

