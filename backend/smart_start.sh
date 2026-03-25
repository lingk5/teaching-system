#!/bin/bash

# 智能启动脚本 - 自动处理端口占用
# 用法：./smart_start.sh [端口号]

PORT=${1:-5000}
MAX_RETRY=3
CURRENT_PORT=$PORT

echo "🚀 教学效果监督系统 - 智能启动"
echo "================================"
echo ""

# 检查并清理端口的函数
check_and_kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null)
    
    if [ -n "$pid" ]; then
        echo "⚠️  端口 $port 被占用 (PID: $pid)"
        
        # 显示进程信息
        ps -p $pid -o pid,command 2>/dev/null
        
        # 尝试杀死进程
        kill -9 $pid 2>/dev/null
        sleep 1
        
        # 再次检查
        if lsof -ti:$port >/dev/null 2>&1; then
            echo "❌ 无法释放端口 $port"
            return 1
        else
            echo "✅ 已释放端口 $port"
            return 0
        fi
    else
        echo "✅ 端口 $port 可用"
        return 0
    fi
}

# 激活虚拟环境
echo "📦 激活虚拟环境..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ 虚拟环境激活失败"
    exit 1
fi

echo "✅ 虚拟环境已激活"
echo ""

# 尝试启动服务器，最多重试 MAX_RETRY 次
for i in $(seq 1 $MAX_RETRY); do
    echo "尝试 $i/$MAX_RETRY - 使用端口 $CURRENT_PORT"
    
    # 检查端口
    check_and_kill_port $CURRENT_PORT
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "🎯 启动服务器..."
        echo "访问地址：http://127.0.0.1:$CURRENT_PORT/pages/login.html"
        echo ""
        echo "按 Ctrl+C 停止服务器"
        echo "================================"
        
        # 启动 Flask（使用环境变量指定端口）
        export FLASK_RUN_PORT=$CURRENT_PORT
        python run.py
        
        # 如果启动失败（例如端口突然被占用）
        if [ $? -ne 0 ]; then
            echo ""
            echo "⚠️  启动失败，尝试下一个端口..."
            CURRENT_PORT=$((CURRENT_PORT + 1))
            sleep 2
        else
            break
        fi
    else
        echo "⚠️  端口 $CURRENT_PORT 无法使用，尝试下一个端口..."
        CURRENT_PORT=$((CURRENT_PORT + 1))
        sleep 1
    fi
done

if [ $i -eq $MAX_RETRY ]; then
    echo ""
    echo "❌ 已达到最大重试次数 ($MAX_RETRY 次)"
    echo "💡 建议："
    echo "   1. 手动检查端口占用：lsof -i :$CURRENT_PORT"
    echo "   2. 修改 run.py 中的默认端口"
    echo "   3. 关闭其他可能占用端口的应用"
    exit 1
fi
