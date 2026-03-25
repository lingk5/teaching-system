# 教学效果监督系统 - 项目交接文档 (Handoff Documentation)

## 1. 项目概况

*   **项目名称**: 教学效果监督系统 (Teaching Effectiveness Monitoring System)
*   **当前版本**: v1.1.0-beta
*   **开发状态**: 已形成可演示主流程，但仍处于“功能收口 + 数据真实性补齐 + 风险治理”阶段，不能按生产完成态交接。
*   **核心功能**: 课程管理、学生管理、多维度数据导入（Excel）、智能预警引擎、学情数据可视化分析。

## 2. 技术栈架构

### 后端 (Backend)
*   **语言**: Python 3.8+
*   **框架**: Flask 3.0.3
*   **数据库**: MySQL (当前代码默认连接)，通过 SQLAlchemy ORM 管理
*   **认证**: Flask-JWT-Extended (JWT Token)
*   **数据处理**: Pandas 2.0.3 + OpenPyXL (用于高效处理 Excel 导入导出)
*   **核心库**:
    *   `flask-cors`: 解决跨域问题
    *   `marshmallow`: 数据序列化与验证
    *   `python-dotenv`: 环境变量管理

### 前端 (Frontend)
*   **技术栈**: 原生 HTML5 + CSS3 + JavaScript (ES6+)
*   **UI 框架**: Bootstrap 5.3 (响应式布局，Modals, Alerts)
*   **图表库**: Chart.js (用于雷达图、趋势图、饼图)
*   **图标库**: Bootstrap Icons
*   **架构模式**: 
    *   模块化开发：`config.js` (配置), `request.js` (请求封装), `auth.js` (认证)
    *   SPA-like 体验：通过 Ajax 局部刷新数据，避免页面整体重载。

## 3. 目录结构说明

```
teaching-system/
├── backend/                  # 后端根目录
│   ├── app/
│   │   ├── models/           # 数据库模型 (User, Course, Student, Data, Warning)
│   │   ├── routes/           # API 路由 (Auth, Courses, Data, Analytics, Warnings, Export)
│   │   ├── services/         # 核心业务逻辑 (WarningEngine)
│   │   └── __init__.py       # Flask 应用工厂
│   ├── instance/             # 历史 SQLite 目录（当前 MySQL 模式下通常为空）
│   ├── test_data/            # 测试用 Excel 数据生成目录
│   ├── generate_test_data.py # 测试数据生成脚本
│   ├── fix_env.py            # 环境自动修复脚本
│   ├── run.py                # 启动入口
│   ├── requirements.txt      # 依赖列表
│   └── start.sh / start.bat / smart_start.sh  # 启动脚本
├── frontend/                 # 前端根目录
│   └── src/
│       ├── css/              # 样式文件
│       ├── js/               # 核心 JS (config.js, request.js, auth.js, validator.js)
│       └── pages/            # 页面 (login, dashboard, courses, students, warnings...)
└── HANDOFF.md                # 本文档
```

## 4. 核心功能与逻辑细节

### 4.1 智能预警引擎 (`backend/app/services/warning_engine.py`)
这是系统的核心大脑。它不再是简单的阈值判断，而是基于**综合评分模型**：
*   **评分公式**: `综合分 = 出勤率(30%) + 作业完成率(30%) + 测验平均分(30%) + 互动得分(10%)`
*   **预警分级**:
    *   🔴 **红色 (Red)**: < 60分 (高风险)
    *   🟠 **橙色 (Orange)**: 60-75分 (中风险)
    *   🟡 **黄色 (Yellow)**: 75-85分 (低风险)
*   **智能建议**: 引擎会自动分析拉低分数的短板（如“作业提交率过低”），并生成针对性的干预建议。

### 4.2 数据导入 (`backend/app/routes/data.py` & `frontend/src/pages/data-import.html`)
*   支持 **批量导入**：学生名单、考勤记录、平时作业、测验/期末成绩。
*   **健壮性设计**: 
    *   后端使用 Pandas 处理 Excel，能自动去除空行、空格。
    *   前端 `request.upload` 封装了 `FormData` 处理。
    *   导入结果会有详细反馈（成功条数、失败条数及具体原因）。

### 4.3 学情分析 (`backend/app/routes/analytics.py`)
*   利用 SQL 聚合查询 (`func.avg`, `func.count`) 实时计算各项指标。
*   **学生详情**: 复用 `WarningEngine` 实时计算该学生的最新雷达图数据，无需预先存储冗余数据。

