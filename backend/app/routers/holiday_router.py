"""Holiday API routes - multi-country holiday queries."""

from fastapi import APIRouter, Query, HTTPException
from datetime import date
from typing import Optional
from app.services.cache_service import redis_cache

router = APIRouter(prefix="/holidays", tags=["holidays"])


@router.get("/month")
def get_month_holidays(
    year: int = Query(..., ge=1900, le=2100, description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    country: str = Query("CN", description="ISO 3166-1 alpha-2 country code"),
):
    """Get all holiday/weekend info for a specific month and country."""
    cache_key = f"holidays:month:{country}:{year}:{month}"
    cached = redis_cache.get(cache_key)
    if cached:
        return cached

    from app.services.holiday_service import holiday_service

    holidays_data = holiday_service.get_month_holidays(year, month, country)

    result = {
        "success": True,
        "year": year,
        "month": month,
        "country": country,
        "count": len(holidays_data),
        "holidays": holidays_data,
    }
    redis_cache.set(cache_key, result, ttl=86400)
    return result

@router.get("/check")
def check_date_holiday(
    check_date: str = Query(..., description="Date string in YYYY-MM-DD format"),
    country: str = Query("CN", description="ISO 3166-1 alpha-2 country code"),
):
    """Check if a specific date is a holiday/weekend for the given country."""
    from app.services.holiday_service import holiday_service

    target_date = date.fromisoformat(check_date)
    info = holiday_service.get_holiday_info(target_date, country)

    return {
        "success": True,
        "date": check_date,
        "country": country,
        "is_holiday": info is not None,
        "holiday_name": info["name"] if info else None,
        "is_weekend": info["is_weekend"] if info else False,
        "is_legal_holiday": info["is_legal_holiday"] if info else False,
    }


@router.get("/countries")
def get_supported_countries():
    """Get list of countries supported by the holiday service."""
    cache_key = "holidays:countries"
    cached = redis_cache.get(cache_key)
    if cached:
        return cached

    from app.services.holiday_service import holiday_service

    result = {
        "success": True,
        "countries": holiday_service.get_supported_countries(),
    }
    redis_cache.set(cache_key, result, ttl=86400)
    return result

