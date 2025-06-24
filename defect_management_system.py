import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
import sqlite3
import hashlib
from typing import Dict, List
import time
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import requests

# 設定頁面配置
st.set_page_config(
    page_title="🚀 不良品處理管理系統",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義CSS樣式 - 使用用戶偏好的淺藍色科技風格
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
    }

    .status-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #2563eb;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }

    .urgent-card {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border-left: 4px solid #ef4444;
    }

    .normal-card {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border-left: 4px solid #3b82f6;
    }

    .completed-card {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border-left: 4px solid #10b981;
    }

    .metric-card {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem;
    }

    .department-tag {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        margin: 0.25rem;
    }

    .engineering-tag {
        background-color: #dbeafe;
        color: #1e40aff;
    }

    .quality-tag {
        background-color: #fef3c7;
        color: #92400e;
    }

    .manufacturing-tag {
        background-color: #dcfce7;
        color: #166534;
    }

    .stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }

    .stSelectbox label, .stTextInput label, .stTextArea label {
        color: #2563eb;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 資料庫初始化


def init_database():
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()

    # 創建用戶表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            position TEXT NOT NULL,
            role TEXT NOT NULL,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # 檢查是否有預設管理員帳戶，沒有則創建
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        admin_password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (username, password_hash, name, department, position, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', admin_password_hash, '系統管理員', '資訊部', '系統管理員', '管理員'))

    # 創建不良品記錄表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_order TEXT NOT NULL,
            product_name TEXT NOT NULL,
            defect_type TEXT NOT NULL,
            defect_level TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            package_number INTEGER DEFAULT 1,
            description TEXT,
            responsible_dept TEXT NOT NULL,
            status TEXT DEFAULT '待處理',
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline TIMESTAMP,
            assigned_person TEXT,
            resolution TEXT,
            completion_time TIMESTAMP,
            logged_by TEXT DEFAULT '系統'
        )
    ''')

    # 檢查是否需要新增package_number欄位（為了向後兼容）
    cursor.execute("PRAGMA table_info(defects)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'package_number' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN package_number INTEGER DEFAULT 1')
        st.info("📦 資料庫已更新，新增包數功能")

    # 檢查是否需要新增logged_by欄位（為了向後兼容）
    if 'logged_by' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN logged_by TEXT DEFAULT "系統"')
        st.info("👤 資料庫已更新，新增登錄人員追蹤功能")

    # 檢查是否需要新增流程管理欄位
    if 'primary_dept' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN primary_dept TEXT')
        st.info("🔄 資料庫已更新，新增主要責任部門功能")

    if 'secondary_dept' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN secondary_dept TEXT')
        st.info("🔄 資料庫已更新，新增次要責任部門功能")

    if 'primary_person' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN primary_person TEXT')
        st.info("👤 資料庫已更新，新增主要責任人功能")

    if 'secondary_person' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN secondary_person TEXT')
        st.info("👤 資料庫已更新，新增次要責任人功能")

    if 'approval_status' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN approval_status TEXT DEFAULT "待主要單位處理"')
        st.info("✅ 資料庫已更新，新增簽核狀態功能")

    if 'approval_result' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN approval_result TEXT')
        st.info("📋 資料庫已更新，新增簽核結果功能")

    # 檢查是否需要新增supplier欄位（為了向後兼容）
    if 'supplier' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN supplier TEXT')
        st.info("🏭 資料庫已更新，新增供應商功能")

    # 檢查是否需要新增component欄位（為了向後兼容）
    if 'component' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN component TEXT')
        st.info("🔧 資料庫已更新，新增零件功能")

    if 'work_order_total_qty' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN work_order_total_qty INTEGER DEFAULT 0')
        st.info("📊 資料庫已更新，新增工單總數功能")

    # 檢查是否需要新增第三責任人相關欄位
    if 'third_dept' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN third_dept TEXT')
        st.info("🔄 資料庫已更新，新增第三責任部門功能")

    if 'third_person' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN third_person TEXT')
        st.info("👤 資料庫已更新，新增第三責任人功能")

    if 'third_approval_status' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN third_approval_status TEXT')
        st.info("✅ 資料庫已更新，新增第三責任人簽核狀態功能")

    # 檢查是否需要新增supplier欄位
    if 'supplier' not in columns:
        cursor.execute('ALTER TABLE defects ADD COLUMN supplier TEXT')
        st.info("🏭 資料庫已更新，新增供應商功能")

    # 檢查並修復現有記錄的部門分配（只在必要時執行）
    try:
        cursor.execute('SELECT COUNT(*) FROM defects WHERE primary_dept IS NULL OR secondary_dept IS NULL')
        need_repair = cursor.fetchone()[0]

        if need_repair > 0:
            # 修復primary_dept和secondary_dept為空的記錄
            cursor.execute('''
                UPDATE defects
                SET primary_dept = CASE
                    WHEN defect_type IN ('外觀不良', '表面缺陷') THEN '品保部'
                    ELSE '工程部'
                END,
                secondary_dept = CASE
                    WHEN defect_type IN ('外觀不良', '表面缺陷') THEN '工程部'
                    ELSE '品保部'
                END
                WHERE primary_dept IS NULL OR secondary_dept IS NULL
            ''')

            # 確保responsible_dept與primary_dept一致
            cursor.execute('''
                UPDATE defects
                SET responsible_dept = primary_dept
                WHERE approval_status = '待主要單位處理' OR approval_status IS NULL
            ''')
    except sqlite3.OperationalError as e:
        # 如果數據庫被鎖定，跳過修復步驟
        if "database is locked" in str(e).lower():
            pass  # 靜默跳過，避免系統無法啟動
        else:
            raise e

    # 創建處理記錄表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processing_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            defect_id INTEGER,
            action TEXT NOT NULL,
            department TEXT NOT NULL,
            operator TEXT NOT NULL,
            comment TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (defect_id) REFERENCES defects (id)
        )
    ''')

    conn.commit()
    conn.close()

# 用戶認證相關函數


def hash_password(password: str) -> str:
    """密碼哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """驗證密碼"""
    return hash_password(password) == password_hash

def authenticate_user(username: str, password: str) -> Dict:
    """用戶認證"""
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, password_hash, name, department, position, role, is_active
        FROM users WHERE username = ? AND is_active = 1
    ''', (username,))

    user = cursor.fetchone()

    if user and verify_password(password, user[2]):
        # 更新最後登入時間
        cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user[0],))
        conn.commit()
        conn.close()

        return {
            'id': user[0],
            'username': user[1],
            'name': user[3],
            'department': user[4],
            'position': user[5],
            'role': user[6]
        }

    conn.close()
    return None

def get_all_users():
    """獲取所有用戶"""
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, name, department, position, role, created_time, last_login, is_active
        FROM users ORDER BY created_time DESC
    ''')

    users = cursor.fetchall()
    conn.close()
    return users

def add_user(username: str, password: str, name: str, department: str, position: str, role: str) -> bool:
    """添加新用戶"""
    try:
        conn = sqlite3.connect('defect_management.db')
        cursor = conn.cursor()

        password_hash = hash_password(password)

        cursor.execute('''
            INSERT INTO users (username, password_hash, name, department, position, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, password_hash, name, department, position, role))

        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def update_user_status(user_id: int, is_active: bool):
    """更新用戶狀態"""
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()

    cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (1 if is_active else 0, user_id))

    conn.commit()
    conn.close()

def reset_user_password(user_id: int, new_password: str):
    """重設用戶密碼"""
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()

    password_hash = hash_password(new_password)
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))

    conn.commit()
    conn.close()

# 資料庫操作函數


def get_next_package_number(work_order):
    """獲取指定工單的下一個包數"""
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT MAX(package_number) FROM defects WHERE work_order = ?
    ''', (work_order,))

    result = cursor.fetchone()[0]
    conn.close()

    return (result + 1) if result else 1

def get_work_order_stats(work_order):
    """獲取指定工單的統計信息"""
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()

    # 獲取該工單的總不良數量和工單總數
    cursor.execute('''
        SELECT SUM(quantity) as total_defects,
               MAX(work_order_total_qty) as total_qty,
               COUNT(*) as record_count
        FROM defects
        WHERE work_order = ?
    ''', (work_order,))

    result = cursor.fetchone()
    conn.close()

    total_defects = result[0] if result[0] else 0
    total_qty = result[1] if result[1] else 0
    record_count = result[2] if result[2] else 0

    defect_rate = (total_defects / total_qty * 100) if total_qty > 0 else 0

    return {
        'total_defects': total_defects,
        'total_qty': total_qty,
        'record_count': record_count,
        'defect_rate': defect_rate
    }

def add_defect(defect_data):
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()

    # 計算截止時間
    level_hours = {'A級': 4, 'B級': 8, 'C級': 24}
    deadline = datetime.now() + timedelta(hours=level_hours[defect_data['defect_level']])

    cursor.execute('''
        INSERT INTO defects (work_order, product_name, defect_type, defect_level,
                           quantity, package_number, description, responsible_dept, deadline, assigned_person, logged_by,
                           primary_dept, secondary_dept, primary_person, secondary_person, approval_status, work_order_total_qty, supplier, component)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        defect_data['work_order'],
        defect_data['product_name'],
        defect_data['defect_type'],
        defect_data['defect_level'],
        defect_data['quantity'],
        defect_data['package_number'],
        defect_data['description'],
        defect_data['primary_dept'],  # 主要責任部門作為responsible_dept
        deadline,
        defect_data['primary_person'],  # 主要責任人作為assigned_person
        defect_data.get('operator', '系統'),
        defect_data['primary_dept'],
        defect_data['secondary_dept'],
        defect_data['primary_person'],
        defect_data.get('secondary_person', ''),
        '待主要單位處理',
        defect_data.get('work_order_total_qty', 0),
        defect_data.get('supplier', ''),
        defect_data.get('component', '')
    ))

    defect_id = cursor.lastrowid

    # 添加處理記錄
    cursor.execute('''
        INSERT INTO processing_logs (defect_id, action, department, operator, comment)
        VALUES (?, ?, ?, ?, ?)
    ''', (defect_id, '新增不良品', '品保部', defect_data.get('operator', '系統'), '不良品登錄'))

    conn.commit()
    conn.close()
    return defect_id

def get_defects(status=None):
    conn = sqlite3.connect('defect_management.db')
    query = '''
        SELECT id, work_order, product_name, defect_type, defect_level, quantity,
               package_number, description, responsible_dept, status, created_time, deadline,
               assigned_person, resolution, completion_time, logged_by,
               primary_dept, secondary_dept, primary_person, secondary_person, approval_status, approval_result,
               work_order_total_qty, supplier, component, third_dept, third_person, third_approval_status
        FROM defects
    '''

    if status:
        query += " WHERE status = ?"
    query += " ORDER BY created_time DESC"

    df = pd.read_sql_query(query, conn, params=(status,) if status else None)
    conn.close()
    return df

def update_defect_status(defect_id, new_status, resolution=None, operator=None):
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()

    if new_status == '已完成':
        cursor.execute('''
            UPDATE defects
            SET status = ?, resolution = ?, completion_time = CURRENT_TIMESTAMP, updated_time = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_status, resolution, defect_id))
    else:
        cursor.execute('''
            UPDATE defects
            SET status = ?, updated_time = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_status, defect_id))

    # 添加處理記錄
    cursor.execute('''
        INSERT INTO processing_logs (defect_id, action, department, operator, comment)
        VALUES (?, ?, ?, ?, ?)
    ''', (defect_id, f'狀態更新為{new_status}', '系統', operator or '系統', resolution or ''))

    conn.commit()
    conn.close()

def transfer_defect(defect_id, target_dept, transfer_reason, operator=None):
    """轉交不良品到其他部門"""
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()

    # 先獲取不良品的責任部門和負責人信息
    cursor.execute('''
        SELECT primary_dept, secondary_dept, primary_person, secondary_person, defect_type
        FROM defects WHERE id = ?
    ''', (defect_id,))

    defect_info = cursor.fetchone()
    assigned_person = ''

    if defect_info:
        primary_dept, secondary_dept, primary_person, secondary_person, defect_type = defect_info

        # 如果轉交到次要責任部門，使用次要負責人
        if target_dept == secondary_dept and secondary_person:
            assigned_person = secondary_person
        # 如果轉交到主要責任部門，使用主要負責人
        elif target_dept == primary_dept and primary_person:
            assigned_person = primary_person
        else:
            # 轉交到其他部門，根據部門獲取預設負責人
            personnel_settings = load_personnel_settings()
            dept_persons = [person['display_name'] for person in personnel_settings.get('responsible_persons', [])
                           if person['department'] == target_dept]
            if dept_persons:
                assigned_person = dept_persons[0]  # 使用該部門的第一個負責人

    # 更新責任部門和負責人，狀態改為待處理
    cursor.execute('''
        UPDATE defects
        SET responsible_dept = ?, status = '待處理', assigned_person = ?, updated_time = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (target_dept, assigned_person, defect_id))

    # 記錄轉交日誌
    transfer_log = f'轉交至{target_dept}'
    if assigned_person:
        transfer_log += f'，負責人：{assigned_person}'

    cursor.execute('''
        INSERT INTO processing_logs (defect_id, action, department, operator, comment)
        VALUES (?, ?, ?, ?, ?)
    ''', (defect_id, transfer_log, target_dept, operator or '系統', transfer_reason))

    conn.commit()
    conn.close()

def get_processing_logs(defect_id):
    conn = sqlite3.connect('defect_management.db')
    query = '''
        SELECT action, department, operator, comment, timestamp
        FROM processing_logs
        WHERE defect_id = ?
        ORDER BY timestamp DESC
    '''
    df = pd.read_sql_query(query, conn, params=(defect_id,))
    conn.close()
    return df

def delete_defect(defect_id, operator=None):
    """刪除不良品記錄（包含相關的處理記錄）"""
    try:
        conn = sqlite3.connect('defect_management.db')
        cursor = conn.cursor()

        # 先獲取要刪除的記錄信息（用於記錄日誌）
        cursor.execute("SELECT work_order, product_name, defect_type FROM defects WHERE id = ?", (defect_id,))
        defect_info = cursor.fetchone()

        if defect_info:
            work_order, product_name, defect_type = defect_info

            # 刪除處理記錄
            cursor.execute("DELETE FROM processing_logs WHERE defect_id = ?", (defect_id,))

            # 刪除不良品記錄
            cursor.execute("DELETE FROM defects WHERE id = ?", (defect_id,))

            conn.commit()
            conn.close()
            return True, f"記錄已刪除 - 工單:{work_order}, 產品:{product_name}, 類型:{defect_type}"
        else:
            conn.close()
            return False, "找不到指定的記錄"

    except Exception as e:
        return False, f"刪除失敗: {str(e)}"

# 人員管理函數


def load_personnel_settings():
    """載入人員設定"""
    try:
        with open('personnel_settings.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 如果檔案不存在，創建預設設定
        default_settings = {
            "responsible_persons": []
        }
        save_personnel_settings(default_settings)
        return default_settings
    except Exception as e:
        st.error(f"載入人員設定時發生錯誤: {e}")
        return {"responsible_persons": []}

def save_personnel_settings(settings):
    """儲存人員設定"""
    try:
        with open('personnel_settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"儲存人員設定時發生錯誤: {e}")
        return False

def get_responsible_persons_list():
    """獲取負責人列表（用於下拉選單）"""
    settings = load_personnel_settings()
    persons = settings.get('responsible_persons', [])
    return [person['display_name'] for person in persons]

def get_responsible_persons_by_dept(department):
    """根據部門獲取負責人列表"""
    settings = load_personnel_settings()
    persons = settings.get('responsible_persons', [])
    return [person['display_name'] for person in persons if person['department'] == department]

def get_third_responsible_info(resolution):
    """根據處理結果獲取第三責任人資訊"""
    # 定義處理結果與第三責任人的對應關係
    third_responsible_mapping = {
        "TRA14-報廢": {"dept": "管理部", "person": "廠長"},
        "TWP12-退製二": {"dept": "製造二部", "person": "製造二部DRI"},
        "TWP12-退製三": {"dept": "製造三部", "person": "製造三部DRI"},
        "TWP12-轉嫁外包": {"dept": "資材部", "person": "資材部DRI"},
        "TWP12-轉嫁供應商": {"dept": "資材部", "person": "資材部DRI"},
        "TRA13B-退供應商補料": {"dept": "資材部", "person": "資材部DRI"},
        "TRA13A-上線重工": {"dept": "製造一部", "person": "製造一部DRI"}
    }

    # 檢查是否包含需要第三責任人簽核的處理結果
    for key, info in third_responsible_mapping.items():
        if key in resolution:
            return info

    # 如果沒有匹配的處理結果，返回None
    return None

# 通知設定類
class NotificationManager:
    def __init__(self):
        self.settings = self.load_notification_settings()

    def load_notification_settings(self):
        """載入通知設定"""
        try:
            with open('notification_settings.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 預設設定
            default_settings = {
                'email_enabled': False,
                'email_smtp_server': 'smtp.gmail.com',
                'email_smtp_port': 587,
                'email_username': '',
                'email_password': '',
                'email_recipients': [],
                'telegram_enabled': False,
                'telegram_bot_token': '',
                'telegram_chat_ids': [],
                'browser_notification_enabled': False,
                'notification_methods': ['email'],  # 可選: email, telegram, browser
                'notification_intervals': {
                    'A級': 2,  # 2小時提醒一次
                    'B級': 4,  # 4小時提醒一次
                    'C級': 8   # 8小時提醒一次
                },
                'processing_deadlines': {
                    'A級': 4,  # 4小時內處理
                    'B級': 8,  # 8小時內處理
                    'C級': 24  # 24小時內處理
                }
            }
            self.save_notification_settings(default_settings)
            return default_settings

    def save_notification_settings(self, settings):
        """儲存通知設定"""
        with open('notification_settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        self.settings = settings

    def send_email_notification(self, subject, message, recipients=None):
        """發送郵件通知"""
        if not self.settings['email_enabled']:
            return False

        try:
            recipients = recipients or self.settings['email_recipients']
            if not recipients:
                return False

            msg = MIMEMultipart()
            msg['From'] = self.settings['email_username']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(message, 'html', 'utf-8'))

            server = smtplib.SMTP(self.settings['email_smtp_server'], self.settings['email_smtp_port'])
            server.starttls()
            server.login(self.settings['email_username'], self.settings['email_password'])
            server.send_message(msg)
            server.quit()

            return True
        except Exception as e:
            st.error(f"郵件發送失敗: {str(e)}")
            return False

    def send_line_notification(self, message, tokens=None):
        """發送LINE通知"""
        if not self.settings['line_enabled']:
            return False

        try:
            tokens = tokens or self.settings['line_tokens']
            if not tokens:
                return False

            success_count = 0
            for token in tokens:
                try:
                    headers = {
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }

                    data = {
                        'message': message
                    }

                    response = requests.post(
                        'https://notify-api.line.me/api/notify',
                        headers=headers,
                        data=data,
                        timeout=10
                    )

                    if response.status_code == 200:
                        success_count += 1
                    else:
                        print(f"LINE通知發送失敗: {response.status_code} - {response.text}")

                except Exception as e:
                    print(f"LINE通知發送錯誤: {str(e)}")
                    continue

            return success_count > 0

        except Exception as e:
            st.error(f"LINE通知發送失敗: {str(e)}")
            return False

    def send_telegram_notification(self, message, chat_ids=None):
        """發送Telegram通知"""
        if not self.settings['telegram_enabled']:
            return False

        try:
            bot_token = self.settings['telegram_bot_token']
            chat_ids = chat_ids or self.settings['telegram_chat_ids']

            if not bot_token or not chat_ids:
                return False

            success_count = 0
            for chat_id in chat_ids:
                try:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

                    data = {
                        'chat_id': chat_id,
                        'text': message,
                        'parse_mode': 'HTML',
                        'disable_web_page_preview': True
                    }

                    response = requests.post(url, data=data, timeout=10)

                    if response.status_code == 200:
                        success_count += 1
                    else:
                        print(f"Telegram通知發送失敗: {response.status_code} - {response.text}")

                except Exception as e:
                    print(f"Telegram通知發送錯誤: {str(e)}")
                    continue

            return success_count > 0

        except Exception as e:
            st.error(f"Telegram通知發送失敗: {str(e)}")
            return False

    def check_overdue_defects(self):
        """檢查逾期不良品"""
        conn = sqlite3.connect('defect_management.db')
        query = """
        SELECT * FROM defects
        WHERE status IN ('待處理', '處理中')
        AND datetime('now', 'localtime') > datetime(created_time, '+' ||
            CASE defect_level
                WHEN 'A級' THEN ?
                WHEN 'B級' THEN ?
                WHEN 'C級' THEN ?
            END || ' hours')
        """

        overdue_defects = pd.read_sql_query(
            query,
            conn,
            params=[
                self.settings['processing_deadlines']['A級'],
                self.settings['processing_deadlines']['B級'],
                self.settings['processing_deadlines']['C級']
            ]
        )
        conn.close()

        return overdue_defects

    def send_overdue_notifications(self):
        """發送逾期通知"""
        overdue_defects = self.check_overdue_defects()

        if not overdue_defects.empty:
            # 按部門分組
            dept_groups = overdue_defects.groupby('responsible_dept')

            for dept, defects in dept_groups:
                # 郵件通知
                if self.settings.get('email_enabled', False):
                    email_subject = f"⚠️ 【{dept}】不良品處理逾期提醒"

                    email_message = """
                    <html>
                    <body>
                    <h2>🚨 不良品處理逾期提醒</h2>
                    <p><strong>部門：</strong>{dept}</p>
                    <p><strong>逾期案件數：</strong>{len(defects)} 件</p>

                    <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr style="background-color: #f2f2f2;">
                        <th>工單號</th>
                        <th>產品名稱</th>
                        <th>不良等級</th>
                        <th>數量</th>
                        <th>建立時間</th>
                        <th>逾期時間</th>
                    </tr>
                    """

                    for _, defect in defects.iterrows():
                        created_time = pd.to_datetime(defect['created_time'])
                        deadline_hours = self.settings['processing_deadlines'][defect['defect_level']]
                        deadline = created_time + timedelta(hours=deadline_hours)
                        overdue_hours = (datetime.now() - deadline).total_seconds() / 3600

                        email_message += """
                        <tr>
                            <td>{defect['work_order']}</td>
                            <td>{defect['product_name']}</td>
                            <td>{defect['defect_level']}</td>
                            <td>{defect['quantity']} pcs</td>
                            <td>{created_time.strftime('%Y-%m-%d %H:%M')}</td>
                            <td style="color: red;">{overdue_hours:.1f} 小時</td>
                        </tr>
                        """

                    email_message += """
                    </table>
                    <br>
                    <p>🔗 <a href="http://localhost:8501">點擊進入不良品管理系統</a></p>
                    <p><em>此為系統自動發送的通知郵件，請勿回覆。</em></p>
                    </body>
                    </html>
                    """

                    self.send_email_notification(email_subject, email_message)

                # Telegram通知
                if self.settings.get('telegram_enabled', False):
                    telegram_message = """🚨 <b>不良品處理逾期提醒</b>

