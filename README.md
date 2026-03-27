# 教学监督系统（teaching-system）

## 项目概览
本项目是基于 `Flask + MySQL + Vanilla JS` 的教学效果监督系统，覆盖：
- 登录认证（JWT）
- 课程/班级/学生管理
- Excel 数据导入与模板下载
- 学情分析与预警处理
- 数据导出

## 快速启动
```bash
cd /Users/a2914452089/Desktop/teaching-system/backend
source venv/bin/activate
./start.sh
```

默认访问：
- `http://127.0.0.1:5000/pages/login.html`

若端口被占用：
```bash
FLASK_RUN_PORT=5001 ./start.sh
```

## 默认演示账号
- `admin / 123456`（管理员）
- `teacher / 123456`（教师）
- `assistant / 123456`（助教）

说明：后端启动时会自动补齐缺失的默认账号（已存在则跳过）。

## 角色权限
- `admin`：可管理用户与课程，查看全量数据
- `teacher`：可管理课程、学生、导入、查看分析与预警
- `assistant`：只读查看课程/学生/分析/预警，不可导入与管理

## 文档索引
- 架构文档：`/Users/a2914452089/Desktop/teaching-system/FULLSTACK_ARCHITECTURE.md`
- 交接文档：`/Users/a2914452089/Desktop/teaching-system/HANDOFF.md`
- 评分策略设计：`/Users/a2914452089/Desktop/teaching-system/docs/superpowers/specs/2026-03-27-composite-score-policy-design.md`
- 实施计划：`/Users/a2914452089/Desktop/teaching-system/docs/superpowers/plans/2026-03-27-composite-score-policy.md`

## 文档同步约定
- 代码变更涉及接口、权限、默认账号、启动方式时，同步更新 `README.md` 与 `FULLSTACK_ARCHITECTURE.md`
- 架构文档中的“历史示例”仅作扩展模板，不能作为当前已实现功能判断依据
