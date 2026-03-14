---
name: pdf-operations
description: 当用户需要处理PDF文档时使用此技能，包括读取PDF文本、提取图片、提取表格、转换为Markdown等操作。
always: false
metadata:
  nanobot:
    emoji: "📄"
    requires:
      bins: ["python"]
      tools:
        [
          "pdf_read_text",
          "pdf_read_structure",
          "pdf_extract_images",
          "pdf_extract_tables",
          "pdf_to_markdown",
        ]
---

# PDF文档操作技能

## 核心原则

- 只处理用户明确要求的PDF操作任务，不做多余处理
- 操作前先确认PDF文件路径是否正确
- 对于大型PDF文件，注意处理时间，可能需要较长时间
- 提取图片或表格时，先确认目标页码范围
- 返回结果要清晰说明提取了多少内容

## 触发条件

- 用户提到"读取PDF"、"打开PDF"、"查看PDF内容"
- 用户提到"提取PDF图片"、"导出PDF图片"
- 用户提到"提取PDF表格"、"PDF表格数据"
- 用户提到"PDF转Markdown"、"PDF转格式"
- 用户提到"查看PDF结构"、"PDF有多少页"
- 用户发送一个PDF文件并要求处理

## 执行步骤

### 场景1：读取PDF文本内容

1. 确认用户提供的PDF文件路径
2. 如果用户未指定页面范围，使用 `pdf_read_text` 读取全部内容
3. 如果用户指定了页面范围（如"1-5页"），使用 `pages` 参数
4. 返回提取的文本内容

### 场景2：提取PDF中的图片

1. 确认文件路径和输出目录
2. 使用 `pdf_extract_images` 提取所有图片
3. 告知用户提取了多少张图片

### 场景3：提取PDF中的表格

1. 确认文件路径和页码
2. 使用 `pdf_extract_tables` 提取表格
3. 以JSON格式返回表格数据

### 场景4：转换为Markdown

1. 确认文件路径和输出路径
2. 使用 `pdf_to_markdown` 转换
3. 可选择保存为.md文件或直接返回内容

## 示例对话

**用户**：帮我读取这个PDF的内容
**你**：好的，请提供PDF文件的完整路径。例如：D:/documents/report.pdf

**用户**：D:/documents/report.pdf
**你**：正在读取PDF内容...
[提取文本内容]
已成功读取PDF内容，共X页。

**用户**：提取这个PDF里的图片
**你**：请提供PDF文件路径和保存图片的目录。例如：提取到 D:/output/images/

**用户**：PDF在 D:/docs/manual.pdf，图片保存到 D:/output/img
**你**：正在提取图片...
[提取图片]
成功提取了 X 张图片，保存到 D:/output/img/

**用户**：把这PDF转成Markdown
**你**：请提供PDF文件路径和输出的Markdown文件路径。

**用户**：D:/docs/report.pdf 转为 D:/output/report.md
**你**：正在转换PDF为Markdown...
转换成功！Markdown内容如下：
[Markdown内容]

## 注意事项/安全守则

- 只读取用户指定的PDF文件，不访问其他文件
- 不执行任何shell命令或安装操作
- 对于加密或受保护的PDF，告知用户可能无法处理
- 确保输出目录有写入权限
- 保持原始PDF内容不变，不做任何修改
