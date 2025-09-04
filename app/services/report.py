"""
報告生成服務
使用 Jinja2 模板生成 Markdown 和其他格式的報告，支援 PDF 模板與 PDF 輸出
"""
import logging
import uuid
import os
import shutil
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import json
import markdown

from jinja2 import Environment, FileSystemLoader, Template
from jinja2.exceptions import TemplateError, TemplateNotFound

from app.settings import settings

# PDF 相關導入（可選，用於測試時 mock）
try:
    import weasyprint
    import fitz  # PyMuPDF
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    weasyprint = None
    fitz = None
    canvas = None
    A4 = None


logger = logging.getLogger(__name__)

# 測試模板路徑
TEST_TEMPLATE_PATH = os.getenv("TEST_TEMPLATE_PATH", "/home/user/yorick_projects/Agent-Only LangGraph Service/Data/Cathay_Q3.pdf")


class ReportService:
    """報告生成服務類別"""

    def __init__(self):
        self.templates_dir = Path("templates/reports")
        self.output_dir = Path(settings.output_dir) / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 模板覆寫表
        self.template_overrides = {}  # e.g. {"stock": "/path/to/xxx.md"}

        # 初始化 Jinja2 環境
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,  # Markdown 不需要自動轉義
            trim_blocks=True,
            lstrip_blocks=True
        )

        # 註冊自定義過濾器
        self._register_filters()

        # PDF 相關設定
        self.pdf_resources_dir = Path("resources/pdf")
        self.pdf_resources_dir.mkdir(parents=True, exist_ok=True)

    def render_pdf_from_html(self, html: str, css_paths: Optional[List[str]] = None) -> bytes:
        """從 HTML 渲染 PDF"""
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF 功能不可用，請安裝 weasyprint")

        # 預設 CSS
        if css_paths is None:
            default_css = self.pdf_resources_dir / "default.css"
            css_paths = [str(default_css)] if default_css.exists() else []

        # 使用 WeasyPrint 渲染
        html_doc = weasyprint.HTML(string=html)
        css_docs = [weasyprint.CSS(filename=css_path) for css_path in css_paths if Path(css_path).exists()]

        return html_doc.write_pdf(stylesheets=css_docs)

    def fill_pdf_acroform(self, template_pdf_path: str, mapping: Dict[str, Any]) -> bytes:
        """填充 PDF AcroForm 欄位"""
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF 功能不可用，請安裝 PyMuPDF")

        # 開啟 PDF
        doc = fitz.open(template_pdf_path)

        # 填充表單欄位
        for page_num in range(len(doc)):
            page = doc[page_num]
            widgets = page.widgets()

            for widget in widgets:
                field_name = widget.field_name
                if field_name in mapping:
                    widget.field_value = str(mapping[field_name])
                    widget.update()

        # 平坦化表單（使欄位不可編輯）
        for page_num in range(len(doc)):
            page = doc[page_num]
            page.apply_redactions()

        # 返回 PDF 字節
        pdf_bytes = doc.write()
        doc.close()

        return pdf_bytes

    def overlay_pdf(self, template_pdf_path: str, layout_spec: Dict[str, Any], mapping: Dict[str, Any]) -> bytes:
        """在 PDF 上疊印文字"""
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF 功能不可用，請安裝 PyMuPDF")

        # 開啟 PDF
        doc = fitz.open(template_pdf_path)

        # 取得預設設定
        defaults = layout_spec.get("defaults", {})
        default_font = defaults.get("font", "helv")
        default_size = defaults.get("size", 10)
        default_color = defaults.get("color", "#000000")

        # 處理每個欄位
        for field in layout_spec.get("fields", []):
            field_name = field["name"]
            if field_name not in mapping:
                continue

            page_num = field["page"]
            x = field["x"]
            y = field["y"]
            font_size = field.get("size", default_size)
            text = str(mapping[field_name])

            if page_num < len(doc):
                page = doc[page_num]
                # 插入文字
                page.insert_text(
                    (x, y),
                    text,
                    fontsize=font_size,
                    color=fitz.utils.getColor(default_color)
                )

        # 返回 PDF 字節
        pdf_bytes = doc.write()
        doc.close()

        return pdf_bytes

    def add_watermark_or_header(self, pdf_bytes: bytes, text: str = "Lens Qunat") -> bytes:
        """添加浮水印或頁眉"""
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF 功能不可用，請安裝 PyMuPDF")

        # 開啟 PDF
        doc = fitz.open("pdf", pdf_bytes)

        # 在每頁添加浮水印
        for page_num in range(len(doc)):
            page = doc[page_num]
            rect = page.rect

            # 添加浮水印（中央，旋轉 45 度）
            center_x = rect.width / 2
            center_y = rect.height / 2

            # 創建文字對象
            text_rect = fitz.Rect(center_x - 100, center_y - 20, center_x + 100, center_y + 20)
            page.insert_textbox(
                text_rect,
                text,
                fontsize=72,
                color=(0.8, 0.8, 0.8),  # 淺灰色
                align=fitz.TEXT_ALIGN_CENTER,
                rotate=45
            )

        # 返回修改後的 PDF
        result_bytes = doc.write()
        doc.close()

        return result_bytes
    
    def _register_filters(self):
        """註冊自定義 Jinja2 過濾器"""

        def format_number(value, decimals=2):
            """格式化數字"""
            if value is None:
                return "N/A"
            try:
                return f"{float(value):,.{decimals}f}"
            except (ValueError, TypeError):
                return str(value)

        def format_percentage(value, decimals=2):
            """格式化百分比"""
            if value is None:
                return "N/A"
            try:
                return f"{float(value):.{decimals}f}%"
            except (ValueError, TypeError):
                return str(value)

        def format_date(value, format_str="%Y-%m-%d"):
            """格式化日期"""
            if value is None:
                return "N/A"
            if isinstance(value, str):
                try:
                    # 嘗試解析 ISO 格式日期
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return dt.strftime(format_str)
                except ValueError:
                    return value
            elif isinstance(value, datetime):
                return value.strftime(format_str)
            return str(value)

        def truncate_text(value, length=100, suffix="..."):
            """截斷文字"""
            if value is None:
                return ""
            text = str(value)
            if len(text) <= length:
                return text
            return text[:length].rstrip() + suffix

        def to_json(value, indent=2):
            """轉換為 JSON 格式"""
            try:
                return json.dumps(value, ensure_ascii=False, indent=indent)
            except (TypeError, ValueError):
                return str(value)

        # 註冊過濾器
        self.jinja_env.filters['format_number'] = format_number
        self.jinja_env.filters['format_percentage'] = format_percentage
        self.jinja_env.filters['format_date'] = format_date
        self.jinja_env.filters['truncate_text'] = truncate_text
        self.jinja_env.filters['to_json'] = to_json

    def set_template_override(self, template_id: str, path: str) -> Dict[str, Any]:
        """設定模板覆寫（支援 PDF 模板）"""
        try:
            # 驗證檔案存在與可讀
            file_path = Path(path)
            if not file_path.exists():
                return {"ok": False, "message": f"模板檔案不存在: {path}"}

            if not file_path.is_file():
                return {"ok": False, "message": f"路徑不是檔案: {path}"}

            if not os.access(file_path, os.R_OK):
                return {"ok": False, "message": f"無法讀取檔案: {path}"}

            # 檢查檔案類型
            supported_extensions = ['.md', '.j2', '.jinja', '.html', '.pdf']
            if file_path.suffix.lower() not in supported_extensions:
                return {
                    "ok": False,
                    "message": f"不支援的模板類型: {file_path.suffix}。支援的類型: {', '.join(supported_extensions)}"
                }

            # 記錄覆寫
            self.template_overrides[template_id] = str(file_path.absolute())

            # 準備回傳資訊
            result_data = {
                "ok": True,
                "template_id": template_id,
                "path": str(file_path.absolute()),
                "template_type": file_path.suffix.lower(),
                "file_size": file_path.stat().st_size,
                "message": f"模板 {template_id} 已覆寫為 {path}"
            }

            # 如果是 PDF 模板，檢查相關文件
            if file_path.suffix.lower() == '.pdf':
                layout_file = file_path.with_suffix(file_path.suffix + '.layout.json')
                if layout_file.exists():
                    result_data["layout_file"] = str(layout_file.absolute())
                    result_data["pdf_mode"] = "overlay"
                    result_data["message"] += f" (Overlay 模式，配置文件: {layout_file.name})"
                else:
                    result_data["pdf_mode"] = "acroform"
                    result_data["message"] += " (AcroForm 模式)"

            return result_data

        except Exception as e:
            return {"ok": False, "message": f"設定模板覆寫時發生錯誤: {str(e)}"}

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出可用的報告模板"""
        templates = []

        # 添加 test_template
        templates.append({
            "id": "test_template",
            "name": "測試模板 (PDF)",
            "path": TEST_TEMPLATE_PATH,
            "size": Path(TEST_TEMPLATE_PATH).stat().st_size if Path(TEST_TEMPLATE_PATH).exists() else 0,
            "modified": datetime.fromtimestamp(Path(TEST_TEMPLATE_PATH).stat().st_mtime).isoformat() if Path(TEST_TEMPLATE_PATH).exists() else None,
            "description": "基於 Cathay Q3 PDF 的測試模板"
        })

        if not self.templates_dir.exists():
            logger.warning(f"模板目錄不存在: {self.templates_dir}")
            return templates
        
        for template_file in self.templates_dir.glob("*.j2"):
            template_info = {
                "id": template_file.stem,
                "name": template_file.name,
                "path": str(template_file),
                "size": template_file.stat().st_size,
                "modified": datetime.fromtimestamp(template_file.stat().st_mtime).isoformat()
            }
            
            # 嘗試讀取模板元資料（如果存在註解）
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 尋找模板描述註解
                    if content.startswith('{#'):
                        end_comment = content.find('#}')
                        if end_comment > 0:
                            comment = content[2:end_comment].strip()
                            template_info["description"] = comment
            except Exception as e:
                logger.warning(f"讀取模板元資料失敗: {template_file} - {e}")
            
            templates.append(template_info)
        
        return templates
    
    def get_template(self, template_id: str) -> Optional[Template]:
        """取得指定的模板"""
        try:
            # 檢查是否有模板覆寫
            if template_id in self.template_overrides:
                override_path = self.template_overrides[template_id]
                logger.info(f"使用覆寫模板: {template_id} -> {override_path}")

                # 直接從檔案載入模板
                with open(override_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                return Template(template_content, environment=self.jinja_env)

            # 使用預設模板
            template_name = f"{template_id}.j2" if not template_id.endswith('.j2') else template_id
            return self.jinja_env.get_template(template_name)
        except TemplateNotFound:
            logger.error(f"模板不存在: {template_id}")
            return None
        except TemplateError as e:
            logger.error(f"模板載入錯誤: {template_id} - {e}")
            return None
        except Exception as e:
            logger.error(f"載入模板時發生錯誤: {template_id} - {e}")
            return None
    
    async def generate_report(self,
                            template_id: str,
                            context: Dict[str, Any],
                            output_filename: Optional[str] = None,
                            output_format: str = "markdown") -> Dict[str, Any]:
        """
        生成報告

        Args:
            template_id: 模板 ID
            context: 模板上下文資料
            output_filename: 輸出檔案名稱（可選）
            output_format: 輸出格式（支援 markdown, pdf）

        Returns:
            生成結果字典
        """
        # 特殊處理 test_template
        if template_id == "test_template":
            return await self._handle_test_template(context, output_filename, output_format)

        # 檢查是否為 PDF 模板
        if template_id in self.template_overrides:
            template_path = Path(self.template_overrides[template_id])
            if template_path.suffix.lower() == '.pdf':
                return await self._handle_pdf_template(template_id, template_path, context, output_filename, output_format)

        # 取得模板
        template = self.get_template(template_id)
        if not template:
            return {
                "ok": False,
                "reason": "template_not_found",
                "message": f"模板不存在: {template_id}",
                "data": None
            }
        
        # 準備上下文資料
        report_context = {
            **context,
            "generated_at": datetime.now().isoformat(),
            "template_id": template_id,
            "report_id": str(uuid.uuid4())
        }
        
        try:
            # 渲染模板
            rendered_content = template.render(**report_context)

            # 生成輸出檔案名稱
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if output_format == "pdf":
                    output_filename = f"{template_id}_{timestamp}_{report_context['report_id'][:8]}.pdf"
                else:
                    output_filename = f"{template_id}_{timestamp}_{report_context['report_id'][:8]}.md"

            # 確保檔案副檔名正確
            if output_format == "markdown" and not output_filename.endswith('.md'):
                output_filename += '.md'
            elif output_format == "pdf" and not output_filename.endswith('.pdf'):
                output_filename += '.pdf'

            # 處理不同輸出格式
            output_path = self.output_dir / output_filename

            if output_format == "pdf":
                # 轉換為 PDF
                pdf_bytes = await self._convert_to_pdf(rendered_content, template_id)
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes)
                mime_type = "application/pdf"
                render_mode = "html2pdf"
            else:
                # 儲存為 Markdown
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(rendered_content)
                mime_type = "text/markdown"
                render_mode = "markdown"

            logger.info(f"報告生成成功: {output_path}")

            return {
                "ok": True,
                "source": "REPORT",
                "data": {
                    "report_id": report_context["report_id"],
                    "template_id": template_id,
                    "output_path": str(output_path),
                    "output_filename": output_filename,
                    "output_format": output_format,
                    "mime": mime_type,
                    "template_ext": Path(template.filename).suffix if hasattr(template, 'filename') else ".j2",
                    "render_mode": render_mode,
                    "file_size": output_path.stat().st_size,
                    "content_length": len(rendered_content) if output_format != "pdf" else len(pdf_bytes),
                    "generated_at": report_context["generated_at"]
                },
                "timestamp": report_context["generated_at"]
            }
            
        except TemplateError as e:
            logger.error(f"模板渲染錯誤: {template_id} - {e}")
            return {
                "ok": False,
                "reason": "template_render_error",
                "message": f"模板渲染錯誤: {str(e)}",
                "data": None
            }
        except Exception as e:
            logger.error(f"報告生成失敗: {template_id} - {e}")
            return {
                "ok": False,
                "reason": "generation_failed",
                "message": f"報告生成失敗: {str(e)}",
                "data": None
            }

    async def _convert_to_pdf(self, content: str, template_id: str) -> bytes:
        """將內容轉換為 PDF"""
        try:
            # 將 Markdown 轉換為 HTML
            html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])

            # 包裝完整的 HTML 文檔
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Report - {template_id}</title>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # 轉換為 PDF
            pdf_bytes = self.render_pdf_from_html(full_html)

            # 添加浮水印
            return self.add_watermark_or_header(pdf_bytes, "Lens Qunat")

        except Exception as e:
            logger.error(f"PDF 轉換失敗: {e}")
            # 如果 PDF 轉換失敗，返回簡單的 PDF
            return self._create_fallback_pdf(content, template_id)

    def _create_fallback_pdf(self, content: str, template_id: str) -> bytes:
        """創建備用 PDF（當 WeasyPrint 不可用時）"""
        if not PDF_AVAILABLE:
            # 返回最小的 PDF 文件
            return b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\nxref\n0 2\ntrailer\n<< /Size 2 /Root 1 0 R >>\nstartxref\n%%EOF\n'

        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from io import BytesIO

            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)

            # 添加標題
            p.setFont("Helvetica-Bold", 16)
            p.drawString(72, 750, f"Report: {template_id}")

            # 添加浮水印
            p.setFont("Helvetica", 48)
            p.setFillGray(0.8)
            p.saveState()
            p.translate(300, 400)
            p.rotate(45)
            p.drawCentredText(0, 0, "Lens Qunat")
            p.restoreState()

            # 添加內容（簡化）
            p.setFont("Helvetica", 10)
            p.setFillGray(0)
            lines = content.split('\n')[:30]  # 限制行數
            y = 700
            for line in lines:
                if y < 50:
                    break
                p.drawString(72, y, line[:80])  # 限制每行字符數
                y -= 15

            p.showPage()
            p.save()

            return buffer.getvalue()

        except Exception as e:
            logger.error(f"備用 PDF 創建失敗: {e}")
            return b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\ntrailer\n<< /Size 1 /Root 1 0 R >>\nstartxref\n%%EOF\n'

    async def _handle_pdf_template(self, template_id: str, template_path: Path, context: Dict[str, Any],
                                 output_filename: Optional[str], output_format: str) -> Dict[str, Any]:
        """處理 PDF 模板"""
        try:
            report_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if not output_filename:
                if output_format == "pdf":
                    output_filename = f"{template_id}_{timestamp}_{report_id[:8]}.pdf"
                else:
                    output_filename = f"{template_id}_{timestamp}_{report_id[:8]}.md"

            # 檢查是否有 layout 配置文件（Overlay 模式）
            layout_file = template_path.with_suffix(template_path.suffix + '.layout.json')

            if layout_file.exists():
                # Overlay 模式
                with open(layout_file, 'r', encoding='utf-8') as f:
                    layout_spec = json.load(f)

                pdf_bytes = self.overlay_pdf(str(template_path), layout_spec, context)
                render_mode = "overlay"
            else:
                # AcroForm 模式
                pdf_bytes = self.fill_pdf_acroform(str(template_path), context)
                render_mode = "acroform"

            # 添加浮水印
            pdf_bytes = self.add_watermark_or_header(pdf_bytes, "Lens Qunat")

            # 儲存 PDF
            output_path = self.output_dir / output_filename
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)

            logger.info(f"PDF 報告生成成功: {output_path}")

            return {
                "ok": True,
                "source": "REPORT",
                "data": {
                    "report_id": report_id,
                    "template_id": template_id,
                    "output_path": str(output_path),
                    "output_filename": output_filename,
                    "output_format": "pdf",
                    "mime": "application/pdf",
                    "template_ext": ".pdf",
                    "render_mode": render_mode,
                    "file_size": output_path.stat().st_size,
                    "generated_at": datetime.now().isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"PDF 模板處理失敗: {template_id} - {e}")
            return {
                "ok": False,
                "reason": "pdf_template_error",
                "message": f"PDF 模板處理失敗: {str(e)}",
                "data": None
            }

    async def _handle_test_template(self, context: Dict[str, Any], output_filename: Optional[str], output_format: str) -> Dict[str, Any]:
        """處理 test_template 特殊情況"""
        try:
            # 檢查 PDF 是否存在
            pdf_path = Path(TEST_TEMPLATE_PATH)
            if not pdf_path.exists():
                return {
                    "ok": False,
                    "reason": "template_not_found",
                    "message": f"測試模板 PDF 不存在: {TEST_TEMPLATE_PATH}",
                    "data": None
                }

            # 生成輸出檔案名稱和報告 ID
            report_id = str(uuid.uuid4())
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"test_template_{timestamp}_{report_id[:8]}.md"

            # 確保檔案副檔名正確
            if output_format == "markdown" and not output_filename.endswith('.md'):
                output_filename += '.md'

            # 生成基於 PDF 的報告內容
            report_content = f"""# 測試報告

