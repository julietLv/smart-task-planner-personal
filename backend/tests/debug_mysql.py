"""
详细的 MySQL 连接诊断
"""
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

print("=" * 60)
print("🔍 MySQL 详细连接诊断")
print("=" * 60)

host = os.getenv("MYSQL_HOST", "localhost")
port = int(os.getenv("MYSQL_PORT", 3306))
user = os.getenv("MYSQL_USER", "root")
password = os.getenv("MYSQL_PASSWORD", "")
database = os.getenv("MYSQL_DATABASE", "task_planner")

print(f"\n📋 连接配置:")
print(f"  Host: {host}")
print(f"  Port: {port}")
print(f"  User: {user}")
print(f"  Password: {'*' * len(password) if password else '(空)'}")
print(f"  Database: {database}")

print("\n" + "-" * 60)
print("🔌 测试 1: 连接到 MySQL 服务器（不指定数据库）")
print("-" * 60)

try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset='utf8mb4'
    )
    print("✅ 连接成功！")

    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()
    print(f"✅ MySQL 版本: {version[0]}")

    cursor.execute("SHOW DATABASES;")
    databases = [db[0] for db in cursor.fetchall()]
    print(f"✅ 可用数据库: {databases}")

    if database in databases:
        print(f"✅ 数据库 '{database}' 存在")
    else:
        print(f"❌ 数据库 '{database}' 不存在")
        print(f"   正在创建...")
        cursor.execute(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ 数据库已创建")

    conn.close()

except pymysql.err.OperationalError as e:
    error_code = e.args[0]
    error_msg = e.args[1]
    print(f"\n❌ 连接失败！")
    print(f"   错误码: {error_code}")
    print(f"   错误信息: {error_msg}")
    print()

    if error_code == 1045:
        print("💡 原因: 用户名或密码错误")
        print("   解决: 检查 .env 中的 MYSQL_USER 和 MYSQL_PASSWORD")
    elif error_code == 2003:
        print("💡 原因: 无法连接到 MySQL 服务器")
        print("   解决: 检查 MySQL 服务是否启动")
    elif error_code == 1049:
        print("💡 原因: 数据库不存在")
        print("   解决: 运行 python 'mysql（测试脚本）.py' 创建数据库")
    else:
        print(f"💡 未知错误，请检查配置")

except Exception as e:
    print(f"\n❌ 未知错误: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "-" * 60)
print("🔌 测试 2: 连接到指定数据库")
print("-" * 60)

try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4'
    )
    print("✅ 成功连接到数据库！")

    cursor = conn.cursor()
    cursor.execute("SHOW TABLES;")
    tables = [table[0] for table in cursor.fetchall()]

    if tables:
        print(f"✅ 表列表: {tables}")
    else:
        print("⚠️  数据库中没有表（首次使用正常）")
        print("   表会在应用启动时自动创建")

    conn.close()
    print("\n✅ 所有测试通过！配置正确")

except pymysql.err.OperationalError as e:
    print(f"\n❌ 连接数据库失败: {e.args[1]}")
except Exception as e:
    print(f"\n❌ 错误: {e}")

print("\n" + "=" * 60)

