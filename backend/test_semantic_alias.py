from app.services.scheduler_service import add_semantic_alias

# 为"晨跑"添加别名
add_semantic_alias("晨跑", "早起跑步")
add_semantic_alias("晨跑", "晨间运动")

# 为"学习"添加别名（如果已学习"学习"习惯）
add_semantic_alias("学习", "看书")
add_semantic_alias("学习", "复习")
