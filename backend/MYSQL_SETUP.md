# MySQL 数据库迁移完成指南

## ✅ 迁移状态

- [x] PyMySQL 驱动安装完成
- [x] MySQL 数据库初始化成功（9 张表）
- [x] 核心数据迁移完成
  - 用户：1 条（排除默认账号 teacher）
  - 课程：3 条
  - 班级：3 条
  - 学生：33 条
- [x] 后端服务运行正常

---

## 📊 Navicat 连接配置

### 方法 1: 基本连接

打开 Navicat，新建连接，填写以下信息：

```
连接名：teaching-system
主机：localhost 或 127.0.0.1
端口：3306
用户名：root
密码：12345678
数据库：teaching_system
```

### 方法 2: 使用专门用户（推荐生产环境）

在 Navicat 中执行 SQL 创建专用用户：

```sql
-- 创建用户
CREATE USER 'teaching'@'localhost' IDENTIFIED BY 'Teaching2024!';

-- 授权
GRANT ALL PRIVILEGES ON teaching_system.* TO 'teaching'@'localhost';
FLUSH PRIVILEGES;
```

然后使用新用户连接：
```
用户名：teaching
密码：Teaching2024!
```

---

## 🔍 验证数据

连接成功后，在 Navicat 中查看：

### 1. 表结构
展开 `teaching_system` 数据库，应该看到 9 张表：
- users (用户表)
- courses (课程表)
- classes (班级表)
- students (学生表)
- attendances (考勤表)
- homeworks (作业表)
- quizzes (测验表)
- interactions (互动表)
- warnings (预警表)

### 2. 查询数据示例

```sql
-- 查看所有用户
SELECT * FROM users;

-- 查看所有课程
SELECT * FROM courses;

-- 查看某个课程的班级
SELECT c.name as course_name, cl.name as class_name 
FROM classes cl
JOIN courses c ON cl.course_id = c.id
WHERE c.id = 1;

-- 查看某个班级的学生
SELECT s.*, cl.name as class_name
FROM students s
JOIN classes cl ON s.class_id = cl.id
WHERE cl.id = 1;

-- 统计每个课程的学生数
SELECT c.name, COUNT(s.id) as student_count
FROM courses c
LEFT JOIN classes cl ON c.id = cl.course_id
LEFT JOIN students s ON cl.id = s.class_id
GROUP BY c.id, c.name;
```

---

## 🚀 启动后端服务

### 方式 1: 使用智能启动脚本（推荐）⭐

**自动处理端口占用问题！**

```bash
cd backend
./smart_start.sh
```

功能特点：
- ✅ 自动检测端口占用
- ✅ 自动清理被占用的端口
- ✅ 智能切换备用端口（5000→5001→5002）
- ✅ 友好的错误提示

自定义端口：
```bash
./smart_start.sh 5001  # 从 5001 端口开始尝试
```

### 方式 2: 直接启动

```bash
cd backend
source venv/bin/activate
python run.py
```

访问：http://127.0.0.1:5000/pages/login.html

### 方式 3: 使用启动脚本

**macOS/Linux:**
```bash
./start.sh
```

**Windows:**
```bat
start.bat
```

---

## ⚙️ 配置文件说明

### .env 文件位置
`/backend/.env`

### 当前配置
```ini
# 密钥配置
SECRET_KEY=your-secret-key-here-please-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here-please-change-in-production

# MySQL 数据库配置
DB_USER=root
DB_PASSWORD=12345678
DB_HOST=localhost
DB_PORT=3306
DB_NAME=teaching_system
```

### 如需修改配置

编辑 `.env` 文件，或者使用完整 URI：

```ini
DATABASE_URI=mysql+pymysql://root:12345678@localhost:3306/teaching_system?charset=utf8mb4
```

---

## 📝 常用操作

### 1. 清空所有数据（重新测试）

```sql
-- 警告：这将删除所有数据！
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE warnings;
TRUNCATE TABLE interactions;
TRUNCATE TABLE quizzes;
TRUNCATE TABLE homeworks;
TRUNCATE TABLE attendances;
TRUNCATE TABLE students;
TRUNCATE TABLE classes;
TRUNCATE TABLE courses;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;
```

### 2. 备份数据库

```bash
# 导出整个数据库
mysqldump -u root -p12345678 teaching_system > backup_$(date +%Y%m%d).sql

# 导入数据库
mysql -u root -p12345678 teaching_system < backup_20260319.sql
```

### 3. 查看数据库大小

```sql
SELECT 
    table_schema AS '数据库',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS '大小 (MB)'
FROM information_schema.tables
WHERE table_schema = 'teaching_system';
```

---

## 🐛 常见问题

### Q1: 端口 5000 被占用

**错误信息:**
```
Address already in use
Port 5000 is in use by another program.
```

**解决方法 1: 查找并关闭占用端口的进程**

```bash
# macOS/Linux: 查看占用 5000 端口的进程
lsof -i :5000

# 或者使用 netstat
netstat -an | grep 5000

# 杀死占用端口的进程（替换 PID 为实际进程号）
kill -9 <PID>

# 示例：如果 lsof 显示 PID 是 12345
kill -9 12345
```

