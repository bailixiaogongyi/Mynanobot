---
name: weather
description: Get current weather and forecasts using Seniverse API (心知天气).
homepage: https://www.seniverse.com
metadata:
  {
    "nanobot":
      {
        "emoji": "🌤️",
        "requires": { "tools": ["weather", "weather_forecast"] },
      },
  }
---

# Weather

使用心知天气 API 获取天气信息，适合国内网络环境。

## 功能

- `weather` 工具：获取实时天气
- `weather_forecast` 工具：获取未来 15 天天气预报

## 获取 API Key

1. 访问 [心知天气](https://www.seniverse.com)
2. 注册账号并创建应用
3. 获取 API Key（私钥）
4. 配置到 `~/.nanobot/config.json` 的 `tools.weather.weather.apiKey`

## 使用示例

### 实时天气

```
查询北京天气
```

返回信息：

- 位置信息（城市、国家、完整路径）
- 天气状况（晴、多云、雨等）
- 温度

### 天气预报

```
查询上海未来3天天气预报
```

返回信息：

- 每日天气（白天/夜间）
- 最高/最低温度
- 风向风力
- 湿度

## 支持的位置格式

- 城市名称：`北京`、`Beijing`、`上海`
- 城市 ID：`WX4FBXXFKE4F`
- 省市组合：`辽宁朝阳`、`广东深圳`
- 经纬度：`39.93:116.40`（纬度:经度）
- IP 地址：`220.181.111.86`
- 自动识别：`ip`（根据请求 IP 自动定位）

## 配置示例

```json
{
  "tools": {
    "weather": {
      "weather": {
        "apiKey": "your_seniverse_api_key"
      }
    }
  }
}
```

## 注意事项

- 免费版每天有调用次数限制
- 支持 14 天免费试用
- 心知天气是中国气象局官方授权数据服务商
