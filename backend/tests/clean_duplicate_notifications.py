from app.models.database import get_connection

print("=" * 60)
print("1️⃣ 查看5月20日的重复摘要")
print("=" * 60)

conn = get_connection()
cursor = conn.cursor()

try:
    cursor.execute("""
        SELECT id, title, created_at, is_read
        FROM notifications 
        WHERE user_id = 1 
        AND type = 'daily_summary'
        AND title LIKE %s
        ORDER BY created_at
    """, ('%2026-05-20%',))

    rows = cursor.fetchall()
    print(f"\n找到 {len(rows)} 条记录：\n")

    for row in rows:
        # 处理元组或字典类型
        if isinstance(row, dict):
            print(f"  ID: {row['id']}")
            print(f"  标题: {row['title']}")
            print(f"  创建时间: {row['created_at']}")
            print(f"  已读: {'是' if row['is_read'] else '否'}")
        else:
            print(f"  ID: {row[0]}")
            print(f"  标题: {row[1]}")
            print(f"  创建时间: {row[2]}")
            print(f"  已读: {'是' if row[3] else '否'}")
        print("-" * 40)

    print("\n" + "=" * 60)
    print("2️ 删除重复的5月20日摘要（保留最早的一条）")
    print("=" * 60)

    confirm = input("\n️  确认要删除重复数据吗？(输入 yes 确认): ")

    if confirm.lower() == 'yes':
        cursor.execute("""
            DELETE FROM notifications 
            WHERE user_id = 1 
            AND type = 'daily_summary'
            AND title LIKE %s
            AND id NOT IN (
                SELECT min_id FROM (
                    SELECT MIN(id) as min_id
                    FROM notifications 
                    WHERE user_id = 1 
                    AND type = 'daily_summary'
                    AND title LIKE %s
                ) as temp
            )
        """, ('%2026-05-20%', '%2026-05-20%'))

        conn.commit()
        deleted_count = cursor.rowcount

        print(f"\n✅ 成功删除 {deleted_count} 条重复记录")
    else:
        print("\n❌ 已取消操作")

except Exception as e:
    print(f"\n❌ 操作失败: {e}")
    import traceback

    traceback.print_exc()
finally:
    conn.close()
    print("\n✅ 数据库连接已关闭")
