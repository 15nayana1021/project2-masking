import fitz  # PyMuPDF
import re

class MaskingService:
    def mask_sensitive_info(self, file_content: bytes, filename: str, names_to_mask: list = []) -> bytes:
        if not filename.lower().endswith(".pdf"):
            return file_content

        try:
            print(f"😷 [Masking] 시작! 파일명: {filename}")
            print(f"🎯 [Masking] AI가 요청한 이름 목록: {names_to_mask}")
            
            doc = fitz.open(stream=file_content, filetype="pdf")
            total_masked_count = 0

            # 1. 탐지할 패턴 정의 (가능한 모든 형식을 다 잡도록 넓게 설정)
            patterns = {
                # 주민번호: 6자리-7자리 (뒷자리 1~4 시작)
                "RRN": r"\d{6}\s*[-~]\s*[1-4][0-9*]{6}", 
                
                # 사업자번호: 3자리-2자리-5자리 (124-81-12345)
                "BIZ": r"\d{3}\s*[-~]\s*\d{2}\s*[-~]\s*\d{5}",
                
                # 전화번호: 0으로 시작, 국번 2~3자리, 중간 3~4자리, 끝 4자리
                # (010, 031, 02 등 모두 포함 / 하이픈, 점, 공백 모두 허용)
                "PHONE": r"0\d{1,2}[\s\-\.~]*\d{3,4}[\s\-\.~]*\d{4}",
                
                # 이메일
                "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            }

            for page_num, page in enumerate(doc):
                # 페이지의 글자를 모두 가져옴
                page_text = page.get_text()

                
                # 1단계: 패턴(숫자) 마스킹 (스마트 검색 적용)
                for type_name, pattern in patterns.items():
                    # 정규식으로 '논리적인' 텍스트를 먼저 찾음 (예: 031-491-1234)
                    found_texts = re.findall(pattern, page_text)
                    
                    for text in found_texts:
                        # (1) 있는 그대로 찾아보기
                        quads = page.search_for(text)
                        
                        # (2) 못 찾으면 '스마트 검색' 가동! (숫자가 쪼개져 있는 경우 대비)
                        if not quads:
                            # 숫자와 문자만 남기고 다 뺌 (031-491 -> 031491)
                            clean_text = re.sub(r'[^a-zA-Z0-9]', '', text)
                            
                            # 글자 사이에 뭐가 끼어있든 찾도록 변환 (0.*3.*1.*4...)
                            # \s*[-.~]?\s* : 공백, 하이픈, 점 등이 있거나 없거나
                            flexible_pattern = r"\s*[-.~]?\s*".join([re.escape(char) for char in clean_text])
                            
                            # 실제 PDF에 적힌 모양대로 다시 찾음
                            visual_matches = re.findall(flexible_pattern, page_text)
                            for vm in visual_matches:
                                quads.extend(page.search_for(vm)) # 찾은 좌표 추가
                        
                        # 마스킹 적용
                        if quads:
                            print(f"   🔒 [P.{page_num+1}] {type_name} 마스킹: '{text}'")
                            for quad in quads:
                                page.add_redact_annot(quad, fill=(0, 0, 0))
                                total_masked_count += 1

                
                # 2단계: 이름 마스킹 (이미 적용된 스마트 검색)
                for name in names_to_mask:
                    clean_name = re.sub(r'\s+', '', name) # 공백 제거
                    if len(clean_name) < 2: continue 

                    # 이름 글자 사이에 공백 허용 검색
                    flexible_pattern = r"\s*".join([re.escape(char) for char in clean_name])
                    found_real_names = re.findall(flexible_pattern, page_text)
                    
                    for real_name in found_real_names:
                        quads = page.search_for(real_name)
                        if quads:
                            print(f"   👤 [P.{page_num+1}] 이름 마스킹: '{real_name}'")
                            for quad in quads:
                                page.add_redact_annot(quad, fill=(0, 0, 0))
                                total_masked_count += 1

                page.apply_redactions()

            masked_bytes = doc.tobytes()
            print(f"✅ [Masking] 최종 완료! 총 {total_masked_count}곳을 가렸습니다.")
            return masked_bytes

        except Exception as e:
            print(f"❌ [Masking] 치명적 오류: {e}")
            return file_content