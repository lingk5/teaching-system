# 教学监督系统

面向计算机学院教学场景的教学效果监督平台，支持 `admin / teacher / assistant` 三角色协作、Excel 数据导入、学情分析、综合预警与报表导出。

## 当前状态

- 已完成主业务闭环：登录、用户管理、课程/班级、学生管理、Excel 导入、学情分析、预警生成/处理、报表导出。
- 已完成前后端双重权限控制：
  - `admin`：查看全部、管理用户、管理课程、补救或强制调整助教指派、导出报表
  - `teacher`：仅访问本人课程，导入数据、管理学生、生成/处理预警、分配助教、导出报表
  - `assistant`：仅查看被指派课程的数据，不能导入、创建、处理预警、导出
- 已完成数据真实性收口：
  - 仪表盘和学情分析页移除演示数据兜底
  - 无数据时显示空状态
  - 综合评分只基于已有指标重算权重
  - `0/5` 指标时综合评分为 `0`
  - 至少 `2/5` 指标覆盖时才允许触发预警

## 评分与预警规则

- 综合评分指标固定为：
  - `attendance`
  - `homework`
  - `quiz`
  - `final_exam`
  - `interaction`
- 默认权重：`20 / 20 / 20 / 30 / 10`
- 评分规则：
  - `0/5` 项有数据：综合评分 `0`
  - `1/5` 项有数据：允许显示评分，但不触发预警
  - `2/5` 及以上：按覆盖项重新归一化权重，并参与预警判定
- 预警状态：
  - 活跃：`active / pending`
  - 已处理：`processed / ignored / following`
  - 自动解除：`cleared`

## 助教指派规则

- 助教以“课程”为粒度指派。
- 默认由教师为自己课程指派助教。
- 管理员可补救或强制调整任意课程的助教指派。
- 助教仅能查看被分配课程。

## 技术栈

- 前端：原生 `HTML + CSS + JavaScript`、`Bootstrap 5`、`Chart.js`
- 后端：`Flask`、`SQLAlchemy`、`Flask-JWT-Extended`
- 数据处理：`Pandas`、`OpenPyXL`
- 数据库：当前默认使用 `MySQL`

## 默认账号

- `admin / 123456`
- `teacher / 123456`
- `assistant / 123456`

## 本地启动

```bash
cd /Users/a2914452089/Desktop/teaching-system/backend
./start.sh
```

启动后访问：

- 前端：`http://127.0.0.1:5000`
- 后端健康检查：`http://127.0.0.1:5000/api/hello`

## 测试

后端全量回归：

```bash
cd /Users/a2914452089/Desktop/teaching-system/backend
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

前端回归：

```bash
cd /Users/a2914452089/Desktop/teaching-system
node --test frontend/tests/auth-role.test.mjs frontend/tests/page-data-integrity.test.mjs
```

## 关键文档

- 架构说明：`/Users/a2914452089/Desktop/teaching-system/FULLSTACK_ARCHITECTURE.md`
- 项目交接：`/Users/a2914452089/Desktop/teaching-system/HANDOFF.md`
- 测试报告：`/Users/a2914452089/Desktop/teaching-system/TEST_REPORT.md`
- 论文主文档：`/Users/a2914452089/Desktop/teaching-system/基于Python的教学效果监督系统的设计与实现.md`
