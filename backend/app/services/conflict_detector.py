"""
区间树冲突检测引擎
基于 intervaltree 实现 O(log n + k) 的高效冲突检测
"""
from intervaltree import Interval, IntervalTree
from datetime import datetime
from typing import List, Dict, Optional


class ConflictDetector:
    """
    基于区间树的冲突检测器

    优势：
    - 时间复杂度：O(log n + k)，k 是冲突数
    - 支持动态插入、删除任务
    - 比线性扫描快 10-100 倍
    """

    def __init__(self):
        self.task_tree = IntervalTree()
        self.task_map = {}  # {task_id: task_data}

    def build_from_tasks(self, tasks: List[Dict]):
        """
        从任务列表构建区间树

        Args:
            tasks: 任务列表，每个任务包含 start_time, end_time, id, title
        """
        self.task_tree.clear()
        self.task_map.clear()

        for task in tasks:
            # 跳过已取消的任务
            if task.get("status") == "cancelled":
                continue

            start = task.get("start_time")
            end = task.get("end_time")

            if start and end:
                # 解析时间
                start_dt = self._parse_time(start)
                end_dt = self._parse_time(end)

                if start_dt and end_dt:
                    task_id = task.get("id", hash(start + end))

                    # 添加到区间树
                    self.task_tree.addi(start_dt, end_dt, task_id)

                    # 保存任务详情
                    self.task_map[task_id] = task

    def find_conflicts(
            self,
            start_time: str,
            end_time: str,
            buffer_minutes: int = 15
    ) -> List[Dict]:
        """
        查找与指定时间段冲突的任务

        Args:
            start_time: 开始时间（ISO格式）
            end_time: 结束时间（ISO格式）
            buffer_minutes: 缓冲时间（分钟）

        Returns:
            冲突任务列表
        """
        start_dt = self._parse_time(start_time)
        end_dt = self._parse_time(end_time)

        if not start_dt or not end_dt:
            return []

        # 应用缓冲时间
        search_start = start_dt
        search_end = end_dt

        if buffer_minutes > 0:
            from datetime import timedelta
            search_end = search_end + timedelta(minutes=buffer_minutes)

        # 区间查询：O(log n + k)
        overlapping = self.task_tree.overlap(search_start, search_end)

        # 构建冲突信息
        conflicts = []
        for interval in overlapping:
            task_id = interval.data
            task_data = self.task_map.get(task_id, {})

            conflicts.append({
                "type": "time_overlap",
                "conflicting_task_id": task_id,
                "conflicting_task_title": task_data.get("title", "未知任务"),
                "conflicting_time": {
                    "start": task_data.get("start_time"),
                    "end": task_data.get("end_time")
                },
                "buffer_minutes": buffer_minutes,
                "message": f"与任务「{task_data.get('title', '未知任务')}」时间冲突（考虑{buffer_minutes}分钟缓冲时间）"
            })

        return conflicts

    def add_task(self, task: Dict, buffer_minutes: int = 15):
        """
        动态添加任务到区间树

        Args:
            task: 任务信息
            buffer_minutes: 缓冲时间
        """
        start = task.get("start_time")
        end = task.get("end_time")

        if start and end:
            start_dt = self._parse_time(start)
            end_dt = self._parse_time(end)

            if start_dt and end_dt:
                from datetime import timedelta
                # 添加缓冲时间到结束时间
                end_with_buffer = end_dt + timedelta(minutes=buffer_minutes)

                task_id = task.get("id", hash(start + end))
                self.task_tree.addi(start_dt, end_with_buffer, task_id)
                self.task_map[task_id] = task

    def remove_task(self, task_id):
        """从区间树中移除任务"""
        if task_id in self.task_map:
            self.task_tree.removei(
                self.task_map[task_id].get("start_time"),
                self.task_map[task_id].get("end_time"),
                task_id
            )
            del self.task_map[task_id]

    def clear(self):
        """清空区间树"""
        self.task_tree.clear()
        self.task_map.clear()

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str:
            return None
        try:
            return datetime.fromisoformat(time_str)
        except (ValueError, TypeError):
            return None


# 全局实例
conflict_detector = ConflictDetector()
