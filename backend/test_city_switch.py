import pymysql

print("=" * 60)
print("修复：MySQL 数据库添加 user_city 字段")
print("=" * 60)

try:
    # 连接 MySQL
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='1314159@yjh',
        database='task_planner',
        charset='utf8mb4'
    )
    cursor = conn.cursor()

    print("\n【步骤 1】检查 user_preferences 表结构...")
    cursor.execute("DESCRIBE user_preferences")
    columns = cursor.fetchall()
    column_names = [col[0] for col in columns]

    print(f"当前字段列表: {', '.join(column_names)}")

    if 'user_city' in column_names:
        print("✅ user_city 字段已存在，无需修复")
    else:
        print("❌ user_city 字段不存在，开始添加...")

        print("\n【步骤 2】添加 user_city 字段...")
        cursor.execute("""
            ALTER TABLE user_preferences 
            ADD COLUMN user_city VARCHAR(100) DEFAULT '北京' COMMENT '用户所在城市'
        """)
        conn.commit()
        print("✅ user_city 字段添加成功！")

    # 步骤 3: 验证字段是否存在
    print("\n【步骤 3】验证字段...")
    cursor.execute("DESCRIBE user_preferences")
    columns = cursor.fetchall()
    column_names = [col[0] for col in columns]

    if 'user_city' in column_names:
        print("✅ 验证通过！user_city 字段存在")

        # 步骤 4: 检查是否有记录
        cursor.execute("SELECT user_id, user_city FROM user_preferences WHERE user_id = 1")
        result = cursor.fetchone()

        if result:
            print(f"当前用户城市: {result[1]}")
        else:
            print("数据库中无用户记录，插入默认记录...")
            cursor.execute("""
                INSERT INTO user_preferences (user_id, user_city) 
                VALUES (1, '北京')
            """)
            conn.commit()
            print("✅ 默认记录插入成功")
    else:
        print("❌ 验证失败！user_city 字段仍未添加")

    conn.close()

    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback

    traceback.print_exc()