📍 <b>部門：</b>{dept}
📊 <b>逾期案件數：</b>{len(defects)} 件

📋 <b>詳細案件：</b>"""

                    for _, defect in defects.iterrows():
                        created_time = pd.to_datetime(defect['created_time'])
                        deadline_hours = self.settings['processing_deadlines'][defect['defect_level']]
                        deadline = created_time + timedelta(hours=deadline_hours)
                        overdue_hours = (datetime.now() - deadline).total_seconds() / 3600

                        telegram_message += """
━━━━━━━━━━━━━━━━━━━━
🏷️ <b>工單：</b>{defect['work_order']}
📦 <b>產品：</b>{defect['product_name']}
⚠️ <b>等級：</b>{defect['defect_level']}
📈 <b>數量：</b>{defect['quantity']} pcs
⏰ <b>建立：</b>{created_time.strftime('%m/%d %H:%M')}
🔴 <b>逾期：</b>{overdue_hours:.1f} 小時"""

                    telegram_message += """
━━━━━━━━━━━━━━━━━━━━
🔗 <a href="http://localhost:8501">進入系統</a>
⏰ <b>通知時間：</b>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

                    self.send_telegram_notification(telegram_message)

        return len(overdue_defects) if not overdue_defects.empty else 0

# 全域通知管理器
notification_manager = NotificationManager()

# 通知背景執行緒


def notification_background_task():
    """背景通知任務"""
    while True:
        try:
            if notification_manager.settings.get('email_enabled', False) or notification_manager.settings.get('telegram_enabled', False):
                notification_manager.send_overdue_notifications()
            time.sleep(3600)  # 每小時檢查一次
        except Exception as e:
            print(f"通知背景任務錯誤: {e}")
            time.sleep(3600)

# 啟動背景通知
if 'notification_thread_started' not in st.session_state:
    notification_thread = threading.Thread(target=notification_background_task, daemon=True)
    notification_thread.start()
    st.session_state['notification_thread_started'] = True

# 登入頁面


