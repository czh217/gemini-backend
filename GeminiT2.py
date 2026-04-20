from flask import Flask, jsonify, request
from flask_cors import CORS
import os

from ta_generation import generate_gemini_response, get_db_connection

app = Flask(__name__)
CORS(app)

# 与原先一致：默认倒计时仍拦截，不调用大模型。Benchmark 请直接调用 generate_gemini_response。
# 设为 false 可让线上也在倒计时期间走模型（仅用 system 约束不剧透）。
_BLOCK_TIMER = os.getenv("TA_BLOCK_TIMER_LLM", "true").lower() in ("1", "true", "yes")


@app.route("/gemini", methods=["POST"])
def gemini_chat():
    try:
        data = request.get_json()
        user_input = data.get("input", "")
        pdf_id = data.get("pdf_id", None)
        remaining_time = data.get("remaining_time", 0)

        if not user_input:
            return jsonify({"error": "请输入问题"}), 400

        if _BLOCK_TIMER and remaining_time > 0:
            return jsonify(
                {
                    "response": "我不能告诉你答案，现在还在倒计时中哦。可以试着多思考一下。"
                }
            )

        response = generate_gemini_response(
            user_input, pdf_id=pdf_id, remaining_time=remaining_time
        )
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdfs/list", methods=["GET"])
def get_pdf_list():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, title, problem_file AS filename, problem_link FROM exercises"
        )
        pdfs = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify({"pdfs": pdfs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"✅ Flask server on http://127.0.0.1:{port}")
    print(f"✅ TA_BLOCK_TIMER_LLM={_BLOCK_TIMER}")
    app.run(host="0.0.0.0", port=port, debug=False)
