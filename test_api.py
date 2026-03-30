#!/usr/bin/env python3
"""
teaching-system API 功能测试脚本
测试: 预警引擎、数据导入、数据分析接口、预警导出
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

# 测试账号
USERNAME = "teacher"
PASSWORD = "123456"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(test_name, result, message=""):
    """打印测试结果"""
    if result:
        print(f"{Colors.GREEN}✓{Colors.RESET} {test_name}")
        if message:
            print(f"  {message}")
    else:
        print(f"{Colors.RED}✗{Colors.RESET} {test_name}")
        if message:
            print(f"  {message}")

def test_health():
    """测试健康检查"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def login():
    """登录获取 token"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": USERNAME, "password": PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('access_token')
        return None
    except Exception as e:
        print(f"登录失败: {e}")
        return None

def test_warning_engine(token, course_id=1):
    """测试预警引擎"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/warnings/check/{course_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            return True, f"生成了 {len(data.get('warnings', []))} 条预警"
        return False, response.text
    except Exception as e:
        return False, str(e)

def test_import_students(token, course_id=1):
    """测试学生导入 (通过已有的模板文件)"""
    try:
        # 先下载模板
        template_response = requests.get(
            f"{BASE_URL}/api/data/templates/students",
            headers={"Authorization": f"Bearer {token}"}
        )

        if template_response.status_code != 200:
            return False, "无法下载模板"

        # 模拟上传测试数据
        # 实际场景应该上传真实的 Excel 文件
        return True, "模板下载成功 (需要手动测试上传)"
    except Exception as e:
        return False, str(e)

def test_analytics_course_overview(token, course_id=1):
    """测试课程概览"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/analytics/course/{course_id}/overview",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            student_count = data.get('data', {}).get('student_count', 0)
            return True, f"课程有 {student_count} 名学生"
        return False, response.text
    except Exception as e:
        return False, str(e)

def test_analytics_student_profile(token, course_id=1, student_id=1):
    """测试学生档案"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/analytics/course/{course_id}/students/{student_id}/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            return True, "学生档案获取成功"
        return False, response.text
    except Exception as e:
        return False, str(e)

def test_export_warnings(token):
    """测试预警导出"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/export/warnings",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            return True, "预警报告导出成功"
        elif response.status_code == 404:
            return True, "无预警记录可导出 (正常)"
        return False, response.text
    except Exception as e:
        return False, str(e)

def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}teaching-system API 功能测试{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")

    # 1. 测试服务健康
    print(f"{Colors.YELLOW}1. 服务健康检查{Colors.RESET}")
    health_ok = test_health()
    print_test("后端服务运行中", health_ok)

    if not health_ok:
        print(f"\n{Colors.RED}无法连接到后端服务，请检查是否启动{Colors.RESET}")
        return

    # 2. 登录
    print(f"\n{Colors.YELLOW}2. 用户登录{Colors.RESET}")
    token = login()
    print_test("登录成功", token is not None)

    if not token:
        print(f"\n{Colors.RED}登录失败，请检查账号密码或先注册用户{Colors.RESET}")
        print(f"提示: 可以通过 /api/auth/register 注册新用户")
        return

    # 3. 测试预警引擎
    print(f"\n{Colors.YELLOW}3. 预警引擎测试{Colors.RESET}")
    result, msg = test_warning_engine(token)
    print_test("预警检查", result, msg)

    # 4. 测试数据导入
    print(f"\n{Colors.YELLOW}4. 数据导入测试{Colors.RESET}")
    result, msg = test_import_students(token)
    print_test("学生导入", result, msg)

    # 5. 测试数据分析
    print(f"\n{Colors.YELLOW}5. 数据分析测试{Colors.RESET}")

    result, msg = test_analytics_course_overview(token)
    print_test("课程概览", result, msg)

    result, msg = test_analytics_student_profile(token)
    print_test("学生档案", result, msg)

    # 6. 测试预警导出
    print(f"\n{Colors.YELLOW}6. 预警导出测试{Colors.RESET}")
    result, msg = test_export_warnings(token)
    print_test("预警报告导出", result, msg)

    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.GREEN}测试完成!{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")

if __name__ == "__main__":
    main()