### 4.4 基础设施 (`frontend/src/js/request.js`)
*   封装了 `fetch`，自动处理：
    *   `Authorization` 头 (Bearer Token)
    *   Base URL 拼接
    *   401 Token 过期自动跳转登录页
    *   统一的错误提示 (Toast/Alert)

## 5. 当前进度 (Progress)

### 5.1 模块状态

| 模块 | 状态 | 当前结论 | 备注 |
| :--- | :--- | :--- | :--- |
| **认证** | ✅ 完成 | 登录、注册、`/me`、JWT 流程可用 | 登录页已接真实后端 |
| **课程** | 🟡 基本完成 | 课程列表、创建课程、创建班级可用 | 出勤率等统计仍有占位值 |
| **学生** | ✅ 完成 | 列表、添加、编辑、删除、个人画像弹窗可用 | 搜索仍是前端内存过滤 |
| **数据导入** | 🟡 基本完成 | 学生/考勤/作业/测验/互动导入可用 | 期末成绩仍借道测验接口 |
| **预警** | ✅ 完成 | 生成、查询、处理、历史记录闭环已通 | 生成逻辑仍是全量扫描 |
| **仪表盘** | 🟡 半完成 | 学生数、预警数来自真实接口 | 出勤率、作业率、趋势图仍有模拟数据 |
| **学情分析** | 🟡 半完成 | 后端接口存在，学生画像接口可用 | 页面图表仍部分模拟 |
| **导出** | 🟡 基本完成 | 学生、成绩、考勤、预警导出可用 | 成绩权重公式需与预警引擎统一 |
| **自动化测试** | ❌ 未完成 | 无测试目录、无回归脚本 | 当前仅做源码级校验 |

### 5.2 已完成的开发细节

*   后端已拆分为 6 个蓝图模块，模型、路由、服务职责边界基本清晰。
*   `WarningEngine` 已支持综合评分、等级判定、最弱项归因与干预建议。
*   导入模块已具备 Excel/CSV 解析、空行清洗、错误明细返回和模板下载能力。
*   `students.html`、`courses.html`、`warnings.html`、`data-import.html` 都已接入真实接口。
*   MySQL 迁移说明、环境修复脚本、智能启动脚本已经具备，适合本地演示环境。

### 5.3 未完成项

*   `analytics.html` 图表尚未完全绑定真实统计数据。
*   `dashboard.html` 的部分指标仍为手工模拟值。
*   期末成绩没有独立模型或独立导入链路，目前靠标题约定和测验表复用。
*   学生搜索、预警筛选、分页没有形成统一的后端查询规范。
*   文档曾长期滞后于代码，现已开始校正，但后续仍需持续维护。

### 5.4 风险与技术债

*   **鉴权风险**：部分 `data`、`analytics`、`warnings` 查询接口未统一加 `@jwt_required()`。
*   **统计口径风险**：预警、导出、页面展示的评分公式与指标命名尚未完全统一。
*   **性能风险**：预警生成按课程遍历学生并实时聚合，数据量上升后会出现瓶颈。
*   **运维风险**：`smart_start.sh` 会直接清理占用端口的进程，只适合本机开发环境。

## 6. 接下来的工作建议 (Next Steps)

1.  **优先收口真实性**:
    *   把 `dashboard.html` 与 `analytics.html` 中的模拟数据全部替换为真实接口结果。
    *   统一预警、导出、页面卡片的评分公式和字段命名。

2.  **优先补安全边界**:
    *   为 `data`、`analytics`、`warnings` 相关接口统一补齐鉴权。
    *   增加教师仅访问自己课程数据的权限约束。

3.  **优先补测试**:
    *   至少补 4 条自动化回归链路：登录、学生导入、预警生成、报表导出。

4.  **第二阶段扩展**:
    *   引入缓存或定时任务，降低预警全量计算的实时压力。
    *   预留学生端、消息通知、生产部署方案。

## 7. 环境重置与启动指南

如果遇到环境问题，请执行以下“核弹级”修复步骤：

1.  **进入后端目录**: `cd backend`
2.  **重置环境**: `python3 fix_env.py` (这会删除旧 venv 并重装所有依赖)
3.  **生成测试数据**: `python3 generate_test_data.py`
4.  **启动服务**: `./start.sh` (Mac/Linux) 或 `start.bat` (Windows)
5.  **访问前端**: 浏览器打开 `http://127.0.0.1:5000`

---
*文档生成时间: 2026-03-25*
