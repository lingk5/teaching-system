/**
 * 通用 HTTP 请求工具 (request.js)
 * 封装原生 fetch API，统一处理请求头、认证、错误响应
 * 依赖: js/config.js (API_BASE)
 */

class Request {
    constructor() {
        this.baseUrl = window.AppConfig?.API_BASE || 'http://127.0.0.1:5000/api';
    }

    /**
     * 发起请求的核心方法
     * @param {string} url - 接口路径 (如 '/courses')
     * @param {object} options - fetch 配置项
     */
    async _fetch(url, options = {}) {
        // 1. 处理 URL (去除开头的斜杠，防止双斜杠)
        const cleanUrl = url.startsWith('/') ? url.slice(1) : url;
        const fullUrl = `${this.baseUrl}/${cleanUrl}`;

        // 2. 默认请求头
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // 3. 自动携带 Token
        const token = localStorage.getItem('token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // 4. 合并配置
        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(fullUrl, config);
            
            // 5. 处理 401 未授权 (Token过期或无效)
            if (response.status === 401) {
                this._handleUnauthorized();
                throw new Error('登录已过期，请重新登录');
            }

            // 6. 解析响应数据
            let data;
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text(); // 处理非JSON响应
            }

            // 7. 处理非 2xx 错误
            if (!response.ok) {
                const errorMessage = (data && data.message) || `请求失败 (${response.status})`;
                throw new Error(errorMessage);
            }

            return data;

        } catch (error) {
            this._handleError(error);
            throw error; // 继续抛出，以便业务代码捕获
        }
    }

    /**
     * 处理 401 未授权
     */
    _handleUnauthorized() {
        console.warn('Token无效或已过期，跳转登录页...');
        localStorage.removeItem('token');
        localStorage.removeItem('userInfo');
        
        // 避免在登录页无限刷新
        if (!window.location.pathname.endsWith('login.html')) {
            window.location.href = window.AppConfig?.PAGES.LOGIN || 'login.html';
        }
    }

    /**
     * 统一错误处理
     */
    _handleError(error) {
        console.error('Request Error:', error);
        // 这里可以接入 Toast 组件，目前先用 alert 或 console
        // alert(error.message); 
    }

    /**
     * GET 请求
     * @param {string} url 
     * @param {object} params - 查询参数对象 { page: 1, size: 10 }
     */
    get(url, params = {}) {
        // 拼接查询参数
        const queryString = new URLSearchParams(params).toString();
        const urlWithParams = queryString ? `${url}?${queryString}` : url;
        return this._fetch(urlWithParams, { method: 'GET' });
    }

    /**
     * POST 请求
     * @param {string} url 
     * @param {object} data - 请求体数据
     */
    post(url, data = {}) {
        return this._fetch(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT 请求
     */
    put(url, data = {}) {
        return this._fetch(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE 请求
     */
    delete(url) {
        return this._fetch(url, { method: 'DELETE' });
    }

    /**
     * 文件上传 (特殊处理 Content-Type)
     * @param {string} url 
     * @param {FormData} formData 
     */
    upload(url, formData) {
        // 上传文件时不要手动设置 Content-Type，让浏览器自动设置 multipart/form-data boundary
        const token = localStorage.getItem('token');
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        return fetch(`${this.baseUrl}/${url.startsWith('/') ? url.slice(1) : url}`, {
            method: 'POST',
            headers: headers,
            body: formData
        }).then(async response => {
             if (response.status === 401) {
                this._handleUnauthorized();
                throw new Error('登录已过期');
            }
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || '上传失败');
            return data;
        });
    }
}

// 导出全局单例
window.request = new Request();
