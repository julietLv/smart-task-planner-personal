# backend/app/services/report_generator.py
from typing import Dict, Any
from app.services.websocket_service import manager
from datetime import datetime, timedelta

# ⭐ 新增导入
from app.services.report_data_processor import (
    query_tasks_for_report,
    calculate_statistics,
    analyze_user_habit,
    calculate_daily_trend
)
from app.services.report_chart_generator import (
    generate_chart_base64,
    cache_chart,
    get_cached_chart
)
from app.services.report_template import (
    render_markdown_report,
    determine_report_tone
)
from app.services.report_suggestion_generator import generate_suggestions
from app.models.task_model import get_user_preferences
from app.services.report_word_generator import create_word_report


async def generate_weekly_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    异步生成周报（Phase 1: Markdown 版本 + Phase 2: Word 导出）
    
    流程：
    1. 查询数据 → Pandas DataFrame
    2. 计算指标 → 统计数据
    3. 生成图表 → Base64 图片
    4. LLM 建议 → 个性化建议
    5. 渲染模板 → Markdown 报告 + Word 文档
    6. WebSocket 推送结果
    """
    # ⭐ 在函数开头导入 redis_cache
    from app.services.cache_service import redis_cache
    
    user_id = payload['user_id']
    time_range = payload.get('time_range', 'this_week')
    
    print(f"📊 开始生成周报 (user_id={user_id}, time_range={time_range})")
    
    try:
        # 1. 查询数据并转为 DataFrame
        print("📥 步骤1: 查询任务数据...")
        tasks_df = query_tasks_for_report(user_id, time_range)
        print(f"✅ 查询到 {len(tasks_df)} 个任务")
        
        if len(tasks_df) == 0:
            return {
                "success": False,
                "error": "本周无任务数据，无法生成报告"
            }
        
        # 2. 数据层：计算指标
        print("📊 步骤2: 计算统计数据...")
        stats = calculate_statistics(tasks_df)
        habits = analyze_user_habit(tasks_df)
        daily_trend = calculate_daily_trend(tasks_df)
        print(f"✅ 统计完成: 总数={stats['total']}, 完成={stats['completed']}, 超时={stats['overdue']}")
        
        # 3. 可视化层：生成图表
        print("🎨 步骤3: 生成图表...")
        user_id_str = str(user_id)
        
        # 状态分布图（环形图）
        status_pie_key = f"status_pie_{user_id_str}_{time_range}"
        status_pie = get_cached_chart(status_pie_key)
        if not status_pie:
            status_pie = generate_chart_base64('pie', stats)
            cache_chart(status_pie_key, status_pie, ttl=3600)
        
        # 每日趋势图（柱状图）
        daily_bar_key = f"daily_bar_{user_id_str}_{time_range}"
        daily_bar = get_cached_chart(daily_bar_key)
        if not daily_bar:
            daily_bar = generate_chart_base64('bar', daily_trend)
            cache_chart(daily_bar_key, daily_bar, ttl=3600)
        
        charts = {
            'status_pie': status_pie,
            'daily_bar': daily_bar
        }
        print("✅ 图表生成完成")
        
        # 4. 内容生成层：LLM 建议
        print("🤖 步骤4: 生成个性化建议...")
        llm_suggestions = await generate_suggestions(stats, habits)
        print("✅ 建议生成完成")
        
        # 5. 确定报告语气和标题
        tone_info = determine_report_tone(stats)
        
        # 6. 准备模板数据
        now = datetime.now()
        if time_range == 'this_week':
            start_date = (now - timedelta(days=now.weekday())).strftime('%Y年%m月%d日')
            end_date = (now - timedelta(days=now.weekday() + 6)).strftime('%Y年%m月%d日')
        else:
            start_date = (now - timedelta(days=7)).strftime('%Y年%m月%d日')
            end_date = now.strftime('%Y年%m月%d日')
        
        # 获取用户偏好
        prefs = get_user_preferences(user_id)
        user_nickname = prefs.user_nickname if prefs and prefs.user_nickname else "彦祖"
        assistant_nickname = "花花"
        
        # 亮点、问题、改进方向
        highlights = []
        issues = []
        improvements = []
        
        if stats['completed'] > 0:
            highlights.append(f"完成了 {stats['completed']} 个任务")
        
        if habits.get('habit_completion', {}).get('early_rise', {}).get('rate', 0) > 0.6:
            highlights.append("早起任务完成率良好")
        
        if stats['overtime_rate'] > 0.6:
            issues.append(f"超时率 {stats['overtime_rate']*100:.0f}% 过高，需立即调整")
        elif stats['overtime_rate'] > 0.4:
            issues.append(f"超时率 {stats['overtime_rate']*100:.0f}% 偏高")
        
        if stats['overtime_rate'] > 0.6:
            improvements.append("下周任务量减少 30%")
            improvements.append("优先处理高优先级积压任务")
        
        report_data = {
            'title': tone_info['title'],
            'warning_message': tone_info['warning'],
            'start_date': start_date,
            'end_date': end_date,
            'generate_time': now.strftime('%Y年%m月%d日 %H:%M'),
            'user_nickname': user_nickname,
            'assistant_nickname': assistant_nickname,
            'stats': stats,
            'charts': charts,
            'daily_data': daily_trend['daily_data'],
            'habits': habits,
            'llm_suggestions': llm_suggestions,
            'highlights': highlights if highlights else ["本周暂无亮点"],
            'issues': issues if issues else ["本周无重大问题"],
            'improvements': improvements if improvements else ["继续保持当前节奏"],
            'next_report_date': (now + timedelta(days=7)).strftime('%Y年%m月%d日')
        }
        
        # 7. 渲染 Markdown 报告
        print("📝 步骤5: 渲染报告模板...")
        markdown_content = render_markdown_report(report_data)
        print(f"✅ 报告生成完成，长度: {len(markdown_content)} 字符")
        
        # ⭐ 新增：生成 Word 文档
        print("📄 步骤5.5: 生成 Word 文档...")
        word_content = create_word_report(report_data)
        print(f"✅ Word 文档生成完成，大小: {len(word_content)} bytes")
        
        # ⭐ 缓存 Word 文档到 Redis（24小时）
        if redis_cache.enabled:
            word_cache_key = f"report_word:{user_id}:{time_range}:{now.strftime('%Y%m%d')}"
            redis_cache.set(word_cache_key, word_content, ttl=86400)
            print(f"💾 Word 文档已缓存: {word_cache_key}")
        
        # 8. WebSocket 推送结果
        print("📤 步骤6: 推送报告...")
        
        # ⭐ 防止重复推送：先检查是否已经推送过
        report_key = f"report_sent:{user_id}:{time_range}:{now.strftime('%Y%m%d%H')}"
        
        if redis_cache.enabled:
            already_sent = redis_cache.get(report_key)
            if already_sent:
                print(f"⚠️ 本小时内已推送过该用户的{time_range}报告，但仍会再次推送（用户可能重新连接）")
            else:
                # 标记为已推送（缓存1小时）
                redis_cache.set(report_key, True, ttl=3600)
        
        # ⭐ 无论是否重复，都推送报告（用户可能刷新页面后需要重新获取）
        push_success = await manager.send_to_user(user_id, {
            "type": "report_generated",
            "data": {
                "markdown": markdown_content,
                "word_available": True,
                "stats": stats,
                "time_range": time_range
            }
        })

        if push_success:
            print("✅ 报告已推送")
        else:
            print("⚠️ 报告推送失败（无在线连接），已缓存待重连后推送")

        # ⭐ 缓存报告数据到 Redis（5分钟有效），供新连接的 WebSocket 获取
        if redis_cache.enabled:
            pending_key = f"pending_report:{user_id}"
            redis_cache.set(pending_key, {
                "type": "report_generated",
                "data": {
                    "markdown": markdown_content,
                    "word_available": True,
                    "stats": stats,
                    "time_range": time_range
                }
            }, ttl=300)
            print(f"💾 报告数据已缓存到 Redis (key={pending_key}, TTL=300s)")

        # ⭐ 最后才清理提交标记，允许下次生成（必须在推送成功后）
        if redis_cache.enabled:
            submit_key = f"report_submitting:{user_id}:{time_range}"
            redis_cache.delete(submit_key)
            print(f"🧹 已清理提交标记: {submit_key}")

        return {
            "success": True,
            "markdown": markdown_content,
            "word_content": word_content,
            "stats": stats,
            "charts": charts
        }
    
    except Exception as e:
        print(f"❌ 周报生成失败: {e}")
        import traceback
        traceback.print_exc()
        
        # ⭐ 异常时也要清理提交标记，避免永久阻塞
        try:
            from app.services.cache_service import redis_cache
            if redis_cache.enabled:
                submit_key = f"report_submitting:{user_id}:{time_range}"
                redis_cache.delete(submit_key)
                print(f"🧹 已清理提交标记: {submit_key}")
        except:
            pass
        
        return {
            "success": False,
            "error": str(e)
        }
