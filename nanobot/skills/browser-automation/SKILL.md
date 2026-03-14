---
name: browser-script
description: "浏览器脚本执行器 - 用户定义JSON脚本，AI调度执行。支持Python和JSON两种脚本格式。"
metadata: { "nanobot": { "emoji": "🌐", "requires": { "bins": ["python"] } } }
---

# 浏览器脚本执行器

用户预定义脚本 → AI 理解脚本能力 → 按需调用执行 → 返回结果

## 支持的脚本格式

| 格式        | 扩展名 | 特点                       |
| ----------- | ------ | -------------------------- |
| JSON 脚本   | .json  | 声明式配置，易于生成和编辑 |
| Python 脚本 | .py    | 灵活强大，支持复杂逻辑     |

## 脚本目录

初始化后脚本目录: `~/.nanobot/browser/scripts/`

项目内置示例: `data/browser/scripts/`

## JSON 脚本结构

```json
[
  {
    "name": "脚本名称",
    "description": "功能描述",
    "category": "类别",
    "keywords": "关键词",
    "params": [
      { "name": "参数名", "type": "string", "required": true, "description": "参数说明" }
    ],
    "returns": [
      { "name": "返回值名", "description": "返回值说明", "return_type": "any" }
    ],
    "steps": [
      { "step_type": "goto", "value": "https://example.com" },
      { "step_type": "fill", "selector": "#input", "value": "text" },
      { "step_type": "click", "selector": ".btn" }
    ]
  }
]
```

## 步骤类型

| step_type      | 描述           |
| -------------- | -------------- |
| goto           | 导航到URL      |
| click          | 点击元素       |
| fill           | 填充输入框     |
| extract        | 提取数据       |
| wait           | 等待           |
| screenshot     | 截图           |
| select         | 选择下拉框     |
| check          | 勾选复选框     |
| hover          | 鼠标悬停       |
| press          | 按键           |

## 步骤字段说明

| 字段            | 类型    | 说明                           |
| --------------- | ------- | ------------------------------ |
| id              | string  | 步骤唯一标识                   |
| step_type       | string  | 步骤类型                       |
| selector        | string  | CSS选择器                      |
| selector_type   | string  | 选择器类型 (默认css)            |
| value           | string  | 值                             |
| param_binding   | string  | 参数绑定，用于动态传入值        |
| description     | string  | 步骤描述                       |
| wait_after      | int     | 步骤后等待毫秒数               |
| timeout         | int     | 超时毫秒数 (默认15000)         |
| screenshot      | string  | 截图保存路径                   |
| extract_type    | string  | 提取类型: text/html/attr       |
| extract_attr    | string  | 提取属性名 (attr类型使用)       |
| result_name     | string  | 结果名称，用于存储提取的数据   |
| multiple        | bool    | 是否提取多个元素               |
| wait_for_element| bool   | 是否等待元素出现               |

## JSON 脚本示例

参考 `data/browser/scripts/crm.json` 文件

```json
[
  {
    "name": "crm",
    "description": "查询CRM系统异常工时记录",
    "category": "其他",
    "keywords": "crm,工时,查询",
    "params": [],
    "returns": [
      { "name": "数据", "description": "异常工时记录", "return_type": "list" }
    ],
    "steps": [
      {
        "id": "1",
        "step_type": "goto",
        "value": "https://crm.example.com/login",
        "description": "导航到登录页"
      },
      {
        "id": "2", 
        "step_type": "fill",
        "selector": "input[placeholder=\"用户名\"]",
        "value": "your_username",
        "description": "输入用户名"
      },
      {
        "id": "3",
        "step_type": "fill", 
        "selector": "input[placeholder=\"密码\"]",
        "value": "your_password",
        "description": "输入密码"
      },
      {
        "id": "4",
        "step_type": "click",
        "selector": ".btn-login",
        "description": "点击登录"
      },
      {
        "id": "5",
        "step_type": "extract",
        "selector": ".data-table tr",
        "extract_type": "text",
        "multiple": true,
        "result_name": "数据",
        "description": "提取工时数据"
      }
    ]
  }
]
```

## Python 脚本模板

```python
"""
@name: 脚本名称
@description: 脚本功能描述
@category: general

@params:
  - param1: 必需参数
  - param2?: 可选参数

@returns:
  - success: 是否成功
  - data: 返回数据

@keywords: 关键词1, 关键词2
"""

from playwright.async_api import async_playwright


async def execute(page, **params):
    \"\"\"
    脚本主函数
    
    Args:
        page: Playwright page 对象
        **params: 脚本参数
        
    Returns:
        dict: 包含 success, message, data 等字段
    \"\"\"
    param1 = params.get('param1', '')
    
    # TODO: 实现你的自动化逻辑
    await page.goto('https://example.com')
    
    # 返回结果
    return {
        'success': True,
        'message': '执行成功',
        'data': {}
    }
```

## 可用命令

- 列出脚本 - 查看所有可用脚本
- 执行 xxx - 执行指定脚本
- 脚本详情 xxx - 查看指定脚本详细信息
- 重载脚本 - 重新加载脚本目录

## 参数绑定

在JSON脚本中，可以使用 `param_binding` 字段绑定用户传入的参数：

```json
{
  "step_type": "fill",
  "selector": "#username",
  "param_binding": "username",
  "description": "输入用户名"
}
```

这样执行时会将用户传入的 `username` 参数值填充到输入框。
