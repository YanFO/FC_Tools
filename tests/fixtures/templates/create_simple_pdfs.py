#!/usr/bin/env python3
"""
创建简单的测试 PDF 文件（不依赖 reportlab）
"""
from pathlib import Path

def create_dummy_pdfs():
    """创建虚拟的 PDF 文件用于测试"""
    templates_dir = Path(__file__).parent
    
    # 创建 AcroForm PDF（虚拟内容）
    acroform_path = templates_dir / "stock_acroform.pdf"
    with open(acroform_path, 'wb') as f:
        # 写入最小的 PDF 头部
        f.write(b'%PDF-1.4\n')
        f.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
        f.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')
        f.write(b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n')
        f.write(b'xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n')
        f.write(b'trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n178\n%%EOF\n')
    
    # 创建 Overlay PDF（虚拟内容）
    overlay_path = templates_dir / "stock_overlay.pdf"
    with open(overlay_path, 'wb') as f:
        # 写入最小的 PDF 头部
        f.write(b'%PDF-1.4\n')
        f.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
        f.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')
        f.write(b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n')
        f.write(b'xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n')
        f.write(b'trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n178\n%%EOF\n')
    
    print(f"Created dummy AcroForm PDF: {acroform_path}")
    print(f"Created dummy Overlay PDF: {overlay_path}")
    print("Note: These are minimal PDF files for testing purposes only.")

if __name__ == "__main__":
    create_dummy_pdfs()
