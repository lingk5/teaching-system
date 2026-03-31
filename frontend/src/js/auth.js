const API_BASE = '/api';

const ROLE_HOME_PAGE = {
    admin: 'users.html',
    teacher: 'dashboard.html',
    assistant: 'analytics.html'
};

const ROLE_ALLOWED_PAGES = {
    admin: new Set(['dashboard.html', 'courses.html', 'users.html', 'students.html', 'data-import.html', 'analytics.html', 'warnings.html', 'index.html']),
    teacher: new Set(['dashboard.html', 'courses.html', 'students.html', 'data-import.html', 'analytics.html', 'warnings.html', 'index.html']),
    assistant: new Set(['dashboard.html', 'courses.html', 'students.html', 'analytics.html', 'warnings.html', 'index.html'])
};

const ROLE_CAPABILITIES = {
    admin: new Set(['manage_users', 'manage_courses', 'manage_students', 'import_data', 'process_warnings', 'generate_warnings', 'export_reports']),
    teacher: new Set(['manage_courses', 'manage_students', 'import_data', 'process_warnings', 'generate_warnings', 'export_reports']),
    assistant: new Set([])
};

const NAV_PAGE_MAP = {
    'nav-dashboard': 'dashboard.html',
    'nav-courses': 'courses.html',
    'nav-users': 'users.html',
    'nav-students': 'students.html',
    'nav-import': 'data-import.html',
    'nav-analytics': 'analytics.html',
    'nav-warnings': 'warnings.html'
};

function getCurrentPageName() {
    const path = window.location.pathname || '';
    return path.split('/').pop() || 'dashboard.html';
}

function normalizeRole(role) {
    return (role || 'teacher').toLowerCase();
}

function getStoredUser() {
    try {
        const userInfoStr = localStorage.getItem('userInfo');
        return userInfoStr ? JSON.parse(userInfoStr) : {};
    } catch (e) {
        return {};
    }
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

function roleHasCapability(role, capability) {
    const normalized = normalizeRole(role);
    const capabilitySet = ROLE_CAPABILITIES[normalized] || new Set();
    return capabilitySet.has(capability);
}

function currentUserCan(capability) {
    const user = getStoredUser();
    return roleHasCapability(user.role, capability);
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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyRoleUI, { once: true });
    } else {
        applyRoleUI();
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
        const user = getStoredUser();
        
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
    const user = getStoredUser();
    const role = normalizeRole(user.role);

    const userRoleEl = document.getElementById('userRole');
    if (userRoleEl) {
        userRoleEl.textContent = getUserRoleText(role);
    }

    Object.entries(NAV_PAGE_MAP).forEach(([elementId, pageName]) => {
        document.querySelectorAll(`#${elementId}`).forEach((el) => {
            el.style.display = canRoleAccessPage(role, pageName) ? '' : 'none';
        });
    });

    document.querySelectorAll('[data-capability]').forEach((el) => {
        const capability = el.dataset?.capability;
        if (!capability) {
            return;
        }

        el.style.display = roleHasCapability(role, capability) ? '' : 'none';
    });

    if (role === 'assistant') {
        document.querySelectorAll(
            'button[onclick*="checkWarnings"], ' +
            'button[onclick*="showAddStudentModal"], ' +
            'button[onclick*="addStudent"], ' +
            'button[onclick*="editStudent"], ' +
            'button[onclick*="deleteStudent"], ' +
            'button[onclick*="addClass"], ' +
            'button[onclick*="createCourse"], ' +
            'button[onclick*="openProcessModal"], ' +
            'button[onclick*="submitProcess"]'
        ).forEach((el) => {
            el.style.display = 'none';
        });
    }
}
