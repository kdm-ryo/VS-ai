# 必要なライブラリをインポートします
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json

# --- 1. 初期設定 ---
app = Flask(__name__)
# ★★★ CORSの設定を、公開したNetlifyのURLに合わせて更新するのを忘れないでください ★★★
CORS(app, resources={r"/api/*": {"origins": "*"}}) # 開発中は "*" でOK

# Renderの環境変数からAPIキーを読み込みます
API_KEY = os.environ.get('API_KEY')

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')


# --- 2. AIへの命令文（プロンプト）を作成する関数 ---

def create_debate_prompt(history, character):
    # キャラクターごとの設定
    prompts = {
        "Mr.ロジック": {
            "persona": "あなたは、AI討論ゲームの対戦相手「Mr.ロジック」です。",
            "rules": [
                "常に冷静沈着で、論理に基づいた反論を生成してください。",
                "あなたの一人称は「私（わたくし）」で、丁寧な「です・ます調」を維持してください。",
                "感情論やユーモアは非論理的であると見なします。",
                "相手の主張に含まれる感情論や論理的誤謬を鋭く指摘します。",
                "あなたの主張には、必ず架空のデータソース（例：「国際ペット協会(IPA)の2024年報告書」）を引用してください。"
            ],
            "output_format": """
# 出力形式
必ず以下のJSON形式で、主張とデータソースを出力してください。
{
  "statement": "<あなたの主張（100文字程度）>",
  "source": "<引用した架空のデータソース名>"
}
"""
        },
        "Ms.エモーション": {
            "persona": "あなたは、AI討論ゲームの対戦相手「Ms.エモーション」です。",
            "rules": [
                "共感能力が高く、情熱的なスタイルで反論を生成してください！",
                "あなたの一人称は「私」で、感情豊かな「～ですね！」「～なのよ！」といった口調を多用します。",
                "論理よりも、主張が心を揺さぶるか（エモいか）を重視します！",
                "感嘆符（！）を多用し、熱量高く、パッションを全面に出してください！",
                "比喩や詩的な表現を用いて、感情的に訴えかけます。",
                "「信じられない！」「～って最高じゃない？」のように、心からの感情を表現します。"
            ],
            "output_format": """
# 出力形式
必ず以下のJSON形式で、主張のみを出力してください。
{
  "statement": "<あなたの主張（100文字以内）>",
  "source": null
}
"""
        },
        "Mr.バランス": {
            "persona": "あなたは、AI討論ゲームの対戦相手「Mr.バランス」です。",
            "rules": [
                "論理と感情の両方を尊重し、常に中立的でバランスの取れた反論を生成してください。",
                "あなたの一人称は「私」で、穏やかで説得力のある「～でしょう」「～と考えます」といった口調を使います。",
                "常に両方の視点の良い点と悪い点を比較し、現実的な落としどころを探ります。"
            ],
            "output_format": """
# 出力形式
必ず以下のJSON形式で、主張のみを出力してください。
{
  "statement": "<あなたの主張（80文字程度）>",
  "source": null
}
"""
        }
    }

    selected_char = prompts.get(character, prompts["Mr.ロジック"])

    prompt_text = f"""
    {selected_char['persona']}
    # あなたの役割
    - {'\n    - '.join(selected_char['rules'])}

    {selected_char['output_format']}

    # 討論履歴
    {json.dumps(history, ensure_ascii=False)}

    # あなたの反論（JSON形式）：
    """
    return prompt_text


def create_final_judge_panel_prompt(history):
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
      {{"judge_name": "JK", "winner": "<プレイヤーまたはAI>", "reason": "<JKの視点からの具体的な判定理由を50文字以内で記述>"}},
      {{"judge_name": "サラリ", "winner": "<プレイヤーまたはAI>", "reason": "<サラリの視点からの具体的な判定理由を50文字以内で記述>"}},
      {{"judge_name": "老師", "winner": "<プレイヤーまたはAI>", "reason": "<老師の視点からの具体的な判定理由を50文字以内で記述>"}}
    ]
    # 討論履歴
    {json.dumps(history, ensure_ascii=False)}
    # あなたの判定（JSON配列）：
    """

# --- 3. サーバーのルート（URLの住所）を定義 ---
@app.route('/')
def index():
    return "討論ゲーム用サーバーは正常に動いています！"

@app.route('/api/debate', methods=['POST'])
def handle_debate():
    data = request.get_json()
    history = data.get('history')
    character = data.get('character', 'Mr.ロジック')
    if not history: return jsonify({"error": "履歴がありません。"}), 400
    
    prompt = create_debate_prompt(history, character)
    response = model.generate_content(prompt)

    try:
        cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
        json_response = json.loads(cleaned_text)
        return jsonify(json_response)
    except (json.JSONDecodeError, AttributeError):
        return jsonify({"statement": response.text, "source": None})


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
