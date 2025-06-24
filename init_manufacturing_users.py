#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
製造二部與製造三部用戶初始化腳本
用於創建製造二部和製造三部的預設用戶帳號，以便進行最終簽核
"""

import sqlite3
import hashlib

def create_manufacturing_users():
    """創建製造二部和製造三部的預設用戶"""
    conn = sqlite3.connect('defect_management.db')
    cursor = conn.cursor()
    
    # 製造二部和製造三部的預設用戶
    users_to_create = [
        {
            'username': 'mfg2_manager',
            'password': 'mfg2123',
            'name': '張主管',
            'department': '製造二部',
            'position': '部門主管',
            'role': '主管'
        },
        {
            'username': 'mfg2_dri',
            'password': 'mfg2456',
            'name': '李經理',
            'department': '製造二部',
            'position': 'DRI',
            'role': '主管'
        },
        {
            'username': 'mfg3_manager',
            'password': 'mfg3123',
            'name': '王主管',
            'department': '製造三部',
            'position': '部門主管',
            'role': '主管'
        },
        {
            'username': 'mfg3_dri',
            'password': 'mfg3456',
            'name': '陳經理',
            'department': '製造三部',
            'position': 'DRI',
            'role': '主管'
        }
    ]
    
    created_count = 0
    
    for user in users_to_create:
        # 檢查用戶是否已存在
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (user['username'],))
        if cursor.fetchone()[0] == 0:
            # 加密密碼
            password_hash = hashlib.sha256(user['password'].encode()).hexdigest()
            
            # 創建用戶
            cursor.execute('''
                INSERT INTO users (username, password_hash, name, department, position, role)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user['username'], password_hash, user['name'], user['department'], 
                  user['position'], user['role']))
            
            created_count += 1
            print(f"✅ 創建用戶：{user['name']} ({user['username']}) - {user['department']}")
        else:
            print(f"⚠️ 用戶已存在：{user['username']}")
    
    conn.commit()
    conn.close()
    
    print(f"\n🎉 完成！共創建 {created_count} 個新用戶")
    print("\n📋 登入資訊：")
    for user in users_to_create:
        print(f"  {user['name']} ({user['department']})：")
        print(f"    用戶名：{user['username']}")
        print(f"    密碼：{user['password']}")
        print()

if __name__ == "__main__":
    print("🚀 開始初始化製造二部與製造三部用戶...")
    create_manufacturing_users()
    print("✅ 初始化完成！") 