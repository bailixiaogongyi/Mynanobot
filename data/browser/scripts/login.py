"""
@name: 登录系统
@description: 使用用户名密码登录指定系统
@category: 认证

@params:
  - username: 用户名或邮箱
  - password: 登录密码
  - url?: 登录页面地址 [default: https://example.com/login]

@returns:
  - success: 是否登录成功
  - message: 结果消息
  - user_info: 用户信息 (dict)

@keywords: 登录, login, signin, 登陆

@examples:
  - 登录系统，用户名 xxx，密码 xxx
  - 帮我登录 xxx 系统
"""


async def execute(page, **params):
    username = params.get("username", "")
    password = params.get("password", "")
    url = params.get("url", "https://example.com/login")

    await page.goto(url)
    await page.wait_for_load_state("networkidle")

    try:
        username_input = await page.query_selector('input[type="text"], input[type="email"], input[name*="user"], input[name*="email"]')
        if username_input:
            await username_input.fill(username)

        password_input = await page.query_selector('input[type="password"]')
        if password_input:
            await password_input.fill(password)

        login_btn = await page.query_selector('button[type="submit"], input[type="submit"], button:has-text("登录"), button:has-text("Login")')
        if login_btn:
            await login_btn.click()

        await page.wait_for_load_state("networkidle")

        current_url = page.url
        if "login" not in current_url.lower():
            return {
                "success": True,
                "message": "登录成功",
                "user_info": {"username": username},
            }
        else:
            error_el = await page.query_selector(".error, .alert-danger, .message-error")
            error_msg = ""
            if error_el:
                error_msg = await error_el.inner_text()
            return {
                "success": False,
                "message": f"登录失败: {error_msg or '请检查用户名密码'}",
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"登录过程出错: {str(e)}",
        }
