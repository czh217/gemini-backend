import mysql.connector
from mysql.connector import Error

try:
    connection = mysql.connector.connect(
        host='hopper.proxy.rlwy.net',
        port=53147,
        user='root',
        password='mkZkHWFzNbCYOdGEBBZpOwbqRQfQnWhx',  # 替换为你的 MySQL 密码
        database='railway'
    )

    if connection.is_connected():
        cursor = connection.cursor()

        # 清空表
        cursor.execute('DELETE FROM pdfs')

        # 插入 12 份 PDF
        for i in range(1, 13):
            cursor.execute(
                'INSERT INTO pdfs (title, filename) VALUES (%s, %s)',
                (f'题目 Blatt{i}', f'Blatt{i}.pdf')
            )

        connection.commit()
        print("Database updated with 12 PDFs.")

except Error as e:
    print(f"Error: {e}")

finally:
    if connection.is_connected():
        cursor.close()
        connection.close()