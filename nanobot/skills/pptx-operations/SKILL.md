---
name: pptx-operations
description: 当用户需要处理PowerPoint演示文稿时使用此技能，包括读取PPT、创建PPT、添加幻灯片、提取图片等操作。
always: false
metadata:
  nanobot:
    emoji: "📽️"
    requires:
      bins: ["python"]
      tools:
        [
          "pptx_read",
          "pptx_create",
          "pptx_add_slide",
          "pptx_extract_images",
          "pptx_list_slides",
        ]
---

# PowerPoint演示文稿操作技能

## 核心原则

- 操作前先确认PPT文件路径是否正确
- 创建新PPT时，先确认标题和内容结构
- 添加幻灯片时，确认使用合适的布局类型
- 提取图片时，确认输出目录有写入权限
- 返回结果要清晰说明处理了多少页幻灯片

## 触发条件

- 用户提到"读取PPT"、"打开PPT"、"查看PPT内容"
- 用户提到"创建PPT"、"新建演示文稿"、"制作PPT"
- 用户提到"添加幻灯片"、"新增一页"
- 用户提到"提取PPT图片"、"导出PPT图片"
- 用户提到"列出幻灯片"、"PPT有多少页"
- 用户发送一个PPT文件并要求处理

## 执行步骤

### 场景1：读取PPT内容

1. 确认用户提供的PPT文件路径
2. 使用 `pptx_list_slides` 查看幻灯片列表
3. 使用 `pptx_read` 读取所有幻灯片内容
4. 返回各页的标题和文本内容

### 场景2：创建新PPT

1. 确认输出路径和PPT标题
2. 如果需要多页内容，准备slides数组
3. 使用 `pptx_create` 创建PPT
4. 确认创建成功并告知用户

### 场景3：添加幻灯片

1. 确认PPT文件路径
2. 准备幻灯片标题和内容
3. 选择合适的布局类型（title/bullet/blank/title_only）
4. 使用 `pptx_add_slide` 添加幻灯片
5. 确认添加成功

### 场景4：提取图片

1. 确认PPT文件路径和输出目录
2. 使用 `pptx_extract_images` 提取所有图片
3. 告知用户提取了多少张图片

## 示例对话

**用户**：帮我读取这个PPT
**你**：好的，请提供PPT文件的完整路径。例如：D:/presentation/report.pptx

**用户**：D:/presentation/report.pptx
**你**：正在读取PPT内容...
[pptx_list_slides - 查看幻灯片]
该PPT共有X页幻灯片：

1. 标题页
2. 项目概述
3. 进度汇报
   ...

正在读取各页详细内容...
[读取完成]
已成功读取PPT内容，共X页。

**用户**：帮我创建一个新的PPT
**你**：请提供以下信息：

1. PPT标题（例如：2024年度总结）
2. 要包含的幻灯片内容（每页的标题和要点）

**用户**：标题是"项目汇报"，包含三页：第一页"项目概述"内容是"项目背景、项目目标"；第二页"进度情况"内容是"已完成60%、下周计划"；第三页"问题建议"内容是"风险评估、解决方案"
**你**：正在创建PPT...
[pptx_create - 创建PPT]
成功创建演示文稿 D:/output/项目汇报.pptx，包含4页幻灯片。

**用户**：在这个PPT里再加一页
**你**：请提供：

1. 幻灯片标题
2. 幻灯片内容
3. 布局类型（title/bullet/blank/title_only）

**用户**：标题"总结"，内容是"本次汇报完毕，请指正"，用title_only布局
**你**：正在添加幻灯片...
[pptx_add_slide - 添加幻灯片]
成功添加1页幻灯片，当前PPT共有5页。

## 注意事项/安全守则

- 只处理用户指定的PPT文件，不访问其他文件
- 不执行任何shell命令或安装操作
- 确保输出目录有写入权限
- 对于.ppt格式（旧版PowerPoint），告知用户需要转换为.pptx格式
- 保持原文件数据不变，建议备份后再修改
