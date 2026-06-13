"""
Alembic 迁移脚本入口

使用方法：
  alembic revision --autogenerate -m "描述"  # 自动生成迁移脚本
  alembic upgrade head                       # 执行所有迁移
  alembic downgrade -1                       # 回退一个版本
  alembic history                            # 查看迁移历史
"""
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

def run_migrations_offline() -> None:
    """离线模式执行迁移"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式执行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
