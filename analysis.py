import base64
import sys
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.ocr import OCRService
from app.services.llm import LLMService
from app.services.masking import MaskingService

router = APIRouter()

def force_print(msg):
    print(msg, file=sys.stdout, flush=True)

@router.post("/analyze")
async def analyze_contract(
    contract_file: UploadFile = File(...),
    registry_file: UploadFile = File(None), 
    target_language: str = Form("ko")
):
    force_print("\n🚀 [1/5] 분석 요청 도착! (이 로그가 보이면 성공)")
    force_print(f"📂 파일명: {contract_file.filename}")

    try:
        ocr_service = OCRService() 
        llm_service = LLMService()
        masking_service = MaskingService()

        file_content = await contract_file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="파일 내용 없음")

        # 1. OCR
        force_print("🏃 [2/5] OCR 분석 중...")
        text_result = await ocr_service.extract(file_content)
        force_print(f"✅ 텍스트 추출 완료 ({len(text_result)}자)")

        # 2. AI
        force_print("🧠 [3/5] AI 분석 중 (이름 추출)...")
        analysis_result = await llm_service.generate_explanation(
            text=text_result, language=target_language
        )
        
        # 이름 확인
        found_names = analysis_result.get("involved_parties", [])
        force_print(f"🕵️ [중요] AI가 찾은 이름: {found_names}")

        # 3. 마스킹
        force_print(f"😷 [4/5] 마스킹 시작 (대상: {found_names})")
        masked_content = masking_service.mask_sensitive_info(
            file_content, 
            contract_file.filename,
            names_to_mask=found_names 
        )

        # 4. 결과 반환
        base64_encoded = base64.b64encode(masked_content).decode('utf-8')
        mime_type = "application/pdf" if contract_file.filename.endswith(".pdf") else "image/png"
        data_url = f"data:{mime_type};base64,{base64_encoded}"
        
        if "documents" not in analysis_result:
            analysis_result["documents"] = {}
        analysis_result["documents"]["masked_pdf_url"] = data_url
        analysis_result["documents"]["registry_url"] = None

        force_print("🎉 [5/5] 모든 과정 완료! 프론트엔드로 전송.")
        return { "success": True, "data": analysis_result, "error": None }

    except Exception as e:
        force_print(f"💥 [에러 발생] {str(e)}")
        return {
            "success": False,
            "data": None,
            "error": { "code": "SYSTEM_ERROR", "message": "오류 발생", "detail": str(e) }
        }