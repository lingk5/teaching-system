const API_BASE = '/api';

const ROLE_HOME_PAGE = {
    admin: 'dashboard.html',
    teacher: 'dashboard.html',
    assistant: 'analytics.html'
};

const ROLE_ALLOWED_PAGES = {
    admin: new Set(['dashboard.html', 'courses.html', 'students.html', 'data-import.html', 'analytics.html', 'warnings.html', 'index.html']),
    teacher: new Set(['dashboard.html', 'courses.html', 'students.html', 'data-import.html', 'analytics.html', 'warnings.html', 'index.html']),
    assistant: new Set(['dashboard.html', 'courses.html', 'students.html', 'analytics.html', 'warnings.html', 'index.html'])
};

function getCurrentPageName() {
    const path = window.location.pathname || '';
    return path.split('/').pop() || 'dashboard.html';
}

function normalizeRole(role) {
    return (role || 'teacher').toLowerCase();
}

function getRoleHomePage(role) {
    const normalized = normalizeRole(role);
    return ROLE_HOME_PAGE[normalized] || 'dashboard.html';
}

function canRoleAccessPage(role, pageName) {
    const normalized = normalizeRole(role);
    const allowSet = ROLE_ALLOWED_PAGES[normalized] || ROLE_ALLOWED_PAGES.teacher;
    return allowSet.has(pageName);
}

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

    const role = normalizeRole(window.currentUser.role);
    const pageName = getCurrentPageName();
    if (!canRoleAccessPage(role, pageName)) {
        window.location.href = getRoleHomePage(role);
        return false;
    }

    applyRoleUI();
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

function getUserRoleText(role) {
    const roleMap = {
        'admin': '管理员',
        'teacher': '教师',
        'assistant': '助教'
    };
    return roleMap[role] || '用户';
}

function loadUserInfoToUI() {
    try {
        const userInfoStr = localStorage.getItem('userInfo');
        const user = userInfoStr ? JSON.parse(userInfoStr) : {};
        
        // 更新用户名
        const userNameEl = document.getElementById('userName');
        if (userNameEl) {
            userNameEl.textContent = user.name || user.username || '用户';
        }
        
        // 更新用户角色
        const userRoleEl = document.getElementById('userRole');
        if (userRoleEl) {
            userRoleEl.textContent = getUserRoleText(user.role);
        }
    } catch (e) {
        console.error('用户信息加载失败:', e);
    }
}

function applyRoleUI() {
    const userInfoStr = localStorage.getItem('userInfo');
    let user = {};
    try {
        user = userInfoStr ? JSON.parse(userInfoStr) : {};
    } catch (e) {
        user = {};
    }
    const role = normalizeRole(user.role);

    const userRoleEl = document.getElementById('userRole');
    if (userRoleEl) {
        userRoleEl.textContent = getUserRoleText(role);
    }

    if (role !== 'admin') {
        document.querySelectorAll('[data-role="admin-only"]').forEach((el) => {
            el.style.display = 'none';
        });
    }

    if (role === 'assistant') {
        document.querySelectorAll('#nav-import').forEach((el) => {
            el.style.display = 'none';
        });
        document.querySelectorAll('[data-role="import"]').forEach((el) => {
            el.style.display = 'none';
        });
        document.querySelectorAll('[data-role="manage"]').forEach((el) => {
            el.style.display = 'none';
        });
        // 兼容旧页面尚未打 data-role 的按钮
        document.querySelectorAll(
            'button[onclick*="checkWarnings"], ' +
            'button[onclick*="showAddStudentModal"], ' +
            'button[onclick*="addStudent"], ' +
            'button[onclick*="editStudent"], ' +
            'button[onclick*="deleteStudent"], ' +
            'button[onclick*="addClass"], ' +
            'button[onclick*="createCourse"]'
        ).forEach((el) => {
            el.style.display = 'none';
        });
    }
}
