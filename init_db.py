"""初始化数据库脚本"""
import pymysql
from passlib.context import CryptContext

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 数据库配置（不指定database，先连接MySQL）
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'max20040808',  # 修改为你的MySQL密码
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def init_database():
    """初始化数据库"""
    print("正在连接 MySQL...")
    conn = pymysql.connect(**DB_CONFIG)
    
    try:
        with conn.cursor() as cursor:
            # 创建数据库
            print("创建数据库 bubble_chat...")
            cursor.execute("CREATE DATABASE IF NOT EXISTS bubble_chat DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute("USE bubble_chat")
            
            # 创建用户表
            print("创建用户表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # 创建消息表
            print("创建消息表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # 检查管理员是否存在
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if cursor.fetchone():
                print("管理员账号已存在")
            else:
                # 插入管理员账号
                print("创建管理员账号...")
                hashed_password = pwd_context.hash("admin123")
                cursor.execute(
                    "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, TRUE)",
                    ('admin', hashed_password)
                )
                print("管理员账号创建成功！")
                print("用户名: admin")
                print("密码: admin123")
            
            conn.commit()
            print("\n数据库初始化完成！")
            
    except Exception as e:
        print(f"错误: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
