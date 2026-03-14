---
name: word-operations
description: "Word文档操作 - 读取内容、调整样式、表格操作、模板生成文档"
metadata:
  nanobot:
    emoji: "📝"
    requires:
      bins: ["python"]
      tools: ["docx_read_structure", "docx_read_text", "docx_read_tables",
              "docx_set_font", "docx_set_paragraph_format", "docx_set_heading_style",
              "docx_set_table_style", "docx_from_template"]
---

# Word文档操作技能

## 工具清单

| 工具 | 用途 | 典型场景 |
|------|------|----------|
| `docx_read_structure` | 查看文档结构 | 了解文档组成、标题层级 |
| `docx_read_text` | 读取文本内容 | 提取正文内容 |
| `docx_read_tables` | 读取表格数据 | 获取表格信息 |
| `docx_set_font` | 设置字体样式 | 统一字体格式 |
| `docx_set_paragraph_format` | 设置段落格式 | 调整行距、缩进 |
| `docx_set_heading_style` | 设置标题样式 | 规范标题格式 |
| `docx_set_table_style` | 设置表格样式 | 美化表格 |
| `docx_from_template` | 模板生成文档 | 批量生成报告、会议纪要 |

## 典型工作流

### 场景1：统一调整文档格式

```
1. docx_read_structure → 了解文档结构
2. docx_set_font → 设置正文字体
3. docx_set_heading_style → 设置各级标题样式
4. docx_set_paragraph_format → 设置行距
```

### 场景2：处理表格

```
1. docx_read_tables → 查看表格内容
2. docx_set_table_style → 设置表格样式
```

### 场景3：生成会议纪要

```
1. 准备模板文件（使用Jinja2语法）
2. docx_from_template → 传入数据生成文档
```

## 字体设置参数

### font_name 常用值

| 中文名 | font_name |
|--------|-----------|
| 微软雅黑 | Microsoft YaHei |
| 宋体 | SimSun |
| 黑体 | SimHei |
| 楷体 | KaiTi |
| 仿宋 | FangSong |

### target 目标范围

| 值 | 说明 |
|----|------|
| `all` | 全部内容 |
| `paragraphs` | 仅正文段落（不含标题） |
| `headings` | 所有标题 |
| `heading1` | 一级标题 |
| `heading2` | 二级标题 |
| `heading3` | 三级标题 |
| `tables` | 表格内容 |

## 模板语法

模板文件使用 Jinja2 语法：

### 变量替换
```
{{title}}      → 标题
{{date}}       → 日期
{{author}}     → 作者
```

### 条件判断
```
{% if show_header %}
显示头部内容
{% endif %}
```

### 循环遍历
```
{% for item in items %}
- {{item.name}}
{% endfor %}
```

### 表格行循环
```
{% for person in attendees %}
| {{person.name}} | {{person.department}} |
{% endfor %}
```

## 示例调用

### 读取文档结构
```json
{
    "path": "/path/to/document.docx"
}
```

### 设置正文字体
```json
{
    "path": "/path/to/document.docx",
    "target": "paragraphs",
    "font_name": "Microsoft YaHei",
    "font_size": 12
}
```

### 设置标题样式
```json
{
    "path": "/path/to/document.docx",
    "heading_level": 1,
    "font_name": "SimHei",
    "font_size": 18,
    "bold": true
}
```

### 设置行距
```json
{
    "path": "/path/to/document.docx",
    "target": "paragraphs",
    "line_spacing": 1.5,
    "first_line_indent": 2
}
```

### 模板生成文档
```json
{
    "template_path": "/templates/meeting.docx",
    "output_path": "/output/meeting_2024-01-15.docx",
    "context": {
        "title": "项目会议纪要",
        "date": "2024年1月15日",
        "attendees": [
            {"name": "张三", "department": "技术部"},
            {"name": "李四", "department": "产品部"}
        ]
    }
}
```
