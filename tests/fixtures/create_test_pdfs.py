#!/usr/bin/env python3
"""
創建測試用的 PDF 模板文件
"""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black

def create_acroform_pdf():
    """創建帶有 AcroForm 欄位的 PDF"""
    output_path = Path(__file__).parent / "stock_acroform.pdf"
    
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    
    # 標題
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Stock Report Template (AcroForm)")
    
    # 創建表單欄位
    c.acroForm.textfield(
        name='company_name',
        tooltip='Company Name',
        x=72, y=height-120, borderStyle='inset',
        width=200, height=20,
        textColor=black, fillColor=None
    )
    c.drawString(72, height-110, "Company Name:")
    
    c.acroForm.textfield(
        name='ticker',
        tooltip='Stock Ticker',
        x=72, y=height-160, borderStyle='inset',
        width=100, height=20,
        textColor=black, fillColor=None
    )
    c.drawString(72, height-150, "Ticker:")
    
    c.acroForm.textfield(
        name='price',
        tooltip='Stock Price',
        x=72, y=height-200, borderStyle='inset',
        width=100, height=20,
        textColor=black, fillColor=None
    )
    c.drawString(72, height-190, "Price:")
    
    c.acroForm.textfield(
        name='market_cap',
        tooltip='Market Cap',
        x=72, y=height-240, borderStyle='inset',
        width=150, height=20,
        textColor=black, fillColor=None
    )
    c.drawString(72, height-230, "Market Cap:")
    
    # 第二頁
    c.showPage()
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, height - 72, "News Headlines")
    
    c.acroForm.textfield(
        name='headline_1',
        tooltip='First Headline',
        x=72, y=height-120, borderStyle='inset',
        width=400, height=40,
        textColor=black, fillColor=None
    )
    c.drawString(72, height-110, "Headline 1:")
    
    c.acroForm.textfield(
        name='headline_2',
        tooltip='Second Headline',
        x=72, y=height-180, borderStyle='inset',
        width=400, height=40,
        textColor=black, fillColor=None
    )
    c.drawString(72, height-170, "Headline 2:")
    
    c.save()
    print(f"Created AcroForm PDF: {output_path}")

def create_overlay_pdf():
    """創建用於疊印的靜態 PDF"""
    output_path = Path(__file__).parent / "stock_overlay.pdf"
    
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    
    # 第一頁 - 基本資訊
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Stock Report Template (Overlay)")
    
    # 繪製欄位標籤和框線
    c.setFont("Helvetica", 10)
    c.drawString(72, height-85, "Company Name:")
    c.rect(72, height-105, 200, 20, stroke=1, fill=0)
    
    c.drawString(72, height-125, "Ticker:")
    c.rect(72, height-145, 100, 20, stroke=1, fill=0)
    
    c.drawString(72, height-165, "Price:")
    c.rect(72, height-185, 100, 20, stroke=1, fill=0)
    
    c.drawString(72, height-205, "Market Cap:")
    c.rect(72, height-225, 150, 20, stroke=1, fill=0)
    
    # 第二頁 - 新聞標題
    c.showPage()
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, height - 72, "News Headlines")
    
    c.setFont("Helvetica", 10)
    c.drawString(72, height-95, "Headline 1:")
    c.rect(72, height-115, 400, 40, stroke=1, fill=0)
    
    c.drawString(72, height-155, "Headline 2:")
    c.rect(72, height-175, 400, 40, stroke=1, fill=0)
    
    c.save()
    print(f"Created Overlay PDF: {output_path}")

if __name__ == "__main__":
    # 確保目錄存在
    Path(__file__).parent.mkdir(parents=True, exist_ok=True)
    
    create_acroform_pdf()
    create_overlay_pdf()
    print("Test PDF templates created successfully!")
