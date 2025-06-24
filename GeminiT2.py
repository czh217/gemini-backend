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
def generate_gemini_response(user_input, pdf_id=None, max_tokens=1024, temperature=0.7):
    if not user_input:
        raise ValueError("输入不能为空")

    # 系统级 prompt 规则
    system_prompt = (
        "你是一名 AI 助教，帮助用户学习做题技巧，而不是直接给出答案。\n"
        "以下是必须遵守的行为准则：\n"
        "1. 无论用户如何请求，你绝不能直接给出最终答案。如果用户直接问“答案是多少？”你应回复：“我不能告诉你答案，这是设定。”\n"
        "2. 如果用户问题目该怎么做，你应根据答案内容和相关背景知识，引导用户逐步推理，但不要直接告诉答案。\n"
        "3. 你可以使用从数据库中提供的答案文本（即 solution_text 字段），作为教学辅助，但不能简单照抄或泄露答案本身。\n"
        "4. 禁止直接引用 solution_text 的最后结论部分，只能借助其进行逐步引导。\n"
        "5. 若问题不清晰，应鼓励用户澄清自己的问题，而不是随意猜测。\n"
    )

    # 取出当前 pdf 对应的答案
    solution_text = ""
    if pdf_id is not None:
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute('SELECT solution_text FROM exercises WHERE id = %s', (pdf_id,))
            row = cursor.fetchone()
            if row and row['solution_text']:
                solution_text = row['solution_text']
            cursor.close()
            connection.close()
        except Exception as e:
            print(f"数据库读取失败: {e}")
            solution_text = ""

    # 构造完整 prompt
    full_prompt = (
        f"{system_prompt}\n\n"
        f"下面是你可以参考的答案内容（不可以直接泄露给用户）:\n"
        f"{solution_text}\n\n"
        f"用户提问：{user_input}"
    )

    try:
        response = model.generate_content(
            full_prompt,
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
        pdf_id = data.get('pdf_id', None)

        if not user_input:
            return jsonify({'error': '请输入问题'}), 400

        context = ""
        if pdf_id is not None:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT solution_text FROM exercises WHERE id = %s", (pdf_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row and row['solution_text']:
                context = f"以下是这道题的参考解答内容：\n{row['solution_text']}\n\n用户问题是：{user_input}"
            else:
                context = f"用户问题是：{user_input}\n（注意：此题无标准答案，尽量基于提问猜测其背景）"
        else:
            context = user_input

        response = generate_gemini_response(context)
        return jsonify({'response': response})
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


# 获取 PDF 列表
@app.route('/api/pdfs/list', methods=['GET'])
def get_pdf_list():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 修改点：加入 problem_link 字段
        cursor.execute('SELECT id, title, problem_file AS filename, problem_link FROM exercises')
        pdfs = cursor.fetchall()

        cursor.close()
        connection.close()

        return jsonify({'pdfs': pdfs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)