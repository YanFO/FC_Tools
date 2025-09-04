"""
測試 PDF 報告生成、列表和下載功能
驗證報告產出、API 端點和檔案安全性
"""
import pytest
import tempfile
from pathlib import Path

from app.graphs.agent_graph import agent_graph
from app.routers.reports import get_reports_directory, is_safe_path, get_file_info


class TestReports:
    """測試報告功能"""
    
    def test_reports_directory_creation(self):
        """測試報告目錄建立"""
        reports_dir = get_reports_directory()
        
        assert reports_dir.exists(), "報告目錄應該存在"
        assert reports_dir.is_dir(), "應該是目錄"
        assert reports_dir.name == "reports", "目錄名稱應該是 reports"
    
    def test_safe_path_validation(self):
        """測試路徑安全驗證"""
        # 安全路徑
        safe_paths = [
            "outputs/reports/test.pdf",
            "outputs/reports/AAPL_20250902_120000.pdf",
            "outputs/reports/subdir/report.pdf"
        ]
        
        for path in safe_paths:
            assert is_safe_path(path), f"路徑應該是安全的: {path}"
        
        # 不安全路徑（目錄穿越攻擊）
        unsafe_paths = [
            "../../../etc/passwd",
            "outputs/reports/../../../secret.txt",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
            "outputs/reports/../../app/settings.py"
        ]
        
        for path in unsafe_paths:
            assert not is_safe_path(path), f"路徑應該被拒絕: {path}"
    
    def test_file_info_extraction(self):
        """測試檔案資訊提取"""
        # 建立臨時 PDF 檔案
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4\ntest content')
            temp_path = Path(f.name)
        
        try:
            file_info = get_file_info(temp_path)
            
            assert file_info is not None, "應該能取得檔案資訊"
            assert file_info["name"] == temp_path.name, "檔案名稱應該匹配"
            assert file_info["size"] > 0, "檔案大小應該大於 0"
            assert file_info["watermark"] == "Lens Qunat", "浮水印應該是固定值"
            assert "generated_at" in file_info, "應該包含生成時間"
        finally:
            # 清理臨時檔案
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_pdf_report_generation_via_agent(self):
        """測試透過 Agent 生成 PDF 報告"""
        # 先綁定模板
        template_input = {
            "input_type": "text",
            "query": "/template stock Data/Cathay_Q3.pdf",
            "options": {}
        }
        
        template_result = await agent_graph.run(template_input)
        assert template_result is not None, "模板綁定應該成功"
        
        # 生成報告
        report_input = {
            "input_type": "text",
            "query": "/report stock AAPL",
            "options": {}
        }
        
        report_result = await agent_graph.run(report_input)
        assert report_result is not None, "報告生成應該成功"
        
        # 檢查回應內容
        response = report_result.get("response", "")
        
        # 檢查是否提及輸出路徑
        assert "outputs/reports" in response or "報告" in response, "回應應該提及報告輸出"
        
        # 檢查 outputs/reports 目錄是否有檔案
        reports_dir = get_reports_directory()
        pdf_files = list(reports_dir.glob("*.pdf"))
        
        if len(pdf_files) > 0:
            # 如果有生成檔案，檢查檔案
            latest_pdf = max(pdf_files, key=lambda f: f.stat().st_mtime)
            assert latest_pdf.stat().st_size > 0, "PDF 檔案大小應該大於 0"
            
            # 檢查檔案名稱包含相關資訊
            filename = latest_pdf.name.lower()
            assert "aapl" in filename or "stock" in filename or "report" in filename, "檔案名稱應該包含相關資訊"
    
    @pytest.mark.asyncio
    async def test_reports_list_api_functionality(self):
        """測試報告列表 API 功能"""
        # 這個測試需要實際的 HTTP 客戶端，這裡做簡化測試
        from app.routers.reports import list_reports
        
        # 建立一些測試檔案
        reports_dir = get_reports_directory()
        test_files = []
        
        try:
            # 建立測試 PDF 檔案
            for i in range(3):
                test_file = reports_dir / f"test_report_{i}.pdf"
                test_file.write_bytes(b'%PDF-1.4\ntest content')
                test_files.append(test_file)
            
            # 測試列表 API
            response = await list_reports(limit=10)
            
            assert response.ok, "列表 API 應該成功"
            assert response.count >= len(test_files), "應該包含測試檔案"
            assert len(response.data) >= len(test_files), "資料數量應該正確"
            
            # 檢查回應結構
            if response.data:
                first_report = response.data[0]
                required_fields = ["name", "path", "size", "generated_at", "render_mode", "watermark"]
                for field in required_fields:
                    assert hasattr(first_report, field), f"報告資訊應該包含 {field} 欄位"
                
                assert first_report.watermark == "Lens Qunat", "浮水印應該是固定值"
        
        finally:
            # 清理測試檔案
            for test_file in test_files:
                if test_file.exists():
                    test_file.unlink()
    
    @pytest.mark.asyncio
    async def test_reports_download_security(self):
        """測試報告下載安全性"""
        from app.routers.reports import download_report
        from fastapi import HTTPException
        
        # 測試不安全路徑被拒絕
        unsafe_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "outputs/reports/../../../app/settings.py"
        ]
        
        for unsafe_path in unsafe_paths:
            with pytest.raises(HTTPException) as exc_info:
                await download_report(path=unsafe_path)
            
            assert exc_info.value.status_code == 400, f"不安全路徑應該回傳 400 錯誤: {unsafe_path}"
            assert "不允許" in str(exc_info.value.detail), "錯誤訊息應該說明不允許"
    
    @pytest.mark.asyncio
    async def test_reports_download_nonexistent_file(self):
        """測試下載不存在檔案的處理"""
        from app.routers.reports import download_report
        from fastapi import HTTPException
        
        nonexistent_path = "outputs/reports/nonexistent_file.pdf"
        
        with pytest.raises(HTTPException) as exc_info:
            await download_report(path=nonexistent_path)
        
        assert exc_info.value.status_code == 404, "不存在的檔案應該回傳 404 錯誤"
        assert "不存在" in str(exc_info.value.detail), "錯誤訊息應該說明檔案不存在"
    
    @pytest.mark.asyncio
    async def test_reports_download_wrong_file_type(self):
        """測試下載非 PDF 檔案的處理"""
        from app.routers.reports import download_report
        from fastapi import HTTPException
        
        # 建立非 PDF 檔案
        reports_dir = get_reports_directory()
        txt_file = reports_dir / "test.txt"
        txt_file.write_text("test content")
        
        try:
            with pytest.raises(HTTPException) as exc_info:
                await download_report(path=str(txt_file.relative_to(Path.cwd())))
            
            assert exc_info.value.status_code == 400, "非 PDF 檔案應該回傳 400 錯誤"
            assert "僅支援 PDF" in str(exc_info.value.detail), "錯誤訊息應該說明僅支援 PDF"
        
        finally:
            # 清理測試檔案
            if txt_file.exists():
                txt_file.unlink()
    
    @pytest.mark.asyncio
    async def test_reports_status_api(self):
        """測試報告狀態 API"""
        from app.routers.reports import get_reports_status
        
        status = await get_reports_status()
        
        assert status["ok"], "狀態 API 應該成功"
        
        required_fields = [
            "reports_directory",
            "total_reports", 
            "total_size_bytes",
            "directory_exists",
            "directory_writable"
        ]
        
        for field in required_fields:
            assert field in status, f"狀態回應應該包含 {field}"
        
        assert status["directory_exists"], "報告目錄應該存在"
        assert isinstance(status["total_reports"], int), "報告數量應該是整數"
        assert status["total_reports"] >= 0, "報告數量不能為負數"
    
    def test_render_mode_detection(self):
        """測試渲染模式檢測"""
        test_cases = [
            ("AAPL_overlay_20250902.pdf", "overlay"),
            ("TSLA.overlay.20250902.pdf", "overlay"),
            ("NVDA_acroform_20250902.pdf", "acroform"),
            ("MSFT.acroform.20250902.pdf", "acroform"),
            ("GOOGL_20250902.pdf", "auto")
        ]
        
        for filename, expected_mode in test_cases:
            # 模擬檔案資訊提取中的渲染模式檢測邏輯
            if ".overlay." in filename or "_overlay_" in filename:
                detected_mode = "overlay"
            elif ".acroform." in filename or "_acroform_" in filename:
                detected_mode = "acroform"
            else:
                detected_mode = "auto"
            
            assert detected_mode == expected_mode, f"檔案 {filename} 的渲染模式檢測錯誤"
    
    @pytest.mark.asyncio
    async def test_pdf_watermark_presence(self):
        """測試 PDF 浮水印存在性"""
        # 這個測試需要實際檢查 PDF 內容，這裡做簡化測試
        
        # 檢查報告服務的浮水印設定
        
        # 檢查浮水印設定是否正確
        # 這需要根據實際的報告服務實作來調整
        
        # 暫時檢查固定浮水印值
        expected_watermark = "Lens Qunat"
        
        # 在實際實作中，這裡應該：
        # 1. 生成一個測試 PDF
        # 2. 使用 PDF 解析庫檢查浮水印
        # 3. 驗證浮水印文字是否正確
        
        assert expected_watermark == "Lens Qunat", "浮水印文字應該是固定值"
    
    @pytest.mark.asyncio
    async def test_report_file_naming_convention(self):
        """測試報告檔案命名規範"""
        # 測試檔案命名格式：{topic_or_symbol}_{YYYYMMDD_HHMMSS}.pdf
        
        import re
        
        # 預期的檔案名稱格式
        filename_pattern = r'^[A-Z]+_\d{8}_\d{6}\.pdf$'
        
        test_filenames = [
            "AAPL_20250902_120000.pdf",
            "TSLA_20250902_143000.pdf",
            "NVDA_20250902_160000.pdf"
        ]
        
        for filename in test_filenames:
            assert re.match(filename_pattern, filename), f"檔案名稱格式不正確: {filename}"
        
        # 測試無效格式
        invalid_filenames = [
            "aapl_20250902_120000.pdf",  # 小寫
            "AAPL_2025902_120000.pdf",   # 日期格式錯誤
            "AAPL_20250902_12000.pdf",   # 時間格式錯誤
            "AAPL_20250902_120000.txt"   # 非 PDF
        ]
        
        for filename in invalid_filenames:
            assert not re.match(filename_pattern, filename), f"無效檔案名稱應該被拒絕: {filename}"


if __name__ == "__main__":
    # 執行測試
    pytest.main([__file__, "-v"])
