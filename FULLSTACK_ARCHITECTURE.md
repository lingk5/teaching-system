# 教学效果监督系统 - 全栈架构规范文档

> **文档目的**: 为新加入的开发者或 AI 助手提供快速上手指南，理解项目全局规范、技术栈和跨端契约  
> **最后更新**: 2026-03-31
> **维护者**: 系统架构团队

---

## 📑 目录

1. [当前开发进度快照](#1-当前开发进度快照)
2. [技术栈全景](#2-技术栈全景)
3. [工程拓扑结构](#3-工程拓扑结构)
4. [核心数据链路](#4-核心数据链路)
5. [API 交互契约](#5-api-交互契约)
6. [数据库规范](#6-数据库规范)
7. [全栈功能开发 SOP](#7-全栈功能开发标准流程 sop)
8. [常见问题与避坑指南](#8-常见问题与避坑指南)

---

## 1. 当前开发进度快照

### 1.1 当前阶段判断

- **总体阶段**: `Beta / 可演示版本`
- **真实状态**: 已完成“登录 -> 管理员用户管理 -> 课程/班级 -> 学生 -> 数据导入 -> 预警生成/处理 -> 基础导出”的主闭环，但“学情分析可视化、统计口径统一、教师数据范围控制、测试规模扩充”仍未完成
- **数据库现状**: 代码默认连接 **MySQL**，`SQLite` 相关描述属于早期方案或论文表述，不能再作为当前部署基线
- **文档结论**: 本项目目前适合课程设计/毕设演示与小范围试运行，不适合直接按“生产完成态”对外宣称

### 1.2 模块进度矩阵

| 模块 | 当前状态 | 实际进展 | 说明 |
|------|----------|----------|------|
| 认证登录 | ✅ 已完成 | 登录、注册、`JWT`、`/me` 已实现 | 前端 `login.html` 已接入真实接口 |
| 用户管理 | ✅ 已完成 | 管理员专用 `users.html`、用户列表/创建/更新接口已恢复 | 仅管理员可见且默认跳转到该页 |
| 课程管理 | 🟡 基本完成 | 课程列表、创建课程、创建班级已完成 | 课程统计中的出勤率仍为占位值 |
| 学生管理 | ✅ 已完成 | 学生列表、添加、编辑、删除、详情弹窗已打通 | 搜索仍为前端内存过滤 |
| 数据导入 | 🟡 基本完成 | 学生、考勤、作业、测验、互动导入与模板下载已实现 | 期末成绩仍复用测验导入逻辑 |
| 智能预警 | ✅ 已完成 | 预警生成、列表、处理、历史记录已实现 | 当前按课程全量扫描，缺少缓存/批处理 |
| 仪表盘 | 🟡 半完成 | 学生数、预警数来自真实接口 | 出勤率、作业率、趋势图仍含模拟数据 |
| 学情分析 | 🟡 半完成 | 后端概览接口与学生画像接口存在 | 页面图表仍大量使用模拟数据填充 |
| 导出报表 | 🟡 基本完成 | 学生、成绩、考勤、预警导出已实现 | 评分权重与预警引擎尚未完全统一 |
| 环境与脚本 | ✅ 已完成 | `fix_env.py`、`start.sh`、`smart_start.sh`、MySQL 初始化文档已具备 | 启动脚本仍偏本地开发用法 |
| 自动化测试 | 🟡 基本建立 | 已补 `unittest` + `node:test` 最小回归集 | 目前覆盖权限与管理员界面，尚未覆盖导入/导出全链路 |

### 1.3 已完成的关键开发细节

- 后端已采用 Flask 蓝图拆分 `auth`、`courses`、`data`、`analytics`、`warnings`、`export`
- 数据模型已拆分为 `User`、`Course`、`Class`、`Student`、`Attendance`、`Homework`、`Quiz`、`Interaction`、`Warning`
- 预警引擎 `WarningEngine` 已实现综合评分、等级判定、短板归因与建议生成
- 前端公共层已抽出 `config.js`、`request.js`、`auth.js`、`validator.js`
- 已恢复管理员专用 `users.html` 页面与 `/api/auth/users*` 接口，支持用户列表、创建、更新、停用
- 已建立基于 `permissions.py` + `auth.js` 的前后端统一角色能力矩阵：`admin / teacher / assistant`
- `students.html`、`courses.html`、`warnings.html`、`data-import.html` 与真实 API 已有可运行联动
- 导入流程已实现 Excel/CSV 解析、空行剔除、前后空格清洗、错误行收集与模板下载
- 已建立最小自动化回归：当前为 11 条后端测试与 3 条前端测试，覆盖管理员界面、权限边界与默认账号

### 1.4 未完成与待收口项

- `analytics.html` 仍存在明显模拟数据逻辑，图表并未完全基于后端真实返回值渲染
- `dashboard.html` 的出勤率、作业率、本周趋势仍未接入真实统计
- `courses.py` 中课程/班级出勤率仍写死为 `85`
- 期末成绩未独立建模，前端仍将 `final` 映射为 `quiz` 导入
- 学生检索、预警筛选、分页还没有形成统一的后端查询规范
- 管理员页面已恢复，但用户管理功能目前仍是基础 CRUD，未扩展为审计日志、密码策略、批量操作
- 文档中仍混有 `SQLite`、`全部核心功能已完成` 等过期表述，已从本次版本开始纠正

### 1.5 当前主要风险

| 风险项 | 影响 | 当前表现 |
|--------|------|----------|
| 教师数据范围控制未闭环 | 中高 | 教师与管理员虽已分离界面，但教师仍未严格限制为“仅访问自己课程” |
| 统计口径不统一 | 高 | 预警引擎使用 `30/30/30/10`，导出成绩报表使用 `30/30/40` |
| 前端展示与真实数据脱节 | 高 | 仪表盘和学情分析仍含模拟值，容易误判“功能已完全落地” |
| 全量扫描性能风险 | 中 | 预警生成按课程逐人计算，数据规模上来后会变慢 |
| 文档漂移 | 中 | 论文、架构文档、交接文档曾长期与实现脱节 |
| 启动脚本安全性 | 中 | `smart_start.sh` 会直接 `kill -9` 端口占用进程，更适合本机开发而非共享环境 |

### 1.6 下一轮迭代建议

1. 统一评分公式、指标命名和导入/导出口径，消除“页面一套、预警一套、导出一套”的分裂状态
2. 补完 `analytics.html` 与 `dashboard.html` 的真实数据渲染，移除模拟图表
3. 将教师权限进一步收口为“仅访问自己课程/班级/学生/预警”
4. 为预警引擎增加缓存、增量刷新或定时任务机制
5. 在现有回归集基础上继续补齐导入、导出、课程管理全链路自动化校验

---

## 2. 技术栈全景

### 2.1 前端技术栈

| 技术分类 | 技术选型 | 版本 | 用途说明 |
|---------|---------|------|---------|
| **UI 框架** | Bootstrap | 5.3.0 | 响应式 UI 组件库（通过 CDN 引入） |
| **图标库** | Bootstrap Icons | latest | 图标资源（通过 CDN 引入） |
| **JavaScript** | Vanilla JS | ES6+ | 原生 JavaScript，无框架依赖 |
| **HTTP 客户端** | Fetch API | native | 原生 fetch，封装在 `request.js` |
| **状态管理** | LocalStorage | native | Token、用户信息存储 |
| **页面路由** | MPA (Multi-Page App) | - | 传统多页应用，非 SPA |

### 2.2 后端技术栈

| 技术分类 | 技术选型 | 版本 | 用途说明 |
|---------|---------|------|---------|
| **Web 框架** | Flask | 3.0.3 | 轻量级 Python Web 框架 |
| **ORM** | SQLAlchemy + Flask-SQLAlchemy | 2.0.36 / 3.1.1 | 对象关系映射 |
| **认证授权** | Flask-JWT-Extended | 4.6.0 | JWT Token 管理（有效期 7 天） |
| **CORS** | Flask-Cors | 5.0.0 | 跨域资源共享支持 |
| **数据验证** | Marshmallow | 3.22.0 | 数据序列化与验证 |
| **数据处理** | Pandas + OpenPyXL | 2.0.3 / 3.1.5 | Excel 导入导出 |
| **密码加密** | Werkzeug | 3.0.6 | password_hash 生成与验证 |
| **环境配置** | python-dotenv | 1.0.1 | `.env` 文件加载 |

### 2.3 数据库

| 技术项 | 选型 | 说明 |
|-------|------|------|
| **数据库类型** | MySQL | 当前代码默认连接方式 |
| **连接方式** | `.env` 或 `DATABASE_URI` | 运行时从环境变量读取 |
| **默认库名** | `teaching_system` | 本地开发默认库 |
| **适用场景** | 本地开发、小规模试运行 | 已优于 SQLite，但尚未完成生产级部署治理 |

> 注：仓库中的 `SQLite` 描述属于早期方案，当前实现已以 `PyMySQL + MySQL` 为主。

### 2.4 缓存（当前未使用）

- ❌ **无专门缓存系统**（如 Redis/Memcached）
- ✅ **替代方案**: 依赖 MySQL 聚合查询和 Flask 进程内计算

### 2.5 部署/构建工具

| 工具类型 | 工具名称 | 用途 |
|---------|---------|------|
| **包管理** | pip + venv | Python 虚拟环境管理 |
| **依赖清单** | `requirements.txt` | Python 依赖锁定 |
| **环境配置** | `.env` | 密钥和配置变量 |
| **启动脚本** | `start.bat` / `start.sh` / `smart_start.sh` | 本地一键启动与端口占用处理 |
| **构建工具** | 无 | 前端无打包编译过程 |

---

## 3. 工程拓扑结构

### 3.1 完整目录树

```
teaching-system/
├── backend/                          # 后端代码目录
│   ├── app/                         # 应用主包
│   │   ├── __init__.py             # Flask 应用工厂 (create_app)
│   │   ├── models/                 # 数据模型层
│   │   │   ├── __init__.py        # 导出所有模型 (db 对象)
│   │   │   ├── user.py            # User 模型 (教师用户)
│   │   │   ├── course.py          # Course, Class, Student 模型
│   │   │   ├── data.py            # Attendance, Homework, Quiz, Interaction 模型
│   │   │   └── warning.py         # Warning 预警模型
│   │   ├── routes/                 # 路由控制器层 (Blueprint)
│   │   │   ├── auth.py            # 认证相关 (/api/auth)
│   │   │   ├── courses.py         # 课程管理 (/api/courses)
│   │   │   ├── data.py            # 数据导入 (/api/data)
│   │   │   ├── analytics.py       # 数据分析 (/api/analytics)
│   │   │   ├── warnings.py        # 预警管理 (/api/warnings)
│   │   │   └── export.py          # 数据导出 (/api/export)
│   │   └── services/               # 业务逻辑服务层
│   │       └── warning_engine.py   # 预警规则引擎 (核心算法)
│   ├── instance/                    # 历史 SQLite 目录（当前 MySQL 模式下通常为空）
│   ├── templates/                   # Excel 模板文件
│   ├── venv/                        # Python 虚拟环境
│   ├── .env                         # 环境变量配置
│   ├── requirements.txt             # Python 依赖清单
│   ├── smart_start.sh               # 智能启动脚本（自动处理端口占用）
│   └── run.py                       # 应用入口文件
│
├── frontend/                        # 前端代码目录
│   └── src/
│       ├── js/                      # JavaScript 公共模块
│       │   ├── config.js           # 全局配置 (API_BASE 等)
│       │   ├── auth.js             # 认证工具 (checkAuth, authFetch)
│       │   ├── request.js          # HTTP 请求封装 (Request 类)
│       │   └── validator.js        # 表单验证工具
│       └── pages/                   # HTML 页面
│           ├── index.html          # 首页 (测试页面)
│           ├── login.html          # 登录页
│           ├── dashboard.html      # 仪表盘
│           ├── courses.html        # 课程管理
│           ├── users.html          # 管理员用户管理
│           ├── students.html       # 学生管理
│           ├── data-import.html    # 数据导入
│           ├── analytics.html      # 数据分析
│           └── warnings.html       # 预警监控
├── backend/tests/                   # Python 回归测试
├── frontend/tests/                  # 前端角色权限测试
│
└── .gitignore                       # Git 忽略配置
```

### 3.2 前后端分离边界

#### 物理分离

```
/frontend/src/          ← 前端代码
/backend/               ← 后端代码
/backend/instance/      ← 数据库文件
```

#### 通信协议

- **协议**: RESTful API
- **API 前缀**: `/api/*`
- **数据格式**: JSON
- **认证方式**: JWT Token (Bearer Authentication)
- **基础地址**: 
  - 开发环境：`http://127.0.0.1:5000/api`
  - 生产环境：需配置反向代理（Nginx/Apache）

#### 静态文件服务

Flask 直接托管前端静态资源：

```python
# backend/app/__init__.py
frontend_src = os.path.abspath(os.path.join(basedir, '..', '..', 'frontend', 'src'))
app = Flask(__name__, static_folder=frontend_src, static_url_path='')
```

访问示例：
- `http://localhost:5000/pages/login.html` → 返回登录页
- `http://localhost:5000/js/request.js` → 返回 JS 文件

### 3.3 公共包位置

#### 前端共享模块 (`/frontend/src/js/`)

| 文件名 | 功能描述 | 核心函数/对象 |
|-------|---------|--------------|
| `config.js` | 全局配置常量 | `CONFIG`, `window.AppConfig` |
| `auth.js` | 认证工具 | `checkAuth()`, `authFetch()`, `logout()` |
| `request.js` | HTTP 请求封装 | `window.request` (GET/POST/PUT/DELETE/Upload) |
| `validator.js` | 表单验证 | `Validator.validate()`, `Validator.showError()` |

#### 后端共享模块

**Models 层** (`/backend/app/models/`):
- `__init__.py`: 导出 `db` 对象和所有模型类
- 各模型文件：定义表结构和关系映射

**Services 层** (`/backend/app/services/`):
- `warning_engine.py`: 预警规则引擎（核心业务逻辑）
  - 综合评分计算
  - 预警等级判定
  - 干预建议生成

---

## 3. 核心数据链路

### 3.1 典型请求生命周期

以"获取课程列表"为例：

```
┌─────────────────┐
│ 1. 用户访问页面  │
│ /courses.html   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 2. Flask 路由匹配│
│ @app.route('/courses')
│ 返回 HTML 页面    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 3. 页面加载 JS   │
│ - 引入 config.js│
│ - 引入 auth.js  │
│ - 检查登录状态  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 4. 发起 API 请求  │
│ request.get(    │
│   '/courses/'   │
│ )               │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 5. Request 封装  │
│ - 读取 Token    │
│ - 添加请求头    │
│ Authorization:  │
│   Bearer <token>│
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 6. Flask 接收请求│
│ - CORS 中间件    │
│ - JWT 验证       │
│ - 路由匹配       │
│ @courses_bp     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 7. 业务逻辑处理  │
│ Course.query.   │
│ all()           │
│ - 遍历课程      │
│ - 查询班级      │
│ - 统计学生数    │
│ - 计算预警数    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 8. ORM 生成 SQL  │
│ SELECT * FROM   │
│ courses;        │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 9. SQLite 执行   │
│ 返回结果集      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 10. 构建 JSON    │
│ {success:true,  │
│  data:[...]}    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ 11. 前端接收响应 │
│ - 解析 JSON      │
│ - DOM 操作渲染   │
└─────────────────┘
```

### 3.2 关键代码位置

#### 前端发起请求

```javascript
// frontend/src/pages/courses.html (line 268)
async function loadCourses() {
    const response = await request.get('/courses/');
    const courses = response.data || [];
    renderCourses(courses);
}
```

#### 后端处理请求

```python
# backend/app/routes/courses.py (line 9-60)
@courses_bp.route('/', methods=['GET'])
@jwt_required()
def get_courses():
    try:
        courses = Course.query.all()
        data = []
        for course in courses:
            # 业务逻辑处理
            classes = Class.query.filter_by(course_id=course.id).all()
            # ...
            data.append({...})
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
```

#### Request 封装

```javascript
// frontend/src/js/request.js (line 17-70)
async _fetch(url, options = {}) {
    // 1. 处理 URL
    const cleanUrl = url.startsWith('/') ? url.slice(1) : url;
    const fullUrl = `${this.baseUrl}/${cleanUrl}`;
    
    // 2. 设置请求头
    const headers = {'Content-Type': 'application/json'};
    
    // 3. 自动携带 Token
    const token = localStorage.getItem('token');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    // 4. 发起请求
    const response = await fetch(fullUrl, {headers, ...options});
    
    // 5. 401 拦截
    if (response.status === 401) {
        this._handleUnauthorized();
        throw new Error('登录已过期');
    }
    
    // 6. 解析响应
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.message || `请求失败 (${response.status})`);
    }
    
    return data;
}
```

---

## 4. API 交互契约

### 4.1 响应格式规范 ⚠️

**现状：缺乏统一标准**

目前存在三种响应模式：

#### 模式 1: 标准成功响应（推荐）

```json
{
  "success": true,
  "message": "操作成功",
  "data": {
    "id": 1,
    "name": "Python 程序设计"
  }
}
```

#### 模式 2: 错误响应

```json
{
  "success": false,
  "message": "用户名或密码错误"
}
```

#### 模式 3: 分页响应（warnings 路由）

```json
{
  "success": true,
  "warnings": [...],
  "stats": {
    "total": 100,
    "red_count": 5
  },
  "total": 100,
  "page": 1,
  "per_page": 10
}
```

### 4.2 建议统一规范

**新开发的功能应遵循以下格式：**

```json
{
  "code": 200,              // HTTP 状态码
  "success": true,          // 布尔值，快速判断
  "message": "获取成功",    // 可选，人类可读的描述
  "data": {},               // 数据主体
  "timestamp": "2026-03-19T10:30:00"  // 可选，时间戳
}
```

**分页数据：**

```json
{
  "code": 200,
  "success": true,
  "message": "获取成功",
  "data": {
    "items": [...],
    "pagination": {
      "total": 100,
      "page": 1,
      "per_page": 10,
      "total_pages": 10
    }
  }
}
```

### 4.3 主要 API 端点清单

#### 认证模块 (`/api/auth`)

| 方法 | 路径 | 描述 | 请求体 | 响应 |
|-----|------|------|--------|------|
| POST | `/login` | 用户登录 | `{username, password}` | `{token, user}` |
| GET | `/me` | 获取当前用户 | - | `{user}` |

#### 课程模块 (`/api/courses`)

| 方法 | 路径 | 描述 | 参数 | 响应 |
|-----|------|------|------|------|
| GET | `/` | 获取所有课程 | - | `{data: [courses]}` |
| POST | `/` | 创建课程 | `{name, code, semester}` | `{data: course}` |
| GET | `/:id/classes` | 获取班级列表 | - | `{data: [classes]}` |
| POST | `/:id/classes` | 创建班级 | `{name}` | `{data: class}` |
| GET | `/:courseId/classes/:classId/students` | 获取学生列表 | - | `{data: [students]}` |
| POST | `/:courseId/classes/:classId/students` | 添加学生 | `{student_no, name, gender}` | `{data: student}` |

#### 数据导入 (`/api/data`)

| 方法 | 路径 | 描述 | 参数 | 响应 |
|-----|------|------|------|------|
| POST | `/import/students` | 导入学生名单 | `FormData(file, course_id)` | `{success_count, skip_count}` |
| POST | `/import/attendance` | 导入考勤数据 | `FormData(file, course_id)` | `{success_count, errors}` |
| POST | `/import/homework` | 导入作业成绩 | `FormData(file, course_id)` | `{success_count, errors}` |
| POST | `/import/quiz` | 导入测验成绩 | `FormData(file, course_id)` | `{success_count, errors}` |
| GET | `/templates/:type` | 下载模板 | - | Excel文件流 |

#### 数据分析 (`/api/analytics`)

| 方法 | 路径 | 描述 | 参数 | 响应 |
|-----|------|------|------|------|
| GET | `/course/:id/overview` | 课程概览 | - | `{student_count, attendance_rate, ...}` |
| GET | `/course/:courseId/students/:studentId/profile` | 学生档案 | - | `{student, attendance, homework, ...}` |

#### 预警管理 (`/api/warnings`)

| 方法 | 路径 | 描述 | 参数 | 响应 |
|-----|------|------|------|------|
| GET | `/` | 获取预警列表 | `?page, level, status, search` | `{warnings, stats, total}` |
| GET | `/:id` | 获取预警详情 | - | `{warning}` |
| POST | `/:id/process` | 处理预警 | `{process_type, process_detail, process_result}` | `{warning}` |
| POST | `/generate` | 手动触发预警生成 | - | `{message}` |

#### 数据导出 (`/api/export`)

| 方法 | 路径 | 描述 | 参数 | 响应 |
|-----|------|------|------|------|
| GET | `/students` | 导出学生名单 | `?course_id, class_id, format` | Excel文件流 |
| GET | `/scores` | 导出成绩报表 | `?course_id, start_date, end_date` | Excel文件流 |
| GET | `/attendance` | 导出考勤统计 | `?course_id, start_date, end_date` | Excel文件流 |
| GET | `/warnings` | 导出预警报告 | `?level, status, start_date, end_date` | Excel文件流 |

---

## 5. 数据库规范

### 5.1 表结构总览

#### 核心实体表

| 表名 | 对应模型 | 描述 | 关键字段 |
|-----|---------|------|---------|
| `users` | User | 教师用户表 | username, password_hash, role |
| `courses` | Course | 课程表 | name, code, teacher_id |
| `classes` | Class | 班级表 | name, course_id |
| `students` | Student | 学生表 | student_no, name, class_id |

#### 业务数据表

| 表名 | 对应模型 | 描述 | 关键字段 |
|-----|---------|------|---------|
| `attendances` | Attendance | 出勤记录 | student_id, date, status |
| `homeworks` | Homework | 作业记录 | student_id, title, score |
| `quizzes` | Quiz | 测验记录 | student_id, title, score |
| `interactions` | Interaction | 课堂互动 | student_id, type, count |
| `warnings` | Warning | 预警记录 | student_id, level, type, status |

### 5.2 命名约定

#### 表名

- ✅ **复数形式**: `users`, `courses`, `students`
- ✅ **小写字母 + 下划线**: `attendances`, `homeworks`

#### 字段名

- ✅ **蛇形命名 (snake_case)**: `student_no`, `created_at`
- ✅ **主键**: `id` (Integer, primary_key=True)
- ✅ **外键**: `<table>_id` (如 `course_id`, `teacher_id`)
- ✅ **时间戳**: `created_at` (DateTime, default=datetime.now)

#### 模型类名

- ✅ **大驼峰命名 (PascalCase)**: `User`, `Course`, `Student`

### 5.3 关系映射规范

#### 一对多关系 (One-to-Many)

```python
# Course -> Classes
class Course(db.Model):
    classes = db.relationship('Class', backref='course', 
                             cascade='all, delete-orphan')

class Class(db.Model):
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
```

#### 多对一关系 (Many-to-One)

```python
# Student -> Class
class Student(db.Model):
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    class_ = db.relationship('Class', backref='students')
```

### 5.4 事务处理规范

#### 标准事务模式

```python
@courses_bp.route('/', methods=['POST'])
@jwt_required()
def create_course():
    try:
        # 1. 创建对象
        course = Course(name='Python 程序设计', ...)
        
        # 2. 添加到会话
        db.session.add(course)
        
        # 3. 提交事务
        db.session.commit()
        
        return jsonify({'success': True, 'data': course.to_dict()}), 201
        
    except Exception as e:
        # 4. 异常回滚
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
```

#### 批量操作事务

```python
# 每 20 条提交一次，避免内存溢出
for i, row in df.iterrows():
    student = Student(...)
    db.session.add(student)
    
    if i % 20 == 0:
        db.session.commit()

db.session.commit()  # 最后一次提交
```

### 5.5 软删除机制 ⚠️

**当前缺失，建议新增功能时补充：**

```python
class BaseModel(db.Model):
    """基础模型，提供软删除功能"""
    __abstract__ = True
    
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    deleted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    @classmethod
    def query(cls):
        """默认过滤已删除的记录"""
        return super().query.filter_by(is_deleted=False)
```

---

## 6. 全栈功能开发标准流程 (SOP)

### 场景：新增"课堂表现记录"功能

需求：记录学生在课堂上的表现（表扬/批评），并在预警系统中纳入考量。

---

### Step 1: 数据库设计

#### 1.1 创建数据模型

**文件**: `backend/app/models/performance.py`

```python
from . import db
from datetime import datetime


class Performance(db.Model):
    """课堂表现记录表"""
    __tablename__ = 'performances'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    
    # 表现类型：praise(表扬)/criticism(批评)
    type = db.Column(db.String(20), nullable=False, comment='表现类型')
    
    # 具体描述
    description = db.Column(db.Text, nullable=False, comment='表现描述')
    
    # 分值影响（正分=表扬，负分=批评）
    score_impact = db.Column(db.Integer, default=0, comment='对综合评分的影响')
    
    # 记录时间
    record_date = db.Column(db.Date, default=datetime.now().date, comment='发生日期')
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    student = db.relationship('Student', backref='performances')
    course = db.relationship('Course', backref='performances')
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'course_id': self.course_id,
            'type': self.type,
            'description': self.description,
            'score_impact': self.score_impact,
            'record_date': self.record_date.strftime('%Y-%m-%d'),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
```

#### 1.2 注册模型

**文件**: `backend/app/models/__init__.py`

```python
# 在文件末尾添加
from .performance import Performance
```

#### 1.3 初始化数据库

```bash
# 进入后端目录
cd backend

# 激活虚拟环境
source venv/bin/activate  # Windows: venv\Scripts\activate

# 启动 Python 交互式命令行
python
```

```python
from app import create_app
from app.models import db

app = create_app()
with app.app_context():
    db.create_all()  # 创建新表
    print("✅ performances 表创建成功")
```

---

### Step 2: 后端接口开发

#### 2.1 创建路由文件

**文件**: `backend/app/routes/performances.py`

```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db, Performance, Student, Course
from datetime import datetime

performances_bp = Blueprint('performances', __name__)


@performances_bp.route('/', methods=['GET'])
@jwt_required()
def get_performances():
    """获取表现记录列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        student_id = request.args.get('student_id', type=int)
        course_id = request.args.get('course_id', type=int)
        
        query = Performance.query
        
        if student_id:
            query = query.filter_by(student_id=student_id)
        if course_id:
            query = query.filter_by(course_id=course_id)
        
        pagination = query.order_by(
            Performance.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        performances = [p.to_dict() for p in pagination.items]
        
        return jsonify({
            'success': True,
            'data': performances,
            'total': pagination.total,
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败：{str(e)}'}), 500


@performances_bp.route('/', methods=['POST'])
@jwt_required()
def create_performance():
    """创建表现记录"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Content-Type 必须是 application/json'}), 400
        
        data = request.get_json()
        
        # 必填字段验证
        required_fields = ['student_id', 'course_id', 'type', 'description']
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({'success': False, 'message': f'缺少字段：{missing}'}), 400
        
        # 验证学生存在
        student = Student.query.get(data['student_id'])
        if not student:
            return jsonify({'success': False, 'message': '学生不存在'}), 404
        
        # 创建记录
        performance = Performance(
            student_id=data['student_id'],
            course_id=data['course_id'],
            type=data['type'],  # 'praise' or 'criticism'
            description=data['description'],
            score_impact=data.get('score_impact', 0),
            record_date=datetime.strptime(data.get('record_date'), '%Y-%m-%d').date() 
                       if data.get('record_date') else datetime.now().date()
        )
        
        db.session.add(performance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '表现记录创建成功',
            'data': performance.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'创建失败：{str(e)}'}), 500


@performances_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_performance(id):
    """删除表现记录"""
    try:
        performance = Performance.query.get(id)
        if not performance:
            return jsonify({'success': False, 'message': '记录不存在'}), 404
        
        db.session.delete(performance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '记录已删除'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'}), 500
```

#### 2.2 注册蓝图

**文件**: `backend/app/__init__.py`

```python
# 在 register_blueprint 部分添加
from .routes.performances import performances_bp
app.register_blueprint(performances_bp, url_prefix='/api/performances')
```

---

### Step 3: 前端页面开发

#### 3.1 创建 HTML 页面

**文件**: `frontend/src/pages/performances.html`

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>课堂表现管理</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <script src="/js/config.js"></script>
    <script src="/js/request.js"></script>
    <script src="/js/auth.js"></script>
    <style>
        .performance-card {
            border-left: 4px solid #ccc;
            margin-bottom: 15px;
        }
        .performance-card.praise {
            border-left-color: #28a745;
            background-color: #f8fff8;
        }
        .performance-card.criticism {
            border-left-color: #dc3545;
            background-color: #fff8f8;
        }
    </style>
</head>
<body>
    <!-- 侧边栏导航 (复用) -->
    <nav class="sidebar">...</nav>
    
    <!-- 主内容区 -->
    <div class="main-content">
        <div class="container-fluid">
            <h2><i class="bi bi-award"></i> 课堂表现管理</h2>
            
            <!-- 添加按钮 -->
            <button class="btn btn-primary mb-3" onclick="showAddModal()">
                <i class="bi bi-plus-circle"></i> 添加表现记录
            </button>
            
            <!-- 筛选条件 -->
            <div class="row mb-3">
                <div class="col-md-4">
                    <select id="filterCourse" class="form-select" onchange="loadPerformances()">
                        <option value="">全部课程</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <input type="text" id="searchStudent" class="form-control" 
                           placeholder="搜索学生姓名或学号" onkeyup="loadPerformances()">
                </div>
            </div>
            
            <!-- 表现记录列表 -->
            <div id="performanceList"></div>
        </div>
    </div>
    
    <!-- 添加模态框 -->
    <div class="modal fade" id="addModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">添加表现记录</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="addForm">
                        <div class="mb-3">
                            <label class="form-label">学生</label>
                            <input type="text" class="form-control" id="studentName" required>
                            <input type="hidden" id="studentId">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">课程</label>
                            <select class="form-select" id="courseId" required></select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">类型</label>
                            <select class="form-select" id="type" required>
                                <option value="praise">表扬</option>
                                <option value="criticism">批评</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">描述</label>
                            <textarea class="form-control" id="description" rows="3" required></textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">分值影响</label>
                            <input type="number" class="form-control" id="scoreImpact" value="0">
                            <small class="form-text text-muted">表扬为正分，批评为负分</small>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                    <button type="button" class="btn btn-primary" onclick="savePerformance()">保存</button>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // 页面加载检查登录状态
        if (!checkAuth()) {
            window.location.href = 'login.html';
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            loadCourses();
            loadPerformances();
        });
        
        // 加载课程列表（用于筛选）
        async function loadCourses() {
            try {
                const response = await request.get('/courses/');
                const courses = response.data || [];
                
                const filterSelect = document.getElementById('filterCourse');
                const courseSelect = document.getElementById('courseId');
                
                courses.forEach(course => {
                    const option1 = new Option(course.name, course.id);
                    const option2 = new Option(course.name, course.id);
                    filterSelect.add(option1);
                    courseSelect.add(option2);
                });
            } catch (error) {
                console.error('加载课程失败:', error);
            }
        }
        
        // 加载表现记录列表
        async function loadPerformances() {
            try {
                const courseId = document.getElementById('filterCourse').value;
                const search = document.getElementById('searchStudent').value;
                
                const params = {};
                if (courseId) params.course_id = courseId;
                if (search) params.search = search;
                
                const response = await request.get('/performances/', params);
                const performances = response.data || [];
                
                if (performances.length === 0) {
                    document.getElementById('performanceList').innerHTML = `
                        <div class="alert alert-info">暂无表现记录</div>
                    `;
                    return;
                }
                
                const html = performances.map(p => `
                    <div class="card performance-card ${p.type}">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <h6 class="card-title">
                                    <i class="bi bi-${p.type === 'praise' ? 'emoji-smile' : 'emoji-frown'}"></i>
                                    ${p.student_name || '未知学生'} - ${p.course_name || '未知课程'}
                                </h6>
                                <small class="text-muted">${p.record_date}</small>
                            </div>
                            <p class="card-text">${p.description}</p>
                            <small class="text-muted">
                                分值影响：${p.score_impact > 0 ? '+' : ''}${p.score_impact}
                            </small>
                        </div>
                    </div>
                `);
                
                document.getElementById('performanceList').innerHTML = html.join('');
            } catch (error) {
                console.error('加载失败:', error);
                document.getElementById('performanceList').innerHTML = `
                    <div class="alert alert-danger">加载失败：${error.message}</div>
                `;
            }
        }
        
        // 显示添加模态框
        function showAddModal() {
            const modal = new bootstrap.Modal(document.getElementById('addModal'));
            modal.show();
        }
        
        // 保存表现记录
        async function savePerformance() {
            const data = {
                student_id: parseInt(document.getElementById('studentId').value),
                course_id: parseInt(document.getElementById('courseId').value),
                type: document.getElementById('type').value,
                description: document.getElementById('description').value,
                score_impact: parseInt(document.getElementById('scoreImpact').value)
            };
            
            try {
                await request.post('/performances/', data);
                
                // 关闭模态框
                const modalEl = document.getElementById('addModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                modal.hide();
                
                // 刷新列表
                loadPerformances();
                
                // 提示成功
                alert('表现记录添加成功！');
            } catch (error) {
                alert(`添加失败：${error.message}`);
            }
        }
    </script>
</body>
</html>
```

#### 3.2 添加路由

**文件**: `backend/app/__init__.py`

```python
@app.route('/performances')
@app.route('/performances.html')
def performances_page():
    return app.send_static_file('pages/performances.html')
```

---

### Step 4: 集成到预警系统

#### 4.1 修改预警引擎

**文件**: `backend/app/services/warning_engine.py`

```python
# 在 _calculate_metrics 方法中添加
def _calculate_metrics(self, student_id):
    """计算所有维度的指标分数"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=self.TIME_DELTA_DAYS)
    
    metrics = {
        'attendance': self._calculate_attendance_score(student_id, start_date, end_date),
        'homework': self._calculate_homework_score(student_id, start_date, end_date),
        'quiz': self._calculate_quiz_score(student_id, start_date, end_date),
        'interaction': self._calculate_interaction_score(student_id, start_date, end_date),
        'performance': self._calculate_performance_score(student_id, start_date, end_date)  # 新增
    }
    
    return metrics

def _calculate_performance_score(self, student_id, start, end):
    """计算课堂表现得分"""
    from ..models.performance import Performance
    
    performances = Performance.query.filter(
        Performance.student_id == student_id,
        Performance.course_id == self.course_id,
        Performance.record_date.between(start.date(), end.date())
    ).all()
    
    total_impact = sum(p.score_impact for p in performances)
    
    # 将影响转换为 0-100 的分数（假设±50 分为满分范围）
    score = 50 + total_impact  # 基准分 50
    return max(0, min(100, score))  # 限制在 0-100 之间
```

#### 4.2 调整权重

```python
# 在 WarningEngine 类中修改
WEIGHTS = {
    'attendance': 0.25,      # 从 0.3 调整为 0.25
    'homework': 0.25,        # 从 0.3 调整为 0.25
    'quiz': 0.25,           # 从 0.3 调整为 0.25
    'interaction': 0.1,
    'performance': 0.15      # 新增维度
}
```

---

### Step 5: 联调测试

#### 5.1 后端测试

```bash
# 启动后端服务
cd backend
source venv/bin/activate
python run.py
```

测试 API：

```bash
# 获取表现记录列表
curl http://127.0.0.1:5000/api/performances/

# 创建表现记录
curl -X POST http://127.0.0.1:5000/api/performances/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "student_id": 1,
    "course_id": 1,
    "type": "praise",
    "description": "课堂上积极回答问题",
    "score_impact": 5
  }'
```

#### 5.2 前端测试

1. 浏览器访问：`http://127.0.0.1:5000/pages/performances.html`
2. 使用演示账号登录：`teacher / 123456`
3. 测试功能：
   - ✅ 查看表现记录列表
   - ✅ 添加新的表现记录
   - ✅ 筛选和搜索
   - ✅ 删除记录

---

### Step 6: 代码审查清单

#### 后端审查

- [ ] 模型是否定义了 `to_dict()` 方法？
- [ ] 所有写操作是否有 `try-except-finally` 和 `rollback`？
- [ ] 是否需要添加 `@jwt_required()` 装饰器？
- [ ] 输入验证是否充分（必填字段、类型检查）？
- [ ] 是否有 SQL 注入风险（使用参数化查询）？
- [ ] 错误信息是否暴露敏感信息？

#### 前端审查

- [ ] 是否正确引入 `config.js`、`request.js`、`auth.js`？
- [ ] 是否检查了登录状态（`checkAuth()`）？
- [ ] API 调用是否使用 `request` 对象而非直接 `fetch`？
- [ ] 错误处理是否完善（try-catch + 用户提示）？
- [ ] 表单验证是否充分（必填、格式）？
- [ ] 是否存在 XSS 风险（避免直接使用 `innerHTML`）？

---

## 7. 常见问题与避坑指南

### 7.1 后端开发常见坑

#### 问题 1: 循环导入错误

```python
# ❌ 错误示范
from app import db
from app.models.user import User  # 如果 user.py 也 from app import db，可能循环导入

# ✅ 正确做法
from . import db  # 使用相对导入
```

#### 问题 2: 数据库未提交

```python
# ❌ 忘记 commit
db.session.add(obj)
return jsonify({'success': True})  # 数据不会写入数据库！

# ✅ 正确做法
db.session.add(obj)
db.session.commit()
```

#### 问题 3: JWT Token 解码失败

```python
# 原因：identity 类型不一致
create_access_token(identity=str(user.id))  # 字符串
get_jwt_identity()  # 返回字符串

# 如果需要整数 ID
current_user_id = int(get_jwt_identity())
```

### 7.2 前端开发常见坑

#### 问题 1: Token 丢失

```javascript
// ❌ 忘记携带 Token
fetch('/api/courses/')  // 401 错误

// ✅ 使用封装的 request 对象
await request.get('/courses/')  // 自动添加 Authorization 头
```

#### 问题 2: 跨域问题

```javascript
// 开发环境：Flask 已配置 CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

// 生产环境：需要 Nginx 反向代理
```

#### 问题 3: 页面跳转后 Token 失效

```javascript
// ❌ 直接跳转
window.location.href = 'dashboard.html'

// ✅ 确保 Token 存在
if (localStorage.getItem('token')) {
    window.location.href = 'dashboard.html'
} else {
    window.location.href = 'login.html'
}
```

### 7.3 数据库操作常见坑

#### 问题 1: N+1 查询

```python
# ❌ 性能差
courses = Course.query.all()
for course in courses:
    classes = Class.query.filter_by(course_id=course.id).all()  # N 次查询

# ✅ 使用 joinedload
from sqlalchemy.orm import joinedload
courses = Course.query.options(joinedload(Course.classes)).all()
```

#### 问题 2: 级联删除导致数据丢失

```python
# ❌ 删除课程会删除所有关联数据
db.session.delete(course)
db.session.commit()

# ✅ 先备份或迁移数据
```

### 7.4 调试技巧

#### 后端调试

```python
# 打印日志
import traceback
try:
    # 业务逻辑
except Exception as e:
    print(f"Error: {str(e)}")
    print(traceback.format_exc())  # 打印完整堆栈
    return jsonify({'success': False, 'message': str(e)}), 500
```

#### 前端调试

```javascript
// 打开浏览器开发者工具 (F12)
// Network 标签查看 API 请求和响应
// Console 标签查看错误信息

// 添加调试日志
console.log('Request data:', data);
console.error('Error details:', error);
```

---

## 附录

### A. 快速启动命令

```bash
# 后端启动
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python run.py

# 访问前端
浏览器打开：http://127.0.0.1:5000/pages/login.html
```

### B. 演示账号

- 账号：`teacher`
- 密码：`123456`

### C. 相关文档

- [HANDOFF.md](./HANDOFF.md) - 项目交接文档
- [基于 Python 的教学效果监督系统的设计与实现.md](./基于 Python 的教学效果监督系统的设计与实现.md) - 毕业论文
- [开发技能.md](./开发技能.md) - 开发技能清单

---

**文档版本**: v1.0  
**最后更新**: 2026-03-19  
**维护说明**: 新增功能或修改架构时，请及时更新本文档
