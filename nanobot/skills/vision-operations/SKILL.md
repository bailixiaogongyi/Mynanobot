---
name: vision-operations
description: 图片内容识别和文生图操作技能，支持图片分析、理解和AI生成图片
always: false
metadata:
  nanobot:
    emoji: "🖼️"
    requires:
      tools: ["understand_image", "generate_image"]
---

# 视觉操作技能

## 核心原则

- 操作前先确认图片路径是否正确
- 对于图片理解，构建清晰具体的问题描述
- 对于文生图，提供详细的提示词以获得更好效果
- 告知用户处理进度和结果

## 触发条件

- 用户发送图片并询问内容
- 用户要求"识别图片"、"分析图片"、"看图"
- 用户提到"画图"、"生成图片"、"创建图像"
- 用户要求描述图片内容或提取图片中的文字/信息

## 图片理解 (understand_image)

### 使用场景

- 分析图片内容
- 描述图片中的场景、物体、人物
- 识别图片中的文字
- 回答关于图片的具体问题

### 最佳实践

1. **确认图片路径**
   - 检查用户提供的路径是否存在
   - 如果是相对路径，转换为绝对路径

2. **构建清晰的问题**
   - 默认问题："详细描述这张图片的内容"
   - 识别文字："这张图片中有哪些文字？请完整列出"
   - 分析场景："图片中有哪些物体？它们的位置关系是什么？"
   - 细节问题："图片中的人穿什么颜色的衣服？"

3. **处理结果**
   - 清晰呈现分析结果
   - 如果结果不完整，可以追问或重新分析

### 示例调用

```
understand_image(
    image_path="/path/to/image.png",
    question="详细描述这张图片的内容，包括主要物体、颜色、场景等"
)
```

## 文生图 (generate_image)

### 使用场景

- 根据文字描述生成图片
- 创建概念图、示意图
- 生成创意图片

### 最佳实践

1. **提示词优化**
   - 使用具体的描述而非抽象概念
   - 包含风格、色调、构图等细节
   - 对于中文提示词，建议翻译为英文以获得更好效果（部分模型）

2. **参数选择**
   - size: 根据用途选择尺寸
     - "1024x1024": 正方形，适合头像、图标
     - "1792x1024": 横版，适合横幅、封面
     - "1024x1792": 竖版，适合海报、手机壁纸
   - quality: "standard" 或 "hd"（仅DALL-E 3支持）
   - n: 生成数量（1-10）

3. **提示词模板**

   **人物肖像**:
   ```
   A portrait of [subject], [style] style, [lighting] lighting, 
   [background], high detail, professional photography
   ```

   **风景场景**:
   ```
   A [time of day] landscape of [scene], [weather] weather,
   [art style], atmospheric, detailed
   ```

   **产品设计**:
   ```
   A product photo of [product], [background] background,
   studio lighting, commercial photography, high quality
   ```

### 示例调用

```
generate_image(
    prompt="A serene Japanese garden with cherry blossoms, 
            koi pond, stone bridge, morning light, 
            impressionist painting style",
    size="1024x1024",
    quality="standard",
    n=1
)
```

## 工作流程

### 场景1：分析用户上传的图片

1. 确认图片路径（用户上传后通常在工作目录或上传目录）
2. 根据用户问题构建分析请求
3. 调用 `understand_image` 工具
4. 整理并呈现结果

### 场景2：生成图片

1. 理解用户的图片需求
2. 优化提示词（必要时翻译为英文）
3. 选择合适的尺寸和质量参数
4. 调用 `generate_image` 工具
5. 返回生成的图片路径

### 场景3：图片内容修改建议

1. 先使用 `understand_image` 分析原图
2. 根据用户需求提出修改建议
3. 如需生成新图，使用 `generate_image`

## 注意事项

- 图片理解依赖视觉模型能力，复杂场景可能需要多次分析
- 文生图效果受提示词质量影响较大
- 生成的图片保存在工作目录的 generated_images 文件夹中
- 部分模型对中文提示词支持有限，建议使用英文提示词