**解决方法 2: 使用其他端口启动**

```bash
# 方法 1: 修改 run.py 中的端口号
# 编辑 backend/run.py，将 port=5000 改为 port=5001
python run.py

# 方法 2: 临时指定端口（如果支持命令行参数）
python run.py --port 5001

# 方法 3: 使用环境变量（推荐）
export FLASK_RUN_PORT=5001
python run.py
```

**解决方法 3: 修改代码更换端口**

编辑 `backend/run.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)  # 改为 5001 或其他端口
```

**解决方法 4: macOS 禁用 AirPlay Receiver（针对 macOS Monterey+）**

macOS 系统服务可能占用 5000 端口：
```
系统偏好设置 -> 通用 -> AirDrop 与接力 -> 关闭"AirPlay 接收器"
```

或者在终端执行：
```bash
# 临时禁用 AirPlay 服务
sudo launchctl unload /System/Library/LaunchAgents/com.apple.airplaydiscovery.plist
```

**解决方法 5: 批量检查和清理端口（一键脚本）**

创建 `check_port.sh` 脚本：
```bash
#!/bin/bash
PORT=${1:-5000}

echo "检查端口 $PORT 的占用情况..."

# 查找占用端口的进程
PID=$(lsof -ti:$PORT)

if [ -z "$PID" ]; then
    echo "✅ 端口 $PORT 未被占用"
else
    echo "⚠️  端口 $PORT 被占用，进程 ID: $PID"
    echo "进程信息:"
    ps -p $PID -o pid,command
    
    read -p "是否强制结束该进程？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill -9 $PID
        echo "✅ 进程已结束"
    else
        echo "ℹ️  请手动处理或使用其他端口"
    fi
fi
```

使用方法：
```bash
chmod +x check_port.sh
./check_port.sh 5000
```

---

### Q2: 连接失败 "Can't connect to MySQL server"

**解决方法：**
1. 检查 MySQL 服务是否运行
   ```bash
   # macOS
   brew services list | grep mysql
   
   # Windows
   services.msc  # 查找 MySQL 服务
   ```

2. 检查端口是否正确
   ```sql
   SHOW VARIABLES LIKE 'port';
   ```

### Q3: 中文乱码

**解决方法：**
```sql
-- 查看字符集设置
SHOW VARIABLES LIKE '%character%';

-- 如果不是 utf8mb4，修改配置文件
-- macOS: /usr/local/etc/my.cnf
-- Windows: C:\ProgramData\MySQL\MySQL Server X.X\my.ini
[mysqld]
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
```

### Q4: 权限错误 "Access denied"

**解决方法：**
```sql
-- 重置用户密码和权限
ALTER USER 'root'@'localhost' IDENTIFIED BY '12345678';
FLUSH PRIVILEGES;
```

---

## 📊 数据库 ER 图

```
users (1) ----< (N) courses
                        \
                         > (1) classes (1) ----< (N) students
                                                \
                                                 > (N) attendances
                                                 > (N) homeworks
                                                 > (N) quizzes
                                                 > (N) interactions
                                                 > (N) warnings
```

---

## ✨ 下一步建议

1. **启用 Redis 缓存**（可选）
   - 提升高频查询性能
   - 减少数据库压力

2. **添加数据库索引**
   ```sql
   -- 为学生表添加索引
   CREATE INDEX idx_student_no ON students(student_no);
   CREATE INDEX idx_class_id ON students(class_id);
   
   -- 为预警表添加索引
   CREATE INDEX idx_warning_status ON warnings(status);
   CREATE INDEX idx_warning_level ON warnings(level);
   ```

3. **定期备份**
   - 设置 cron 任务每天自动备份
   - 保留最近 7 天的备份

---

## 📋 快速参考卡片

### 端口占用？一键解决！

```bash
# 方案 1: 使用智能启动脚本（推荐）
./smart_start.sh

# 方案 2: 手动检查并清理
lsof -i :5000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# 方案 3: 换个端口启动
export FLASK_RUN_PORT=5001 && python run.py
```

### 常用命令速查

```bash
# 查看端口占用
lsof -i :5000

# 杀死进程
kill -9 <PID>

# 启动服务
python run.py

# 后台启动
nohup python run.py > server.log 2>&1 &

# 查看日志
tail -f server.log

# 停止服务
pkill -f "python run.py"
```

### 数据库操作

```bash
# 备份数据库
mysqldump -u root -p teaching_system > backup.sql

# 恢复数据库
mysql -u root -p teaching_system < backup.sql

# 查看表数量
mysql -u root -p -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='teaching_system';"
```

### 紧急救援

**Q: 端口一直占用怎么办？**
```bash
# 批量清理 5000-5003 端口
for port in 5000 5001 5002 5003; do
    PID=$(lsof -ti:$port)
    [ -n "$PID" ] && kill -9 $PID && echo "已清理端口 $port"
done
```

**Q: MySQL 连不上？**
```bash
# 检查 MySQL 状态
brew services list | grep mysql

# 重启 MySQL
brew services restart mysql
```

---

**文档更新时间**: 2026-03-19  
**数据库版本**: MySQL 8.0+  
**字符集**: utf8mb4
