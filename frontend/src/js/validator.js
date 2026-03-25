/**
 * 表单验证工具类
 * 使用示例：
 * const errors = Validator.validate([
 *     { value: username, rules: ['required', 'length:3,20'], name: '用户名' }
 * ]);
 */
const Validator = {
    // 验证非空
    required: (value, fieldName) => {
        if (!value || value.trim() === '') {
            return `${fieldName}不能为空`;
        }
        return null;
    },
    
    // 验证长度
    length: (value, min, max, fieldName) => {
        const len = value.length;
        if (len < min || len > max) {
            return `${fieldName}长度必须在${min}-${max}个字符之间`;
        }
        return null;
    },
    
    // 验证学号（纯数字）
    studentNo: (value, fieldName = '学号') => {
        if (!/^\d+$/.test(value)) {
            return `${fieldName}必须为纯数字`;
        }
        if (value.length < 5 || value.length > 20) {
            return `${fieldName}长度必须在5-20位之间`;
        }
        return null;
    },
    
    // 验证分数（0-100）
    score: (value, fieldName = '分数') => {
        const num = parseFloat(value);
        if (isNaN(num)) {
            return `${fieldName}必须是数字`;
        }
        if (num < 0 || num > 100) {
            return `${fieldName}必须在0-100之间`;
        }
        return null;
    },
    
    // 验证日期格式（YYYY-MM-DD）
    date: (value, fieldName = '日期') => {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
            return `${fieldName}格式必须为YYYY-MM-DD（如2024-01-15）`;
        }
        // 检查是否有效日期
        const date = new Date(value);
        if (isNaN(date.getTime())) {
            return `${fieldName}不是有效日期`;
        }
        return null;
    },
    
    // 验证邮箱
    email: (value, fieldName = '邮箱') => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            return `${fieldName}格式不正确`;
        }
        return null;
    },
    
    // 验证手机号（中国大陆）
    phone: (value, fieldName = '手机号') => {
        if (!/^1[3-9]\d{9}$/.test(value)) {
            return `${fieldName}格式不正确（请输入11位手机号）`;
        }
        return null;
    },
    
    // 验证下拉框选择
    selected: (value, fieldName = '选项') => {
        if (!value || value === '' || value === '请选择') {
            return `请选择${fieldName}`;
        }
        return null;
    },
    
    // 主验证方法
    validate: function(fields) {
        const errors = [];
        for (const field of fields) {
            const { value, rules, name } = field;
            
            for (const rule of rules) {
                let error = null;
                
                // 解析规则参数（如 length:3,20）
                if (rule.includes(':')) {
                    const [ruleName, params] = rule.split(':');
                    const args = params.split(',').map(p => isNaN(p) ? p : Number(p));
                    
                    switch(ruleName) {
                        case 'length':
                            error = this.length(value, args[0], args[1], name);
                            break;
                    }
                } else {
                    // 无参数规则
                    switch(rule) {
                        case 'required':
                            error = this.required(value, name);
                            break;
                        case 'studentNo':
                            error = this.studentNo(value, name);
                            break;
                        case 'score':
                            error = this.score(value, name);
                            break;
                        case 'date':
                            error = this.date(value, name);
                            break;
                        case 'email':
                            error = this.email(value, name);
                            break;
                        case 'phone':
                            error = this.phone(value, name);
                            break;
                        case 'selected':
                            error = this.selected(value, name);
                            break;
                    }
                }
                
                if (error) {
                    errors.push(error);
                    break; // 该字段有错误就停止检查该字段的其他规则
                }
            }
        }
        return errors;
    },
    
    // 显示错误提示（通用）
    showError: function(message, containerId = null) {
        if (containerId) {
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = `<div class="alert alert-danger" role="alert">${message}</div>`;
                return;
            }
        }
        alert(message);
    },
    
    // 清除错误提示
    clearError: function(containerId = null) {
        if (containerId) {
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = '';
            }
        }
    }
};
