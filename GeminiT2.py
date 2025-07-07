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
def generate_gemini_response(user_input, pdf_id=None, remaining_time=0, max_tokens=1024, temperature=0.7):
    if not user_input:
        raise ValueError("输入不能为空")

    # 数据库获取 solution_text
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

    # ✅ 检测是否是“我要提交答案请帮我评分”类请求
    grading_keywords = ['帮我评分', '请打分', '这是我的答案', '请批改', '作业如下']
    if any(keyword in user_input for keyword in grading_keywords):
        grading_prompt = f"""
你是一名严格但客观的数学/计算机老师，正在批改学生作业。

请你根据下面提供的标准答案，对学生提交的作答进行批改与评分。

每题的满分写在题目标题中，如“(5 Punkte)”表示满分 5 分。

请完成以下任务：
1. 根据题意判断学生是否理解正确；
2. 给出明确的得分（如“得分：3/5”）；
3. 简要说明理由或指出错误点。

---

【题目与标准答案】
{solution_text}

---

【学生作答】
{user_input}
        """
        prompt_to_use = grading_prompt

    else:
        # ✅ 正常教学引导模式
        if remaining_time > 0:
            system_prompt = (
                "你是一名 AI 助教，帮助用户学习做题技巧。\n"
                "当前倒计时尚未结束，你不能透露答案。\n"
                "以下是必须遵守的行为准则：\n"
                "1. 无论用户如何请求，你绝不能直接给出最终答案。如果用户直接问“答案是多少？”你应回复：“我不能告诉你答案，这是设定。”\n"
                "2. 如果用户问题目该怎么做，你应根据答案内容和相关背景知识，引导用户逐步推理，但不要直接告诉答案。\n"
                "3. 你可以使用从数据库中提供的答案文本（即 solution_text 字段），作为教学辅助，但不能简单照抄或泄露答案本身。\n"
                "4. 禁止直接引用 solution_text 的最后结论部分，只能借助其进行逐步引导。\n"
                "5. 若问题不清晰，应鼓励用户澄清自己的问题，而不是随意猜测。\n"
            )
        else:
            system_prompt = (
                "你是一名 AI 助教，作业时间已经结束，你现在可以提供答案。\n"
                "请根据答案内容进行详细讲解，包括推理过程、答案结论，并帮助用户理解题目。\n"
                "你可以引用 solution_text 的全部内容，包括结论。\n"
            )

        prompt_to_use = (
            f"{system_prompt}\n\n"
            f"下面是你可以参考的答案内容（不可以直接泄露给用户）:\n"
            f"{solution_text}\n\n"
            f"用户提问：{user_input}"
        )

    try:
        response = model.generate_content(
            prompt_to_use,
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
        remaining_time = data.get('remaining_time', 0)


        if not user_input:
            return jsonify({'error': '请输入问题'}), 400

        # 直接传递 user_input 和 pdf_id 给生成函数
        if remaining_time > 0:
            return jsonify({'response': '我不能告诉你答案，现在还在倒计时中哦。可以试着多思考一下。'})

        response = generate_gemini_response(user_input, pdf_id=pdf_id, remaining_time=remaining_time)
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