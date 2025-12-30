from openai import AzureOpenAI
import json

class LLMService:
    def __init__(self):
        print(f"🤖 LLM 서비스 시작! 연결 모델: {REAL_DEPLOYMENT}")
        self.client = AzureOpenAI(
            azure_endpoint=REAL_ENDPOINT,
            api_key=REAL_KEY,
            api_version="2024-02-15-preview"
        )
        self.deployment_name = REAL_DEPLOYMENT

    async def generate_explanation(self, text: str, mode: str = "general", language: str = "ko") -> dict:
        print("🚀 [LLM] AI 분석 요청 생성 중...")
        
        system_prompt = """
        You are a professional legal contract analyzer.
        You MUST output the result in valid JSON format only.
        """

        # 이름을 더 잘 찾도록 프롬프트 강화
        user_prompt = f"""
        Analyze the following contract text (Language: {language}).
        
        [IMPORTANT REQUIREMENTS]
        1. Extract 'involved_parties' accurately. 
           - Extract ONLY the names of people/companies (e.g., "홍길동", "김철수").
           - Do NOT include titles like "임대인", "Representative".
        2. If 'evidence' or specific clause is found for a risk, include it in 'evidence' field inside 'rules'.
        3. Return strictly valid JSON.

        [JSON Structure Example]
        {{
            "summary": {{ "title": "Contract Summary", "risk_count": 0, "service_type": "monthly" }},
            "summary_text": "Summarize in 3 lines.",
            "involved_parties": ["홍길동", "김철수"],
            "rules": [
                {{ 
                    "id": 1, 
                    "status": "FAIL", 
                    "title": "Risk Title", 
                    "content": "Risk Description", 
                    "importance": "HIGH",
                    "evidence": {{ "detail": "Article 3 Clause 2..." }}
                }}
            ],
            "documents": {{ "masked_pdf_url": null, "registry_url": null }}
        }}

        [Contract Text]
        {text[:4000]}
        """

        try:
            # API 호출 (이제 위에서 정의한 변수를 사용하므로 에러 안 남)
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )

            result_content = response.choices[0].message.content
            print(f"✅ [LLM] AI 응답 수신 완료! (길이: {len(result_content)})")
            
            # JSON 파싱
            parsed_result = json.loads(result_content)
            
            # 안전장치: 필수 키가 없으면 채워넣기
            if "involved_parties" not in parsed_result:
                parsed_result["involved_parties"] = []
            if "rules" not in parsed_result:
                parsed_result["rules"] = []
            if "documents" not in parsed_result:
                parsed_result["documents"] = {"masked_pdf_url": None, "registry_url": None}

            return parsed_result

        except Exception as e:
            print(f"❌ [LLM] 생성 중 치명적 에러 발생: {str(e)}")
            # 에러 발생 시 빈 껍데기 반환 (마스킹은 안 되더라도 화면은 뜨게 함)
            return {
                "summary": {"title": "분석 실패", "risk_count": 0},
                "summary_text": f"AI 분석 중 오류가 발생했습니다. ({str(e)})",
                "involved_parties": [],
                "rules": [],
                "documents": {"masked_pdf_url": None, "registry_url": None}
            }