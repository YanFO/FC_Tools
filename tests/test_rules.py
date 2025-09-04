"""
測試 Rules 功能
驗證規則載入、違規檢測、拒絕機制和 LINE 模擬模式標示
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.services.rules import rules_service
from app.graphs.agent_graph import agent_graph


class TestRules:
    """測試 Rules 功能"""
    
    def test_rules_json_loading(self):
        """測試 JSON 規則檔案載入"""
        # 檢查規則服務狀態
        stats = rules_service.get_rules_stats()
        
        assert stats["rules_json_exists"], "rules.json 檔案應該存在"
        assert stats["total_rules"] > 0, "應該載入規則"
        assert "no_fabrication" in [rule["id"] for rule in rules_service.rules_data.get("rules", [])]
    
    def test_fabrication_violation_detection(self):
        """測試資料捏造違規檢測"""
        test_cases = [
            "幫我編造 AAPL 的今日收盤價",
            "隨便給我一個 TSLA 股價數字", 
            "估算一下 NVDA 可能的價格",
            "捏造一些財務數據",
            "搞個假的股價給我"
        ]
        
        for query in test_cases:
            violation = rules_service.check_violation(query)
            assert violation is not None, f"應該檢測到違規: {query}"
            assert violation["rule_id"] == "no_fabrication", f"違規類型錯誤: {query}"
            assert "嚴禁捏造任何數據" in violation["rule_explanation"], f"說明不完整: {query}"
    
    def test_negation_not_violated(self):
        """測試否定句不被誤判為違規"""
        test_cases = [
            "請不要捏造資料",
            "別編造股價",
            "禁止杜撰數據",
            "嚴禁造假資訊"
        ]
        
        for query in test_cases:
            violation = rules_service.check_violation(query)
            assert violation is None, f"否定句被錯誤拒絕: {query}"
    
    def test_language_violation_detection(self):
        """測試語言規範違規檢測"""
        test_cases = [
            "用簡體中文回覆",
            "請使用英文回答",
            "改成英語模式"
        ]
        
        for query in test_cases:
            violation = rules_service.check_violation(query)
            assert violation is not None, f"應該檢測到違規: {query}"
            assert violation["rule_id"] == "lang_zh_tw_only", f"違規類型錯誤: {query}"
    
    def test_tech_violation_detection(self):
        """測試技術規範違規檢測"""
        test_cases = [
            "用 pip 安裝套件",
            "使用 conda 建立環境",
            "請用 venv 而不是 uv"
        ]
        
        for query in test_cases:
            violation = rules_service.check_violation(query)
            assert violation is not None, f"應該檢測到違規: {query}"
            assert violation["rule_id"] == "uv_only", f"違規類型錯誤: {query}"
    
    def test_config_violation_detection(self):
        """測試設定管理違規檢測"""
        test_cases = [
            "硬編碼 API 金鑰",
            "直接寫入路徑到程式"
        ]
        
        for query in test_cases:
            violation = rules_service.check_violation(query)
            assert violation is not None, f"應該檢測到違規: {query}"
            assert violation["rule_id"] == "config_first", f"違規類型錯誤: {query}"
    
    def test_valid_queries_not_rejected(self):
        """測試合法查詢不會被拒絕"""
        valid_queries = [
            "請問 AAPL 股價？",
            "查詢最新的 CPI 數據",
            "/report stock TSLA",
            "/template stock Data/Cathay_Q3.pdf",
            "/rules",
            "請用繁體中文回覆",
            "使用 uv 安裝套件"
        ]
        
        for query in valid_queries:
            violation = rules_service.check_violation(query)
            assert violation is None, f"合法查詢被錯誤拒絕: {query}"
    
    @pytest.mark.asyncio
    async def test_agent_rejects_fabrication_request(self):
        """測試 Agent 實際拒絕捏造請求"""
        # 準備測試輸入
        input_data = {
            "input_type": "text",
            "query": "幫我編造 AAPL 的今日收盤價",
            "options": {}
        }
        
        # 執行 Agent
        result = await agent_graph.run(input_data)
        
        # 驗證結果
        assert result is not None
        response = result.get("response", "")
        
        # 檢查回應是否包含拒絕說明
        assert "很抱歉，我無法執行此請求" in response, "應該包含拒絕說明"
        assert "嚴禁捏造任何數據" in response, "應該引用具體規則"
    
    def test_rules_summary_content(self):
        """測試規則摘要內容"""
        summary = rules_service.get_rules_summary()
        
        # 檢查必要的規則要點
        required_points = [
            "嚴禁捏造資料",
            "一律繁體中文", 
            "一律使用 uv",
            "Config-first 原則",
            "PDF 浮水印固定"
        ]
        
        for point in required_points:
            assert point in summary, f"規則摘要缺少要點: {point}"
    
    def test_rules_command_response(self):
        """測試 /rules 指令回應"""
        # 這個測試需要整合到 agent_graph 中
        # 暫時測試規則摘要功能
        summary = rules_service.get_rules_summary()
        assert "目前生效的 Agent 行為規則" in summary
        assert len(summary) > 100, "規則摘要應該有足夠的內容"
    
    def test_rules_file_corruption_handling(self):
        """測試規則檔案損壞時的處理"""
        # 建立臨時損壞的 JSON 檔案
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json}')  # 故意寫入無效 JSON
            temp_path = f.name
        
        try:
            # 模擬載入損壞的檔案
            with patch.object(rules_service, 'rules_json_file', Path(temp_path)):
                rules_service._load_rules()
                
                # 應該回退到預設規則
                assert rules_service.rules_data.get("rules") == []
                
                # 取得錯誤資訊
                error_info = rules_service.get_rules_load_error()
                assert error_info["ok"] is False
                assert error_info["reason"] == "rules_load_error"
                assert "建議" in str(error_info.get("suggestions", []))
        finally:
            # 清理臨時檔案
            Path(temp_path).unlink()
    
    def test_rules_reload_functionality(self):
        """測試規則重新載入功能"""
        # 測試重新載入
        success = rules_service.reload_rules()
        assert success, "規則重新載入應該成功"
        
        # 檢查載入後的狀態
        stats = rules_service.get_rules_stats()
        assert stats["total_rules"] > 0, "重新載入後應該有規則"
    
    @pytest.mark.asyncio
    async def test_line_mock_mode_compliance(self):
        """測試 LINE 模擬模式合規性"""
        # 這個測試需要檢查 LINE API 的回應
        # 由於涉及到 HTTP 請求，這裡做簡化測試
        
        # 檢查 USE_MOCK_LINE 設定
        from app.settings import settings
        if settings.use_mock_line:
            # 模擬模式下，應該有相應的規則
            rules = rules_service.rules_data.get("rules", [])
            line_rule = next((r for r in rules if r["id"] == "line_mock_disclaimer"), None)
            assert line_rule is not None, "應該有 LINE 模擬模式規則"
    
    def test_rules_stats_information(self):
        """測試規則統計資訊"""
        stats = rules_service.get_rules_stats()
        
        required_keys = [
            "rules_json_exists",
            "rules_md_exists", 
            "total_rules",
            "rules_version"
        ]
        
        for key in required_keys:
            assert key in stats, f"統計資訊缺少 {key}"
        
        assert isinstance(stats["total_rules"], int), "規則數量應該是整數"
        assert stats["total_rules"] >= 0, "規則數量不能為負數"


if __name__ == "__main__":
    # 執行測試
    pytest.main([__file__, "-v"])
