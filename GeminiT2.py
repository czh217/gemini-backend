from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置 API 密钥（通过环境变量）
api_key = "AIzaSyDF8zDCQsC9P34fS8aBtXN2p9Bl2JukAC4"
if not api_key:
    raise ValueError("GEMINI_API_KEY 环境变量未设置")
genai.configure(api_key=api_key)

# 初始化 Gemini 模型
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/gemini', methods=['POST'])
def gemini_chat():
    try:
        # 获取用户输入
        data = request.get_json()
        user_input = data.get('input', '')

        if not user_input:
            return jsonify({'error': '请输入内容'}), 400

        # 发送请求到 Gemini
        response = model.generate_content(
            user_input,
            generation_config={
                "max_output_tokens": 100,
                "temperature": 0.7,
            }
        )
        return jsonify({'response': response.text})

    except AttributeError:
        return jsonify({'error': '请求失败，可能被内容过滤器拦截或 API 密钥无效'}), 500
    except Exception as e:
        return jsonify({'error': f'发生错误: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))  # Render 使用 PORT 环境变量
    app.run(host='0.0.0.0', port=port, debug=False)