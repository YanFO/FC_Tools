"""
檔案處理測試
測試檔案載入、RAG 和報告生成功能
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import sys

# 加入專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.file_ingest import FileIngestService
from app.services.rag import RAGService
from app.services.report import ReportService


class TestFileIngestService:
    """檔案處理服務測試"""
    
    @pytest.fixture
    def temp_text_file(self):
        """建立臨時文字檔案"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("這是一個測試文件。\n\n包含多個段落的內容。\n\n用於測試檔案處理功能。")
            temp_path = f.name
        
        yield temp_path
        
        # 清理
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def temp_markdown_file(self):
        """建立臨時 Markdown 檔案"""
        content = """# 測試文件

## 第一章節

這是第一章節的內容。

## 第二章節

這是第二章節的內容，包含一些重要資訊。

### 子章節

更詳細的內容在這裡。
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        yield temp_path
        
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_is_supported_file(self):
        """測試支援的檔案格式檢查"""
        service = FileIngestService()
        
        assert service.is_supported_file("test.pdf") is True
        assert service.is_supported_file("test.docx") is True
        assert service.is_supported_file("test.txt") is True
        assert service.is_supported_file("test.md") is True
        assert service.is_supported_file("test.markdown") is True
        assert service.is_supported_file("test.jpg") is False
        assert service.is_supported_file("test.xlsx") is False
    
    @pytest.mark.asyncio
    async def test_load_text_file(self, temp_text_file):
        """測試載入文字檔案"""
        service = FileIngestService()
        
        result = await service.load_file(temp_text_file)
        
        assert result["ok"] is True
        assert "data" in result
        assert result["data"]["file_type"] == ".txt"
        assert "測試文件" in result["data"]["content"]
        assert result["data"]["page_count"] == 1
    
    @pytest.mark.asyncio
    async def test_load_markdown_file(self, temp_markdown_file):
        """測試載入 Markdown 檔案"""
        service = FileIngestService()
        
        result = await service.load_file(temp_markdown_file)
        
        assert result["ok"] is True
        assert result["data"]["file_type"] == ".md"
        assert "測試文件" in result["data"]["content"]
        assert "第一章節" in result["data"]["content"]
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self):
        """測試載入不存在的檔案"""
        service = FileIngestService()
        
        result = await service.load_file("nonexistent.txt")
        
        assert result["ok"] is False
        assert result["reason"] == "file_not_found"
    
    @pytest.mark.asyncio
    async def test_load_unsupported_file(self):
        """測試載入不支援的檔案格式"""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            service = FileIngestService()
            result = await service.load_file(temp_path)
            
            assert result["ok"] is False
            assert result["reason"] == "unsupported_format"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_chunk_text_simple(self):
        """測試簡單文字分塊"""
        service = FileIngestService()
        text = "這是第一段。\n\n這是第二段。\n\n這是第三段。"
        
        chunks = service.chunk_text(text, chunk_size=20, chunk_overlap=5)
        
        assert len(chunks) > 0
        assert all("id" in chunk for chunk in chunks)
        assert all("text" in chunk for chunk in chunks)
        assert all("start_char" in chunk for chunk in chunks)
        assert all("end_char" in chunk for chunk in chunks)
    
    def test_chunk_text_preserve_structure(self):
        """測試保持結構的文字分塊"""
        service = FileIngestService()
        text = "第一段落內容。\n\n第二段落內容。\n\n第三段落內容。"
        
        chunks = service.chunk_text(text, chunk_size=50, preserve_structure=True)
        
        assert len(chunks) > 0
        # 檢查是否保持段落邊界
        for chunk in chunks:
            assert not chunk["text"].startswith("\n")
            assert not chunk["text"].endswith("\n\n")
    
    @pytest.mark.asyncio
    async def test_process_file_complete(self, temp_text_file):
        """測試完整檔案處理流程"""
        service = FileIngestService()
        
        result = await service.process_file(temp_text_file, chunk_size=100)
        
        assert result["ok"] is True
        assert "file_info" in result["data"]
        assert "content" in result["data"]
        assert "chunks" in result["data"]
        assert "chunk_count" in result["data"]
        assert result["data"]["chunk_count"] > 0


class TestRAGService:
    """RAG 服務測試"""
    
    @pytest.fixture
    def mock_rag_service(self):
        """建立模擬的 RAG 服務"""
        service = RAGService()
        # 模擬有 OpenAI 客戶端
        service.openai_client = MagicMock()
        return service
    
    def test_check_embedding_capability_no_client(self):
        """測試沒有 OpenAI 客戶端的情況"""
        service = RAGService()
        service.openai_client = None
        
        result = service._check_embedding_capability()
        
        assert result["ok"] is False
        assert result["reason"] == "missing_api_key"
    
    def test_check_embedding_capability_with_client(self, mock_rag_service):
        """測試有 OpenAI 客戶端的情況"""
        result = mock_rag_service._check_embedding_capability()
        
        assert result["ok"] is True
    
    @pytest.mark.asyncio
    async def test_create_embeddings_success(self, mock_rag_service):
        """測試成功建立嵌入向量"""
        # 模擬 OpenAI API 回應
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6])
        ]
        
        mock_rag_service.openai_client.embeddings.create = AsyncMock(return_value=mock_response)
        
        texts = ["第一段文字", "第二段文字"]
        result = await mock_rag_service.create_embeddings(texts)
        
        assert result["ok"] is True
        assert len(result["data"]["embeddings"]) == 2
        assert result["data"]["count"] == 2
    
    @pytest.mark.asyncio
    async def test_create_embeddings_no_client(self):
        """測試沒有客戶端時建立嵌入向量"""
        service = RAGService()
        service.openai_client = None
        
        result = await service.create_embeddings(["test"])
        
        assert result["ok"] is False
        assert result["reason"] == "missing_api_key"
    
    @pytest.mark.asyncio
    async def test_add_documents_success(self, mock_rag_service):
        """測試成功加入文件"""
        # 模擬嵌入向量建立
        mock_rag_service.create_embeddings = AsyncMock(return_value={
            "ok": True,
            "data": {
                "embeddings": [[0.1, 0.2], [0.3, 0.4]],
                "count": 2
            }
        })
        
        chunks = [
            {"id": 0, "text": "第一段", "start_char": 0, "end_char": 10, "length": 10},
            {"id": 1, "text": "第二段", "start_char": 11, "end_char": 20, "length": 9}
        ]
        
        file_info = {
            "path": "/test/file.txt",
            "name": "file.txt",
            "type": ".txt"
        }
        
        result = await mock_rag_service.add_documents(chunks, file_info)
        
        assert result["ok"] is True
        assert result["data"]["chunks_added"] == 2
        assert result["data"]["embeddings_created"] == 2
    
    @pytest.mark.asyncio
    async def test_query_documents_success(self, mock_rag_service):
        """測試成功查詢文件"""
        # 模擬查詢嵌入向量建立
        mock_rag_service.create_embeddings = AsyncMock(return_value={
            "ok": True,
            "data": {
                "embeddings": [[0.1, 0.2, 0.3]]
            }
        })
        
        # 模擬向量搜尋結果
        mock_rag_service.vector_store.search = MagicMock(return_value=[
            ({"text": "相關文字", "file_name": "test.txt", "chunk_id": 0, "start_char": 0, "end_char": 10}, 0.9)
        ])
        
        result = await mock_rag_service.query_documents("測試問題")
        
        assert result["ok"] is True
        assert len(result["data"]["relevant_chunks"]) == 1
        assert result["data"]["relevant_chunks"][0]["similarity"] == 0.9


class TestReportService:
    """報告服務測試"""
    
    @pytest.fixture
    def temp_template_dir(self):
        """建立臨時模板目錄"""
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        template_dir = Path(temp_dir) / "templates" / "reports"
        template_dir.mkdir(parents=True)
        
        # 建立測試模板
        test_template = template_dir / "test_template.j2"
        test_template.write_text("""# 測試報告

