const API_BASE = '/api';

function checkAuth() {
    const token = localStorage.getItem('token');
    const expires = localStorage.getItem('tokenExpires');
    
    if (!token) {
        window.location.href = 'login.html';
        return false;
    }
    
    if (expires && new Date(expires) < new Date()) {
        localStorage.clear();
        window.location.href = 'login.html?expired=1';
        return false;
    }
    
    try {
        const userInfoStr = localStorage.getItem('userInfo');
        if (userInfoStr && userInfoStr !== 'undefined' && userInfoStr !== 'null') {
            window.currentUser = JSON.parse(userInfoStr);
        } else {
            window.currentUser = {};
        }
    } catch (e) {
        console.error('Failed to parse userInfo from localStorage:', e);
        window.currentUser = {};
    }
    return true;
}

async function authFetch(url, options = {}) {
    const token = localStorage.getItem('token');
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
    
    const response = await fetch(url, options);
    
    if (response.status === 401) {
        localStorage.clear();
        alert('登录已过期，请重新登录');
        window.location.href = 'login.html';
        return;
    }
    
    return response;
}

function logout() {
    localStorage.clear();
    window.location.href = 'login.html';
}