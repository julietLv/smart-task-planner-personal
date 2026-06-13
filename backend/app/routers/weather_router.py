"""天气服务路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date

router = APIRouter(prefix="/weather", tags=["weather"])


class WeatherRequest(BaseModel):
    city: str
    date: Optional[str] = None
    user_id: Optional[int] = 1


class CityUpdateRequest(BaseModel):
    user_id: Optional[int] = 1
    city: str


@router.get("/current")
def get_current_weather(city: str = None, user_id: int = 1):
    """
    获取指定城市的当前天气

    Args:
        city: 城市名称（不传则使用用户设置的城市）
        user_id: 用户ID

    Returns:
        天气信息
    """
    try:
        from app.services.weather_service import weather_service
        from app.models.task_model import get_user_preferences

        # 如果没有指定城市，获取用户设置的城市
        if not city:
            prefs = get_user_preferences(user_id)
            city = prefs.user_city if prefs else "北京"

        # 获取今天天气
        today = date.today()
        weather = weather_service.get_weather(today, city)

        return {
            "success": True,
            "city": city,
            "date": today.isoformat(),
            **weather
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取天气失败: {str(e)}")


@router.get("/forecast")
def get_weather_forecast(city: str = None, days: int = 3, user_id: int = 1):
    """
    获取未来几天天气预报

    Args:
        city: 城市名称
        days: 天数
        user_id: 用户ID

    Returns:
        天气预报列表
    """
    try:
        from app.services.weather_service import weather_service
        from app.models.task_model import get_user_preferences

        if not city:
            prefs = get_user_preferences(user_id)
            city = prefs.user_city if prefs else "北京"

        from datetime import timedelta
        forecasts = []

        for i in range(days):
            check_date = date.today() + timedelta(days=i)
            weather = weather_service.get_weather(check_date, city)
            forecasts.append({
                "date": check_date.isoformat(),
                **weather
            })

        return {
            "success": True,
            "city": city,
            "forecasts": forecasts
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取天气预报失败: {str(e)}")


@router.put("/city")
def update_user_city(request: CityUpdateRequest):
    """
    更新用户城市设置

    Args:
        request: 包含用户ID和城市名称

    Returns:
        更新结果
    """
    try:
        from app.models.task_model import update_user_preferences

        update_user_preferences(
            user_id=request.user_id,
            user_city=request.city
        )

        return {
            "success": True,
            "message": f"城市已更新为: {request.city}",
            "city": request.city
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新城市失败: {str(e)}")


@router.get("/city")
def get_user_city(user_id: int = 1):
    """
    获取用户设置的城市

    Args:
        user_id: 用户ID

    Returns:
        用户城市
    """
    try:
        from app.models.task_model import get_user_preferences

        prefs = get_user_preferences(user_id)
        city = prefs.user_city if prefs else "北京"

        return {
            "success": True,
            "city": city
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取城市失败: {str(e)}")