**生成時間：** {{ generated_at }}
**標題：** {{ title or "預設標題" }}

## 內容

{{ content or "沒有內容" }}

## 項目列表

{% if items %}
{% for item in items %}
- {{ item }}
{% endfor %}
{% else %}
沒有項目
{% endif %}
""", encoding='utf-8')
        
        yield template_dir
        
        # 清理
        shutil.rmtree(temp_dir)
    
    def test_report_service_initialization(self):
        """測試報告服務初始化"""
        service = ReportService()
        
        assert service.jinja_env is not None
        assert service.templates_dir is not None
        assert service.output_dir is not None
    
    def test_custom_filters(self):
        """測試自定義過濾器"""
        service = ReportService()
        
        # 測試 format_number 過濾器
        format_number = service.jinja_env.filters['format_number']
        assert format_number(1234.567, 2) == "1,234.57"
        assert format_number(None) == "N/A"
        
        # 測試 format_percentage 過濾器
        format_percentage = service.jinja_env.filters['format_percentage']
        assert format_percentage(12.345, 2) == "12.35%"
        
        # 測試 truncate_text 過濾器
        truncate_text = service.jinja_env.filters['truncate_text']
        long_text = "這是一段很長的文字" * 10
        truncated = truncate_text(long_text, 20)
        assert len(truncated) <= 23  # 20 + "..."
    
    @pytest.mark.asyncio
    async def test_generate_report_success(self, temp_template_dir):
        """測試成功生成報告"""
        service = ReportService()
        service.templates_dir = temp_template_dir
        
        context = {
            "title": "測試報告標題",
            "content": "這是測試內容",
            "items": ["項目1", "項目2", "項目3"]
        }
        
        result = await service.generate_report("test_template", context)
        
        assert result["ok"] is True
        assert "output_path" in result["data"]
        assert "report_id" in result["data"]
        
        # 檢查生成的檔案
        output_path = Path(result["data"]["output_path"])
        assert output_path.exists()
        
        content = output_path.read_text(encoding='utf-8')
        assert "測試報告標題" in content
        assert "這是測試內容" in content
        assert "項目1" in content
    
    @pytest.mark.asyncio
    async def test_generate_report_template_not_found(self):
        """測試模板不存在的情況"""
        service = ReportService()
        
        result = await service.generate_report("nonexistent_template", {})
        
        assert result["ok"] is False
        assert result["reason"] == "template_not_found"
    
    def test_list_templates(self, temp_template_dir):
        """測試列出模板"""
        service = ReportService()
        service.templates_dir = temp_template_dir
        
        templates = service.list_templates()

        # 現在有兩個 test_template：PDF 版本和 J2 版本
        assert len(templates) >= 1

        # 檢查是否包含 test_template
        template_ids = [t["id"] for t in templates]
        assert "test_template" in template_ids

        # 檢查 PDF 版本的 test_template
        pdf_template = next((t for t in templates if t["id"] == "test_template" and "PDF" in t["name"]), None)
        assert pdf_template is not None
        assert "測試模板 (PDF)" in pdf_template["name"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
