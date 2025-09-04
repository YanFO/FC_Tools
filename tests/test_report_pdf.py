"""
PDF 报告生成测试
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

from app.services.report import ReportService


class TestReportPDF:
    """PDF 报告生成测试类"""
    
    @pytest.fixture
    def report_service(self):
        """创建报告服务实例"""
        return ReportService()
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_pdf_template_registration(self, report_service):
        """测试 PDF 模板注册"""
        # 使用测试 PDF 文件
        pdf_path = Path("tests/fixtures/templates/stock_acroform.pdf")
        
        # 注册模板
        result = report_service.set_template_override("stock", str(pdf_path))
        
        assert result["ok"] is True
        assert result["template_id"] == "stock"
        assert result["template_type"] == ".pdf"
        assert "pdf_mode" in result
        assert result["pdf_mode"] in ["acroform", "overlay"]
    
    @pytest.mark.asyncio
    async def test_report_stock_pdf_output(self, report_service, temp_dir):
        """测试股票 PDF 报告输出"""
        # Mock PDF 功能
        with patch("app.services.report.PDF_AVAILABLE", True), \
             patch.object(report_service, "fill_pdf_acroform", return_value=b"fake_pdf_content"), \
             patch.object(report_service, "add_watermark_or_header", return_value=b"fake_pdf_with_watermark"):
            
            # 注册 PDF 模板
            pdf_path = Path("tests/fixtures/templates/stock_acroform.pdf")
            report_service.set_template_override("stock", str(pdf_path))
            
            # 生成报告
            context = {
                "company_name": "Apple Inc.",
                "ticker": "AAPL",
                "price": "150.00",
                "market_cap": "2.5T"
            }
            
            result = await report_service.generate_report(
                template_id="stock",
                context=context,
                output_format="pdf"
            )
            
            assert result["ok"] is True
            assert result["source"] == "REPORT"
            assert result["data"]["mime"] == "application/pdf"
            assert result["data"]["output_path"].endswith(".pdf")
            assert Path(result["data"]["output_path"]).exists()
            assert Path(result["data"]["output_path"]).stat().st_size > 0
    
    @pytest.mark.asyncio
    async def test_report_pdf_acroform_fill(self, report_service):
        """测试 PDF AcroForm 填充"""
        # Mock PyMuPDF
        mock_doc = MagicMock()
        mock_doc.write.return_value = b"filled_pdf_content"
        mock_doc.__len__.return_value = 1
        
        mock_page = MagicMock()
        mock_widget = MagicMock()
        mock_widget.field_name = "company_name"
        mock_page.widgets.return_value = [mock_widget]
        mock_doc.__getitem__.return_value = mock_page
        
        with patch("app.services.report.PDF_AVAILABLE", True), \
             patch("app.services.report.fitz.open", return_value=mock_doc):
            
            mapping = {"company_name": "Apple Inc.", "ticker": "AAPL"}
            result = report_service.fill_pdf_acroform("fake_template.pdf", mapping)
            
            assert result == b"filled_pdf_content"
            assert mock_widget.field_value == "Apple Inc."
            mock_widget.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_report_pdf_overlay(self, report_service):
        """测试 PDF Overlay 疊印"""
        # Mock PyMuPDF
        mock_doc = MagicMock()
        mock_doc.write.return_value = b"overlay_pdf_content"
        mock_doc.__len__.return_value = 2
        
        mock_page = MagicMock()
        mock_doc.__getitem__.return_value = mock_page
        
        with patch("app.services.report.PDF_AVAILABLE", True), \
             patch("app.services.report.fitz.open", return_value=mock_doc):
            
            layout_spec = {
                "defaults": {"font": "helv", "size": 10, "color": "#000000"},
                "fields": [
                    {"name": "company_name", "page": 0, "x": 72, "y": 96, "size": 14},
                    {"name": "ticker", "page": 0, "x": 72, "y": 120}
                ]
            }
            
            mapping = {"company_name": "Apple Inc.", "ticker": "AAPL"}
            result = report_service.overlay_pdf("fake_template.pdf", layout_spec, mapping)
            
            assert result == b"overlay_pdf_content"
            # 验证文字插入被调用
            assert mock_page.insert_text.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cli_pdf_output_file_flag(self, temp_dir):
        """测试 CLI PDF 输出文件标志"""
        
        output_file = temp_dir / "msft.pdf"
        
        # Mock 相关服务
        with patch("app.agent_cli.agent_graph") as mock_graph, \
             patch("app.services.report.PDF_AVAILABLE", True):
            
            # Mock agent 返回结果
            mock_graph.run.return_value = {
                "ok": True,
                "response": "报告已生成",
                "tool_results": [{
                    "ok": True,
                    "source": "REPORT",
                    "data": {
                        "output_path": str(output_file),
                        "mime": "application/pdf",
                        "template_id": "stock"
                    }
                }]
            }
            
            # 创建假的 PDF 文件
            output_file.write_bytes(b"fake_pdf_content")
            
            # 测试 CLI 调用
            import sys
            test_args = [
                "agent_cli.py",
                "--input-type", "text",
                "--query", "/report stock MSFT",
                "--output-format", "pdf",
                "--output-file", str(output_file)
            ]
            
            with patch.object(sys, 'argv', test_args):
                # 这里我们主要测试参数解析，实际执行会很复杂
                from app.agent_cli import setup_argument_parser
                parser = setup_argument_parser()
                args = parser.parse_args(test_args[1:])
                
                assert args.output_format == "pdf"
                assert args.output_file == str(output_file)
    
    def test_markdown_to_pdf_conversion(self, report_service):
        """测试 Markdown 到 PDF 转换"""
        markdown_content = """
