from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import pymysql
import os
import json
from config import get_db_connection, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

app = FastAPI(title="Bubble Chat API")

# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# 数据模型
class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class MessageCreate(BaseModel):
    content: str
    message_type: Optional[str] = 'text'
    media_url: Optional[str] = None

class MessageResponse(BaseModel):
    id: int
    user_id: int
    username: str
    content: str
    message_type: str
    media_url: Optional[str]
    is_admin: bool
    avatar: Optional[str]
    created_at: str

class UserInfo(BaseModel):
    id: int
    username: str
    is_admin: bool

# 工具函数
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的认证凭证")
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的认证凭证")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, is_admin, avatar FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if user is None:
                raise HTTPException(status_code=401, detail="用户不存在")
            return user
    finally:
        conn.close()

@app.put("/api/update-username")
async def update_username(new_username: str, current_user: dict = Depends(get_current_user)):
    """修改用户名"""
    if not new_username or len(new_username.strip()) == 0:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    
    new_username = new_username.strip()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (new_username, current_user['id']))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已被使用")
            
            # 更新用户名
            cursor.execute("UPDATE users SET username = %s WHERE id = %s", (new_username, current_user['id']))
            conn.commit()
            
            return {"username": new_username}
    finally:
        conn.close()

@app.get("/api/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user

# API路由
@app.post("/api/register")
async def register(user: UserRegister):
    """用户注册"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查用户名是否存在
            cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名已存在")
            
            # 创建新用户
            hashed_password = get_password_hash(user.password)
            cursor.execute(
                "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, FALSE)",
                (user.username, hashed_password)
            )
            conn.commit()
            user_id = cursor.lastrowid
            
            # 生成token
            token = create_access_token({"user_id": user_id})
            return {
                "token": token,
                "user": {
                    "id": user_id,
                    "username": user.username,
                    "is_admin": False
                }
            }
    finally:
        conn.close()

@app.post("/api/login")
async def login(user: UserLogin):
    """用户登录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, password, is_admin FROM users WHERE username = %s",
                (user.username,)
            )
            db_user = cursor.fetchone()
            
            if not db_user or not verify_password(user.password, db_user['password']):
                raise HTTPException(status_code=401, detail="用户名或密码错误")
            
            token = create_access_token({"user_id": db_user['id']})
            return {
                "token": token,
                "user": {
                    "id": db_user['id'],
                    "username": db_user['username'],
                    "is_admin": db_user['is_admin']
                }
            }
    finally:
        conn.close()

@app.post("/api/upload-media")
async def upload_media(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """上传图片或视频"""
    # 检查文件类型
    allowed_types = ['image/', 'video/']
    if not any(file.content_type.startswith(t) for t in allowed_types):
        raise HTTPException(status_code=400, detail="只能上传图片或视频文件")
    
    # 创建上传目录
    upload_dir = "uploads/media"
    os.makedirs(upload_dir, exist_ok=True)
    
    # 生成文件名
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{current_user['id']}_{int(datetime.now().timestamp())}{file_ext}"
    file_path = os.path.join(upload_dir, filename)
    
    # 保存文件
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    media_url = f"/uploads/media/{filename}"
    media_type = 'image' if file.content_type.startswith('image/') else 'video'
    
    return {"media_url": media_url, "media_type": media_type}

@app.get("/uploads/media/{filename}")
async def get_media(filename: str):
    """获取媒体文件"""
    file_path = os.path.join("uploads/media", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="文件不存在")

@app.post("/api/upload-avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """上传头像"""
    # 检查文件类型
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只能上传图片文件")
    
    # 创建上传目录
    upload_dir = "uploads/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    
    # 生成文件名
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{current_user['id']}_{int(datetime.now().timestamp())}{file_ext}"
    file_path = os.path.join(upload_dir, filename)
    
    # 保存文件
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # 更新数据库
    avatar_url = f"/uploads/avatars/{filename}"
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET avatar = %s WHERE id = %s", (avatar_url, current_user['id']))
            conn.commit()
    finally:
        conn.close()
    
    return {"avatar": avatar_url}

@app.get("/uploads/avatars/{filename}")
async def get_avatar(filename: str):
    """获取头像"""
    file_path = os.path.join("uploads/avatars", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="头像不存在")

@app.post("/api/messages")
async def send_message(message: MessageCreate, current_user: dict = Depends(get_current_user)):
    """发送消息"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO messages (user_id, content, message_type, media_url) VALUES (%s, %s, %s, %s)",
                (current_user['id'], message.content, message.message_type, message.media_url)
            )
            conn.commit()
            message_id = cursor.lastrowid
            
            msg_data = {
                "id": message_id,
                "user_id": current_user['id'],
                "username": current_user['username'],
                "content": message.content,
                "message_type": message.message_type,
                "media_url": message.media_url,
                "is_admin": current_user['is_admin'],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 广播新消息给所有连接的客户端
            await manager.broadcast({"type": "new_message", "data": msg_data})
            
            return msg_data
    finally:
        conn.close()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接"""
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/messages", response_model=List[MessageResponse])
async def get_messages(current_user: dict = Depends(get_current_user)):
    """
    获取消息列表
    - 普通用户：只能看到管理员和自己的消息
    - 管理员：可以看到所有消息
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if current_user['is_admin']:
                # 管理员看所有消息
                cursor.execute("""
                    SELECT m.id, m.user_id, u.username, m.content, m.message_type, m.media_url, u.is_admin, u.avatar, m.created_at
                    FROM messages m
                    JOIN users u ON m.user_id = u.id
                    ORDER BY m.created_at ASC
                """)
            else:
                # 普通用户只看管理员和自己的消息
                cursor.execute("""
                    SELECT m.id, m.user_id, u.username, m.content, m.message_type, m.media_url, u.is_admin, u.avatar, m.created_at
                    FROM messages m
                    JOIN users u ON m.user_id = u.id
                    WHERE u.is_admin = TRUE OR m.user_id = %s
                    ORDER BY m.created_at ASC
                """, (current_user['id'],))
            
            messages = cursor.fetchall()
            return [
                {
                    "id": msg['id'],
                    "user_id": msg['user_id'],
                    "username": msg['username'],
                    "content": msg['content'],
                    "message_type": msg['message_type'],
                    "media_url": msg['media_url'],
                    "is_admin": msg['is_admin'],
                    "avatar": msg['avatar'],
                    "created_at": msg['created_at'].strftime("%Y-%m-%d %H:%M:%S")
                }
                for msg in messages
            ]
    finally:
        conn.close()

@app.get("/")
async def root():
    """返回首页"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Bubble Chat API"}

# 挂载静态文件
if os.path.exists("style.css"):
    @app.get("/style.css")
    async def get_style():
        return FileResponse("style.css")

if os.path.exists("script.js"):
    @app.get("/script.js")
    async def get_script():
        return FileResponse("script.js")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
