// 全局配置文件
// 建议在 index.html 或所有页面的 head 中最先引入

const defaultApiBase = (
    typeof window !== 'undefined' && window.location && window.location.origin
) ? `${window.location.origin}/api` : 'http://127.0.0.1:5000/api';

const CONFIG = {
    // 后端 API 基础地址 (末尾不要带斜杠)
    // 默认使用同源地址，避免本地代理影响 127.0.0.1 请求
    API_BASE: defaultApiBase,
    
    // 页面路由配置 (用于跳转)
    PAGES: {
        LOGIN: 'login.html',
        DASHBOARD: 'dashboard.html',
        COURSES: 'courses.html',
        STUDENTS: 'students.html',
        IMPORT: 'data-import.html',
        ANALYTICS: 'analytics.html',
        WARNINGS: 'warnings.html'
    },

    // 系统名称
    APP_NAME: '教学效果监督系统'
};

// 防止变量被篡改 (可选)
Object.freeze(CONFIG);

// 将配置挂载到 window 对象，方便全局访问
window.AppConfig = CONFIG;
window.API_BASE = CONFIG.API_BASE; // 兼容旧代码
