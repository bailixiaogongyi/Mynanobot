---
name: excel-operations
description: 当用户需要处理Excel表格文件时使用此技能，包括读取数据、写入数据、工作表管理、单元格操作等。
always: false
metadata:
  nanobot:
    emoji: "📊"
    requires:
      bins: ["python"]
      tools:
        [
          "excel_read",
          "excel_write",
          "excel_list_sheets",
          "excel_create_sheet",
          "excel_set_cell",
        ]
---

# Excel表格操作技能

## 核心原则

- 操作前先确认Excel文件路径是否正确
- 读取时注意数据量，避免一次性读取过大文件
- 写入数据时，建议先确认数据格式是否符合预期
- 对于重要数据，建议用户在操作前备份原文件
- 返回结果要清晰说明读取/写入了多少行数据

## 触发条件

- 用户提到"读取Excel"、"打开Excel"、"查看表格数据"
- 用户提到"写入Excel"、"导出Excel"、"生成报表"
- 用户提到"创建工作表"、"新建Sheet"
- 用户提到"列出所有Sheet"、"查看有哪些工作表"
- 用户提到"设置单元格"、"修改单元格"
- 用户发送一个Excel文件并要求处理

## 执行步骤

### 场景1：读取Excel数据

1. 确认用户提供的Excel文件路径
2. 使用 `excel_list_sheets` 查看有哪些工作表
3. 使用 `excel_read` 读取指定工作表数据
4. 如果数据量大，可使用 `max_rows` 参数限制行数
5. 返回JSON格式的数据

### 场景2：写入数据到Excel

1. 确认文件路径和输出位置
2. 准备数据（headers表头 + rows数据行）
3. 使用 `excel_write` 写入数据
4. 确认写入成功并告知用户

### 场景3：管理工作表

1. 使用 `excel_list_sheets` 查看现有工作表
2. 使用 `excel_create_sheet` 创建新工作表
3. 确认创建成功

### 场景4：修改单元格

1. 确认文件路径、工作表名、单元格位置
2. 使用 `excel_set_cell` 设置单元格值
3. 确认修改成功

## 示例对话

**用户**：帮我读取这个Excel文件
**你**：好的，请提供Excel文件的完整路径。例如：D:/data/sales.xlsx

**用户**：D:/data/sales.xlsx
**你**：正在读取Excel文件...
[excel_list_sheets - 查看工作表]
该文件包含以下工作表：Sheet1, Sheet2, 销售数据

请问要读取哪个工作表的数据？

**用户**：读取销售数据这个Sheet
**你**：正在读取销售数据...
[excel_read - 读取数据]
已成功读取销售数据工作表，共X行X列数据。

**用户**：帮我创建一个新的Excel文件
**你**：请提供以下信息：

1. 要保存的路径，例如：D:/output/new_file.xlsx
2. 表头数据（列名）
3. 要写入的数据

**用户**：保存到 D:/output/report.xlsx，表头是姓名、年龄、部门，数据是张三、25、研发部
**你**：正在创建Excel文件...
[excel_write - 写入数据]
成功创建Excel文件 D:/output/report.xlsx，包含1行表头和1行数据。

**用户**：在刚才的文件里添加一行数据
**用户**：D:/output/report.xlsx，李四、28、产品部
**你**：正在追加数据...
[excel_write - 追加模式]
成功追加1行数据到 D:/output/report.xlsx

## 注意事项/安全守则

- 只处理用户指定的Excel文件，不访问其他文件
- 不执行任何shell命令或安装操作
- 确保输出目录有写入权限
- 对于.xls格式（旧版Excel），告知用户需要转换为.xlsx格式
- 保持原文件数据不变，建议备份后再修改
