# 学生活动签到系统 (Student Check-in System)

这是一个基于 **FastAPI (Python)** 和 **MySQL** 开发的地理位置签到系统。系统支持**多管理员/多组织隔离**，管理员可以创建活动并生成二维码，学生通过邮箱验证登录后，扫描二维码并在指定地点范围内进行签到和签退。

系统集成了 **高德地图 API** 用于地理围栏判定，支持防作弊（距离校验），并具备完善的管理员后台。

## ✨ 主要功能

### 👨‍💻 管理员端 (多租户支持)

  * **独立账户**：每个管理员拥有独立的活动列表和学生数据，互不干扰。
  * **活动管理**：
      * 创建活动：设置名称、时间、签到半径，并在地图上可视化点选位置（支持拖拽修改）。
      * 生成二维码：一键生成活动专属签到二维码。
      * 编辑/删除：支持修改活动时间、地点及半径，支持删除活动（级联删除签到记录）。
  * **数据统计**：查看每个活动的详细签到/签退日志（包含学号、姓名、时间）。

### 🙋‍♂️ 学生端

  * **邮箱验证登录**：使用邮箱发送验证码登录（防暴力破解，限制发送频率）。
  * **首次注册绑定**：首次登录特定组织的活动时，需绑定学号和姓名（绑定后该账号归属于该组织）。
  * **组织隔离**：防止 A 学校的学生扫描 B 学校的二维码进行签到。
  * **扫码签到/签退**：
      * **LBS 地理围栏**：系统自动获取 GPS 位置，计算与活动中心的距离，仅在规定半径内允许签到。
      * **状态同步**：支持跨设备状态检测，防止重复签到，支持异地签退。

## 🛠 技术栈

  * **后端框架**: FastAPI (Python 3.8+)
  * **数据库**: MySQL 5.7+ / 8.0+
  * **ORM/DB库**: `mysql-connector-python` (原生 SQL 封装)
  * **前端**: 原生 HTML5 + CSS3 + JavaScript (无构建步骤，开箱即用)
  * **地图服务**: 高德地图 JS API (AMap)
  * **认证机制**: OAuth2 + JWT (JSON Web Tokens)
  * **工具库**: `pydantic` (数据校验), `haversine` (距离计算)

## 📂 项目结构

```text
students_checkin_system/
├── app/
│   ├── __init__.py
│   ├── main.py             # API 主入口
│   ├── config.py           # 配置加载 (.env)
│   ├── models.py           # Pydantic 数据模型
│   ├── db_utils.py         # 数据库 CRUD 操作 (含事务管理)
│   ├── security.py         # JWT 加密与鉴权逻辑
│   ├── coord_utils.py      # 坐标系转换 (GCJ02 <-> WGS84)
│   ├── create_admin.py     # 创建管理员脚本
│   └── static/             # 前端页面
│       ├── admin_dashboard.html
│       ├── admin_login.html
│       ├── checkin.html
│       └── student_login.html
├── requirements.txt        # 依赖列表
├── .env                    # (需新建) 环境变量配置文件
└── README.md               # 项目说明
```

## 🚀 安装与部署

### 1\. 环境准备

确保已安装 Python 3.8+ 和 MySQL 服务。

### 2\. 安装依赖

在项目根目录下运行：

```bash
pip install -r requirements.txt
```

### 3\. 数据库初始化

请在 MySQL 中创建一个数据库（例如 `student_system_db`），并执行以下 SQL 语句。

> **注意**：与旧版本相比，表结构增加了 `admin_id` 以支持多用户隔离。

```sql
CREATE DATABASE IF NOT EXISTS student_system_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_system_db;

-- 1. 管理员表
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. 参与者表 (增加 admin_id 以区分不同组织的相同学号)
CREATE TABLE participants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    admin_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admins(id),
    -- 同一个管理员下的学号不能重复，但不同管理员可以有相同学号
    UNIQUE KEY unique_student_admin (student_id, admin_id)
);

-- 3. 活动表 (关联到管理员)
CREATE TABLE activities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    unique_code VARCHAR(36) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    location_name VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    radius_meters INT DEFAULT 100,
    start_time DATETIME,
    end_time DATETIME,
    admin_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admins(id)
);

-- 4. 签到日志表
CREATE TABLE check_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    activity_id INT,
    participant_id INT,
    device_session_token VARCHAR(255),
    check_in_time DATETIME,
    check_out_time DATETIME,
    check_in_lat DECIMAL(10, 8),
    check_in_lon DECIMAL(11, 8),
    check_out_lat DECIMAL(10, 8),
    check_out_lon DECIMAL(11, 8),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    FOREIGN KEY (participant_id) REFERENCES participants(id)
);

-- 5. 验证码表
CREATE TABLE verification_codes (
    email VARCHAR(100) PRIMARY KEY,
    code VARCHAR(10),
    expires_at DATETIME
);
```

### 4\. 配置文件 (.env)

在项目根目录（与 `app/` 同级）创建一个名为 `.env` 的文件，并填入以下内容：

```ini
# 数据库配置
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_db_password
DB_NAME=student_system_db

# JWT 安全密钥 (生产环境请生成随机强密码)
JWT_SECRET_KEY=please_change_this_to_a_secure_random_string

# 邮件发送配置 (用于发送验证码，以 QQ 邮箱为例)
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_smtp_auth_code
```

### 5\. 创建首个管理员

运行以下命令，按照提示输入用户名和密码：

```bash
python -m app.create_admin
```

### 6\. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📖 使用指南

### 管理员流程

1.  访问 `http://localhost:8000/static/admin_login.html`（或根据 Nginx 配置的路径）。
2.  登录后进入控制台。
3.  **创建活动**：填写信息，在地图上点击选择中心点。
4.  **分发**：在活动列表中点击“二维码”，下载图片或复制链接发送给学生。

### 学生流程

1.  扫描管理员提供的二维码。
2.  输入邮箱获取验证码。如果是该组织的新用户，系统会提示输入学号和姓名。
3.  登录成功后点击“立即签到”。允许浏览器获取地理位置权限。
4.  活动结束离开时，点击“签退”。

## ⚠️ 注意事项

1.  **HTTPS 必须开启**：浏览器的地理位置 API (`navigator.geolocation`) 在非 Localhost 环境下**强制要求 HTTPS**。若部署在公网服务器，请配置 Nginx 反向代理并启用 SSL 证书。
2.  **高德地图 Key**：项目中使用的 Key 仅供测试。请前往 [高德开放平台](https://console.amap.com/) 申请您自己的 Web 端 (JS API) Key，并替换 `admin_dashboard.html` 和 `checkin.html` 中的 Key 和安全密钥配置。
3.  **时区问题**：代码中使用 `datetime.now()`，请确保服务器时区设置正确。
4.  **Nginx 配置**：如果你使用了 `/students_system/` 这样的子路径反代，请确保前端 HTML 中的 API 请求路径与 Nginx 的 rewrite 规则匹配。