# Test Report

## Summary
This is a test report.

| Item | Value |
|------|-------|
| Stock | AAPL |
| Price | $150 |
        """
        
        # Mock WeasyPrint
        mock_html_doc = MagicMock()
        mock_html_doc.write_pdf.return_value = b"converted_pdf_content"
        
        with patch("app.services.report.PDF_AVAILABLE", True), \
             patch("app.services.report.weasyprint.HTML", return_value=mock_html_doc), \
             patch("app.services.report.weasyprint.CSS"), \
             patch.object(report_service, "add_watermark_or_header", return_value=b"final_pdf_content"):
            
            result = asyncio.run(report_service._convert_to_pdf(markdown_content, "test"))
            
            assert result == b"final_pdf_content"
            mock_html_doc.write_pdf.assert_called_once()
    
    def test_watermark_addition(self, report_service):
        """测试浮水印添加"""
        # Mock PyMuPDF
        mock_doc = MagicMock()
        mock_doc.write.return_value = b"watermarked_pdf"
        mock_doc.__len__.return_value = 1
        
        mock_page = MagicMock()
        mock_page.rect.width = 612
        mock_page.rect.height = 792
        mock_doc.__getitem__.return_value = mock_page
        
        with patch("app.services.report.PDF_AVAILABLE", True), \
             patch("app.services.report.fitz.open", return_value=mock_doc):
            
            result = report_service.add_watermark_or_header(b"original_pdf", "Lens Qunat")
            
            assert result == b"watermarked_pdf"
            mock_page.insert_textbox.assert_called_once()
            
            # 验证浮水印参数
            call_args = mock_page.insert_textbox.call_args
            assert "Lens Qunat" in call_args[0]  # 文字内容
            assert call_args[1]["rotate"] == 45  # 旋转角度
    
    @pytest.mark.asyncio
    async def test_pdf_fallback_when_weasyprint_unavailable(self, report_service):
        """测试 WeasyPrint 不可用时的备用方案"""
        with patch("app.services.report.PDF_AVAILABLE", False):
            
            result = await report_service._convert_to_pdf("test content", "test")
            
            # 应该返回最小的 PDF 内容
            assert result.startswith(b'%PDF-1.4')
            assert b'%%EOF' in result
