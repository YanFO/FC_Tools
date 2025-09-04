"""
測試 CLI File Report 功能
"""
import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

# 加入專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graphs.agent_graph import build_graph


class TestCLIFileReport:
    """測試 CLI File Report 功能"""

    @pytest.mark.asyncio
    async def test_file_report_generates_output_file(self):
        """測試 File Agent 報告任務會產檔並返回 REPORT 結果"""
        # 創建臨時測試檔案
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            test_file_path = f.name
            f.write("Test PDF content")
        
        try:
            # Mock 相關服務
            with patch("app.graphs.agent_graph.file_ingest_service.process_file", new=AsyncMock(return_value={
                "ok": True,
                "source": "FILE",
                "data": {"content": "Test file content", "metadata": {"pages": 1}}
            })), \
            patch("app.graphs.agent_graph.report_service.generate_report", new=AsyncMock(return_value={
                "ok": True,
                "source": "REPORT",
                "data": {
                    "template_id": "stock",
                    "output_path": "/tmp/test_report.md",
                    "output_filename": "stock_20250901_12345678.md",
                    "file_size": 1024,
                    "generated_at": "2025-09-01T12:00:00"
                }
            })):
                graph = build_graph()
                
                result = await graph.ainvoke({
                    "input_type": "file",
                    "file_info": {
                        "path": test_file_path,
                        "task": "report",
                        "template_id": "stock"
                    },
                    "messages": [],
                    "warnings": [],
                    "sources": [],
                    "tool_loop_count": 0,
                    "tool_call_sigs": []
                }, config={"recursion_limit": 8})
                
                final_response = result.get("final_response", {})
                
                # 應該成功執行
                assert final_response.get("ok") is True
                
                # 應該有工具結果
                tool_results = final_response.get("tool_results", [])
                print(f"Tool results count: {len(tool_results)}")
                for i, tr in enumerate(tool_results):
                    print(f"Tool result {i}: {tr}")
                assert len(tool_results) > 0

                # 檢查是否有 REPORT 結果
                report_results = [tr for tr in tool_results
                                if isinstance(tr, dict) and tr.get("source") == "REPORT"]
                print(f"Report results: {report_results}")
                assert len(report_results) > 0, "應該有 REPORT 工具結果"
                
                # 檢查 REPORT 結果的內容
                report_result = report_results[0]
                assert report_result.get("ok") is True
                assert "output_path" in report_result.get("data", {})
                assert report_result["data"]["template_id"] == "stock"
                
        finally:
            # 清理臨時檔案
            Path(test_file_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_single_line_path_file_resolution(self):
        """測試單行路徑檔自動解析功能"""
        # 創建真實的目標檔案
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as target_file:
            target_path = target_file.name
            target_file.write("Target PDF content")
        
        # 創建單行路徑檔
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as path_file:
            path_file_path = path_file.name
            path_file.write(target_path)  # 只寫入目標檔案路徑
        
        try:
            # Mock 相關服務
            with patch("app.graphs.agent_graph.file_ingest_service.load_file", new=AsyncMock(return_value={
                "ok": True,
                "source": "FILE",
                "data": {"content": "Target file content", "metadata": {"pages": 1}}
            })), \
            patch("app.services.report.ReportService.generate_report", new=AsyncMock(return_value={
                "ok": True,
                "source": "REPORT",
                "data": {
                    "template_id": "stock",
                    "output_path": "/tmp/test_report.md",
                    "output_filename": "stock_20250901_12345678.md"
                }
            })):
                graph = build_graph()
                
                result = await graph.ainvoke({
                    "input_type": "file",
                    "file_info": {
                        "path": path_file_path,  # 使用路徑檔
                        "task": "report",
                        "template_id": "stock"
                    },
                    "messages": [],
                    "warnings": [],
                    "sources": [],
                    "tool_loop_count": 0,
                    "tool_call_sigs": []
                }, config={"recursion_limit": 8})
                
                final_response = result.get("final_response", {})
                
                # 應該成功執行
                assert final_response.get("ok") is True
                
                # 應該有 REPORT 結果
                tool_results = final_response.get("tool_results", [])
                report_results = [tr for tr in tool_results 
                                if isinstance(tr, dict) and tr.get("source") == "REPORT"]
                assert len(report_results) > 0, "應該有 REPORT 工具結果"
                
        finally:
            # 清理臨時檔案
            Path(target_path).unlink(missing_ok=True)
            Path(path_file_path).unlink(missing_ok=True)

    def test_cli_argument_validation(self):
        """測試 CLI 參數驗證"""
        from app.agent_cli import validate_arguments
        import argparse
        
        # 測試缺少 --file 參數
        args = argparse.Namespace(
            input_type="file",
            file=None,
            task="report",
            template_id="stock"
        )
        error = validate_arguments(args)
        assert error is not None
        assert "需要 --file 指向實體檔案" in error
        
        # 測試缺少 --template-id 參數
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            args = argparse.Namespace(
                input_type="file",
                file=f.name,
                task="report",
                template_id=None
            )
            error = validate_arguments(args)
            assert error is not None
            assert "report 任務需要 --template-id" in error
