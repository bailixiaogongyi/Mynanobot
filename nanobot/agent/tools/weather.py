"""Weather tool using Seniverse API (适合国内网络环境)."""

import os
from typing import Any

import httpx

from nanobot.agent.tools.base import Tool
from nanobot.utils.http_client import http_client

SENIVERSE_API_URL = "https://api.seniverse.com/v3/weather/now.json"


class WeatherTool(Tool):
    """Get current weather using Seniverse API (心知天气, 适合国内网络环境)."""
    
    name = "weather"
    description = "Get current weather for a location. Returns temperature, condition, humidity, wind, etc."
    parameters = {
        "type": "object",
        "properties": {
            "location": {
                "type": "string", 
                "description": "Location to query. Supports: city name (北京/Beijing), city ID, "
                              "province+city (辽宁朝阳), coordinates (39.93:116.40), IP address, or 'ip' for auto-detect"
            },
            "language": {
                "type": "string",
                "enum": ["zh-Hans", "zh-Hant", "en", "ja", "de", "fr", "es", "pt", "hi", "id", "ru", "th", "ar"],
                "description": "Language for results (default: zh-Hans for Simplified Chinese)"
            },
            "unit": {
                "type": "string",
                "enum": ["c", "f"],
                "description": "Temperature unit: c for Celsius (default), f for Fahrenheit"
            }
        },
        "required": ["location"]
    }
    
    def __init__(self, api_key: str | None = None, api_key_getter=None):
        self._init_api_key = api_key
        self._api_key_getter = api_key_getter

    @property
    def api_key(self) -> str:
        """Resolve API key at call time so env/config changes are picked up."""
        if self._api_key_getter:
            return self._api_key_getter() or ""
        return self._init_api_key or os.environ.get("SENIVERSE_API_KEY", "")

    async def execute(
        self, 
        location: str,
        language: str = "zh-Hans",
        unit: str = "c",
        **kwargs: Any
    ) -> str:
        if not self.api_key:
            return (
                "Error: 心知天气 API key 未配置。"
                "请在 ~/.nanobot/config.json 的 tools.weather.apiKey 中设置 "
                "(或设置环境变量 SENIVERSE_API_KEY)，然后重启网关。\n"
                "获取 API Key: https://www.seniverse.com"
            )
        
        try:
            client = await http_client.get_client("weather", timeout=10.0)
            r = await client.get(
                SENIVERSE_API_URL,
                params={
                    "key": self.api_key,
                    "location": location,
                    "language": language,
                    "unit": unit
                }
            )
            r.raise_for_status()
            
            data = r.json()
            results = data.get("results", [])
            if not results:
                return f"未找到该位置的天气信息: {location}"
            
            result = results[0]
            loc = result.get("location", {})
            now = result.get("now", {})
            last_update = result.get("last_update", "")
            
            location_name = loc.get("name", location)
            country = loc.get("country", "")
            path = loc.get("path", "")
            
            text = now.get("text", "")
            code = now.get("code", "")
            temperature = now.get("temperature", "")
            
            unit_symbol = "°C" if unit == "c" else "°F"
            
            lines = [
                f"📍 位置: {location_name}",
            ]
            if path:
                lines.append(f"   完整路径: {path}")
            if country:
                lines.append(f"   国家/地区: {country}")
            
            lines.extend([
                "",
                f"🌤️ 天气: {text}",
                f"🌡️ 温度: {temperature}{unit_symbol}",
            ])
            
            if last_update:
                lines.extend([
                    "",
                    f"🕐 更新时间: {last_update}"
                ])
            
            return "\n".join(lines)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return "API Key 无效或已过期，请检查心知天气 API Key 配置"
            elif e.response.status_code == 429:
                return "API 调用次数超限，请稍后再试或升级心知天气套餐"
            return f"天气查询失败 (HTTP {e.response.status_code}): {e.response.text[:200]}"
        except Exception as e:
            return f"天气查询出错: {e}"


class WeatherForecastTool(Tool):
    """Get weather forecast using Seniverse API (心知天气)."""
    
    name = "weather_forecast"
    description = "Get weather forecast for up to 15 days. Returns daily forecasts with high/low temps."
    parameters = {
        "type": "object",
        "properties": {
            "location": {
                "type": "string", 
                "description": "Location to query. Supports: city name, city ID, coordinates, IP address"
            },
            "days": {
                "type": "integer",
                "description": "Number of days (1-15, default: 3)",
                "minimum": 1,
                "maximum": 15
            },
            "language": {
                "type": "string",
                "enum": ["zh-Hans", "zh-Hant", "en"],
                "description": "Language for results (default: zh-Hans)"
            },
            "unit": {
                "type": "string",
                "enum": ["c", "f"],
                "description": "Temperature unit: c for Celsius (default), f for Fahrenheit"
            }
        },
        "required": ["location"]
    }
    
    def __init__(self, api_key: str | None = None, api_key_getter=None):
        self._init_api_key = api_key
        self._api_key_getter = api_key_getter

    @property
    def api_key(self) -> str:
        if self._api_key_getter:
            return self._api_key_getter() or ""
        return self._init_api_key or os.environ.get("SENIVERSE_API_KEY", "")

    async def execute(
        self, 
        location: str,
        days: int = 3,
        language: str = "zh-Hans",
        unit: str = "c",
        **kwargs: Any
    ) -> str:
        if not self.api_key:
            return (
                "Error: 心知天气 API key 未配置。"
                "请在 ~/.nanobot/config.json 的 tools.weather.apiKey 中设置 "
                "(或设置环境变量 SENIVERSE_API_KEY)，然后重启网关。"
            )
        
        days = min(max(days, 1), 15)
        forecast_url = "https://api.seniverse.com/v3/weather/daily.json"
        
        try:
            client = await http_client.get_client("weather", timeout=10.0)
            r = await client.get(
                forecast_url,
                params={
                    "key": self.api_key,
                    "location": location,
                    "language": language,
                    "unit": unit,
                    "days": days
                }
            )
            r.raise_for_status()
            
            data = r.json()
            results = data.get("results", [])
            if not results:
                return f"未找到该位置的天气预报: {location}"
            
            result = results[0]
            loc = result.get("location", {})
            daily = result.get("daily", [])
            
            location_name = loc.get("name", location)
            path = loc.get("path", "")
            
            unit_symbol = "°C" if unit == "c" else "°F"
            
            lines = [
                f"📍 {location_name} 天气预报",
            ]
            if path:
                lines.append(f"   {path}")
            lines.append("")
            
            for day in daily[:days]:
                date = day.get("date", "")
                text_day = day.get("text_day", "")
                text_night = day.get("text_night", "")
                high = day.get("high", "")
                low = day.get("low", "")
                wind_direction = day.get("wind_direction", "")
                wind_scale = day.get("wind_scale", "")
                humidity = day.get("humidity", "")
                
                lines.append(f"📅 {date}")
                lines.append(f"   白天: {text_day} | 夜间: {text_night}")
                lines.append(f"   温度: {low}{unit_symbol} ~ {high}{unit_symbol}")
                if wind_direction and wind_scale:
                    lines.append(f"   风向: {wind_direction} {wind_scale}级")
                if humidity:
                    lines.append(f"   湿度: {humidity}%")
                lines.append("")
            
            return "\n".join(lines).strip()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return "API Key 无效或已过期，请检查心知天气 API Key 配置"
            elif e.response.status_code == 429:
                return "API 调用次数超限，请稍后再试或升级心知天气套餐"
            return f"天气预报查询失败 (HTTP {e.response.status_code})"
        except Exception as e:
            return f"天气预报查询出错: {e}"
