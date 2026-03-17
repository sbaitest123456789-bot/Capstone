import os
from dotenv import load_dotenv
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, HallucinationMetric, GEval

# 環境変数の読み込み
load_dotenv()

def run_comprehensive_evaluation():
    print("🚀 [DeepEval] LLMソリューションの総合品質評価を開始します...\n")
#   print("🚀 [DeepEval] Starting comprehensive quality evaluation of the LLM solution...\n")

    # ==========================================
    # 1. テストケースの定義
    # 1. Test Case Definition
    # ==========================================
    user_query = "MediaServer12のCPU使用率が異常に高くなっています。解決策を教えてください。"
    
    retrieved_context = [
        "【過去の事例】MediaServer12でCPU使用率が95%を超える事象が発生。原因はエンコーダープロセスの暴走。解決策: 処理パラメータの最適化とサービスの再起動を実施。"
    ]
    
    actual_ai_output = """
    1. Priority: High
    2. Routing: [ L2 DB & Storage Team ]
    3. Resolution Suggestion:
    ■ English
    - Optimize processing parameters.
    - Restart the encoder service.
    ■ 日本語
    - 処理パラメータを最適化してください。
    - エンコーダーサービスを再起動してください。
    """

    user_query = "The CPU usage on MediaServer12 is abnormally high. Please provide a solution."

    # retrieved_context = [
    # "[Past Incident] An issue occurred on MediaServer12 where CPU usage exceeded 95%. The root cause was a runaway encoder process. Solution: Optimized processing parameters and restarted the service."
    # ]

    # actual_ai_output = """
    # 1. Priority: High
    # 2. Routing: [ L2 DB & Storage Team ]
    # 3. Resolution Suggestion:
    # ■ English
    # - Optimize processing parameters.
    # - Restart the encoder service.
    # ■ Japanese
    # - Optimize processing parameters.
    # - Restart the encoder service.
    # """

    test_case = LLMTestCase(
        input=user_query,
        actual_output=actual_ai_output,
        retrieval_context=retrieved_context,
        context=retrieved_context
    )

    # ==========================================
    # 2. 評価指標（Metrics）の定義
    # 2. Definition of Evaluation Metrics
    # ==========================================
    # 既存の評価1・2
    # Existing Evaluations 1 & 2
    relevancy_metric = AnswerRelevancyMetric(threshold=0.7)
    faithfulness_metric = FaithfulnessMetric(threshold=0.7)
    
    # 🌟 新規追加の評価3: ハルシネーション（コンテキストにない捏造のチェック）
    # 🌟 New Addition: Evaluation 3 — Hallucinations (Checking for Fabrications Outside the Context)
    hallucination_metric = HallucinationMetric(threshold=0.5)
    
    # 🌟 新規追加の評価4: ガードレール（指定フォーマット・バイリンガル要件の遵守）
    # 🌟 New Addition – Evaluation 4: Guardrails (Compliance with Specified Format and Bilingual Requirements)
    guardrail_metric = GEval(
        name="Format and Bilingual Guardrail",
        criteria="出力は必ず '1. Priority:', '2. Routing:', '3. Resolution Suggestion:' の3項目を含み、かつ '■ English' と '■ 日本語' の両方のセクションが存在しなければならない。",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=1.0 # ルール違反は許容しないため1.0（満点のみ合格）
    )

    # ==========================================
    # 3. 順番に評価を実行してログを出力
    # 3. Execute evaluations sequentially and output logs.
    # ==========================================
    metrics_to_run = [
        ("評価1: Answer Relevancy (質問への関連性)", relevancy_metric),
        ("評価2: Faithfulness (過去事例への忠実性)", faithfulness_metric),
        ("評価3: Hallucination (捏造・ハルシネーションの有無)", hallucination_metric),
        ("評価4: Guardrail (SOP・フォーマット要件の遵守)", guardrail_metric)
    ]
    # metrics_to_run = [
    #     ("Evaluation 1: Answer Relevancy (Relevance to the Question)", relevancy_metric),
    #     ("Evaluation 2: Faithfulness (Fidelity to Past Examples)", faithfulness_metric),
    #     ("Evaluation 3: Hallucination (Presence of Fabrications/Hallucinations)", hallucination_metric),
    #     ("Evaluation 4: Guardrail (Adherence to SOPs and Formatting Requirements)", guardrail_metric)

    for name, metric in metrics_to_run:
        print(f"📊 {name} を計測中...")
        metric.measure(test_case)
        print(f"結果: {'✅ 合格 (PASSED)' if metric.is_successful() else '❌ 不合格 (FAILED)'}")
        print(f"スコア: {metric.score}")
        print(f"理由: {metric.reason}\n")
        
    print("✨ 全ての評価プロセスが完了しました！")

    # for name, metric in metrics_to_run:
    # print(f"📊 Measuring {name}...")
    # metric.measure(test_case)
    # print(f"Result: {'✅ PASSED' if metric.is_successful() else '❌ FAILED'}")
    # print(f"Score: {metric.score}")
    # print(f"Reason: {metric.reason}\n")

    # print("✨ All evaluation processes complete!")

if __name__ == "__main__":
    run_comprehensive_evaluation()