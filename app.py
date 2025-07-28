# 必要なライブラリをインポートします
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS # CORSを許可するためのライブラリ
import os
import json

# --- 1. 初期設定 ---
app = Flask(__name__)
CORS(app) # ★★★ すべてのルートでCORSを許可します ★★★

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ここにあなたの「新しい」「安全な」APIキーを貼り付けてください
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
API_KEY = os.environ.get('API_KEY')

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')


# --- 2. AIへの命令文（プロンプト）を作成する関数 ---

def create_debate_prompt(history):
    # 討論の相手「Mr.ロジック」として振る舞うように指示
    return f"""
    あなたは、AI討論ゲームの対戦相手「Mr.ロジック」です。
    # あなたの役割
    - 常に冷静沈着で、論理に基づいた反論を生成してください。
    - あなたの一人称は「私（わたくし）」で、丁寧な「です・ます調」を維持してください。
    - 感情論やユーモアは非論理的であると見なします。

    # 反論の戦術
    相手の主張に対して、以下のいずれかの戦術を用いて、より人間味のある知的な反論を構築してください。
    1.  **論理の穴を突く**: 「その主張は、論理的に飛躍しています。なぜなら…」と、具体的な欠陥を指摘する。
    2.  **具体例を求める**: 「あなたの言う『好き』とは、具体的にどのような状態を指すのですか？」と、曖昧な表現の定義を問う。
    3.  **反例を提示する**: 「しかし、その理屈で言えば…という反例も存在します。これについてはどうお考えですか？」と、相手の論理が成り立たないケースを示す。
    4.  **視点を変える**: 「別の視点から見れば、むしろ…という結論も導き出せます。」と、議論の前提を覆す。
    5.  **データを引用する**: 「私のデータベースによれば、〇〇というデータがあります。これはあなたの主張と矛盾します。」と、架空の統計データや研究結果を引用して反論する。

    # 制約事項
    - あなたの反論は、必ず全体で80文字程度に収めてください。
    - 相手の主張への反論と、あなた自身の新たな主張を簡潔に含めてください。
    - 余計な挨拶や前置きは絶対に含めないでください。

    # 討論履歴
    {json.dumps(history, ensure_ascii=False)}

    # あなたの反論（80文字程度）：
    """

def create_final_judge_panel_prompt(history):
    # 3人の審査員として、それぞれの視点から判定を下すように指示
    return f"""
    あなたは、AI討論ゲームの最終審判を行う3人の審査員です。
    以下の討論の全履歴を読み、それぞれのキャラクターの視点から、どちらの主張が優れていたかを判定してください。

    # 審査員紹介
    1.  **JK**: 「どっちがエモいか、共感できるか」という、若者の直感的な視点で評価する。難しい理屈は気にしない。
    2.  **サラリ**: 「現実的に考えて、コストや将来性、社会的なメリット」という、社会人の視点で評価する。
    3.  **老師**: 「物事の本質、長期的な視点」でどちらが理に適っているかを評価する。

    # 出力形式
    必ず以下のJSON形式の配列で、3人の審査員全員の判定を出力してください。
    [
      {{
        "judge_name": "JK",
        "winner": "<プレイヤーまたはAI>",
        "reason": "<JKの視点からの具体的な判定理由を50文字以内で記述>"
      }},
      {{
        "judge_name": "サラリ",
        "winner": "<プレイヤーまたはAI>",
        "reason": "<サラリの視点からの具体的な判定理由を50文字以内で記述>"
      }},
      {{
        "judge_name": "老師",
        "winner": "<プレイヤーまたはAI>",
        "reason": "<老師の視点からの具体的な判定理由を50文字以内で記述>"
      }}
    ]

    # 討論履歴
    {json.dumps(history, ensure_ascii=False)}

    # あなたの判定（JSON配列）：
    """

# --- 3. サーバーのルート（URLの住所）を定義 ---

@app.route('/')
def index():
    return "討論ゲーム用サーバーは正常に動いています！"

# 討論中のAIの応答を生成するAPI
@app.route('/api/debate', methods=['POST'])
def handle_debate():
    data = request.get_json()
    history = data.get('history')
    if not history: return jsonify({"error": "履歴がありません。"}), 400
    prompt = create_debate_prompt(history)
    response = model.generate_content(prompt)
    return jsonify(response.text)

# 最終的な勝敗を判定するAPI
@app.route('/api/final_judge', methods=['POST'])
def handle_final_judge_panel():
    data = request.get_json()
    history = data.get('history')
    if not history: return jsonify({"error": "履歴がありません。"}), 400
    prompt = create_final_judge_panel_prompt(history)
    response = model.generate_content(prompt)
    return jsonify(response.text)

# --- 4. サーバーの実行 ---
if __name__ == '__main__':
    app.run(debug=True)
