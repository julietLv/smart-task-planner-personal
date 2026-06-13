"""
周报图表生成器 - matplotlib + Base64
"""
import matplotlib
matplotlib.use('Agg')  # 非交互式后端

import matplotlib.pyplot as plt
import base64
from io import BytesIO
from typing import Dict, Any

# ⭐ 新增：导入 Redis 缓存服务
try:
    from app.services.cache_service import redis_cache
except ImportError:
    redis_cache = None

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def cache_chart(key: str, chart_data: str, ttl: int = 3600) -> bool:
    """
    缓存图表数据到 Redis
    
    Args:
        key: 缓存键名
        chart_data: Base64 编码的图表数据
        ttl: 过期时间（秒），默认 1 小时
    
    Returns:
        是否缓存成功
    """
    if redis_cache and redis_cache.enabled:
        try:
            redis_cache.set(key, chart_data, ttl=ttl)
            return True
        except Exception as e:
            print(f"⚠️ 图表缓存失败: {e}")
            return False
    return False


def get_cached_chart(key: str) -> str | None:
    """
    从 Redis 获取缓存的图表数据
    
    Args:
        key: 缓存键名
    
    Returns:
        Base64 编码的图表数据，未命中返回 None
    """
    if redis_cache and redis_cache.enabled:
        try:
            cached = redis_cache.get(key)
            return cached if cached else None
        except Exception as e:
            print(f"⚠️ 读取图表缓存失败: {e}")
            return None
    return None


def generate_chart_base64(chart_type: str, data: Dict[str, Any]) -> str:
    """
    生成图表并转为 Base64
    
    Args:
        chart_type: 'pie' (环形图), 'bar' (柱状图), 'line' (折线图)
        data: 图表数据
    
    Returns:
        Base64 编码的图片字符串 (data:image/png;base64,...)
    """
    # ⭐ 缩小图表尺寸：从 8x6 改为 6x4，更适合报告展示
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    
    if chart_type == 'pie':
        # 环形图 - 任务状态分布
        sizes = [data.get('completed', 0), data.get('in_progress', 0), data.get('overdue', 0)]
        labels = ['已完成', '进行中', '已超时']
        colors = ['#4CAF50', '#2196F3', '#F44336']
        
        # 过滤掉0值
        valid_data = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]
        if valid_data:
            sizes, labels, colors = zip(*valid_data)
            
            wedges, texts, autotexts = ax.pie(
                sizes, 
                labels=labels, 
                colors=colors,
                autopct='%1.1f%%',
                startangle=90,
                wedgeprops=dict(width=0.5, edgecolor='white', linewidth=1.5),
                textprops={'fontsize': 10, 'fontweight': 'bold'}
            )
            # ⭐ 调整百分比字体样式
            for autotext in autotexts:
                autotext.set_fontsize(9)
                autotext.set_fontweight('bold')
                autotext.set_color('white')
            
            ax.set_title('任务状态分布', fontsize=12, fontweight='bold', pad=15)
        else:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=12)
            ax.set_title('任务状态分布', fontsize=12, fontweight='bold')
    
    elif chart_type == 'bar':
        # 柱状图 - 每日完成趋势
        labels = data.get('labels', [])
        values = data.get('values', [])
        
        if labels and values:
            bars = ax.bar(labels, values, color='#4CAF50', edgecolor='white', linewidth=0.5, width=0.6)
            
            # 在柱子上方显示数值
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                           f'{int(height)}', ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            ax.set_ylabel('完成任务数', fontsize=10, fontweight='bold')
            ax.set_title('每日完成任务趋势', fontsize=12, fontweight='bold', pad=15)
            ax.set_ylim(0, max(values) * 1.25 if max(values) > 0 else 5)
            
            # ⭐ 调整X轴标签字体
            ax.tick_params(axis='x', labelsize=9)
            ax.tick_params(axis='y', labelsize=9)
            
            # ⭐ 添加网格线，更规整
            ax.yaxis.grid(True, linestyle='--', alpha=0.3)
            ax.set_axisbelow(True)
        else:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=12)
            ax.set_title('每日完成任务趋势', fontsize=12, fontweight='bold')
    
    # 调整布局，增加内边距
    plt.tight_layout(pad=1.5)
    
    # 保存为 Base64
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='white', edgecolor='none')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return f"data:image/png;base64,{img_base64}"