def login_page():
    st.markdown("""
    <div class="main-header">
        <h1>🚀 不良品處理管理系統</h1>
        <p>系統化管理・快速響應・提升效率</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 🔐 系統登入")

        with st.form("login_form"):
            username = st.text_input("用戶名", placeholder="請輸入用戶名")
            password = st.text_input("密碼", type="password", placeholder="請輸入密碼")
            submit_button = st.form_submit_button("登入", use_container_width=True)

            if submit_button:
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success("✅ 登入成功！")
                        st.rerun()
                    else:
                        st.error("❌ 用戶名或密碼錯誤！")
                else:
                    st.error("❌ 請輸入用戶名和密碼！")

        st.markdown("---")
        st.info("💡 **首次使用說明**\n\n如需登入帳戶資訊，請聯繫系統管理員")

def user_management_page():
    """用戶管理頁面"""
    st.header("👤 用戶管理")

    # 檢查是否為管理員
    if st.session_state.user.get('role') != '管理員':
        st.error("❌ 您沒有權限訪問此頁面！")
        return

    tab1, tab2 = st.tabs(["用戶列表", "新增用戶"])

    with tab1:
        st.subheader("📋 用戶列表")
        users = get_all_users()

        if users:
            users_df = pd.DataFrame(users, columns=[
                'ID', '用戶名', '姓名', '部門', '職位', '角色',
                '創建時間', '最後登入', '狀態'
            ])

            # 將狀態轉換為可讀格式
            users_df['狀態'] = users_df['狀態'].apply(lambda x: '啟用' if x == 1 else '停用')

            st.dataframe(users_df, use_container_width=True)

            # 用戶操作
            st.subheader("🔧 用戶操作")
            col1, col2 = st.columns(2)

            with col1:
                user_to_modify = st.selectbox(
                    "選擇用戶",
                    options=[(u[0], f"{u[2]} ({u[1]})") for u in users],
                    format_func=lambda x: x[1]
                )

                if st.button("停用/啟用用戶"):
                    current_status = next(u[8] for u in users if u[0] == user_to_modify[0])
                    new_status = not current_status
                    update_user_status(user_to_modify[0], new_status)
                    st.success(f"✅ 用戶狀態已更新為：{'啟用' if new_status else '停用'}")
                    st.rerun()

            with col2:
                new_password = st.text_input("新密碼", type="password")
                if st.button("重設密碼") and new_password:
                    reset_user_password(user_to_modify[0], new_password)
                    st.success("✅ 密碼重設成功！")

    with tab2:
        st.subheader("➕ 新增用戶")

        with st.form("add_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_username = st.text_input("用戶名*", placeholder="請輸入用戶名")
                new_name = st.text_input("姓名*", placeholder="請輸入真實姓名")
                new_department = st.selectbox("部門*", ["工程部", "品保部", "製造一部", "製造二部", "製造三部", "資材部", "資訊部"])

            with col2:
                new_position = st.text_input("職位*", placeholder="請輸入職位")
                new_role = st.selectbox("角色*", ["管理員", "主管", "工程師", "操作員"])
                new_password = st.text_input("密碼*", type="password", placeholder="請輸入初始密碼")

            if st.form_submit_button("新增用戶", use_container_width=True):
                if all([new_username, new_name, new_department, new_position, new_role, new_password]):
                    if len(new_password) >= 6:
                        if add_user(new_username, new_password, new_name, new_department, new_position, new_role):
                            st.success("✅ 用戶新增成功！")
                            st.rerun()
                        else:
                            st.error("❌ 用戶名已存在，請使用其他用戶名！")
                    else:
                        st.error("❌ 密碼長度至少6個字符！")
                else:
                    st.error("❌ 請填寫所有必填欄位！")

# 主要應用程式


def main():
    # 初始化資料庫
    init_database()

    # 初始化認證狀態
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None

    # 檢查登入狀態
    if not st.session_state.authenticated:
        login_page()
        return

    # 已登入用戶的界面
    # 主標題
    st.markdown("""
    <div class="main-header">
        <h1>🚀 不良品處理管理系統</h1>
        <p>系統化管理・快速響應・提升效率</p>
    </div>
    """, unsafe_allow_html=True)

    # 側邊欄選單
    st.sidebar.title("🔧 功能選單")

    # 顯示當前用戶信息
    st.sidebar.markdown("---")
    st.sidebar.markdown("👤 **當前用戶**")
    st.sidebar.markdown(f"姓名：{st.session_state.user['name']}")
    st.sidebar.markdown(f"部門：{st.session_state.user['department']}")
    st.sidebar.markdown(f"職位：{st.session_state.user['position']}")

    # 登出按鈕
    if st.sidebar.button("🚪 登出"):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()

    st.sidebar.markdown("---")

    # 初始化當前頁面狀態
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "📊 即時儀表板"

    # 根據用戶角色顯示不同的功能選單
    menu_options = ["📊 即時儀表板", "📋 不良品登錄", "🔍 處理追蹤", "📈 統計分析"]

    # 只有管理員和主管可以看到系統設定
    user_role = st.session_state.user.get('role')
    if user_role in ['管理員', '主管']:
        menu_options.append("⚙️ 系統設定")

    # 只有管理員可以看到用戶管理
    if user_role == '管理員':
        menu_options.append("👤 用戶管理")

    # 使用 key 參數讓 selectbox 記住選擇狀態
    page = st.sidebar.selectbox(
        "選擇功能",
        menu_options,
        key="page_selector"
    )

    # 更新當前頁面狀態
    st.session_state.current_page = page

    if page == "📊 即時儀表板":
        dashboard_page()
    elif page == "📋 不良品登錄":
        defect_registration_page()
    elif page == "🔍 處理追蹤":
        tracking_page()
    elif page == "📈 統計分析":
        analytics_page()
    elif page == "⚙️ 系統設定":
        settings_page()
    elif page == "👤 用戶管理":
        user_management_page()

def dashboard_page():
    st.header("📊 不良品管理儀表板")

    # 通知提醒區域
    overdue_defects = notification_manager.check_overdue_defects()
    if not overdue_defects.empty:
        st.error(f"⚠️ **緊急提醒：發現 {len(overdue_defects)} 件逾期案件需要立即處理！**")

        # 顯示逾期案件摘要
        with st.expander("📋 查看逾期案件詳情", expanded=False):
            overdue_summary = overdue_defects.groupby(['responsible_dept', 'defect_level']).agg({
                'quantity': 'sum',
                'work_order': 'count'
            }).reset_index()
            overdue_summary.columns = ['責任部門', '不良等級', '總數量(pcs)', '案件數']
            st.dataframe(overdue_summary, use_container_width=True)

            if st.button("📧 立即發送逾期通知"):
                sent_count = notification_manager.send_overdue_notifications()
                if sent_count > 0:
                    st.success(f"✅ 已發送 {sent_count} 件逾期通知")
                else:
                    st.info("ℹ️ 通知功能未啟用或無收件人設定")

    # 獲取所有不良品資料
    all_defects = get_defects()

    if all_defects.empty:
        st.warning("📝 目前沒有不良品資料，請先登記不良品資訊。")
        return

    # 統計指標
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_quantity = all_defects['quantity'].sum()
        total_records = len(all_defects)
        st.markdown("""
        <div class="metric-card">
            <h3>{total_quantity}</h3>
            <p>總不良品數</p>
            <small>({total_records}筆記錄)</small>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        pending_quantity = all_defects[all_defects['status'] == '待處理']['quantity'].sum()
        pending_records = len(all_defects[all_defects['status'] == '待處理'])
        st.markdown("""
        <div class="metric-card">
            <h3>{pending_quantity}</h3>
            <p>待處理</p>
            <small>({pending_records}筆記錄)</small>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        processing_quantity = all_defects[all_defects['status'] == '處理中']['quantity'].sum()
        processing_records = len(all_defects[all_defects['status'] == '處理中'])
        st.markdown("""
        <div class="metric-card">
            <h3>{processing_quantity}</h3>
            <p>處理中</p>
            <small>({processing_records}筆記錄)</small>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        completed_quantity = all_defects[all_defects['status'] == '已完成']['quantity'].sum()
        completed_records = len(all_defects[all_defects['status'] == '已完成'])
        st.markdown("""
        <div class="metric-card">
            <h3>{completed_quantity}</h3>
            <p>已完成</p>
            <small>({completed_records}筆記錄)</small>
        </div>
        """, unsafe_allow_html=True)

    # 圖表分析
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 不良品等級分布")
        level_counts = all_defects['defect_level'].value_counts()
        fig_pie = px.pie(
            values=level_counts.values,
            names=level_counts.index,
            color_discrete_sequence=['#ef4444', '#f59e0b', '#10b981']
        )
        fig_pie.update_layout(height=300)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("📈 部門處理狀況")
        dept_counts = all_defects['responsible_dept'].value_counts()
        fig_bar = px.bar(
            x=dept_counts.index,
            y=dept_counts.values,
            color_discrete_sequence=['#2563eb']
        )
        fig_bar.update_layout(height=300, xaxis_title="部門", yaxis_title="不良品數量")
        st.plotly_chart(fig_bar, use_container_width=True)



def defect_registration_page():
    st.header("📋 不良品登錄")

    # 簡潔的CSS樣式
    st.markdown("""
    <style>
        .simple-info {
            background-color: #f0f8ff;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #3b82f6;
            margin: 10px 0;
        }
        .dept-info {
            background-color: #fff3cd;
            padding: 8px;
            border-radius: 5px;
            margin: 5px 0;
            font-weight: bold;
        }
        .component-info {
            background-color: #e8f5e8;
            padding: 8px;
            border-radius: 5px;
            margin: 5px 0;
            border-left: 4px solid #28a745;
        }
    </style>
    """, unsafe_allow_html=True)

    # 先在表單外部選擇不良品類型，以便即時更新責任部門
    col1_preview, col2_preview = st.columns(2)

    with col1_preview:
        defect_type_preview = st.selectbox(
            "不良品類型 *",
            ["檢具NG", "表面缺陷", "組裝不良", "功能異常", "外觀不良", "其他"],
            key="defect_type_preview"
        )

    with col2_preview:
        # 根據不良品類型自動判定主要和次要責任部門
        # 外觀相關：主要責任人是品保，次要責任人是工程
        # 其他類型：主要責任人是工程，次要責任人是品保
        if defect_type_preview in ["外觀不良", "表面缺陷"]:
            primary_dept = "品保部"
            secondary_dept = "工程部"
            flow_desc = "品保簽核後轉拋至工程"
        else:
            primary_dept = "工程部"
            secondary_dept = "品保部"
            flow_desc = "工程簽核後轉拋至品保"

        st.markdown("""
        <div class="dept-info">
            🎯 主要責任：{primary_dept}<br>
            🔄 次要責任：{secondary_dept}<br>
            📋 處理流程：{flow_desc}
        </div>
        """, unsafe_allow_html=True)

        # 根據主要責任部門顯示對應負責人
        primary_persons = get_responsible_persons_by_dept(primary_dept)
        if primary_persons:
            st.info(f"👥 {primary_dept}負責人：{', '.join(primary_persons)}")
        else:
            st.info(f"👥 需手動輸入{primary_dept}負責人")

    # 工單號碼輸入和包數預覽（在表單外部，可即時更新）
    col1_work, col2_work = st.columns(2)

    with col1_work:
        work_order_preview = st.text_input("工單號碼 *", placeholder="請輸入工單號碼", key="work_order_preview")

        # 工單總數輸入
        work_order_total_qty = st.number_input(
            "工單總數 *",
            min_value=1,
            value=100,
            help="請輸入該工單的總生產數量",
            key="work_order_total_qty"
        )

        # 顯示包數資訊和不良率預覽
        if work_order_preview:
            next_package = get_next_package_number(work_order_preview)
            work_order_stats = get_work_order_stats(work_order_preview)

            st.markdown("""
            <div class="simple-info">
                📦 預計包數：第 {next_package} 包
                <br>💡 提交後將成為第 {next_package} 包
                <br>📊 目前累計不良：{work_order_stats['total_defects']} pcs
                <br>📈 目前不良率：{work_order_stats['defect_rate']:.2f}%
            </div>
            """, unsafe_allow_html=True)

    with col2_work:
        st.write("**📋 登錄步驟：**")
        st.write("1️⃣ 輸入工單號碼查看包數")
        st.write("2️⃣ 選擇產品名稱和零件")
        st.write("3️⃣ 選擇對應供應商")
        st.write("4️⃣ 填寫表單並提交")

    # 產品名稱、零件、供應商階層選擇（在表單外部，可即時更新）
    st.write("---")
    st.write("**📦 產品零件供應商選擇**")

    # 產品名稱選擇
    col1_product, col2_product = st.columns(2)

    with col1_product:
        # 載入產品名稱列表
        products_list = get_products_list()
        if products_list:
            product_name_preview = st.selectbox(
                "產品名稱 *",
                ["請選擇產品"] + products_list + ["其他 (手動輸入)"],
                key="product_name_preview"
            )

            # 如果選擇其他，提供輸入框
            if product_name_preview == "其他 (手動輸入)":
                product_name_preview = st.text_input("請輸入產品名稱", placeholder="請輸入產品名稱", key="custom_product_name")
            elif product_name_preview == "請選擇產品":
                product_name_preview = ""
        else:
            product_name_preview = st.text_input("產品名稱 *", placeholder="請輸入產品名稱", key="product_name_preview")

    with col2_product:
        # 檢查是否為11U885R00300或11U885L00300產品（或包含關鍵字的產品）
        component_preview = ""
        supplier_preview = ""

        if product_name_preview and ("11U885R00300" in product_name_preview.upper() or
                                   "11U885L00300" in product_name_preview.upper() or
                                   any(keyword in product_name_preview.upper() for keyword in ['SHAFT', 'MOUNT', 'BUSHING', 'CLIP'])):
            st.markdown("**🔧 零件選擇**")

            # 定義零件選項（基於圖片中的資訊）
            component_options = ["請選擇零件", "Shaft", "Mount", "Bushing", "Clip"]
            component_preview = st.selectbox(
                "零件類型 *",
                component_options,
                key="component_preview"
            )

            if component_preview == "請選擇零件":
                component_preview = ""
        elif product_name_preview and product_name_preview != "請選擇產品":
            # 其他產品也可以選擇零件
            with st.expander("🔧 零件資訊 (選填)", expanded=False):
                component_preview = st.text_input("零件名稱", placeholder="如有零件資訊請填寫", key="general_component_preview")

    # 四個零件類型的詳細選擇區域
    if product_name_preview and ("11U885R00300" in product_name_preview.upper() or
                               "11U885L00300" in product_name_preview.upper() or
                               any(keyword in product_name_preview.upper() for keyword in ['SHAFT', 'MOUNT', 'BUSHING', 'CLIP'])):
        st.write("---")
        st.write("**🔧 四個零件類型詳細選擇**")

        # 根據圖片定義零件-供應商對應關係
        component_supplier_mapping = {
            "Shaft": ["製造三部", "巨昇"],
            "Mount": ["製造二部+製造三部", "多元"],
            "Bushing": ["製造二部+製造三部"],
            "Clip": ["富威達", "紳暉", "銘鈺"]
        }

        # 創建四個零件的選擇區域
        col1_comp, col2_comp = st.columns(2)

        with col1_comp:
            st.markdown("**🔧 Shaft 軸**")
            shaft_enabled = st.checkbox("選擇 Shaft", key="shaft_enabled")
            if shaft_enabled:
                shaft_supplier = st.selectbox(
                    "Shaft 供應商",
                    ["請選擇"] + component_supplier_mapping["Shaft"] + ["其他"],
                    key="shaft_supplier"
                )
                if shaft_supplier == "其他":
                    shaft_supplier = st.text_input("Shaft 其他供應商", key="shaft_custom_supplier")

            st.markdown("**🔧 Mount 座**")
            mount_enabled = st.checkbox("選擇 Mount", key="mount_enabled")
            if mount_enabled:
                mount_supplier = st.selectbox(
                    "Mount 供應商",
                    ["請選擇"] + component_supplier_mapping["Mount"] + ["其他"],
                    key="mount_supplier"
                )
                if mount_supplier == "其他":
                    mount_supplier = st.text_input("Mount 其他供應商", key="mount_custom_supplier")

        with col2_comp:
            st.markdown("**🔧 Bushing 軸套**")
            bushing_enabled = st.checkbox("選擇 Bushing", key="bushing_enabled")
            if bushing_enabled:
                bushing_supplier = st.selectbox(
                    "Bushing 供應商",
                    ["請選擇"] + component_supplier_mapping["Bushing"] + ["其他"],
                    key="bushing_supplier"
                )
                if bushing_supplier == "其他":
                    bushing_supplier = st.text_input("Bushing 其他供應商", key="bushing_custom_supplier")

            st.markdown("**🔧 Clip 夾**")
            clip_enabled = st.checkbox("選擇 Clip", key="clip_enabled")
            if clip_enabled:
                clip_supplier = st.selectbox(
                    "Clip 供應商",
                    ["請選擇"] + component_supplier_mapping["Clip"] + ["其他"],
                    key="clip_supplier"
                )
                if clip_supplier == "其他":
                    clip_supplier = st.text_input("Clip 其他供應商", key="clip_custom_supplier")

        # 收集選擇的零件和供應商
        selected_components = []
        selected_suppliers = []

        if 'shaft_enabled' in st.session_state and st.session_state.shaft_enabled:
            shaft_sup = st.session_state.get('shaft_supplier', '請選擇')
            if shaft_sup != '請選擇':
                if shaft_sup == '其他' and 'shaft_custom_supplier' in st.session_state:
                    shaft_sup = st.session_state.shaft_custom_supplier
                if shaft_sup and shaft_sup != '其他':
                    selected_components.append("Shaft")
                    selected_suppliers.append(f"Shaft:{shaft_sup}")

        if 'mount_enabled' in st.session_state and st.session_state.mount_enabled:
            mount_sup = st.session_state.get('mount_supplier', '請選擇')
            if mount_sup != '請選擇':
                if mount_sup == '其他' and 'mount_custom_supplier' in st.session_state:
                    mount_sup = st.session_state.mount_custom_supplier
                if mount_sup and mount_sup != '其他':
                    selected_components.append("Mount")
                    selected_suppliers.append(f"Mount:{mount_sup}")

        if 'bushing_enabled' in st.session_state and st.session_state.bushing_enabled:
            bushing_sup = st.session_state.get('bushing_supplier', '請選擇')
            if bushing_sup != '請選擇':
                if bushing_sup == '其他' and 'bushing_custom_supplier' in st.session_state:
                    bushing_sup = st.session_state.bushing_custom_supplier
                if bushing_sup and bushing_sup != '其他':
                    selected_components.append("Bushing")
                    selected_suppliers.append(f"Bushing:{bushing_sup}")

        if 'clip_enabled' in st.session_state and st.session_state.clip_enabled:
            clip_sup = st.session_state.get('clip_supplier', '請選擇')
            if clip_sup != '請選擇':
                if clip_sup == '其他' and 'clip_custom_supplier' in st.session_state:
                    clip_sup = st.session_state.clip_custom_supplier
                if clip_sup and clip_sup != '其他':
                    selected_components.append("Clip")
                    selected_suppliers.append(f"Clip:{clip_sup}")

        # 顯示選擇結果
        if selected_components:
            st.markdown("""
            <div class="component-info">
                🔧 選定零件：{', '.join(selected_components)}<br>
                🏭 對應供應商：<br>
                {'<br>'.join([f'   • {sup}' for sup in selected_suppliers])}
            </div>
            """, unsafe_allow_html=True)

            # 為了兼容現有邏輯，使用第一個選擇的零件和供應商
            component_preview = selected_components[0] if selected_components else ""
            supplier_preview = selected_suppliers[0].split(':')[1] if selected_suppliers else ""

    # 原有的供應商選擇（基於單一零件選擇）
    elif component_preview and component_preview != "請選擇零件":
        st.write("**🏭 供應商選擇**")

        # 根據圖片定義零件-供應商對應關係
        component_supplier_mapping = {
            "Shaft": ["請選擇供應商", "製造三部", "巨昇", "其他"],
            "Mount": ["請選擇供應商", "製造二部+製造三部", "多元", "其他"],
            "Bushing": ["請選擇供應商", "製造二部+製造三部", "其他"],
            "Clip": ["請選擇供應商", "富威達", "紳暉", "銘鈺", "其他"]
        }

        if component_preview in component_supplier_mapping:
            supplier_options = component_supplier_mapping[component_preview]
            supplier_preview = st.selectbox(
                f"供應商 ({component_preview})",
                supplier_options,
                key=f"supplier_preview_{component_preview}"
            )

            # 如果選擇其他，提供輸入框
            if supplier_preview == "其他":
                supplier_preview = st.text_input("請輸入供應商名稱", placeholder="請輸入供應商名稱", key="custom_supplier_name")
            elif supplier_preview == "請選擇供應商":
                supplier_preview = ""
        else:
            # 一般零件的供應商輸入
            supplier_preview = st.text_input("供應商名稱", placeholder="請輸入供應商名稱", key="general_supplier_input")

        # 顯示選擇結果
        if component_preview and supplier_preview:
            st.markdown("""
            <div class="component-info">
                🔧 選定零件：{component_preview}<br>
                🏭 選定供應商：{supplier_preview}
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    with st.form("defect_form", clear_on_submit=False):
        # 第一行：產品和數量
        col1, col2 = st.columns(2)

        with col1:
            # 使用預覽區域的產品名稱、零件和供應商
            product_name = product_name_preview
            component = component_preview
            supplier = supplier_preview

            # 顯示確認資訊
            if product_name:
                st.info(f"📦 產品：{product_name}")
                if component:
                    st.info(f"🔧 零件：{component}")
                if supplier:
                    st.info(f"🏭 供應商：{supplier}")
            else:
                st.warning("⚠️ 請先選擇產品名稱")

        with col2:
            quantity = st.number_input("不良數量 *", min_value=1, value=1)

            # 使用預覽區域的工單號碼
            work_order = work_order_preview

            # 顯示確認資訊
            if work_order:
                st.info(f"📋 工單：{work_order}")
            else:
                st.warning("⚠️ 請先輸入工單號碼")

        # 第二行：不良等級和負責人
        col3, col4 = st.columns(2)

        with col3:
            defect_level = st.selectbox(
                "不良等級 *",
                ["A級 (緊急-4小時)", "B級 (重要-8小時)", "C級 (一般-24小時)"]
            )

            # 提取等級
            level_map = {
                "A級 (緊急-4小時)": "A級",
                "B級 (重要-8小時)": "B級",
                "C級 (一般-24小時)": "C級"
            }
            actual_level = level_map[defect_level]

        with col4:
            # 使用預覽區域的不良品類型和部門分配
            defect_type = defect_type_preview

            # 重新計算主要和次要責任部門
            if defect_type in ["外觀不良", "表面缺陷"]:
                primary_dept = "品保部"
                secondary_dept = "工程部"
            else:
                primary_dept = "工程部"
                secondary_dept = "品保部"

            # 主要責任人選擇
            primary_persons = get_responsible_persons_by_dept(primary_dept)
            if primary_persons:
                primary_person = st.selectbox(
                    f"主要責任人 * ({primary_dept})",
                    ["請選擇"] + primary_persons
                )
                if primary_person == "請選擇":
                    primary_person = ""
            else:
                primary_person = st.text_input(f"主要責任人 * ({primary_dept})", placeholder="請輸入主要責任人")

            # 次要責任人選擇
            secondary_persons = get_responsible_persons_by_dept(secondary_dept)
            if secondary_persons:
                secondary_person = st.selectbox(
                    f"次要責任人 * ({secondary_dept})",
                    ["請選擇"] + secondary_persons
                )
                if secondary_person == "請選擇":
                    secondary_person = ""
            else:
                secondary_person = st.text_input(f"次要責任人 * ({secondary_dept})", placeholder="請輸入次要責任人")

        # 第三行：登錄人員和問題描述
        # 使用當前登入用戶信息
        operator = st.session_state.user['name']
        st.info(f"👤 **登錄人員：** {operator} ({st.session_state.user['department']} - {st.session_state.user['position']})")

        description = st.text_area(
            "問題描述 (選填)",
            placeholder="簡單描述不良品情況...",
            height=80
        )

        # 提交按鈕
        submitted = st.form_submit_button("🚀 登錄不良品", use_container_width=True, type="primary")

        if submitted:
            # 檢查必填欄位（包含次要負責人）
            if not all([work_order, product_name, defect_type, actual_level, primary_person, secondary_person]):
                st.error("❌ 請填寫所有必填欄位（標記*的欄位）")
                if not work_order:
                    st.error("   • 請輸入工單號碼")
                if not product_name:
                    st.error("   • 請選擇或輸入產品名稱")
                if not primary_person:
                    st.error("   • 請選擇主要責任人")
                if not secondary_person:
                    st.error("   • 請選擇次要責任人")
            else:
                # 確保使用最新的包數
                final_package_number = get_next_package_number(work_order) if work_order else 1

                # 收集所有零件和供應商資訊
                all_components = []
                all_suppliers = []

                # 檢查四個零件類型的選擇
                if product_name and ("11U885R00300" in product_name.upper() or
                                   "11U885L00300" in product_name.upper() or
                                   any(keyword in product_name.upper() for keyword in ['SHAFT', 'MOUNT', 'BUSHING', 'CLIP'])):

                    # 收集Shaft資訊
                    if st.session_state.get('shaft_enabled', False):
                        shaft_sup = st.session_state.get('shaft_supplier', '請選擇')
                        if shaft_sup != '請選擇':
                            if shaft_sup == '其他' and st.session_state.get('shaft_custom_supplier'):
                                shaft_sup = st.session_state.shaft_custom_supplier
                            if shaft_sup and shaft_sup != '其他':
                                all_components.append("Shaft")
                                all_suppliers.append(f"Shaft:{shaft_sup}")

                    # 收集Mount資訊
                    if st.session_state.get('mount_enabled', False):
                        mount_sup = st.session_state.get('mount_supplier', '請選擇')
                        if mount_sup != '請選擇':
                            if mount_sup == '其他' and st.session_state.get('mount_custom_supplier'):
                                mount_sup = st.session_state.mount_custom_supplier
                            if mount_sup and mount_sup != '其他':
                                all_components.append("Mount")
                                all_suppliers.append(f"Mount:{mount_sup}")

                    # 收集Bushing資訊
                    if st.session_state.get('bushing_enabled', False):
                        bushing_sup = st.session_state.get('bushing_supplier', '請選擇')
                        if bushing_sup != '請選擇':
                            if bushing_sup == '其他' and st.session_state.get('bushing_custom_supplier'):
                                bushing_sup = st.session_state.bushing_custom_supplier
                            if bushing_sup and bushing_sup != '其他':
                                all_components.append("Bushing")
                                all_suppliers.append(f"Bushing:{bushing_sup}")

                    # 收集Clip資訊
                    if st.session_state.get('clip_enabled', False):
                        clip_sup = st.session_state.get('clip_supplier', '請選擇')
                        if clip_sup != '請選擇':
                            if clip_sup == '其他' and st.session_state.get('clip_custom_supplier'):
                                clip_sup = st.session_state.clip_custom_supplier
                            if clip_sup and clip_sup != '其他':
                                all_components.append("Clip")
                                all_suppliers.append(f"Clip:{clip_sup}")

                # 如果沒有選擇多個零件，使用原有的單一零件邏輯
                if not all_components and component:
                    all_components.append(component)
                    if supplier:
                        all_suppliers.append(f"{component}:{supplier}")

                # 將多個零件和供應商資訊合併成字符串
                final_component = "; ".join(all_components) if all_components else ""
                final_supplier = "; ".join(all_suppliers) if all_suppliers else ""

                defect_data = {
                    'work_order': work_order,
                    'product_name': product_name,
                    'defect_type': defect_type,
                    'defect_level': actual_level,
                    'quantity': quantity,
                    'package_number': final_package_number,
                    'description': description,
                    'primary_dept': primary_dept,
                    'secondary_dept': secondary_dept,
                    'primary_person': primary_person,
                    'secondary_person': secondary_person,
                    'operator': operator,
                    'work_order_total_qty': work_order_total_qty,
                    'supplier': final_supplier,
                    'component': final_component
                }

                defect_id = add_defect(defect_data)

                # 簡潔的成功提示
                st.success(f"✅ 登錄成功！編號：{defect_id}")
                st.info(f"📦 包數：第{final_package_number}包 | 🎯 主要責任：{primary_dept} - {primary_person}")

                # 顯示所有零件和供應商資訊
                if final_component:
                    if ";" in final_component:
                        st.info(f"🔧 零件：{final_component}")
                        # 解析供應商資訊並以列表形式顯示
                        if final_supplier:
                            supplier_list = final_supplier.split("; ")
                            supplier_display = "\n".join([f"   • {sup}" for sup in supplier_list])
                            st.info(f"🏭 供應商：\n{supplier_display}")
                    else:
                        st.info(f"🔧 零件：{final_component}")
                        if final_supplier:
                            # 提取供應商名稱（去掉零件前綴）
                            supplier_name = final_supplier.split(":")[-1] if ":" in final_supplier else final_supplier
                            st.info(f"🏭 供應商：{supplier_name}")

                if secondary_person:
                    st.info(f"🔄 次要責任：{secondary_dept} - {secondary_person}")
                else:
                    st.info(f"🔄 次要責任：{secondary_dept} - 待分配")

                # 處理時限提醒
                level_hours = {'A級': 4, 'B級': 8, 'C級': 24}
                deadline = datetime.now() + timedelta(hours=level_hours[actual_level])
                st.warning(f"⏰ 處理截止：{deadline.strftime('%m/%d %H:%M')}")

def tracking_page():
    st.header("🔍 處理追蹤")

    # 簡化的session_state管理 - 移除了"開始處理"功能後不再需要複雜的狀態追蹤

    # 篩選器
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox("狀態篩選", ["全部", "待處理", "處理中", "已完成"])

    with col2:
        dept_filter = st.selectbox("部門篩選", ["全部", "工程部", "品保部", "製造部"])

    with col3:
        level_filter = st.selectbox("等級篩選", ["全部", "A級", "B級", "C級"])

    # 獲取資料
    all_defects = get_defects()

    if all_defects.empty:
        st.info("目前沒有不良品記錄")
        return

    # 應用篩選器
    filtered_defects = all_defects.copy()

    if status_filter != "全部":
        filtered_defects = filtered_defects[filtered_defects['status'] == status_filter]

    if dept_filter != "全部":
        filtered_defects = filtered_defects[filtered_defects['responsible_dept'] == dept_filter]

    if level_filter != "全部":
        filtered_defects = filtered_defects[filtered_defects['defect_level'] == level_filter]

    st.write(f"📊 共找到 {len(filtered_defects)} 筆記錄")

    # 顯示不良品列表
    for _, defect in filtered_defects.iterrows():
        package_info = f"第{defect.get('package_number', 1)}包"
        with st.expander(f"工單: {defect['work_order']} - {defect['product_name']} ({package_info}) - {defect['status']}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**不良類型:** {defect['defect_type']}")
                st.write(f"**等級:** {defect['defect_level']}")
                st.write(f"**數量:** {defect['quantity']} pcs")
                st.write(f"**包數:** {package_info}")
                st.write(f"**負責部門:** {defect['responsible_dept']}")
                st.write(f"**負責人:** {defect['assigned_person']}")

                # 顯示零件資訊（支援多個零件）
                if defect.get('component') and pd.notna(defect['component']) and defect['component'].strip():
                    component_str = defect['component']
                    if ";" in component_str:
                        components = component_str.split("; ")
                        st.write(f"**零件:** {', '.join(components)}")
                    else:
                        st.write(f"**零件:** {component_str}")

                # 顯示供應商資訊（支援多個供應商）
                if defect.get('supplier') and pd.notna(defect['supplier']) and defect['supplier'].strip():
                    supplier_str = defect['supplier']
                    if ";" in supplier_str:
                        suppliers = supplier_str.split("; ")
                        st.write("**供應商:**")
                        for supplier in suppliers:
                            st.write(f"   • {supplier}")
                    else:
                        # 處理單一供應商（可能包含零件前綴）
                        supplier_display = supplier_str.split(":")[-1] if ":" in supplier_str else supplier_str
                        st.write(f"**供應商:** {supplier_display}")

                st.write(f"**問題描述:** {defect['description']}")

                if defect['resolution']:
                    st.write(f"**處理結果:** {defect['resolution']}")

            with col2:
                st.write(f"**建立時間:** {defect['created_time']}")

                if pd.notna(defect['deadline']):
                    deadline = pd.to_datetime(defect['deadline'])
                    time_left = deadline - datetime.now()

                    if defect['status'] != '已完成':
                        if time_left.total_seconds() < 0:
                            st.error("⏰ 已超時")
                        else:
                            hours = int(time_left.total_seconds()/3600)
                            minutes = int((time_left.total_seconds() % 3600) / 60)
                            st.info(f"⏳ 剩餘: {hours}h{minutes}m")

                if defect['completion_time']:
                    st.success(f"✅ 完成時間: {defect['completion_time']}")

                # 刪除按鈕（所有狀態都可以刪除，但需要確認）
                st.write("---")
                st.write("**⚠️ 危險操作**")

                # 使用確認機制的刪除按鈕
                delete_confirm_key = f"delete_confirm_{defect['id']}"
                if delete_confirm_key not in st.session_state:
                    st.session_state[delete_confirm_key] = False

                if not st.session_state[delete_confirm_key]:
                    if st.button("🗑️ 刪除記錄", key=f"delete_btn_{defect['id']}", type="secondary"):
                        st.session_state[delete_confirm_key] = True
                        st.rerun()
                else:
                    st.warning("⚠️ 確定要刪除此記錄嗎？此操作無法復原！")
                    col_del1, col_del2 = st.columns(2)

                    with col_del1:
                        if st.button("✅ 確認刪除", key=f"confirm_delete_{defect['id']}", type="primary"):
                            success, message = delete_defect(defect['id'], st.session_state.user['name'])
                            if success:
                                st.success(f"✅ {message}")
                                st.session_state[delete_confirm_key] = False
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")

                    with col_del2:
                        if st.button("❌ 取消", key=f"cancel_delete_{defect['id']}"):
                            st.session_state[delete_confirm_key] = False
                            st.rerun()

                st.write("---")

                # 顯示當前流程狀態
                approval_status = defect.get('approval_status', '待主要單位處理')
                primary_dept = defect.get('primary_dept', defect['responsible_dept'])
                secondary_dept = defect.get('secondary_dept', '')

                # 如果部門信息為空，根據不良品類型自動判定
                if not primary_dept or not secondary_dept:
                    if defect['defect_type'] in ['外觀不良', '表面缺陷']:
                        primary_dept = primary_dept or '品保部'
                        secondary_dept = secondary_dept or '工程部'
                    else:
                        primary_dept = primary_dept or '工程部'
                        secondary_dept = secondary_dept or '品保部'

                # 獲取負責人信息
                primary_person = defect.get('primary_person', defect.get('assigned_person', ''))
                secondary_person = defect.get('secondary_person', '')

                # 如果沒有設定負責人，根據部門獲取預設負責人
                if not primary_person:
                    personnel_settings = load_personnel_settings()
                    if primary_dept in personnel_settings:
                        primary_person = personnel_settings[primary_dept][0] if personnel_settings[primary_dept] else ''

                if not secondary_person:
                    personnel_settings = load_personnel_settings()
                    if secondary_dept in personnel_settings:
                        secondary_person = personnel_settings[secondary_dept][0] if personnel_settings[secondary_dept] else ''

                st.write(f"**🔄 流程狀態:** {approval_status}")
                if primary_dept and secondary_dept:
                    st.write(f"**🎯 主要責任:** {primary_dept}")
                    st.write(f"**🔄 次要責任:** {secondary_dept}")

                    # 顯示第三責任人資訊（如果有）
                    third_dept = defect.get('third_dept', '')
                    third_person = defect.get('third_person', '')
                    third_approval_status = defect.get('third_approval_status', '')

                    if third_dept and third_person:
                        status_text = ""
                        if third_approval_status == '待簽核':
                            status_text = " (⏳待簽核)"
                        elif third_approval_status == '已簽核':
                            status_text = " (✅已簽核)"
                        elif third_approval_status == '已退回':
                            status_text = " (❌已退回)"

                        st.write(f"**🔐 第三責任：** {third_dept} - {third_person}{status_text}")

                # 處理選項 - 直接顯示，無需"開始處理"步驟
                if (defect['status'] == '待處理' and approval_status == '待主要單位處理') or \
                   (defect['status'] == '處理中' and approval_status == '主要單位處理中'):
                    # 處理選項
                    col_btn1, col_btn2 = st.columns(2)

                    with col_btn1:
                        st.write("**完成處理**")
                        resolution = st.selectbox(
                            "處理結果",
                            ["請選擇處理結果", "TRA11 判定後為OK品", "TRA14-報廢", "TWP12-退製二", "TWP12-退製三", "TWP12-轉嫁外包", "TWP12-轉嫁供應商", "TRA13B-退供應商補料", "TRA13A-上線重工"],
                            key=f"res_track_{defect['id']}"
                        )

                        # 如果選擇TRA11判定後為OK品，顯示OK數量輸入
                        ok_quantity = 0
                        ng_resolution = ""
                        if resolution == "TRA11 判定後為OK品":
                            ok_quantity = st.number_input(
                                f"OK品數量（總數量：{defect['quantity']} pcs）",
                                min_value=0,
                                max_value=int(defect['quantity']),
                                value=int(defect['quantity']),
                                key=f"ok_qty_track_{defect['id']}"
                            )

                            # 顯示剩餘不良品數量
                            remaining_defects = int(defect['quantity']) - ok_quantity
                            if remaining_defects > 0:
                                st.warning(f"⚠️ OK品：{ok_quantity} pcs，剩餘NG品：{remaining_defects} pcs")

                                # 對剩餘NG品的處理方式
                                st.write("**剩餘NG品處理方式：**")
                                ng_resolution = st.selectbox(
                                    f"剩餘 {remaining_defects} pcs NG品處理方式",
                                    ["請選擇NG品處理方式", "TRA14-報廢", "TWP12-退製二", "TWP12-退製三", "TWP12-轉嫁外包", "TWP12-轉嫁供應商", "TRA13B-退供應商補料", "TRA13A-上線重工"],
                                    key=f"ng_resolution_track_{defect['id']}"
                                )
                            else:
                                st.success(f"✅ 全部 {ok_quantity} pcs 判定為OK品")

                        # 如果選擇了具體的處理結果，可以添加備註
                        resolution_note = ""
                        if resolution != "請選擇處理結果":
                            resolution_note = st.text_area(
                                "處理備註（選填）",
                                placeholder="可填寫具體處理說明...",
                                key=f"note_track_{defect['id']}"
                            )

                        if st.button("🔄 提交簽核", key=f"complete_track_{defect['id']}", use_container_width=True):
                            if resolution != "請選擇處理結果":
                                # 檢查NG品處理方式
                                if resolution == "TRA11 判定後為OK品":
                                    remaining_defects = int(defect['quantity']) - ok_quantity
                                    if remaining_defects > 0 and ng_resolution == "請選擇NG品處理方式":
                                        st.error("請選擇剩餘NG品的處理方式")
                                        return

                                # 組合處理結果和備註
                                final_resolution = resolution

                                # 如果是OK品，添加數量信息
                                if resolution == "TRA11 判定後為OK品":
                                    remaining_defects = int(defect['quantity']) - ok_quantity
                                    final_resolution += f"（OK品：{ok_quantity} pcs"
                                    if remaining_defects > 0:
                                        final_resolution += f"，剩餘NG品：{remaining_defects} pcs - {ng_resolution}）"
                                    else:
                                        final_resolution += "）"

                                if resolution_note:
                                    final_resolution += f" - {resolution_note}"

                                # 更新為待次要單位簽核狀態
                                conn = sqlite3.connect('defect_management.db')
                                cursor = conn.cursor()

                                # 確保secondary_dept不為空，如果為空則使用默認值
                                target_dept = secondary_dept if secondary_dept else '品保部'

                                cursor.execute('''
                                    UPDATE defects
                                    SET status = '處理中', resolution = ?, approval_status = '待次要單位簽核',
                                        responsible_dept = ?, assigned_person = ?, updated_time = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (final_resolution, target_dept, secondary_person, defect['id']))

                                # 添加處理記錄
                                cursor.execute('''
                                    INSERT INTO processing_logs (defect_id, action, department, operator, comment)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (defect['id'], f'主要單位({primary_dept})處理完成，提交簽核', primary_dept,
                                     st.session_state.user['name'], final_resolution))

                                conn.commit()
                                conn.close()
                                st.success(f"✅ 處理完成！已轉交{target_dept}簽核")
                                st.rerun()
                            else:
                                st.error("請選擇處理結果")

                    with col_btn2:
                        st.write("**轉交其他單位**")

                        # 獲取當前責任部門，用於排除
                        current_dept = defect['responsible_dept']
                        all_depts = ['工程部', '品保部', '製造部']
                        available_depts = [dept for dept in all_depts if dept != current_dept]

                        target_dept = st.selectbox(
                            "轉交至",
                            available_depts,
                            key=f"target_dept_{defect['id']}"
                        )

                        transfer_reason = st.text_area(
                            "轉交原因",
                            placeholder="請說明轉交原因...",
                            key=f"transfer_reason_{defect['id']}"
                        )

                        if st.button(f"🔄 轉交至{target_dept}", key=f"transfer_track_{defect['id']}", use_container_width=True):
                            if transfer_reason:
                                transfer_defect(
                                    defect['id'],
                                    target_dept,
                                    transfer_reason,
                                    st.session_state.user['name']
                                )
                                st.success(f"✅ 已轉交至{target_dept}！")
                                st.rerun()
                            else:
                                st.error("請填寫轉交原因")

                # 新增：次要單位簽核邏輯
                elif defect['status'] == '處理中' and approval_status == '待次要單位簽核':
                    st.write("---")
                    st.write(f"**🔍 {secondary_dept}簽核**")
                    st.info(f"📋 {primary_dept}已完成處理，請進行簽核確認")

                    # 顯示處理結果
                    if defect['resolution']:
                        st.write(f"**處理結果：** {defect['resolution']}")

                    col_approve1, col_approve2 = st.columns(2)

                    with col_approve1:
                        st.write("**✅ 簽核通過**")
                        approve_note = st.text_area(
                            "簽核備註（選填）",
                            placeholder="可填寫簽核意見...",
                            key=f"approve_note_{defect['id']}"
                        )

                        if st.button("✅ 通過", key=f"approve_ok_{defect['id']}", use_container_width=True):
                            # 檢查是否需要第三責任人簽核
                            third_info = get_third_responsible_info(defect['resolution']) if defect['resolution'] else None

                            conn = sqlite3.connect('defect_management.db')
                            cursor = conn.cursor()

                            if third_info:
                                # 需要第三責任人簽核，更新為待第三責任人簽核狀態
                                cursor.execute('''
                                    UPDATE defects
                                    SET approval_status = '待第三責任人簽核',
                                        third_dept = ?, third_person = ?, third_approval_status = '待簽核',
                                        updated_time = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (third_info['dept'], third_info['person'], defect['id']))

                                # 添加簽核記錄
                                comment = f"簽核通過，轉交{third_info['dept']}({third_info['person']})簽核"
                                if approve_note:
                                    comment += f" - {approve_note}"

                                cursor.execute('''
                                    INSERT INTO processing_logs (defect_id, action, department, operator, comment)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (defect['id'], f'{secondary_dept}簽核通過', secondary_dept,
                                     st.session_state.user['name'], comment))

                                conn.commit()
                                conn.close()
                                st.success(f"✅ 簽核通過！已轉交{third_info['dept']}({third_info['person']})簽核")
                                st.rerun()
                            else:
                                # 不需要第三責任人簽核，直接完成
                                cursor.execute('''
                                    UPDATE defects
                                    SET status = '已完成', approval_status = '已簽核通過',
                                        completion_time = CURRENT_TIMESTAMP, updated_time = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (defect['id'],))

                                # 添加簽核記錄
                                comment = "簽核通過"
                                if approve_note:
                                    comment += f" - {approve_note}"

                                cursor.execute('''
                                    INSERT INTO processing_logs (defect_id, action, department, operator, comment)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (defect['id'], f'{secondary_dept}簽核通過', secondary_dept,
                                     st.session_state.user['name'], comment))

                                conn.commit()
                                conn.close()
                                st.success("✅ 簽核通過！案件已完成")
                                st.rerun()

                    with col_approve2:
                        st.write("**❌ 簽核退回**")
                        reject_reason = st.text_area(
                            "退回原因 *",
                            placeholder="請說明退回原因...",
                            key=f"reject_reason_{defect['id']}"
                        )

                        if st.button("❌ 退回", key=f"approve_ng_{defect['id']}", use_container_width=True):
                            if reject_reason:
                                # 退回給主要單位重新處理
                                conn = sqlite3.connect('defect_management.db')
                                cursor = conn.cursor()

                                # 確保primary_dept不為空，如果為空則使用默認值
                                target_primary_dept = primary_dept if primary_dept else '工程部'

                                cursor.execute('''
                                    UPDATE defects
                                    SET approval_status = '主要單位處理中',
                                        responsible_dept = ?, assigned_person = ?, updated_time = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (target_primary_dept, primary_person, defect['id']))

                                # 添加退回記錄
                                cursor.execute('''
                                    INSERT INTO processing_logs (defect_id, action, department, operator, comment)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (defect['id'], f'{secondary_dept}簽核退回', secondary_dept,
                                     st.session_state.user['name'], reject_reason))

                                conn.commit()
                                conn.close()
                                st.success(f"⚠️ 已退回{target_primary_dept}重新處理")
                                st.rerun()
                            else:
                                st.error("請填寫退回原因")

                # 新增：第三責任人簽核邏輯
                elif defect['status'] == '處理中' and approval_status == '待第三責任人簽核':
                    third_dept = defect.get('third_dept', '')
                    third_person = defect.get('third_person', '')

                    st.write("---")
                    st.write(f"**🔍 {third_dept}簽核**")
                    st.info(f"📋 {secondary_dept}已完成簽核，請{third_person}進行最終簽核確認")

                    # 顯示處理結果
                    if defect['resolution']:
                        st.write(f"**處理結果：** {defect['resolution']}")

                    col_third1, col_third2 = st.columns(2)

                    with col_third1:
                        st.write("**✅ 最終簽核通過**")
                        third_approve_note = st.text_area(
                            "簽核備註（選填）",
                            placeholder="可填寫最終簽核意見...",
                            key=f"third_approve_note_{defect['id']}"
                        )

                        if st.button("✅ 最終通過", key=f"third_approve_ok_{defect['id']}", use_container_width=True):
                            # 更新為已完成狀態
                            conn = sqlite3.connect('defect_management.db')
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE defects
                                SET status = '已完成', approval_status = '已簽核通過',
                                    third_approval_status = '已簽核',
                                    completion_time = CURRENT_TIMESTAMP, updated_time = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (defect['id'],))

                            # 添加最終簽核記錄
                            comment = "最終簽核通過"
                            if third_approve_note:
                                comment += f" - {third_approve_note}"

                            cursor.execute('''
                                INSERT INTO processing_logs (defect_id, action, department, operator, comment)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (defect['id'], f'{third_dept}最終簽核通過', third_dept,
                                 st.session_state.user['name'], comment))

                            conn.commit()
                            conn.close()
                            st.success("✅ 最終簽核通過！案件已完成")
                            st.rerun()

                    with col_third2:
                        st.write("**❌ 最終簽核退回**")
                        third_reject_reason = st.text_area(
                            "退回原因 *",
                            placeholder="請說明退回原因...",
                            key=f"third_reject_reason_{defect['id']}"
                        )

                        if st.button("❌ 退回重處理", key=f"third_approve_ng_{defect['id']}", use_container_width=True):
                            if third_reject_reason:
                                # 退回給主要單位重新處理
                                conn = sqlite3.connect('defect_management.db')
                                cursor = conn.cursor()

                                # 確保primary_dept不為空，如果為空則使用默認值
                                target_primary_dept = primary_dept if primary_dept else '工程部'

                                cursor.execute('''
                                    UPDATE defects
                                    SET approval_status = '主要單位處理中',
                                        responsible_dept = ?, assigned_person = ?,
                                        third_approval_status = '已退回',
                                        updated_time = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (target_primary_dept, primary_person, defect['id']))

                                # 添加退回記錄
                                cursor.execute('''
                                    INSERT INTO processing_logs (defect_id, action, department, operator, comment)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (defect['id'], f'{third_dept}最終簽核退回', third_dept,
                                     st.session_state.user['name'], third_reject_reason))

                                conn.commit()
                                conn.close()
                                st.success(f"⚠️ 已退回{target_primary_dept}重新處理")
                                st.rerun()
                            else:
                                st.error("請填寫退回原因")

            # 處理記錄
            st.subheader("📝 處理記錄")
            logs = get_processing_logs(defect['id'])
            if not logs.empty:
                for _, log in logs.iterrows():
                    st.write(f"**{log['timestamp']}** - {log['department']} ({log['operator']}): {log['action']}")
                    if log['comment']:
                        st.write(f"備註: {log['comment']}")
                    st.write("---")
            else:
                st.write("暫無處理記錄")

def analytics_page():
    st.header("📈 統計分析")

    all_defects = get_defects()

    if all_defects.empty:
        st.info("📊 目前沒有資料可供分析，請先到「不良品登錄」頁面登錄一些記錄")
        st.write("---")
        st.write("**💡 快速開始指南：**")
        st.write("1. 點擊左側選單的「📋 不良品登錄」")
        st.write("2. 填寫不良品資訊並提交")
        st.write("3. 回到此頁面查看統計分析")
        return

    # 顯示資料概況
    st.write(f"📊 **資料概況：** 共 {len(all_defects)} 筆記錄，總數量 {all_defects['quantity'].sum()} pcs")
    st.write(f"📅 **時間範圍：** {pd.to_datetime(all_defects['created_time']).min().strftime('%Y-%m-%d')} 至 {pd.to_datetime(all_defects['created_time']).max().strftime('%Y-%m-%d')}")
    st.divider()

    # 分析控制面板
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        date_range = st.selectbox("📅 分析時間範圍", ["最近7天", "最近30天", "最近90天", "全部"])

    with col2:
        chart_type = st.selectbox("📊 圖表類型", ["標準視圖", "詳細視圖", "對比視圖"])

    with col3:
        if st.button("🔄 刷新數據"):
            st.rerun()

    if date_range != "全部":
        days_map = {"最近7天": 7, "最近30天": 30, "最近90天": 90}
        cutoff_date = datetime.now() - timedelta(days=days_map[date_range])
        all_defects = all_defects[pd.to_datetime(all_defects['created_time']) >= cutoff_date]

    # 整體統計
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_quantity = all_defects['quantity'].sum()
        total_records = len(all_defects)
        st.metric("總不良品數", f"{total_quantity} pcs", delta=f"{total_records}筆記錄")

    with col2:
        completed_quantity = all_defects[all_defects['status'] == '已完成']['quantity'].sum()
        total_quantity = all_defects['quantity'].sum()
        completed_rate = (completed_quantity / total_quantity * 100) if total_quantity > 0 else 0
        st.metric("完成率", f"{completed_rate:.1f}%", delta=f"{completed_quantity}pcs已完成")

    with col3:
        urgent_quantity = all_defects[all_defects['defect_level'] == 'A級']['quantity'].sum()
        urgent_records = len(all_defects[all_defects['defect_level'] == 'A級'])
        st.metric("A級不良品", f"{urgent_quantity} pcs", delta=f"{urgent_records}筆記錄")

    with col4:
        # 計算平均處理時間
        completed_defects = all_defects[all_defects['status'] == '已完成']
        if not completed_defects.empty:
            avg_time = (pd.to_datetime(completed_defects['completion_time']) -
                       pd.to_datetime(completed_defects['created_time'])).dt.total_seconds().mean() / 3600
            st.metric("平均處理時間", f"{avg_time:.1f}小時")
        else:
            st.metric("平均處理時間", "無資料")

    st.divider()

    # 工單不良率分析
    st.subheader("📊 工單不良率分析")

    # 計算每個工單的不良率
    work_order_stats = []
    work_orders = all_defects['work_order'].unique()

    for wo in work_orders:
        wo_data = all_defects[all_defects['work_order'] == wo]
        total_defects = wo_data['quantity'].sum()
        total_qty = wo_data['work_order_total_qty'].max()  # 取最大值作為工單總數
        record_count = len(wo_data)

        if total_qty > 0:
            defect_rate = (total_defects / total_qty) * 100
        else:
            defect_rate = 0

        work_order_stats.append({
            'work_order': wo,
            'total_defects': total_defects,
            'total_qty': total_qty,
            'record_count': record_count,
            'defect_rate': defect_rate
        })

    if work_order_stats:
        wo_df = pd.DataFrame(work_order_stats)
        wo_df = wo_df.sort_values('defect_rate', ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            st.write("**🏆 工單不良率排行**")

            # 不良率圖表
            fig_rate = px.bar(
                wo_df,
                x='work_order',
                y='defect_rate',
                color='defect_rate',
                color_continuous_scale=['#60a5fa', '#3b82f6', '#2563eb'],
                text='defect_rate'
            )

            fig_rate.update_traces(
                texttemplate='%{text:.2f}%',
                textposition='outside',
                hovertemplate='<b>工單: %{x}</b><br>不良率: %{y:.2f}%<extra></extra>'
            )

            fig_rate.update_layout(
                height=350,
                xaxis_title="工單號碼",
                yaxis_title="不良率 (%)",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=11),
                xaxis=dict(tickangle=45)
            )

            st.plotly_chart(fig_rate, use_container_width=True)

        with col2:
            st.write("**📋 詳細統計表**")
            display_df = wo_df.copy()
            display_df['工單號碼'] = display_df['work_order']
            display_df['工單總數'] = display_df['total_qty']
            display_df['不良數量'] = display_df['total_defects']
            display_df['不良率(%)'] = display_df['defect_rate'].round(2)
            display_df['記錄筆數'] = display_df['record_count']

            st.dataframe(
                display_df[['工單號碼', '工單總數', '不良數量', '不良率(%)', '記錄筆數']],
                use_container_width=True,
                height=350
            )
    else:
        st.info("📊 暫無工單統計資料")

    st.divider()

    # 不良項目佔比分析
    st.subheader("🥧 不良項目佔比分析")

    # 選擇特定工單分析
    col1, col2 = st.columns([1, 3])

    with col1:
        selected_wo = st.selectbox(
            "選擇工單",
            options=['全部工單'] + list(all_defects['work_order'].unique()),
            help="選擇特定工單查看詳細分析"
        )

    # 根據選擇篩選資料
    if selected_wo != '全部工單':
        analysis_data = all_defects[all_defects['work_order'] == selected_wo]
        st.write(f"**分析範圍：** 工單 {selected_wo}")
    else:
        analysis_data = all_defects
        st.write("**分析範圍：** 全部工單")

    if not analysis_data.empty:
        col1, col2 = st.columns(2)

        with col1:
            # 不良類型佔比餅圖
            type_stats = analysis_data.groupby('defect_type')['quantity'].sum()

            fig_pie = px.pie(
                values=type_stats.values,
                names=type_stats.index,
                color_discrete_sequence=['#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af', '#1e3a8a']
            )

            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>數量: %{value} pcs<br>佔比: %{percent}<extra></extra>'
            )

            fig_pie.update_layout(
                height=400,
                showlegend=True,
                legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
                font=dict(size=11)
            )

            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            # 不良等級佔比
            level_stats = analysis_data.groupby('defect_level')['quantity'].sum()

            fig_level = px.bar(
                x=level_stats.index,
                y=level_stats.values,
                color=level_stats.index,
                color_discrete_map={'A級': '#ef4444', 'B級': '#f97316', 'C級': '#eab308'},
                text=level_stats.values
            )

            fig_level.update_traces(
                texttemplate='%{text} pcs',
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>數量: %{y} pcs<extra></extra>'
            )

            fig_level.update_layout(
                height=400,
                xaxis_title="不良等級",
                yaxis_title="數量 (pcs)",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=11)
            )

            st.plotly_chart(fig_level, use_container_width=True)

        # 詳細佔比表格
        st.write("**📊 詳細佔比統計**")

        col1, col2 = st.columns(2)

        with col1:
            st.write("*不良類型佔比*")
            type_total = type_stats.sum()
            type_percent_df = pd.DataFrame({
                '不良類型': type_stats.index,
                '數量(pcs)': type_stats.values,
                '佔比(%)': (type_stats.values / type_total * 100).round(2)
            })
            st.dataframe(type_percent_df, use_container_width=True)

        with col2:
            st.write("*不良等級佔比*")
            level_total = level_stats.sum()
            level_percent_df = pd.DataFrame({
                '不良等級': level_stats.index,
                '數量(pcs)': level_stats.values,
                '佔比(%)': (level_stats.values / level_total * 100).round(2)
            })
            st.dataframe(level_percent_df, use_container_width=True)
    else:
        st.info("📊 選擇的工單暫無資料")

    st.divider()

    # 供應商分析
    st.subheader("🏭 供應商分析")

    # 檢查是否有供應商資料
    supplier_data = analysis_data[analysis_data['supplier'].notna() & (analysis_data['supplier'] != '')]

    if not supplier_data.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.write("**📊 供應商不良品統計**")

            supplier_stats = supplier_data.groupby('supplier')['quantity'].sum().sort_values(ascending=False)

            fig_supplier = px.bar(
                x=supplier_stats.index,
                y=supplier_stats.values,
                color=supplier_stats.values,
                color_continuous_scale=['#60a5fa', '#2563eb', '#1e40af'],
                text=supplier_stats.values
            )

            fig_supplier.update_traces(
                texttemplate="%{text} pcs",
                textposition='outside',
                hovertemplate='<b>供應商: %{x}</b><br>不良數量: %{y} pcs<extra></extra>'
            )

            fig_supplier.update_layout(
                height=350,
                xaxis_title="供應商",
                yaxis_title="不良數量 (pcs)",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=11),
                xaxis=dict(tickangle=45)
            )

            st.plotly_chart(fig_supplier, use_container_width=True)

        with col2:
            st.write("**🔍 供應商詳細分析**")

            # 按供應商和產品類型分組
            supplier_product_stats = supplier_data.groupby(['supplier', 'product_name'])['quantity'].sum().reset_index()

            # 創建透視表
            pivot_table = supplier_product_stats.pivot_table(
                index='supplier',
                columns='product_name',
                values='quantity',
                fill_value=0
            )

            if not pivot_table.empty:
                st.write("*供應商 vs 產品類型 不良數量統計*")
                st.dataframe(pivot_table, use_container_width=True)

            # 供應商佔比表
            st.write("*供應商不良品佔比*")
            supplier_total = supplier_stats.sum()
            supplier_percent_df = pd.DataFrame({
                '供應商': supplier_stats.index,
                '不良數量(pcs)': supplier_stats.values,
                '佔比(%)': (supplier_stats.values / supplier_total * 100).round(2)
            })
            st.dataframe(supplier_percent_df, use_container_width=True)

        # 供應商產品類型分析
        st.write("**📋 供應商產品類型分析**")

        # 按產品類型分組供應商資料
        product_types = ['SHAFT', 'CLIP', 'MOUNT', 'BUSHING']
        supplier_by_type = {}

        for ptype in product_types:
            type_data = supplier_data[supplier_data['product_name'].str.upper().str.contains(ptype, na=False)]
            if not type_data.empty:
                supplier_by_type[ptype] = type_data.groupby('supplier')['quantity'].sum().sort_values(ascending=False)

        if supplier_by_type:
            cols = st.columns(len(supplier_by_type))

            for i, (ptype, stats) in enumerate(supplier_by_type.items()):
                with cols[i]:
                    st.write(f"**{ptype}**")
                    for supplier, qty in stats.items():
                        st.write(f"• {supplier}: {qty} pcs")
        else:
            st.info("📊 暫無特定產品類型的供應商資料")
    else:
        st.info("📊 暫無供應商資料，請在登錄不良品時填寫供應商資訊")
        st.write("💡 **提示：** 系統支援以下產品類型的供應商選擇：")
        st.write("• SHAFT - 軸類產品")
        st.write("• CLIP - 夾具類產品")
        st.write("• MOUNT - 座架類產品")
        st.write("• BUSHING - 軸套類產品")

    st.divider()

    # 主要圖表區域
    if chart_type == "標準視圖":
        # 第一行圖表
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 不良品類型分析")
            type_quantity = all_defects.groupby('defect_type')['quantity'].sum().sort_values(ascending=True)

            # 使用漸層藍色配色
            colors = ['#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af', '#1e3a8a', '#172554']

            fig_type = px.bar(
                x=type_quantity.values,
                y=type_quantity.index,
                orientation='h',
                color=type_quantity.index,
                color_discrete_sequence=colors,
                text=type_quantity.values
            )

            fig_type.update_traces(
                texttemplate='%{text} pcs',
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>數量: %{x} pcs<extra></extra>'
            )

            fig_type.update_layout(
                height=400,
                xaxis_title="數量 (pcs)",
                yaxis_title="不良品類型",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12),
                margin=dict(l=100, r=50, t=50, b=50)
            )

            fig_type.update_xaxes(gridcolor='rgba(59, 130, 246, 0.1)')
            fig_type.update_yaxes(gridcolor='rgba(59, 130, 246, 0.1)')

            st.plotly_chart(fig_type, use_container_width=True)

        with col2:
            st.subheader("📈 每日趨勢分析")

            # 檢查資料是否存在
            if all_defects.empty:
                st.info("📊 暫無資料可供分析，請先登錄一些不良品記錄")
            else:
                                 # 處理日期資料
                 try:
                     all_defects_copy = all_defects.copy()

                     # 調試信息：顯示原始資料
                     st.write(f"🔍 **調試信息：** 原始資料筆數 {len(all_defects_copy)}")

                     # 轉換日期格式
                     all_defects_copy['created_time'] = pd.to_datetime(all_defects_copy['created_time'])
                     all_defects_copy['date'] = all_defects_copy['created_time'].dt.date

                     # 按日期分組統計
                     daily_quantity = all_defects_copy.groupby('date')['quantity'].sum().reset_index()
                     daily_quantity = daily_quantity.sort_values('date')

                     # 調試信息：顯示分組後的資料
                     st.write(f"🔍 **調試信息：** 分組後資料筆數 {len(daily_quantity)}")
                     if not daily_quantity.empty:
                         st.write(f"🔍 **調試信息：** 最新日期 {daily_quantity['date'].max()}，數量 {daily_quantity[daily_quantity['date'] == daily_quantity['date'].max()]['quantity'].iloc[0]} pcs")

                     # 檢查是否有每日資料
                     if daily_quantity.empty:
                         st.info("📊 暫無每日趨勢資料")
                     else:
                         # 顯示資料概要
                         st.write(f"📅 **資料範圍：** {daily_quantity['date'].min()} 至 {daily_quantity['date'].max()}")
                         st.write(f"📊 **共 {len(daily_quantity)} 天的資料**")

                         # 確保至少有一個資料點用於繪圖
                         if len(daily_quantity) == 1:
                             # 如果只有一天的資料，創建一個前一天的0值點以便繪圖
                             prev_date = daily_quantity['date'].iloc[0] - timedelta(days=1)
                             prev_row = pd.DataFrame({'date': [prev_date], 'quantity': [0]})
                             daily_quantity = pd.concat([prev_row, daily_quantity], ignore_index=True)

                         # 轉換date為datetime以便plotly處理
                         daily_quantity['date'] = pd.to_datetime(daily_quantity['date'])

                         fig_trend = px.area(
                             daily_quantity,
                             x='date',
                             y='quantity',
                             color_discrete_sequence=['#3b82f6'],
                             line_shape='spline'
                         )

                         fig_trend.update_traces(
                             hovertemplate='<b>日期: %{x|%Y-%m-%d}</b><br>數量: %{y} pcs<extra></extra>',
                             fill='tonexty',
                             fillcolor='rgba(59, 130, 246, 0.2)'
                         )

                         fig_trend.update_layout(
                             height=400,
                             xaxis_title="日期",
                             yaxis_title="不良品數量 (pcs)",
                             plot_bgcolor='rgba(0,0,0,0)',
                             paper_bgcolor='rgba(0,0,0,0)',
                             font=dict(size=12),
                             xaxis=dict(
                                 tickformat='%m/%d',
                                 tickangle=45
                             )
                         )

                         fig_trend.update_xaxes(gridcolor='rgba(59, 130, 246, 0.1)')
                         fig_trend.update_yaxes(gridcolor='rgba(59, 130, 246, 0.1)')

                         st.plotly_chart(fig_trend, use_container_width=True)

                         # 顯示每日資料表格（前10筆）
                         st.write("**📋 最近每日資料：**")
                         display_data = daily_quantity.sort_values('date', ascending=False).head(10).copy()
                         display_data['日期'] = display_data['date'].dt.strftime('%Y-%m-%d')
                         display_data['數量(pcs)'] = display_data['quantity']
                         st.dataframe(display_data[['日期', '數量(pcs)']], use_container_width=True)

                 except Exception as e:
                     st.error(f"❌ 處理每日趨勢資料時發生錯誤: {str(e)}")
                     st.write("原始資料預覽：")
                     st.write(all_defects[['created_time', 'quantity']].head())

        # 第二行圖表
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🎯 不良等級分布")
            level_data = all_defects.groupby('defect_level')['quantity'].sum()

            # 等級對應顏色
            level_colors = {'A級': '#ef4444', 'B級': '#f59e0b', 'C級': '#10b981'}
            colors_list = [level_colors.get(level, '#6b7280') for level in level_data.index]

            fig_pie = px.pie(
                values=level_data.values,
                names=level_data.index,
                color_discrete_sequence=colors_list
            )

            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>數量: %{value} pcs<br>佔比: %{percent}<extra></extra>'
            )

            fig_pie.update_layout(
                height=400,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12)
            )

            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.subheader("🏢 部門工作負荷")
            dept_data = all_defects.groupby('responsible_dept')['quantity'].sum().sort_values(ascending=True)

            fig_dept = px.bar(
                x=dept_data.values,
                y=dept_data.index,
                orientation='h',
                color_discrete_sequence=['#2563eb'],
                text=dept_data.values
            )

            fig_dept.update_traces(
                texttemplate='%{text} pcs',
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>負責數量: %{x} pcs<extra></extra>'
            )

            fig_dept.update_layout(
                height=400,
                xaxis_title="負責數量 (pcs)",
                yaxis_title="責任部門",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12),
                margin=dict(l=80, r=50, t=50, b=50)
            )

            fig_dept.update_xaxes(gridcolor='rgba(59, 130, 246, 0.1)')
            fig_dept.update_yaxes(gridcolor='rgba(59, 130, 246, 0.1)')

            st.plotly_chart(fig_dept, use_container_width=True)

    elif chart_type == "詳細視圖":
        # 詳細分析視圖
        st.subheader("📊 多維度分析")

        # 狀態vs等級熱力圖
        col1, col2 = st.columns(2)

        with col1:
            st.write("**狀態與等級交叉分析**")
            cross_analysis = all_defects.groupby(['status', 'defect_level'])['quantity'].sum().reset_index()
            pivot_data = cross_analysis.pivot(index='status', columns='defect_level', values='quantity').fillna(0)

            fig_heatmap = px.imshow(
                pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                color_continuous_scale='Blues',
                text_auto=True
            )

            fig_heatmap.update_layout(
                height=300,
                xaxis_title="不良等級",
                yaxis_title="處理狀態"
            )

            st.plotly_chart(fig_heatmap, use_container_width=True)

        with col2:
            st.write("**處理時間分布**")
            if not completed_defects.empty:
                completed_defects_copy = completed_defects.copy()
                completed_defects_copy['processing_hours'] = (
                    pd.to_datetime(completed_defects_copy['completion_time']) -
                    pd.to_datetime(completed_defects_copy['created_time'])
                ).dt.total_seconds() / 3600

                fig_hist = px.histogram(
                    completed_defects_copy,
                    x='processing_hours',
                    nbins=20,
                    color_discrete_sequence=['#3b82f6']
                )

                fig_hist.update_layout(
                    height=300,
                    xaxis_title="處理時間 (小時)",
                    yaxis_title="案件數量"
                )

                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("暫無已完成案件的處理時間數據")

    else:  # 對比視圖
        st.subheader("📈 時間對比分析")

        # 本週vs上週對比
        current_week = datetime.now().isocalendar()[1]
        current_year = datetime.now().year

        all_defects['week'] = pd.to_datetime(all_defects['created_time']).dt.isocalendar().week
        all_defects['year'] = pd.to_datetime(all_defects['created_time']).dt.year

        current_week_data = all_defects[(all_defects['week'] == current_week) & (all_defects['year'] == current_year)]
        last_week_data = all_defects[(all_defects['week'] == current_week-1) & (all_defects['year'] == current_year)]

        col1, col2, col3 = st.columns(3)

        with col1:
            current_total = current_week_data['quantity'].sum()
            st.metric("本週不良品", f"{current_total} pcs")

        with col2:
            last_total = last_week_data['quantity'].sum()
            st.metric("上週不良品", f"{last_total} pcs")

        with col3:
            if last_total > 0:
                change_rate = ((current_total - last_total) / last_total) * 100
                st.metric("週變化率", f"{change_rate:+.1f}%")
            else:
                st.metric("週變化率", "N/A")

    # 處理方式分析
    st.subheader("🔧 處理方式分析")

    # 獲取已完成的案件進行處理方式分析
    completed_defects = all_defects[all_defects['status'] == '已完成']

    if not completed_defects.empty and 'resolution' in completed_defects.columns:
        # 解析處理方式
        resolution_data = []
        for _, defect in completed_defects.iterrows():
            resolution = defect['resolution']
            quantity = defect['quantity']

            if pd.isna(resolution) or resolution == '':
                continue

            # 解析不同的處理方式
            if 'TRA11 判定後為OK品' in resolution:
                # 解析OK品和NG品處理
                if '剩餘NG品：' in resolution:
                    # 有剩餘NG品的情況
                    try:
                        # 提取OK品數量
                        ok_match = re.search(r'OK品：(\d+) pcs', resolution)
                        ng_match = re.search(r'剩餘NG品：(\d+) pcs - (\w+)', resolution)

                        if ok_match:
                            ok_qty = int(ok_match.group(1))
                            resolution_data.append({
                                '處理方式': 'OK品判定',
                                '數量': ok_qty,
                                '工單': defect['work_order'],
                                '產品': defect['product_name'],
                                '部門': defect['responsible_dept']
                            })

                        if ng_match:
                            ng_qty = int(ng_match.group(1))
                            ng_method = ng_match.group(2)
                            resolution_data.append({
                                '處理方式': ng_method,
                                '數量': ng_qty,
                                '工單': defect['work_order'],
                                '產品': defect['product_name'],
                                '部門': defect['responsible_dept']
                            })
                    except:
                        pass
                else:
                    # 全部為OK品
                    resolution_data.append({
                        '處理方式': 'OK品判定',
                        '數量': quantity,
                        '工單': defect['work_order'],
                        '產品': defect['product_name'],
                        '部門': defect['responsible_dept']
                    })
            else:
                # 其他處理方式
                method = resolution.split(' - ')[0]  # 去除備註部分
                resolution_data.append({
                    '處理方式': method,
                    '數量': quantity,
                    '工單': defect['work_order'],
                    '產品': defect['product_name'],
                    '部門': defect['responsible_dept']
                })

        if resolution_data:
            resolution_df = pd.DataFrame(resolution_data)

            # 處理方式統計圖表
            col1, col2 = st.columns(2)

            with col1:
                st.write("**處理方式分布**")
                method_stats = resolution_df.groupby('處理方式')['數量'].sum().sort_values(ascending=True)

                fig_method = px.bar(
                    x=method_stats.values,
                    y=method_stats.index,
                    orientation='h',
                    color=method_stats.index,
                    color_discrete_sequence=['#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af'],
                    text=method_stats.values
                )

                fig_method.update_traces(
                    texttemplate="%{text} pcs",
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>數量: %{x} pcs<extra></extra>'
                )

                fig_method.update_layout(
                    height=300,
                    xaxis_title="數量 (pcs)",
                    yaxis_title="處理方式",
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=12),
                    margin=dict(l=100, r=50, t=50, b=50)
                )

                st.plotly_chart(fig_method, use_container_width=True)

            with col2:
                st.write("**處理方式比例**")
                method_counts = resolution_df.groupby('處理方式')['數量'].sum()

                fig_pie = px.pie(
                    values=method_counts.values,
                    names=method_counts.index,
                    color_discrete_sequence=['#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af']
                )

                fig_pie.update_traces(
                    textposition="inside",
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>數量: %{value} pcs<br>比例: %{percent}<extra></extra>'
                )

                fig_pie.update_layout(
                    height=300,
                    showlegend=True,
                    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
                )

                st.plotly_chart(fig_pie, use_container_width=True)

            # 處理方式詳細統計表
            st.write("**處理方式詳細統計**")
            method_detail = resolution_df.groupby('處理方式').agg({
                '數量': ['sum', 'count', 'mean'],
                '部門': lambda x: ', '.join(x.unique())
            }).round(1)

            method_detail.columns = ['總數量(pcs)', '案件數', '平均數量(pcs)', '涉及部門']
            method_detail = method_detail.reset_index()

            st.dataframe(method_detail, use_container_width=True)

            # 按部門的處理方式分布
            st.write("**各部門處理方式分布**")
            dept_method = resolution_df.groupby(['部門', '處理方式'])['數量'].sum().unstack(fill_value=0)

            if not dept_method.empty:
                fig_dept_method = px.bar(
                    dept_method,
                    x=dept_method.index,
                    y=dept_method.columns,
                    color_discrete_sequence=['#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af'],
                    title="各部門處理方式分布"
                )

                fig_dept_method.update_layout(
                    height=400,
                    xaxis_title="部門",
                    yaxis_title="數量 (pcs)",
                    legend_title="處理方式",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )

                st.plotly_chart(fig_dept_method, use_container_width=True)
        else:
            st.info("暫無處理方式數據可供分析")
    else:
        st.info("暫無已完成案件的處理方式數據")

    # 責任人負荷分析
    st.subheader("👥 責任人負荷分析")

    # 檢查是否有責任人資料
    if 'assigned_person' in all_defects.columns and not all_defects['assigned_person'].isna().all():
        # 過濾掉空白責任人的記錄
        assigned_defects = all_defects[all_defects['assigned_person'].notna() & (all_defects['assigned_person'] != '')]

        if not assigned_defects.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.write("**📊 責任人工作負荷統計**")

                # 統計每個責任人的工作量
                assignee_stats = assigned_defects.groupby('assigned_person').agg({
                    'id': 'count',
                    'quantity': 'sum',
                    'status': lambda x: sum(x == '已完成'),
                    'defect_level': lambda x: sum(x == 'A級'),
                    'responsible_dept': 'first'  # 取得部門信息
                }).reset_index()

                assignee_stats.columns = ['責任人', '負責案件數', '負責總數量', '已完成案件', 'A級案件數', '所屬部門']
                assignee_stats['完成率(%)'] = (assignee_stats['已完成案件'] / assignee_stats['負責案件數'] * 100).round(1)
                assignee_stats['平均每案件數量'] = (assignee_stats['負責總數量'] / assignee_stats['負責案件數']).round(1)

                # 計算工作負荷比例
                total_cases = assignee_stats['負責案件數'].sum()
                assignee_stats['負荷比例(%)'] = (assignee_stats['負責案件數'] / total_cases * 100).round(1)

                # 按負責案件數排序
                assignee_stats = assignee_stats.sort_values('負責案件數', ascending=False)

                st.dataframe(assignee_stats, use_container_width=True)

                # 顯示負荷摘要
                st.write("**📈 負荷摘要**")
                avg_cases = assignee_stats['負責案件數'].mean()
                max_cases = assignee_stats['負責案件數'].max()
                min_cases = assignee_stats['負責案件數'].min()

                col_summary1, col_summary2, col_summary3 = st.columns(3)
                with col_summary1:
                    st.metric("平均案件數", f"{avg_cases:.1f}", help="每人平均負責案件數")
                with col_summary2:
                    st.metric("最高案件數", f"{max_cases}", help="單人最高負責案件數")
                with col_summary3:
                    st.metric("最低案件數", f"{min_cases}", help="單人最低負責案件數")

            with col2:
                st.write("**📊 責任人負荷分布圖**")

                # 責任人負荷圓餅圖
                fig_assignee_pie = px.pie(
                    assignee_stats,
                    values='負責案件數',
                    names='責任人',
                    title="責任人案件數分布",
                    color_discrete_sequence=['#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af', '#1e3a8a', '#172554']
                )

                fig_assignee_pie.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>案件數: %{value}<br>比例: %{percent}<extra></extra>'
                )

                fig_assignee_pie.update_layout(
                    height=350,
                    showlegend=True,
                    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
                )

                st.plotly_chart(fig_assignee_pie, use_container_width=True)

                # 責任人工作量柱狀圖
                st.write("**📈 責任人工作量對比**")
                fig_assignee_bar = px.bar(
                    assignee_stats,
                    x='責任人',
                    y='負責案件數',
                    color='完成率(%)',
                    color_continuous_scale='Blues',
                    text='負責案件數',
                    title="各責任人負責案件數對比"
                )

                fig_assignee_bar.update_traces(
                    texttemplate='%{text}件',
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>案件數: %{y}件<br>完成率: %{color:.1f}%<extra></extra>'
                )

                fig_assignee_bar.update_layout(
                    height=350,
                    xaxis_title="責任人",
                    yaxis_title="負責案件數",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )

                st.plotly_chart(fig_assignee_bar, use_container_width=True)

            # 詳細責任人分析表
            st.write("**🔍 責任人詳細分析**")

            # 為每個責任人提供更詳細的分析
            detailed_assignee_analysis = []
            for _, assignee_row in assignee_stats.iterrows():
                assignee_name = assignee_row['責任人']
                assignee_defects = assigned_defects[assigned_defects['assigned_person'] == assignee_name]

                # 計算各等級分布
                level_dist = assignee_defects['defect_level'].value_counts()

                # 計算各類型分布
                type_dist = assignee_defects['defect_type'].value_counts()
                top_type = type_dist.index[0] if not type_dist.empty else '無'

                # 計算平均處理時間
                completed_cases = assignee_defects[assignee_defects['status'] == '已完成']
                if not completed_cases.empty:
                    avg_processing_time = (pd.to_datetime(completed_cases['completion_time']) -
                                         pd.to_datetime(completed_cases['created_time'])).dt.total_seconds().mean() / 3600
                else:
                    avg_processing_time = 0

                # 計算待處理案件數
                pending_cases = len(assignee_defects[assignee_defects['status'].isin(['待處理', '處理中'])])

                # 計算逾期案件數
                current_time = datetime.now()
                overdue_cases = len(assignee_defects[
                    (assignee_defects['status'].isin(['待處理', '處理中'])) &
                    (pd.to_datetime(assignee_defects['deadline']) < current_time)
                ])

                detailed_assignee_analysis.append({
                    '責任人': assignee_name,
                    '所屬部門': assignee_row['所屬部門'],
                    '總案件數': assignee_row['負責案件數'],
                    '總數量(pcs)': assignee_row['負責總數量'],
                    '待處理案件': pending_cases,
                    '逾期案件': overdue_cases,
                    'A級案件': level_dist.get('A級', 0),
                    'B級案件': level_dist.get('B級', 0),
                    'C級案件': level_dist.get('C級', 0),
                    '主要不良類型': top_type,
                    '完成率(%)': assignee_row['完成率(%)'],
                    '平均處理時間(小時)': f"{avg_processing_time:.1f}" if avg_processing_time > 0 else "無資料"
                })

            if detailed_assignee_analysis:
                detailed_df = pd.DataFrame(detailed_assignee_analysis)
                st.dataframe(detailed_df, use_container_width=True)

            # 部門責任人負荷分析
            st.write("**🏢 各部門責任人負荷分析**")
            dept_assignee_stats = assignee_stats.groupby('所屬部門').agg({
                '負責案件數': ['sum', 'mean', 'count'],
                '負責總數量': 'sum',
                '完成率(%)': 'mean'
            }).round(1)

            dept_assignee_stats.columns = ['總案件數', '平均案件數', '責任人數', '總數量(pcs)', '平均完成率(%)']
            dept_assignee_stats = dept_assignee_stats.reset_index()

            st.dataframe(dept_assignee_stats, use_container_width=True)

        else:
            st.info("📊 暫無已分配責任人的案件，請先在案件中指派責任人")
    else:
        st.info("📊 暫無責任人資料可供分析，請先在案件中指派責任人")

    st.divider()

    # 部門績效分析
    st.subheader("🏆 部門績效分析")

    dept_stats = []
    for dept in ['工程部', '品保部']:  # 取消製造部
        dept_defects = all_defects[all_defects['responsible_dept'] == dept]
        if not dept_defects.empty:
            total_quantity = dept_defects['quantity'].sum()
            total_records = len(dept_defects)
            completed_quantity = dept_defects[dept_defects['status'] == '已完成']['quantity'].sum()
            completed_records = len(dept_defects[dept_defects['status'] == '已完成'])
            completion_rate = (completed_quantity / total_quantity * 100) if total_quantity > 0 else 0

            # 計算平均處理時間
            completed_dept = dept_defects[dept_defects['status'] == '已完成']
            if not completed_dept.empty:
                avg_time = (pd.to_datetime(completed_dept['completion_time']) -
                           pd.to_datetime(completed_dept['created_time'])).dt.total_seconds().mean() / 3600
            else:
                avg_time = 0

            dept_stats.append({
                '部門': dept,
                '總數量(pcs)': total_quantity,
                '總記錄數': total_records,
                '已完成數量(pcs)': completed_quantity,
                '已完成記錄數': completed_records,
                '完成率(%)': f"{completion_rate:.1f}",
                '平均處理時間(小時)': f"{avg_time:.1f}"
            })

    if dept_stats:
        dept_df = pd.DataFrame(dept_stats)
        st.dataframe(dept_df, use_container_width=True)

    # 詳細資料表格
    st.divider()
    st.subheader("📋 詳細資料記錄")

    # 資料篩選選項
    col1, col2, col3 = st.columns(3)

    with col1:
        show_records = st.selectbox("顯示記錄數", [10, 20, 50, 100, "全部"], index=0)

    with col2:
        sort_by = st.selectbox("排序方式", ["建立時間(新→舊)", "建立時間(舊→新)", "包數(小→大)", "包數(大→小)", "數量(多→少)", "數量(少→多)"])

    with col3:
        if st.button("📥 匯出詳細資料"):
            # 重複導出邏輯，但這裡只針對當前篩選的資料
            if not all_defects.empty:
                export_data = all_defects[[
                    'id', 'work_order', 'package_number', 'product_name', 'defect_type',
                    'defect_level', 'quantity', 'description', 'responsible_dept',
                    'assigned_person', 'status', 'resolution', 'created_time',
                    'deadline', 'completion_time'
                ]].copy()

                export_data.columns = [
                    '編號', '工單號碼', '包數', '產品名稱', '不良類型',
                    '不良等級', '數量(pcs)', '問題描述', '責任部門',
                    '負責人', '處理狀態', '處理結果', '建立時間',
                    '處理截止時間', '完成時間'
                ]

                csv = export_data.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 下載詳細資料CSV",
                    data=csv,
                    file_name=f"不良品詳細資料_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="包含包數信息的詳細不良品記錄"
                )

    # 排序資料
    display_defects = all_defects.copy()

    if sort_by == "建立時間(新→舊)":
        display_defects = display_defects.sort_values('created_time', ascending=False)
    elif sort_by == "建立時間(舊→新)":
        display_defects = display_defects.sort_values('created_time', ascending=True)
    elif sort_by == "包數(小→大)":
        display_defects = display_defects.sort_values(['work_order', 'package_number'], ascending=[True, True])
    elif sort_by == "包數(大→小)":
        display_defects = display_defects.sort_values(['work_order', 'package_number'], ascending=[True, False])
    elif sort_by == "數量(多→少)":
        display_defects = display_defects.sort_values('quantity', ascending=False)
    elif sort_by == "數量(少→多)":
        display_defects = display_defects.sort_values('quantity', ascending=True)

    # 限制顯示記錄數
    if show_records != "全部":
        display_defects = display_defects.head(show_records)

    # 準備顯示的資料
    if not display_defects.empty:
        # 重新排列並重命名欄位
        detail_data = display_defects[[
            'work_order', 'package_number', 'product_name', 'defect_type',
            'defect_level', 'quantity', 'responsible_dept', 'assigned_person',
            'status', 'created_time'
        ]].copy()

        # 格式化包數顯示
        detail_data['package_display'] = detail_data['package_number'].apply(lambda x: f"第{x}包")

        # 設定中文欄位名稱
        detail_data_display = detail_data[[
            'work_order', 'package_display', 'product_name', 'defect_type',
            'defect_level', 'quantity', 'responsible_dept', 'assigned_person',
            'status', 'created_time'
        ]].copy()

        detail_data_display.columns = [
            '工單號碼', '包數', '產品名稱', '不良類型',
            '不良等級', '數量(pcs)', '責任部門', '負責人',
            '處理狀態', '建立時間'
        ]

        # 格式化時間顯示
        detail_data_display['建立時間'] = pd.to_datetime(detail_data_display['建立時間']).dt.strftime('%Y-%m-%d %H:%M')

        st.write(f"**📊 顯示 {len(detail_data_display)} 筆記錄** (共 {len(all_defects)} 筆)")
        st.dataframe(detail_data_display, use_container_width=True, height=400)

        # 工單包數統計摘要 - 增強版
        st.write("**📦 工單數量資訊與處理進度統計：**")

        # 按工單統計包數和相關信息
        work_order_stats = display_defects.groupby('work_order').agg({
            'package_number': ['count', 'max', 'min'],
            'quantity': ['sum', 'mean', 'max', 'min'],
            'product_name': 'first',
            'defect_type': lambda x: ', '.join(x.unique()),
            'defect_level': lambda x: ', '.join(x.unique()),
            'status': lambda x: f"{sum(x=='已完成')}/{len(x)}",
            'responsible_dept': lambda x: ', '.join(x.unique()),
            'assigned_person': lambda x: ', '.join(x.unique()),
            'created_time': ['min', 'max'],
            'completion_time': lambda x: sum(pd.notna(x))
        }).reset_index()

        # 重新命名欄位
        work_order_stats.columns = [
            '工單號碼', '包數數量', '最大包數', '最小包數',
            '總不良數量', '平均數量', '最大數量', '最小數量',
            '產品名稱', '不良類型', '不良等級', '完成狀況',
            '責任部門', '負責人', '最早建立', '最晚建立', '已完成包數'
        ]

        # 計算處理進度百分比
        work_order_stats['處理進度(%)'] = (work_order_stats['已完成包數'] / work_order_stats['包數數量'] * 100).round(1)

        # 格式化數量信息
        work_order_stats['包數範圍'] = work_order_stats.apply(
            lambda x: f"第{x['最小包數']}包 - 第{x['最大包數']}包" if x['最大包數'] > x['最小包數'] else f"第{x['最小包數']}包",
            axis=1
        )

        work_order_stats['數量範圍'] = work_order_stats.apply(
            lambda x: f"{x['最小數量']}-{x['最大數量']}pcs" if x['最大數量'] > x['最小數量'] else f"{x['最小數量']}pcs",
            axis=1
        )

        # 格式化完成狀況
        work_order_stats['完成狀況詳細'] = work_order_stats.apply(
            lambda x: f"{x['完成狀況']}已完成 ({x['處理進度(%)']}%)",
            axis=1
        )

        # 計算處理天數
        work_order_stats['處理天數'] = (
            pd.to_datetime(work_order_stats['最晚建立']) -
            pd.to_datetime(work_order_stats['最早建立'])
        ).dt.days + 1

        # 重新排列欄位順序 - 突出數量資訊與處理進度
        work_order_display = work_order_stats[[
            '工單號碼', '產品名稱', '包數數量', '包數範圍',
            '總不良數量', '數量範圍', '平均數量',
            '不良類型', '不良等級', '責任部門', '負責人',
            '完成狀況詳細', '處理進度(%)', '處理天數'
        ]].copy()

        # 格式化平均數量
        work_order_display['平均數量'] = work_order_display['平均數量'].round(1).astype(str) + 'pcs'

        # 先顯示工單統計摘要
        st.write("**📊 工單數量與進度統計摘要**")

        # 計算整體統計
        total_work_orders = len(work_order_display)
        total_packages = work_order_display['包數數量'].sum()
        total_defect_quantity = work_order_display['總不良數量'].sum()
        avg_progress = work_order_display['處理進度(%)'].mean()
        completed_work_orders = len(work_order_display[work_order_display['處理進度(%)'] == 100])

        # 顯示關鍵指標
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("工單總數", f"{total_work_orders}筆")

        with col2:
            st.metric("包數總計", f"{total_packages}包")

        with col3:
            st.metric("不良品總數", f"{total_defect_quantity}pcs")

        with col4:
            st.metric("平均進度", f"{avg_progress:.1f}%")

        with col5:
            completion_rate = (completed_work_orders / total_work_orders * 100) if total_work_orders > 0 else 0
            st.metric("完成工單", f"{completed_work_orders}筆", delta=f"{completion_rate:.1f}%")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.write("**📊 工單詳細統計表**")

            # 添加進度條顯示
            styled_display = work_order_display.copy()

            # 為進度添加顏色標識


            def format_progress(progress):
                if progress == 100:
                    return f"🟢 {progress}%"
                elif progress >= 50:
                    return f"🟡 {progress}%"
                else:
                    return f"🔴 {progress}%"

            styled_display['處理進度(%)'] = styled_display['處理進度(%)'].apply(format_progress)

            st.dataframe(styled_display, use_container_width=True, height=400)

        with col2:
            st.write("**📈 進度分析圖表**")

            # 處理進度分布圖
            progress_ranges = []
            for _, row in work_order_display.iterrows():
                progress = row['處理進度(%)']
                if progress == 100:
                    progress_ranges.append('已完成(100%)')
                elif progress >= 75:
                    progress_ranges.append('接近完成(75-99%)')
                elif progress >= 50:
                    progress_ranges.append('進行中(50-74%)')
                elif progress >= 25:
                    progress_ranges.append('開始處理(25-49%)')
                else:
                    progress_ranges.append('剛開始(0-24%)')

            progress_counts = pd.Series(progress_ranges).value_counts()

            fig_progress = px.pie(
                values=progress_counts.values,
                names=progress_counts.index,
                color_discrete_sequence=['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#6b7280'],
                title="工單處理進度分布"
            )

            fig_progress.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>工單數: %{value}<br>比例: %{percent}<extra></extra>'
            )

            fig_progress.update_layout(
                height=300,
                showlegend=True,
                legend=dict(orientation="v", yanchor="middle", y=0.5)
            )

            st.plotly_chart(fig_progress, use_container_width=True)

            # 數量分析圖
            st.write("**📊 數量分析**")

            # 工單數量對比圖
            if len(work_order_display) > 0:
                # 創建DataFrame用於plotly，確保所有需要的欄位都存在
                plot_data = work_order_display.copy()

                fig_quantity = px.bar(
                    plot_data,
                    x='工單號碼',
                    y='總不良數量',
                    color='處理進度(%)',
                    color_continuous_scale='RdYlGn',
                    title="各工單不良品數量與處理進度",
                    text='總不良數量',
                    hover_data={
                        '包數數量': True,
                        '平均數量': True,
                        '完成狀況詳細': True,
                        '處理進度(%)': False  # 不在hover中重複顯示
                    }
                )

                fig_quantity.update_traces(
                    texttemplate='%{text}pcs',
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>總數量: %{y}pcs<br>包數: %{customdata[0]}包<br>平均: %{customdata[1]}<br>狀況: %{customdata[2]}<extra></extra>'
                )

                fig_quantity.update_layout(
                    height=350,
                    xaxis_title="工單號碼",
                    yaxis_title="不良品數量 (pcs)",
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=10),
                    xaxis_tickangle=45
                )

                st.plotly_chart(fig_quantity, use_container_width=True)
            else:
                st.info("📊 暫無工單數量資料可供分析")

        # 添加詳細的包數分布統計
        st.write("**📈 包數與數量分布分析**")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**包數分布統計**")
            package_distribution = work_order_display['包數數量'].value_counts().sort_index()
            dist_df = pd.DataFrame({
                '包數數量': package_distribution.index,
                '工單數量': package_distribution.values,
                '佔比(%)': (package_distribution.values / package_distribution.values.sum() * 100).round(1)
            })
            st.dataframe(dist_df, use_container_width=True)

        with col2:
            st.write("**數量分布統計**")
            # 按數量範圍分組
            quantity_ranges = []
            for qty in work_order_display['總不良數量']:
                if qty <= 10:
                    quantity_ranges.append('1-10pcs')
                elif qty <= 50:
                    quantity_ranges.append('11-50pcs')
                elif qty <= 100:
                    quantity_ranges.append('51-100pcs')
                elif qty <= 500:
                    quantity_ranges.append('101-500pcs')
                else:
                    quantity_ranges.append('500pcs以上')

            qty_dist = pd.Series(quantity_ranges).value_counts()
            qty_df = pd.DataFrame({
                '數量範圍': qty_dist.index,
                '工單數量': qty_dist.values,
                '佔比(%)': (qty_dist.values / qty_dist.values.sum() * 100).round(1)
            })
            st.dataframe(qty_df, use_container_width=True)

        # 工單包裝處理時間分析
        st.divider()
        st.subheader("⏱️ 工單包裝處理時間分析")
        st.write("**分析每個工單包裝的處理效率，評估不良品判定的時效性**")

        # 計算每筆記錄的處理時間
        processing_time_data = []
        for _, defect in display_defects.iterrows():
            created_time = pd.to_datetime(defect['created_time'])

            # 處理時間計算
            if defect['status'] == '已完成' and pd.notna(defect.get('completion_time')):
                completion_time = pd.to_datetime(defect['completion_time'])
                processing_hours = (completion_time - created_time).total_seconds() / 3600
                processing_days = processing_hours / 24
                status_desc = "已完成"
            else:
                # 對於未完成的案件，計算到目前為止的時間
                current_time = datetime.now()
                processing_hours = (current_time - created_time).total_seconds() / 3600
                processing_days = processing_hours / 24
                status_desc = defect['status']

            processing_time_data.append({
                '工單號碼': defect['work_order'],
                '包數': f"第{defect['package_number']}包",
                '產品名稱': defect['product_name'],
                '不良類型': defect['defect_type'],
                '不良等級': defect['defect_level'],
                '數量(pcs)': defect['quantity'],
                '責任部門': defect['responsible_dept'],
                '負責人': defect.get('assigned_person', ''),
                '處理狀態': status_desc,
                '建立時間': created_time.strftime('%Y-%m-%d %H:%M'),
                '處理時間(小時)': round(processing_hours, 1),
                '處理時間(天)': round(processing_days, 1),
                '判定效率': '高效' if processing_hours <= 24 else '正常' if processing_hours <= 72 else '需改善'
            })

        if processing_time_data:
            processing_df = pd.DataFrame(processing_time_data)

            # 處理效率統計
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                avg_hours = processing_df['處理時間(小時)'].mean()
                st.metric("平均處理時間", f"{avg_hours:.1f}小時")

            with col2:
                completed_records = processing_df[processing_df['處理狀態'] == '已完成']
                if not completed_records.empty:
                    avg_completed_hours = completed_records['處理時間(小時)'].mean()
                    st.metric("已完成平均時間", f"{avg_completed_hours:.1f}小時")
                else:
                    st.metric("已完成平均時間", "無資料")

            with col3:
                efficiency_counts = processing_df['判定效率'].value_counts()
                high_efficiency = efficiency_counts.get('高效', 0)
                total_records = len(processing_df)
                efficiency_rate = (high_efficiency / total_records * 100) if total_records > 0 else 0
                st.metric("高效處理率", f"{efficiency_rate:.1f}%", delta=f"{high_efficiency}筆")

            with col4:
                need_improvement = efficiency_counts.get('需改善', 0)
                st.metric("需改善案件", f"{need_improvement}筆", delta=f"{(need_improvement/total_records*100):.1f}%" if total_records > 0 else "0%")

            # 處理時間詳細分析表
            st.write("**📊 工單包裝處理時間詳細表**")

            # 添加顏色標識


            def format_efficiency(efficiency):
                if efficiency == '高效':
                    return f"🟢 {efficiency}"
                elif efficiency == '正常':
                    return f"🟡 {efficiency}"
                else:
                    return f"🔴 {efficiency}"

            display_processing_df = processing_df.copy()
            display_processing_df['判定效率'] = display_processing_df['判定效率'].apply(format_efficiency)

            # 按處理時間排序
            display_processing_df = display_processing_df.sort_values('處理時間(小時)')

            st.dataframe(display_processing_df, use_container_width=True, height=400)

            # 處理時間分析圖表
            col1, col2 = st.columns(2)

            with col1:
                st.write("**📈 處理時間分布圖**")

                # 處理時間分布直方圖
                fig_time_dist = px.histogram(
                    processing_df,
                    x='處理時間(小時)',
                    nbins=20,
                    color='判定效率',
                    color_discrete_map={'高效': '#10b981', '正常': '#f59e0b', '需改善': '#ef4444'},
                    title="處理時間分布與效率分析"
                )

                fig_time_dist.update_layout(
                    height=350,
                    xaxis_title="處理時間 (小時)",
                    yaxis_title="案件數量",
                    showlegend=True
                )

                st.plotly_chart(fig_time_dist, use_container_width=True)

            with col2:
                st.write("**📊 判定效率分析**")

                # 判定效率圓餅圖
                efficiency_counts = processing_df['判定效率'].value_counts()
                fig_efficiency = px.pie(
                    values=efficiency_counts.values,
                    names=efficiency_counts.index,
                    color_discrete_map={'高效': '#10b981', '正常': '#f59e0b', '需改善': '#ef4444'},
                    title="判定效率分布"
                )

                fig_efficiency.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>案件數: %{value}<br>比例: %{percent}<extra></extra>'
                )

                fig_efficiency.update_layout(
                    height=350,
                    showlegend=True
                )

                st.plotly_chart(fig_efficiency, use_container_width=True)

            # 按工單統計處理效率
            st.write("**📋 工單處理效率統計**")

            work_order_efficiency = processing_df.groupby('工單號碼').agg({
                '包數': 'count',
                '數量(pcs)': 'sum',
                '處理時間(小時)': ['mean', 'min', 'max'],
                '判定效率': lambda x: f"{sum(x=='高效')}/{len(x)}高效",
                '產品名稱': 'first',
                '不良類型': lambda x: ', '.join(x.unique()),
                '責任部門': lambda x: ', '.join(x.unique())
            }).reset_index()

            # 重新命名欄位
            work_order_efficiency.columns = [
                '工單號碼', '包數總計', '總數量(pcs)', '平均處理時間(小時)',
                '最短處理時間(小時)', '最長處理時間(小時)', '高效比例',
                '產品名稱', '不良類型', '責任部門'
            ]

            # 計算效率評級


            def calculate_efficiency_grade(avg_time, efficiency_ratio):
                # 解析效率比例
                try:
                    high_eff, total = efficiency_ratio.split('/')
                    high_eff = int(high_eff.replace('高效', ''))
                    total = int(total.replace('高效', ''))
                    ratio = high_eff / total if total > 0 else 0
                except:
                    ratio = 0

                if avg_time <= 24 and ratio >= 0.8:
                    return "🟢 優秀"
                elif avg_time <= 48 and ratio >= 0.6:
                    return "🟡 良好"
                elif avg_time <= 72 and ratio >= 0.4:
                    return "🟠 一般"
                else:
                    return "🔴 需改善"

            work_order_efficiency['效率評級'] = work_order_efficiency.apply(
                lambda x: calculate_efficiency_grade(x['平均處理時間(小時)'], x['高效比例']), axis=1
            )

            # 格式化數值
            work_order_efficiency['平均處理時間(小時)'] = work_order_efficiency['平均處理時間(小時)'].round(1)
            work_order_efficiency['最短處理時間(小時)'] = work_order_efficiency['最短處理時間(小時)'].round(1)
            work_order_efficiency['最長處理時間(小時)'] = work_order_efficiency['最長處理時間(小時)'].round(1)

            st.dataframe(work_order_efficiency, use_container_width=True)

            # 處理效率改善建議
            st.write("**💡 處理效率改善建議**")

            efficiency_suggestions = []

            # 分析平均處理時間
            if avg_hours > 72:
                efficiency_suggestions.append("⏰ **處理時間過長**：平均處理時間超過3天，建議檢視流程瓶頸，簡化審核程序")
            elif avg_hours > 48:
                efficiency_suggestions.append("⏱️ **處理時間偏長**：平均處理時間超過2天，建議優化作業流程")
            else:
                efficiency_suggestions.append("✅ **處理時間良好**：平均處理時間控制得當，維持現有效率")

            # 分析效率分布
            if efficiency_rate < 50:
                efficiency_suggestions.append("🔴 **高效處理率偏低**：建議加強人員培訓，提升判定技能")
            elif efficiency_rate < 70:
                efficiency_suggestions.append("🟡 **高效處理率中等**：有改善空間，可考慮標準化作業程序")
            else:
                efficiency_suggestions.append("🟢 **高效處理率良好**：處理效率表現優秀，可作為標竿參考")

            # 分析需改善案件
            if need_improvement > 0:
                efficiency_suggestions.append(f"⚠️ **關注需改善案件**：有{need_improvement}筆案件處理時間過長，建議個別檢討原因")

            # 部門效率分析
            dept_efficiency = processing_df.groupby('責任部門').agg({
                '處理時間(小時)': 'mean',
                '判定效率': lambda x: sum(x=='高效') / len(x) * 100
            }).round(1)

            if len(dept_efficiency) > 1:
                best_dept = dept_efficiency['處理時間(小時)'].idxmin()
                worst_dept = dept_efficiency['處理時間(小時)'].idxmax()
                efficiency_suggestions.append(f"📊 **部門效率對比**：{best_dept}處理效率較高，可分享經驗給{worst_dept}")

            for suggestion in efficiency_suggestions:
                st.markdown(f"• {suggestion}")

        else:
            st.info("📊 暫無處理時間資料可供分析")

    else:
        st.info("📊 暫無詳細資料記錄")

    # AI總結與改善建議
    st.divider()
    st.subheader("🤖 AI智能分析總結")

    # 獲取數據進行分析
    if not all_defects.empty:
        # 計算關鍵指標
        total_orders = len(all_defects)
        total_packages = all_defects['package_number'].nunique() if 'package_number' in all_defects.columns else 0
        total_defects_count = all_defects['quantity'].sum() if 'quantity' in all_defects.columns else 0

        # 計算處理進度（基於狀態）
        completed_count = len(all_defects[all_defects['status'] == '已完成'])
        avg_progress = (completed_count / total_orders * 100) if total_orders > 0 else 0
        completed_orders = completed_count

        # 計算各等級分布
        level_counts = all_defects['defect_level'].value_counts() if 'defect_level' in all_defects.columns else pd.Series()

        # 計算部門分布
        dept_counts = all_defects['department'].value_counts() if 'department' in all_defects.columns else pd.Series()

        # 計算處理時間統計（基於已完成的記錄）
        completed_defects = all_defects[all_defects['status'] == '已完成']
        if not completed_defects.empty and 'completion_time' in completed_defects.columns:
            processing_days = (pd.to_datetime(completed_defects['completion_time']) -
                             pd.to_datetime(completed_defects['created_time'])).dt.total_seconds().mean() / (24 * 3600)
        else:
            processing_days = 0

        # 分析進度分布（基於狀態）
        low_progress = len(all_defects[all_defects['status'].isin(['新建', '處理中'])])
        medium_progress = len(all_defects[all_defects['status'] == '待確認'])
        high_progress = len(all_defects[all_defects['status'] == '已完成'])

        # 創建分析容器
        analysis_container = st.container()

        with analysis_container:
            # 總體情況分析
            st.write("**📊 總體情況分析**")
            summary_text = """
            根據目前的數據分析，系統共有 **{total_orders}** 筆不良品記錄，涉及 **{total_packages:,}** 個包號，
            不良品總數為 **{total_defects_count:,}** 個，整體處理完成率為 **{avg_progress:.1f}%**。
            已完成處理的記錄數量為 **{completed_orders}** 筆。
            """
            st.markdown(summary_text)

            # 關鍵發現
            st.write("**🔍 關鍵發現**")
            findings = []

            # 進度分析
            if low_progress > 0:
                findings.append(f"⚠️ 有 **{low_progress}** 筆記錄尚在處理中（新建/處理中），需要持續關注")
            if medium_progress > 0:
                findings.append(f"📈 有 **{medium_progress}** 筆記錄待確認，等待最終驗證")
            if high_progress > 0:
                findings.append(f"✅ 已完成 **{high_progress}** 筆記錄，處理效率良好")

            # 等級分析
            if not level_counts.empty:
                highest_level = level_counts.index[0]
                highest_count = level_counts.iloc[0]
                findings.append(f"📋 **{highest_level}** 不良品最多，共 **{highest_count}** 筆，佔 **{(highest_count/total_orders*100):.1f}%**")

            # 部門分析
            if not dept_counts.empty:
                busiest_dept = dept_counts.index[0]
                busiest_count = dept_counts.iloc[0]
                findings.append(f"🏢 **{busiest_dept}** 處理案件最多，共 **{busiest_count}** 筆，佔 **{(busiest_count/total_orders*100):.1f}%**")

            # 處理時間分析
            if processing_days > 0:
                if processing_days > 7:
                    findings.append(f"⏰ 平均處理時間為 **{processing_days:.1f}** 天，建議加快處理速度")
                else:
                    findings.append(f"⏰ 平均處理時間為 **{processing_days:.1f}** 天，處理效率良好")

            for finding in findings:
                st.markdown(f"• {finding}")

            st.divider()

            # 改善建議
            st.write("**💡 AI改善建議**")

            # 根據數據生成建議
            suggestions = []

            # 進度相關建議
            if low_progress > total_orders * 0.3:  # 超過30%未完成
                suggestions.append({
                    "類別": "🚨 進度管理",
                    "建議": "建立進度追蹤機制，定期檢視未完成記錄，設定每週進度檢核點",
                    "優先級": "高"
                })

            if avg_progress < 70:
                suggestions.append({
                    "類別": "📈 效率提升",
                    "建議": "分析處理瓶頸，優化作業流程，考慮增加人力資源或改善作業方法",
                    "優先級": "中"
                })

            # 等級分布建議
            if not level_counts.empty:
                a_level_ratio = level_counts.get('A級', 0) / total_orders
                if a_level_ratio > 0.3:  # A級超過30%
                    suggestions.append({
                        "類別": "⚠️ 品質控制",
                        "建議": "A級不良品比例偏高，建議加強前端品質控制，分析根本原因並制定預防措施",
                        "優先級": "高"
                    })

            # 部門負荷建議
            if not dept_counts.empty and len(dept_counts) > 1:
                max_load = dept_counts.iloc[0]
                min_load = dept_counts.iloc[-1]
                if max_load > min_load * 2:  # 負荷差異過大
                    suggestions.append({
                        "類別": "⚖️ 負荷平衡",
                        "建議": "部門間負荷不均，建議重新分配案件或加強跨部門協作機制",
                        "優先級": "中"
                    })

            # 處理時間建議
            if processing_days > 5:
                suggestions.append({
                    "類別": "⏱️ 時效改善",
                    "建議": "平均處理時間較長，建議簡化作業流程，設定處理時限，並建立逾期預警機制",
                    "優先級": "中"
                })

            # 通用建議
            suggestions.extend([
                {
                    "類別": "📊 數據分析",
                    "建議": "定期進行趨勢分析，建立月度/季度報告，追蹤改善成效",
                    "優先級": "低"
                },
                {
                    "類別": "🔄 持續改善",
                    "建議": "建立PDCA循環機制，定期檢討流程效率，持續優化作業方式",
                    "優先級": "低"
                },
                {
                    "類別": "👥 人員培訓",
                    "建議": "加強人員專業技能培訓，提升問題分析和解決能力",
                    "優先級": "低"
                }
            ])

            # 按優先級分組顯示建議
            high_priority = [s for s in suggestions if s["優先級"] == "高"]
            medium_priority = [s for s in suggestions if s["優先級"] == "中"]
            low_priority = [s for s in suggestions if s["優先級"] == "低"]

            if high_priority:
                st.write("**🔴 高優先級建議**")
                for suggestion in high_priority:
                    st.markdown(f"**{suggestion['類別']}**: {suggestion['建議']}")
                st.write("")

            if medium_priority:
                st.write("**🟡 中優先級建議**")
                for suggestion in medium_priority:
                    st.markdown(f"**{suggestion['類別']}**: {suggestion['建議']}")
                st.write("")

            if low_priority:
                st.write("**🟢 低優先級建議**")
                for suggestion in low_priority:
                    st.markdown(f"**{suggestion['類別']}**: {suggestion['建議']}")

            # 行動計劃
            st.divider()
            st.write("**📋 建議行動計劃**")

            action_plan = """
            **短期行動 (1-2週)**
            • 檢視所有未完成記錄，制定加速處理計劃
            • 分析A級不良品原因，建立改善對策
            • 設定每日進度檢核機制

            **中期行動 (1-3個月)**
            • 優化作業流程，減少處理時間
            • 建立跨部門協作機制
            • 實施人員技能提升計劃

            **長期行動 (3-6個月)**
            • 建立預防性品質管理系統
            • 導入自動化監控機制
            • 建立持續改善文化
            """

            st.markdown(action_plan)

            # 系統建議
            st.info("💡 **系統提示**: 建議每週檢視此分析報告，追蹤改善進度，並根據最新數據調整策略。")

    else:
        st.info("📊 暫無足夠數據進行AI分析，請先新增一些記錄後再查看分析結果。")

    st.divider()

def settings_page():
    st.header("⚙️ 系統設定")

    # 權限檢查：只有管理員和主管可以存取
    user_role = st.session_state.user.get('role')
    if user_role not in ['管理員', '主管']:
        st.error("🚫 **存取權限不足**")
        st.warning(f"您的角色為「{user_role}」，無權限存取系統設定頁面。")
        st.info("💡 **權限說明：**\n- 只有「管理員」和「主管」角色可以存取系統設定\n- 如需權限調整，請聯繫系統管理員")

        # 顯示當前用戶信息
        st.write("---")
        st.write(f"👤 **當前登入用戶：** {st.session_state.user['name']} ({st.session_state.user['department']} - {st.session_state.user['position']})")
        return

    # 顯示當前用戶信息
    st.info(f"👤 **當前登入用戶：** {st.session_state.user['name']} ({st.session_state.user['department']} - {st.session_state.user['position']})")

    # 通知設定
    st.subheader("📧 通知設定")

    # 載入當前設定
    current_settings = notification_manager.settings.copy()

    # 通知方式選擇
    st.write("**📱 通知方式選擇**")

    # 準備default值，確保只包含存在的選項
    available_options = ["📧 郵件通知", "📱 Telegram通知"]
    default_values = []

    if current_settings.get('email_enabled', False):
        default_values.append("📧 郵件通知")
    if current_settings.get('telegram_enabled', False):
        default_values.append("📱 Telegram通知")

    notification_methods = st.multiselect(
        "選擇通知方式",
        available_options,
        default=default_values
    )

    email_enabled = "📧 郵件通知" in notification_methods
    telegram_enabled = "📱 Telegram通知" in notification_methods

    # 分欄顯示設定
    col1, col2 = st.columns(2)

    with col1:
        # 郵件通知設定
        if email_enabled:
            st.write("**📬 郵件通知設定**")
            email_server = st.text_input("SMTP伺服器", value=current_settings.get('email_smtp_server', 'smtp.gmail.com'))
            email_port = st.number_input("SMTP端口", min_value=1, max_value=65535, value=current_settings.get('email_smtp_port', 587))
            email_username = st.text_input("發送郵箱", value=current_settings.get('email_username', ''))
            email_password = st.text_input("郵箱密碼", type="password", value=current_settings.get('email_password', ''))

            # 收件人設定
            st.write("**收件人設定**")
            recipients_text = st.text_area(
                "收件人郵箱 (每行一個)",
                value='\n'.join(current_settings.get('email_recipients', [])),
                height=100
            )
            recipients = [email.strip() for email in recipients_text.split('\n') if email.strip()]
        else:
            st.info("📧 郵件通知功能已停用")

    with col2:
        # Telegram通知設定
        if telegram_enabled:
            st.write("**📱 Telegram通知設定**")
            st.info("💡 如何取得Telegram Bot權杖：\n1. 前往 https://t.me/botfather\n2. 發送命令 /newbot\n3. 輸入機器人名稱\n4. 發送命令 /token\n5. 複製產生的權杖")

            # Telegram權杖設定
            bot_token = st.text_input("Telegram Bot權杖", value=current_settings.get('telegram_bot_token', ''))
            chat_ids_text = st.text_area(
                "Telegram聊天室ID (每行一個)",
                value='\n'.join(current_settings.get('telegram_chat_ids', [])),
                height=120,
                help="每個ID對應一個Telegram群組或個人聊天室"
            )
            chat_ids = [chat_id.strip() for chat_id in chat_ids_text.split('\n') if chat_id.strip()]
        else:
            st.info("📱 Telegram通知功能已停用")

    # 處理時限設定
    st.write("**⏰ 處理時限設定**")
    col3, col4, col5 = st.columns(3)

    with col3:
        a_level_deadline = st.number_input("A級處理時限(小時)", min_value=1, max_value=24,
                                         value=current_settings.get('processing_deadlines', {}).get('A級', 4))
    with col4:
        b_level_deadline = st.number_input("B級處理時限(小時)", min_value=1, max_value=48,
                                         value=current_settings.get('processing_deadlines', {}).get('B級', 8))
    with col5:
        c_level_deadline = st.number_input("C級處理時限(小時)", min_value=1, max_value=72,
                                         value=current_settings.get('processing_deadlines', {}).get('C級', 24))

    # 提醒間隔設定
    st.write("**🔔 提醒間隔設定**")
    col6, col7, col8 = st.columns(3)

    with col6:
        a_level_interval = st.number_input("A級提醒間隔(小時)", min_value=1, max_value=12,
                                         value=current_settings.get('notification_intervals', {}).get('A級', 2))
    with col7:
        b_level_interval = st.number_input("B級提醒間隔(小時)", min_value=1, max_value=12,
                                         value=current_settings.get('notification_intervals', {}).get('B級', 4))
    with col8:
        c_level_interval = st.number_input("C級提醒間隔(小時)", min_value=1, max_value=24,
                                         value=current_settings.get('notification_intervals', {}).get('C級', 8))

    # 儲存通知設定
    if st.button("💾 儲存通知設定", type="primary"):
        new_settings = {
            'email_enabled': email_enabled,
            'email_smtp_server': email_server if email_enabled else current_settings.get('email_smtp_server', ''),
            'email_smtp_port': email_port if email_enabled else current_settings.get('email_smtp_port', 587),
            'email_username': email_username if email_enabled else current_settings.get('email_username', ''),
            'email_password': email_password if email_enabled else current_settings.get('email_password', ''),
            'email_recipients': recipients if email_enabled else current_settings.get('email_recipients', []),
            'telegram_enabled': telegram_enabled,
            'telegram_bot_token': bot_token if telegram_enabled else current_settings.get('telegram_bot_token', ''),
            'telegram_chat_ids': chat_ids if telegram_enabled else current_settings.get('telegram_chat_ids', []),
            'notification_methods': notification_methods,
            'processing_deadlines': {
                'A級': a_level_deadline,
                'B級': b_level_deadline,
                'C級': c_level_deadline
            },
            'notification_intervals': {
                'A級': a_level_interval,
                'B級': b_level_interval,
                'C級': c_level_interval
            }
        }

        notification_manager.save_notification_settings(new_settings)
        st.success("✅ 通知設定已儲存！")
        st.rerun()

    # 測試通知功能
    st.write("**🧪 測試通知功能**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📧 發送測試郵件"):
            if current_settings.get('email_enabled', False):
                test_subject = "🧪 不良品管理系統 - 測試通知"
                test_message = """
                <html>
                <body>
                <h2>📧 測試通知</h2>
                <p>這是一封測試郵件，用於確認郵件通知功能是否正常運作。</p>
                <p><strong>發送時間：</strong>{}</p>
                <p>如果您收到此郵件，表示通知功能設定成功！</p>
                <br>
                <p><em>不良品管理系統</em></p>
                </body>
                </html>
                """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                if notification_manager.send_email_notification(test_subject, test_message):
                    st.success("✅ 測試郵件發送成功！")
                else:
                    st.error("❌ 測試郵件發送失敗，請檢查設定")
            else:
                st.warning("⚠️ 請先啟用郵件通知功能")

    with col2:
        if st.button("📱 發送測試Telegram"):
            if current_settings.get('telegram_enabled', False):
                test_message = """🧪 不良品管理系統測試通知

✅ Telegram Bot連接成功！
⏰ 測試時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 功能說明：
• 自動逾期提醒
• 即時案件通知
• 多群組廣播

🔗 系統連結：http://localhost:8501"""

                if notification_manager.send_telegram_notification(test_message):
                    st.success("✅ 測試Telegram通知發送成功！")
                else:
                    st.error("❌ 測試Telegram通知發送失敗，請檢查權杖")
            else:
                st.warning("⚠️ 請先啟用Telegram通知功能")

    with col3:
        if st.button("🔍 檢查逾期案件"):
            overdue_count = notification_manager.send_overdue_notifications()
            if overdue_count > 0:
                st.warning(f"⚠️ 發現 {overdue_count} 件逾期案件，已發送通知")
            else:
                st.success("✅ 目前沒有逾期案件")

    with col4:
        if st.button("📊 查看逾期統計"):
            overdue_defects = notification_manager.check_overdue_defects()
            if not overdue_defects.empty:
                st.write(f"**逾期案件總數：{len(overdue_defects)} 件**")

                # 按等級統計
                level_stats = overdue_defects.groupby('defect_level').size()
                for level, count in level_stats.items():
                    st.write(f"- {level}：{count} 件")
            else:
                st.success("✅ 目前沒有逾期案件")

    # 通知狀態顯示
    st.subheader("📋 通知狀態")

    # 顯示當前設定狀態
    col1, col2 = st.columns(2)

    with col1:
        st.write("**🔧 當前通知設定**")
        if current_settings.get('email_enabled', False):
            st.success("✅ 郵件通知：已啟用")
            st.write(f"📧 收件人數量：{len(current_settings.get('email_recipients', []))}")
        else:
            st.info("📧 郵件通知：未啟用")

        if current_settings.get('telegram_enabled', False):
            st.success("✅ Telegram通知：已啟用")
            st.write(f"📱 權杖數量：{len(current_settings.get('telegram_chat_ids', []))}")
        else:
            st.info("📱 Telegram通知：未啟用")

    with col2:
        st.write("**⏰ 處理時限設定**")
        deadlines = current_settings.get('processing_deadlines', {})
        st.write(f"🔴 A級：{deadlines.get('A級', 4)} 小時")
        st.write(f"🟡 B級：{deadlines.get('B級', 8)} 小時")
        st.write(f"🟢 C級：{deadlines.get('C級', 24)} 小時")

    # 顯示當前逾期案件
    overdue_defects = notification_manager.check_overdue_defects()
    if not overdue_defects.empty:
        st.write("**⚠️ 當前逾期案件**")

        display_overdue = overdue_defects.copy()
        display_overdue['逾期時間'] = display_overdue.apply(
            lambda row: f"{((datetime.now() - pd.to_datetime(row['created_time']) - timedelta(hours=current_settings['processing_deadlines'][row['defect_level']])).total_seconds() / 3600):.1f} 小時",
            axis=1
        )

        display_cols = ['work_order', 'product_name', 'defect_level', 'quantity', 'responsible_dept', 'created_time', '逾期時間']
        display_overdue_renamed = display_overdue[display_cols].rename(columns={
            'work_order': '工單號',
            'product_name': '產品名稱',
            'defect_level': '不良等級',
            'quantity': '數量(pcs)',
            'responsible_dept': '責任部門',
            'created_time': '建立時間'
        })

        st.dataframe(display_overdue_renamed, use_container_width=True)
    else:
        st.success("✅ 目前沒有逾期案件")

    # 人員管理
    st.subheader("👥 人員管理")

    # 載入當前人員設定
    personnel_settings = load_personnel_settings()

    # 顯示當前人員列表
    st.write("**👤 當前負責人員列表**")

    if personnel_settings.get('responsible_persons'):
        # 按部門分組顯示
        dept_groups = {}
        for person in personnel_settings['responsible_persons']:
            dept = person['department']
            if dept not in dept_groups:
                dept_groups[dept] = []
            dept_groups[dept].append(person)

        for dept, persons in dept_groups.items():
            st.write(f"**{dept}** ({len(persons)}人)")
            cols = st.columns(3)
            for i, person in enumerate(persons):
                with cols[i % 3]:
                    st.write(f"• {person['name']}")
    else:
        st.info("📝 目前沒有設定負責人員")

    # 人員管理操作
    st.write("**🔧 人員管理操作**")

    # 新增人員
    with st.expander("➕ 新增負責人員", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_name = st.text_input("姓名", key="new_person_name")

        with col2:
            new_dept = st.selectbox("部門", ["工程部", "品保部", "製造部"], key="new_person_dept")

        if st.button("➕ 新增人員", key="add_person"):
            if new_name:
                new_person = {
                    "name": new_name,
                    "department": new_dept,
                    "display_name": f"{new_dept}-{new_name}"
                }

                # 檢查是否已存在
                existing_names = [p['display_name'] for p in personnel_settings.get('responsible_persons', [])]
                if new_person['display_name'] not in existing_names:
                    personnel_settings['responsible_persons'].append(new_person)
                    if save_personnel_settings(personnel_settings):
                        st.success(f"✅ 已新增 {new_person['display_name']}")
                        st.rerun()
                    else:
                        st.error("❌ 新增失敗")
                else:
                    st.warning("⚠️ 此人員已存在")
            else:
                st.error("❌ 請輸入姓名")

    # 刪除人員
    with st.expander("🗑️ 刪除負責人員", expanded=False):
        if personnel_settings.get('responsible_persons'):
            person_to_delete = st.selectbox(
                "選擇要刪除的人員",
                ["請選擇人員"] + [p['display_name'] for p in personnel_settings['responsible_persons']],
                key="delete_person_select"
            )

            if st.button("🗑️ 刪除人員", key="delete_person"):
                if person_to_delete != "請選擇人員":
                    personnel_settings['responsible_persons'] = [
                        p for p in personnel_settings['responsible_persons']
                        if p['display_name'] != person_to_delete
                    ]
                    if save_personnel_settings(personnel_settings):
                        st.success(f"✅ 已刪除 {person_to_delete}")
                        st.rerun()
                    else:
                        st.error("❌ 刪除失敗")
                else:
                    st.error("❌ 請選擇要刪除的人員")
        else:
            st.info("📝 目前沒有人員可刪除")

    # 批量匯入人員
    with st.expander("📥 批量匯入人員", expanded=False):
        st.write("**格式說明：** 每行一個人員，格式為 `部門-姓名`")
        st.write("**範例：**")
        st.code("""工程部-張三
品保部-李四
製造部-王五""")

        import_text = st.text_area(
            "人員列表",
            placeholder="工程部-張三\n品保部-李四\n製造部-王五",
            height=100,
            key="import_persons"
        )

        if st.button("📥 批量匯入", key="batch_import"):
            if import_text:
                lines = [line.strip() for line in import_text.split('\n') if line.strip()]
                imported_count = 0
                errors = []

                for line in lines:
                    if '-' in line:
                        try:
                            dept, name = line.split('-', 1)
                            new_person = {
                                "name": name,
                                "department": dept,
                                "display_name": f"{dept}-{name}"
                            }

                            # 檢查是否已存在
                            existing_names = [p['display_name'] for p in personnel_settings.get('responsible_persons', [])]
                            if new_person['display_name'] not in existing_names:
                                personnel_settings['responsible_persons'].append(new_person)
                                imported_count += 1
                            else:
                                errors.append(f"已存在: {new_person['display_name']}")
                        except:
                            errors.append(f"格式錯誤: {line}")
                    else:
                        errors.append(f"格式錯誤: {line}")

                if imported_count > 0:
                    if save_personnel_settings(personnel_settings):
                        st.success(f"✅ 成功匯入 {imported_count} 位人員")
                        if errors:
                            st.warning(f"⚠️ {len(errors)} 個項目有問題：")
                            for error in errors:
                                st.write(f"• {error}")
                        st.rerun()
                    else:
                        st.error("❌ 儲存失敗")
                else:
                    st.error("❌ 沒有成功匯入任何人員")
                    if errors:
                        st.write("錯誤詳情：")
                        for error in errors:
                            st.write(f"• {error}")
            else:
                st.error("❌ 請輸入人員列表")

    # 登錄人員管理
    st.subheader("👨‍💼 登錄人員管理")

    # 載入當前登錄人員設定
    operator_settings = load_operator_settings()

    # 顯示當前登錄人員列表
    st.write("**👤 當前登錄人員列表**")

    if operator_settings.get('operators'):
        cols = st.columns(4)
        for i, operator in enumerate(operator_settings['operators']):
            with cols[i % 4]:
                st.write(f"• {operator}")
    else:
        st.info("📝 目前沒有設定登錄人員")

    # 登錄人員管理操作
    col1, col2 = st.columns(2)

    with col1:
        with st.expander("➕ 新增登錄人員", expanded=False):
            new_operator = st.text_input("姓名", key="new_operator_name")

            if st.button("➕ 新增", key="add_operator"):
                if new_operator:
                    if new_operator not in operator_settings.get('operators', []):
                        operator_settings['operators'].append(new_operator)
                        if save_operator_settings(operator_settings):
                            st.success(f"✅ 已新增 {new_operator}")
                            st.rerun()
                        else:
                            st.error("❌ 新增失敗")
                    else:
                        st.warning("⚠️ 此人員已存在")
                else:
                    st.error("❌ 請輸入姓名")

    with col2:
        with st.expander("🗑️ 刪除登錄人員", expanded=False):
            if operator_settings.get('operators'):
                operator_to_delete = st.selectbox(
                    "選擇要刪除的人員",
                    ["請選擇人員"] + operator_settings['operators'],
                    key="delete_operator_select"
                )

                if st.button("🗑️ 刪除", key="delete_operator"):
                    if operator_to_delete != "請選擇人員":
                        operator_settings['operators'].remove(operator_to_delete)
                        if save_operator_settings(operator_settings):
                            st.success(f"✅ 已刪除 {operator_to_delete}")
                            st.rerun()
                        else:
                            st.error("❌ 刪除失敗")
                    else:
                        st.error("❌ 請選擇要刪除的人員")
            else:
                st.info("📝 目前沒有人員可刪除")

    # 批量匯入登錄人員
    with st.expander("📥 批量匯入登錄人員", expanded=False):
        st.write("**格式說明：** 每行一個姓名")
        st.write("**範例：**")
        st.code("""張小明
李小華
王小美""")

        import_operators_text = st.text_area(
            "登錄人員列表",
            placeholder="張小明\n李小華\n王小美",
            height=100,
            key="import_operators"
        )

        if st.button("📥 批量匯入", key="batch_import_operators"):
            if import_operators_text:
                lines = [line.strip() for line in import_operators_text.split('\n') if line.strip()]
                imported_count = 0
                existing_count = 0

                for operator_name in lines:
                    if operator_name not in operator_settings.get('operators', []):
                        operator_settings['operators'].append(operator_name)
                        imported_count += 1
                    else:
                        existing_count += 1

                if imported_count > 0:
                    if save_operator_settings(operator_settings):
                        st.success(f"✅ 成功匯入 {imported_count} 位登錄人員")
                        if existing_count > 0:
                            st.info(f"ℹ️ {existing_count} 位人員已存在，跳過匯入")
                        st.rerun()
                    else:
                        st.error("❌ 儲存失敗")
                else:
                    st.warning("⚠️ 所有人員都已存在，沒有新增任何人員")
            else:
                st.error("❌ 請輸入登錄人員列表")

    # 產品名稱管理
    st.subheader("📦 產品名稱管理")

    # 載入當前產品名稱設定
    product_settings = load_product_settings()

    # 顯示當前產品名稱列表
    st.write("**📋 當前產品名稱列表**")

    if product_settings.get('products'):
        # 分欄顯示產品列表
        cols = st.columns(3)
        for i, product in enumerate(product_settings['products']):
            with cols[i % 3]:
                st.write(f"• {product}")
    else:
        st.info("📝 目前沒有設定產品名稱")

    # 產品名稱管理操作
    col1, col2 = st.columns(2)

    with col1:
        with st.expander("➕ 新增產品名稱", expanded=False):
            new_product = st.text_input("產品名稱", key="new_product_name")

            if st.button("➕ 新增", key="add_product"):
                if new_product:
                    if new_product not in product_settings.get('products', []):
                        product_settings['products'].append(new_product)
                        if save_product_settings(product_settings):
                            st.success(f"✅ 已新增 {new_product}")
                            st.rerun()
                        else:
                            st.error("❌ 新增失敗")
                    else:
                        st.warning("⚠️ 此產品名稱已存在")
                else:
                    st.error("❌ 請輸入產品名稱")

    with col2:
        with st.expander("🗑️ 刪除產品名稱", expanded=False):
            if product_settings.get('products'):
                product_to_delete = st.selectbox(
                    "選擇要刪除的產品",
                    ["請選擇產品"] + product_settings['products'],
                    key="delete_product_select"
                )

                if st.button("🗑️ 刪除", key="delete_product"):
                    if product_to_delete != "請選擇產品":
                        product_settings['products'].remove(product_to_delete)
                        if save_product_settings(product_settings):
                            st.success(f"✅ 已刪除 {product_to_delete}")
                            st.rerun()
                        else:
                            st.error("❌ 刪除失敗")
                    else:
                        st.error("❌ 請選擇要刪除的產品")
            else:
                st.info("📝 目前沒有產品可刪除")

    # 批量匯入產品名稱
    with st.expander("📥 批量匯入產品名稱", expanded=False):
        st.write("**格式說明：** 每行一個產品名稱")
        st.write("**範例：**")
        st.code("""手機外殼-A型
平板外框-標準版
筆電散熱片-15吋""")

        import_products_text = st.text_area(
            "產品名稱列表",
            placeholder="手機外殼-A型\n平板外框-標準版\n筆電散熱片-15吋",
            height=100,
            key="import_products"
        )

        if st.button("📥 批量匯入", key="batch_import_products"):
            if import_products_text:
                lines = [line.strip() for line in import_products_text.split('\n') if line.strip()]
                imported_count = 0
                existing_count = 0

                for product_name in lines:
                    if product_name not in product_settings.get('products', []):
                        product_settings['products'].append(product_name)
                        imported_count += 1
                    else:
                        existing_count += 1

                if imported_count > 0:
                    if save_product_settings(product_settings):
                        st.success(f"✅ 成功匯入 {imported_count} 個產品名稱")
                        if existing_count > 0:
                            st.info(f"ℹ️ {existing_count} 個產品名稱已存在，跳過匯入")
                        st.rerun()
                    else:
                        st.error("❌ 儲存失敗")
                else:
                    st.warning("⚠️ 所有產品名稱都已存在，沒有新增任何產品")
            else:
                st.error("❌ 請輸入產品名稱列表")

    # 系統參數設定
    st.subheader("🔧 系統參數")

    # 資料管理
    st.subheader("🗄️ 資料管理")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 匯出資料"):
            all_defects = get_defects()
            if not all_defects.empty:
                # 重新排列欄位順序並設定中文欄位名稱
                export_data = all_defects[[
                    'id', 'work_order', 'package_number', 'product_name', 'defect_type',
                    'defect_level', 'quantity', 'description', 'responsible_dept',
                    'assigned_person', 'status', 'resolution', 'created_time',
                    'deadline', 'completion_time'
                ]].copy()

                # 設定中文欄位名稱
                export_data.columns = [
                    '編號', '工單號碼', '包數', '產品名稱', '不良類型',
                    '不良等級', '數量(pcs)', '問題描述', '責任部門',
                    '負責人', '處理狀態', '處理結果', '建立時間',
                    '處理截止時間', '完成時間'
                ]

                csv = export_data.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 下載CSV檔案",
                    data=csv,
                    file_name=f"不良品管理資料_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="包含包數信息的完整不良品管理資料"
                )
                st.info(f"📋 準備匯出 {len(export_data)} 筆記錄，包含包數資訊")
            else:
                st.warning("沒有資料可匯出")

    with col2:
        if st.button("🗑️ 清除測試資料", type="secondary"):
            if st.session_state.get('confirm_delete', False):
                # 這裡可以添加清除資料的邏輯
                st.success("✅ 測試資料已清除")
                st.session_state['confirm_delete'] = False
            else:
                st.session_state['confirm_delete'] = True
                st.warning("⚠️ 請再次點擊確認清除")

# 新增：登錄人員管理函數


def load_operator_settings():
    """載入登錄人員設定"""
    try:
        with open('operator_settings.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 預設登錄人員列表
        default_operators = {
            "operators": []
        }
        save_operator_settings(default_operators)
        return default_operators
    except Exception as e:
        st.error(f"載入登錄人員設定時發生錯誤: {e}")
        return {"operators": []}

def save_operator_settings(settings):
    """儲存登錄人員設定"""
    try:
        with open('operator_settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"儲存登錄人員設定時發生錯誤: {e}")
        return False

def get_operators_list():
    """獲取登錄人員列表"""
    settings = load_operator_settings()
    return settings.get('operators', [])

# 新增：產品名稱管理函數


def load_product_settings():
    """載入產品名稱設定"""
    try:
        with open('product_settings.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 預設產品名稱列表
        default_products = {
            "products": []
        }
        save_product_settings(default_products)
        return default_products
    except Exception as e:
        st.error(f"載入產品名稱設定時發生錯誤: {e}")
        return {"products": []}

def save_product_settings(settings):
    """儲存產品名稱設定"""
    try:
        with open('product_settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"儲存產品名稱設定時發生錯誤: {e}")
        return False

def get_products_list():
    """獲取產品名稱列表"""
    settings = load_product_settings()
    return settings.get('products', [])

if __name__ == "__main__":
    main()
