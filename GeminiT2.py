from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import google.generativeai as genai
import os
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Gemini 初始化
def init_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 环境变量未设置")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

model = init_gemini()

# Gemini 对话
def generate_gemini_response(user_input, max_tokens=100, temperature=0.7):
    if not user_input:
        raise ValueError("输入不能为空")
    try:
        response = model.generate_content(
            user_input,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return response.text
    except AttributeError:
        raise Exception("请求失败，可能被内容过滤器拦截或 API 密钥无效")
    except Exception as e:
        raise Exception(f"发生错误: {str(e)}")

@app.route('/gemini', methods=['POST'])
def gemini_chat():
    try:
        data = request.get_json()
        user_input = data.get('input', '')
        response = generate_gemini_response(user_input)
        return jsonify({'response': response})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# MySQL 数据库连接
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='hopper.proxy.rlwy.net',
            port=53147,
            user='root',
            password='mkZkHWFzNbCYOdGEBBZpOwbqRQfQnWhx',  # 替换为你的 MySQL 密码
            database='railway'
        )
        return connection
    except Error as e:
        raise Exception(f"数据库连接失败: {e}")

# 获取 PDF 文件
@app.route('/api/pdf/<int:pdf_id>', methods=['GET'])
def get_pdf(pdf_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT title, filename FROM pdfs WHERE id = %s', (pdf_id,))
        pdf = cursor.fetchone()
        cursor.close()
        connection.close()

        if not pdf:
            return jsonify({'error': 'PDF 未找到'}), 404

        file_path = os.path.join('uploads', secure_filename(pdf['filename']))
        if not os.path.exists(file_path):
            return jsonify({'error': 'PDF 文件不存在'}), 404

        return send_file(file_path, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 获取 PDF 列表
@app.route('/api/pdfs/list', methods=['GET'])
def get_pdf_list():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 修改点：加入 problem_link 字段
        cursor.execute('SELECT id, title, filename, problem_link FROM pdfs')
        pdfs = cursor.fetchall()

        cursor.close()
        connection.close()

        return jsonify({'pdfs': pdfs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)