基於模板: {pdf_path.name}
生成時間: {datetime.now().isoformat()}
報告 ID: {report_id}

## 模板來源
- 檔案路徑: {TEST_TEMPLATE_PATH}
- 檔案大小: {pdf_path.stat().st_size if pdf_path.exists() else 0} bytes

## 上下文資料
{json.dumps(context, ensure_ascii=False, indent=2)}

## 附件
原始 PDF 模板已複製到輸出目錄。
"""

            # 儲存報告
            output_path = self.output_dir / output_filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)

            # 複製 PDF 到輸出目錄
            pdf_output_path = self.output_dir / pdf_path.name
            if pdf_path.exists():
                shutil.copy2(pdf_path, pdf_output_path)

            return {
                "ok": True,
                "reason": "success",
                "message": "測試報告生成成功",
                "data": {
                    "template_id": "test_template",
                    "report_id": report_id,
                    "output_path": str(output_path),
                    "pdf_path": str(pdf_output_path) if pdf_path.exists() else None,
                    "content_preview": report_content[:200] + "..." if len(report_content) > 200 else report_content
                }
            }

        except Exception as e:
            logger.error(f"測試模板處理失敗: {e}")
            return {
                "ok": False,
                "reason": "generation_error",
                "message": f"測試模板處理失敗: {str(e)}",
                "data": None
            }
    
    def get_report_content(self, report_path: str) -> Dict[str, Any]:
        """讀取已生成的報告內容"""
        path = Path(report_path)
        
        # 如果是相對路徑，嘗試在輸出目錄中尋找
        if not path.is_absolute():
            path = self.output_dir / path
        
        if not path.exists():
            return {
                "ok": False,
                "reason": "report_not_found",
                "message": f"報告檔案不存在: {report_path}",
                "data": None
            }
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "ok": True,
                "data": {
                    "path": str(path),
                    "filename": path.name,
                    "content": content,
                    "size": path.stat().st_size,
                    "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                },
                "source": "report_service",
                "timestamp": None
            }
            
        except Exception as e:
            logger.error(f"讀取報告失敗: {path} - {e}")
            return {
                "ok": False,
                "reason": "read_failed",
                "message": f"讀取報告失敗: {str(e)}",
                "data": None
            }
    
    def list_generated_reports(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出已生成的報告"""
        reports = []
        
        if not self.output_dir.exists():
            return reports
        
        # 取得所有報告檔案
        report_files = list(self.output_dir.glob("*.md"))
        
        # 按修改時間排序（最新的在前）
        report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for report_file in report_files[:limit]:
            try:
                stat = report_file.stat()
                reports.append({
                    "filename": report_file.name,
                    "path": str(report_file),
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception as e:
                logger.warning(f"取得報告資訊失敗: {report_file} - {e}")
        
        return reports
    
    def delete_report(self, report_path: str) -> Dict[str, Any]:
        """刪除報告檔案"""
        path = Path(report_path)
        
        # 如果是相對路徑，嘗試在輸出目錄中尋找
        if not path.is_absolute():
            path = self.output_dir / path
        
        if not path.exists():
            return {
                "ok": False,
                "reason": "report_not_found",
                "message": f"報告檔案不存在: {report_path}",
                "data": None
            }
        
        try:
            path.unlink()
            logger.info(f"報告已刪除: {path}")
            
            return {
                "ok": True,
                "data": {
                    "deleted_path": str(path),
                    "deleted_filename": path.name
                },
                "source": "report_service",
                "timestamp": None
            }
            
        except Exception as e:
            logger.error(f"刪除報告失敗: {path} - {e}")
            return {
                "ok": False,
                "reason": "delete_failed",
                "message": f"刪除報告失敗: {str(e)}",
                "data": None
            }


# 全域報告服務實例
report_service = ReportService()
