import pymysql

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'max20040808',  # 修改为你的MySQL密码
    'database': 'bubble_chat',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# JWT配置
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)
