"""backend/app/routers/holiday_router.py - 节假日查询路由"""
from fastapi import APIRouter, Query, HTTPException
from datetime import date, timedelta
from typing import Optional

router = APIRouter(prefix="/holidays", tags=["holidays"])


@router.get("/month")
def get_month_holidays(year: int = Query(..., description="年份"),
                       month: int = Query(..., description="月份")):
    """
    获取指定月份的所有节假日信息

    Args:
        year: 年份
        month: 月份 (1-12)

    Returns:
        该月份所有节假日的日期和名称
    """
    try:
        from app.services.holiday_service import holiday_service

        # ✅ 验证年份范围
        if year < 1900 or year > 2100:
            raise HTTPException(status_code=400, detail="年份必须在 1900-2100 之间")
        
        # 验证月份范围
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="月份必须在 1-12 之间")

        # 计算该月的第一天和最后一天
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        # 遍历该月所有日期，找出节假日
        holidays = []
        current = first_day
        while current <= last_day:
            holiday_name = holiday_service.get_holiday_name(current)
            if holiday_name:
                holidays.append({
                    "date": current.isoformat(),
                    "name": holiday_name,
                    "is_legal_holiday": holiday_name != "周末"
                })
            current += timedelta(days=1)

        return {
            "success": True,
            "year": year,
            "month": month,
            "count": len(holidays),
            "holidays": holidays
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取节假日失败: {str(e)}")


@router.get("/check")
def check_date_holiday(check_date: str = Query(..., description="日期 YYYY-MM-DD")):
    """
    检查指定日期是否为节假日

    Args:
        check_date: 日期字符串 (格式: YYYY-MM-DD)

    Returns:
        节假日信息
    """
    try:
        from app.services.holiday_service import holiday_service

        # 解析日期
        target_date = date.fromisoformat(check_date)

        holiday_name = holiday_service.get_holiday_name(target_date)

        return {
            "success": True,
            "date": check_date,
            "is_holiday": holiday_service.is_holiday(target_date),
            "holiday_name": holiday_name,
            "is_legal_holiday": holiday_name != "周末" if holiday_name else False
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查节假日失败: {str(e)}")
