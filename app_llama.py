# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from openai import OpenAI
# import os
# import mysql.connector
# from mysql.connector import Error
#
# app = Flask(__name__)
# CORS(app)
#
# # ============================================================
# # 1️⃣ 初始化本地 LLaMA 客户端
# # ============================================================
# client = OpenAI(
#     api_key="not-needed",               # LM Studio 不需要真实 API key
#     base_url="http://127.0.0.1:1234/v1" # 你的 LM Studio 本地 API 地址
# )
#
# # ============================================================
# # 2️⃣ 生成 LLaMA 回复
# # ============================================================
# def generate_llama_response(user_input, pdf_id=None, remaining_time=0,
#                             model_name="llama-3.2-3b-instruct", max_tokens=1024, temperature=0.7):
#     if not user_input:
#         raise ValueError("输入不能为空")
#
#     # 从数据库读取 solution_text
#     solution_text = ""
#     if pdf_id is not None:
#         try:
#             connection = get_db_connection()
#             cursor = connection.cursor(dictionary=True)
#             cursor.execute('SELECT solution_text FROM exercises WHERE id = %s', (pdf_id,))
#             row = cursor.fetchone()
#             if row and row['solution_text']:
#                 solution_text = row['solution_text']
#             cursor.close()
#             connection.close()
#         except Exception as e:
#             print(f"数据库读取失败: {e}")
#             solution_text = ""
#
#     # 检测是否是“评分请求”
#     grading_keywords = [
#         '帮我评分', '请打分', '这是我的答案', '请批改', '作业如下',
#         'grade my answer', 'please score', 'bewerte meine Antwort'
#     ]
#
#     if any(k in user_input for k in grading_keywords):
#         system = (
#             "You are a strict but fair teaching assistant. "
#             "Grade the student's answer according to the rubric and output ONLY valid JSON in this format: "
#             "{\"score\":x,\"max_score\":y,\"reasoning\":\"...\",\"items\":[{\"sub\":\"1\",\"score\":...}]}"
#         )
#         prompt = f"Question & reference solution:\n{solution_text}\n\nStudent answer:\n{user_input}\nReturn only JSON."
#     else:
#         if remaining_time > 0:
#             system = (
#                 "You are a helpful teaching assistant. The test is still ongoing. "
#                 "Do NOT reveal final answers. Only provide hints, partial reasoning, or guidance in English or German."
#             )
#         else:
#             system = (
#                 "You are a helpful teaching assistant. The test is over. "
#                 "Provide a complete step-by-step explanation and the final answer in English or German."
#             )
#         prompt = f"Reference solution (do not leak early):\n{solution_text}\n\nUser query:\n{user_input}"
#
#     # 调用 LLaMA 本地模型
#     try:
#         response = client.chat.completions.create(
#             model=model_name,
#             messages=[
#                 {"role": "system", "content": system},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=temperature,
#             max_tokens=max_tokens
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         raise Exception(f"LLaMA 请求失败: {e}")
#
# # ============================================================
# # 3️⃣ Flask 路由：前端 POST 请求这里
# # ============================================================
# @app.route('/llama', methods=['POST'])
# def llama_chat():
#     try:
#         data = request.get_json()
#         user_input = data.get('input', '')
#         pdf_id = data.get('pdf_id', None)
#         remaining_time = data.get('remaining_time', 0)
#
#         if not user_input:
#             return jsonify({'error': '请输入问题'}), 400
#
#         if remaining_time > 0:
#             # 倒计时中：提前返回提示
#             return jsonify({'response': 'I cannot reveal the answer yet. Try reasoning on your own first.'})
#
#         response = generate_llama_response(
#             user_input, pdf_id=pdf_id, remaining_time=remaining_time
#         )
#         return jsonify({'response': response})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
#
# # ============================================================
# # 4️⃣ MySQL 数据库连接
# # ============================================================
# def get_db_connection():
#     try:
#         connection = mysql.connector.connect(
#             host='hopper.proxy.rlwy.net',
#             port=53147,
#             user='root',
#             password='mkZkHWFzNbCYOdGEBBZpOwbqRQfQnWhx',
#             database='railway'
#         )
#         return connection
#     except Error as e:
#         raise Exception(f"数据库连接失败: {e}")
#
# # ============================================================
# # 5️⃣ 获取 PDF 列表（原逻辑保留）
# # ============================================================
# @app.route('/api/pdfs/list', methods=['GET'])
# def get_pdf_list():
#     try:
#         connection = get_db_connection()
#         cursor = connection.cursor(dictionary=True)
#         cursor.execute('SELECT id, title, problem_file AS filename, problem_link FROM exercises')
#         pdfs = cursor.fetchall()
#         cursor.close()
#         connection.close()
#         return jsonify({'pdfs': pdfs})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
#
# # ============================================================
# # 6️⃣ 启动 Flask 应用
# # ============================================================
# if __name__ == '__main__':
#     port = int(os.getenv('PORT', 5000))
#     print(f"✅ Flask server running on http://127.0.0.1:{port}")
#     print("✅ LLaMA API base URL: http://127.0.0.1:1234/v1")
#     app.run(host='0.0.0.0', port=port, debug=False)
