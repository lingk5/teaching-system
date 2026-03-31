# teaching-system 回归测试报告

**测试日期:** 2026-03-31
**测试人员:** Codex (GPT-5)
**测试方式:** 本地自动化回归与源码级验证
**代码基线:** 当前工作区（含资源范围收口、助教指派、覆盖率评分规则、前端真实数据渲染）

---

## 📋 验证范围

- 后端权限与范围回归：`backend/tests/test_role_permissions.py`、`backend/tests/test_scoped_access_and_assignments.py`
- 预警覆盖率规则回归：`backend/tests/test_warning_coverage_rules.py`、`backend/tests/test_weight_config.py`
- UI/文档回归：`backend/tests/test_rbac_ui_regressions.py`
- 前端角色矩阵与页面完整性回归：`frontend/tests/auth-role.test.mjs`、`frontend/tests/page-data-integrity.test.mjs`
- 语法与补丁校验：`python3 -m compileall`、`git diff --check`

---

## ✅ 测试结果总结

### 1. 角色权限与管理员界面

| 测试项 | 状态 | 详情 |
|--------|------|------|
| 管理员默认落点 | ✅ 通过 | `admin` 登录后默认进入 `users.html` |
| 管理员用户列表接口 | ✅ 通过 | `/api/auth/users` 对管理员返回 200 |
| 教师访问用户管理接口 | ✅ 通过 | `/api/auth/users` 对教师返回 403 |
| 助教课程导入越权 | ✅ 通过 | `/api/data/courses/import` 对助教返回 403 |
| 助教修改学生越权 | ✅ 通过 | `/api/courses/students/<id>` 对助教返回 403 |
| 助教处理预警越权 | ✅ 通过 | `/api/warnings/<id>/process` 对助教返回 403 |
| 管理员页面文件 | ✅ 通过 | `frontend/src/pages/users.html` 存在且已接真实接口 |

**验证要点:**
- ✅ `admin / teacher / assistant` 三角色页面与能力已重新分离
- ✅ 管理员用户管理页面与后端接口已恢复
- ✅ 前后端权限矩阵已统一，前端隐藏与后端 403 校验一致

---

### 2. 文档与页面结构回归

| 测试项 | 状态 | 详情 |
|--------|------|------|
| 登录页演示账号展示 | ✅ 通过 | `login.html` 中包含 `admin / teacher / assistant` |
| 登录页管理员跳转 | ✅ 通过 | `admin` 默认跳转 `users.html` |
| 预警页鉴权守卫 | ✅ 通过 | `warnings.html` 仍包含 `checkAuth` 与 `applyRoleUI` |
| 管理员控制台文案 | ✅ 通过 | `users.html` 包含管理员专用访问限制提示 |

**验证要点:**
- ✅ 论文和总文档可以据此同步为当前真实工程状态
- ✅ 管理员界面不是占位页面，而是已接真实用户管理 API 的可用页面

---

### 3. 自动化回归基线

| 测试项 | 状态 | 详情 |
|--------|------|------|
| 后端 `unittest` | ✅ 通过 | 共 29 条测试全部通过 |
| 前端 `node:test` | ✅ 通过 | 共 6 条测试全部通过 |
| Python 编译检查 | ✅ 通过 | `python3 -m compileall backend/app backend/tests` 通过 |
| Patch 校验 | ✅ 通过 | `git diff --check` 通过 |

**验证要点:**
- ✅ 当前仓库已经具备覆盖 RBAC、资源范围、助教指派、覆盖率预警规则的回归基线
- ✅ 可在论文中表述为“已建立基础自动化回归验证机制”

---

## ⚠️ 当前仍未完全完成的部分

- 期末成绩仍未独立建模，当前继续复用 `quiz`
- 学生搜索、预警筛选、分页仍需统一后端查询规范
- 预警引擎仍为全量扫描，数据量扩大后会有性能压力

---

## 📊 整体评估

| 维度 | 状态 | 说明 |
|------|------|------|
| 功能完整性 | ✅ 良好 | 主流程、课程范围、助教指派、预警闭环均可演示 |
| 角色权限 | ✅ 良好 | 三角色界面、能力矩阵和资源范围已分离 |
| 稳定性 | ✅ 良好 | 当前自动化回归全部通过 |
| 数据真实性 | ✅ 良好 | 仪表盘和学情分析已移除模拟兜底 |
| 数据一致性 | ✅ 良好 | 评分字段与导出口径已统一到预警引擎 |

---

## 🎯 建议

### 论文交付建议
1. 论文中可表述为“系统已完成主流程、RBAC + 资源范围控制，并建立自动化回归验证集”。
2. 可以表述“系统图表已接真实接口，无数据时采用空状态展示”，但不要宣称“系统已达到生产级完备状态”。
3. 对数据库现状应统一表述为“当前代码默认使用 MySQL，ORM 保留迁移能力”，不要再写成 SQLite 当前基线。

### 后续优化
1. 为期末成绩建立独立模型与独立导入链路。
2. 将学生搜索、预警筛选、课程统计统一到后端查询规范。
3. 为预警生成补缓存、增量刷新或定时任务。
4. 扩展自动化回归到导入、导出、课程管理全链路。

---

## 📝 本次验证命令

```bash
cd /Users/a2914452089/Desktop/teaching-system
python3 -m unittest discover -s backend/tests -v
node --test frontend/tests/auth-role.test.mjs frontend/tests/page-data-integrity.test.mjs
python3 -m compileall backend/app backend/tests
git diff --check
```

---

**测试结论:** ✅ **当前仓库的角色权限、资源范围、助教指派、覆盖率预警规则与前端页面完整性验证通过，适合用于毕业设计演示与论文提交说明。**
