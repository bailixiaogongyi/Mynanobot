"""
@name: 查询报表
@description: 查询指定日期范围的报表数据
@category: 报表

@params:
  - start_date: 开始日期 (string)
  - end_date: 结束日期 (string)
  - report_type?: 报表类型 [default: daily]

@returns:
  - success: 是否成功
  - message: 结果消息
  - data: 报表数据列表 (list)
  - total: 数据总数 (int)

@keywords: 报表, 查询, report, 数据, 统计

@examples:
  - 查询上个月的报表
  - 查询 2024-01-01 到 2024-01-31 的报表
"""


async def execute(page, **params):
    start_date = params.get("start_date", "")
    end_date = params.get("end_date", "")
    report_type = params.get("report_type", "daily")

    try:
        date_start_input = await page.query_selector('input[name*="start"], input[placeholder*="开始"], input[id*="start"]')
        if date_start_input:
            await date_start_input.fill(start_date)

        date_end_input = await page.query_selector('input[name*="end"], input[placeholder*="结束"], input[id*="end"]')
        if date_end_input:
            await date_end_input.fill(end_date)

        search_btn = await page.query_selector('button:has-text("查询"), button:has-text("搜索"), button:has-text("Query")')
        if search_btn:
            await search_btn.click()

        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)

        data = []
        rows = await page.query_selector_all("table tbody tr, .data-row, .list-item")
        for row in rows[:20]:
            cells = await row.query_selector_all("td, .cell")
            row_data = []
            for cell in cells:
                text = await cell.inner_text()
                row_data.append(text.strip())
            if row_data:
                data.append(row_data)

        return {
            "success": True,
            "message": f"查询完成，共 {len(data)} 条数据",
            "data": data,
            "total": len(data),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"查询过程出错: {str(e)}",
            "data": [],
            "total": 0,
        }
