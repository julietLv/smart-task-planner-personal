"""
MySQL 数据库初始化脚本
使用前请确保：
1. MySQL 服务已启动
2. 已在 .env 中配置正确的数据库信息
3. 已安装 pymysql: pip install pymysql
"""
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()


def create_database():
    """创建数据库（如果不存在）"""
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", 3306))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "task_planner")
    
    print(f"🔌 连接到 MySQL: {host}:{port}")
    
    try:
        # 先连接到 MySQL 服务器（不指定数据库）
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # 创建数据库（如果不存在）
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ 数据库 '{database}' 已就绪")
        
        cursor.close()
        conn.close()
        
        return True
        
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1045:
            print(f"❌ 认证失败：用户名或密码错误")
            print(f"   请检查 .env 文件中的 MYSQL_USER 和 MYSQL_PASSWORD")
        elif e.args[0] == 2003:
            print(f"❌ 无法连接到 MySQL 服务器")
            print(f"   请确认 MySQL 服务是否正在运行")
        else:
            print(f"❌ 连接错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False


def main():
    print("=" * 60)
    print("🚀 MySQL 数据库初始化工具")
    print("=" * 60)
    
    success = create_database()
    
    if success:
        print("\n✅ 数据库初始化成功！")
        print("   现在可以启动应用了: python main.py")
    else:
        print("\n❌ 数据库初始化失败，请检查配置后重试")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

