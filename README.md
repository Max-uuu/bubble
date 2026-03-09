# Bubble Chat
## 功能特点

- ✅ 用户注册/登录系统
- ✅ 管理员和普通用户角色区分
- ✅ 普通用户只能看到管理员和自己的消息
- ✅ 管理员可以看到所有用户的消息
- ✅ 实时消息轮询（每3秒刷新）
- ✅ JWT Token 认证
- ✅ 密码加密存储

## 安装步骤

### 1. 安装 Python 依赖

```bash
D:\anaconda\python.exe -m pip install -r requirements.txt
```

### 2. 配置 MySQL 数据库

修改 `config.py` 中的数据库配置：

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',  # 修改为你的MySQL密码
    'database': 'bubble_chat',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}
```

### 3. 创建数据库和表

在 MySQL 中执行 `database.sql` 文件：

```bash
mysql -u root -p < database.sql
```

或者手动执行：

```bash
mysql -u root -p
```

然后复制粘贴 `database.sql` 中的内容执行。

### 4. 启动后端服务

```bash
D:\anaconda\python.exe main.py
```

后端将运行在 `http://localhost:8000`

### 5. 打开前端页面

直接用浏览器打开 `index.html` 文件即可。

## 默认账号

- 用户名：`admin`
- 密码：`admin123`
- 角色：管理员

## API 接口

### 用户认证

- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `GET /api/me` - 获取当前用户信息

### 消息管理

- `POST /api/messages` - 发送消息
- `GET /api/messages` - 获取消息列表（根据用户角色返回不同内容）

## 权限说明

### 普通用户
- 可以发送消息
- 只能看到管理员发送的消息和自己发送的消息
- 看不到其他普通用户的消息

### 管理员
- 可以发送消息
- 可以看到所有用户的消息
- 消息会显示"管理员"标签

## 技术栈

- 后端：FastAPI + PyMySQL
- 前端：原生 HTML + CSS + JavaScript
- 数据库：MySQL
- 认证：JWT Token
- 密码加密：bcrypt

## 注意事项

1. 确保 MySQL 服务已启动
2. 确保 Python 环境已安装所有依赖
3. 前端需要通过浏览器打开，不能直接用 file:// 协议（CORS限制）
4. 如果遇到 CORS 问题，可以使用 Live Server 或其他本地服务器
