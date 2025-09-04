#!/usr/bin/env python3
"""
手动验收测试脚本 - PDF 报告生成和 Session 功能
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.report import ReportService
from app.services.session_store import SessionStore


async def test_pdf_template_registration():
    """测试 1: PDF 模板注册"""
    print("=== 测试 1: PDF 模板注册 ===")
    
    try:
        rs = ReportService()
        
        # 注册 AcroForm PDF 模板
        acroform_path = "tests/fixtures/templates/stock_acroform.pdf"
        result = rs.set_template_override("stock", acroform_path)
        
        print(f"AcroForm 模板注册结果: {result}")
        assert result["ok"] is True
        assert result["template_type"] == ".pdf"
        assert result["pdf_mode"] == "acroform"
        
        # 注册 Overlay PDF 模板
        overlay_path = "tests/fixtures/templates/stock_overlay.pdf"
        result2 = rs.set_template_override("stock_overlay", overlay_path)
        
        print(f"Overlay 模板注册结果: {result2}")
        assert result2["ok"] is True
        assert result2["pdf_mode"] == "overlay"
        
        print("✅ PDF 模板注册测试通过")
        return True
        
    except Exception as e:
        print(f"❌ PDF 模板注册测试失败: {e}")
        return False


async def test_pdf_report_generation():
    """测试 2: PDF 报告生成"""
    print("\n=== 测试 2: PDF 报告生成 ===")
    
    try:
        rs = ReportService()
        
        # 注册模板
        rs.set_template_override("stock", "tests/fixtures/templates/stock_acroform.pdf")
        
        # 生成 PDF 报告
        context = {
            "company_name": "Apple Inc.",
            "ticker": "AAPL",
            "price": "150.00",
            "market_cap": "2.5T",
            "headline_1": "Apple reports strong Q3 earnings",
            "headline_2": "iPhone sales exceed expectations"
        }
        
        result = await rs.generate_report(
            template_id="stock",
            context=context,
            output_format="pdf"
        )
        
        print(f"PDF 报告生成结果: {result}")
        
        if result["ok"]:
            output_path = Path(result["data"]["output_path"])
            print(f"PDF 文件路径: {output_path}")
            print(f"文件大小: {output_path.stat().st_size} bytes")
            print(f"MIME 类型: {result['data']['mime']}")
            print(f"渲染模式: {result['data']['render_mode']}")
            
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            assert result["data"]["mime"] == "application/pdf"
            
            print("✅ PDF 报告生成测试通过")
            return True
        else:
            print(f"❌ PDF 报告生成失败: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ PDF 报告生成测试失败: {e}")
        return False


async def test_markdown_to_pdf():
    """测试 3: Markdown 转 PDF"""
    print("\n=== 测试 3: Markdown 转 PDF ===")
    
    try:
        rs = ReportService()
        
        # 使用标准 Markdown 模板生成 PDF
        context = {
            "symbols": ["AAPL", "MSFT"],
            "quotes": [
                {"symbol": "AAPL", "price": 150.0, "change": 2.5, "changesPercentage": 1.7},
                {"symbol": "MSFT", "price": 300.0, "change": -1.2, "changesPercentage": -0.4}
            ],
            "profiles": [
                {"symbol": "AAPL", "companyName": "Apple Inc.", "industry": "Technology"},
                {"symbol": "MSFT", "companyName": "Microsoft Corp.", "industry": "Technology"}
            ]
        }
        
        result = await rs.generate_report(
            template_id="stock",  # 使用标准 Jinja 模板
            context=context,
            output_format="pdf"
        )
        
        print(f"Markdown 转 PDF 结果: {result}")
        
        if result["ok"]:
            output_path = Path(result["data"]["output_path"])
            print(f"PDF 文件路径: {output_path}")
            print(f"文件大小: {output_path.stat().st_size} bytes")
            
            assert output_path.exists()
            assert result["data"]["render_mode"] == "html2pdf"
            
            print("✅ Markdown 转 PDF 测试通过")
            return True
        else:
            print(f"❌ Markdown 转 PDF 失败: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Markdown 转 PDF 测试失败: {e}")
        return False


def test_session_context():
    """测试 4: Session 上下文功能"""
    print("\n=== 测试 4: Session 上下文功能 ===")
    
    try:
        # 创建临时数据库
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        ss = SessionStore(db_path)
        
        # 创建 session
        session_id = ss.create_session()
        print(f"创建 Session: {session_id}")
        
        # 第一轮对话
        ss.append_turn(
            session_id,
            "之后都用繁体中文，标的预设 AAPL",
            "好的，我会使用繁体中文回答，并将 AAPL 作为预设标的。"
        )
        
        # 第二轮对话
        ss.append_turn(
            session_id,
            "帮我做份小报告",
            "我将为您生成 AAPL 的繁体中文报告。"
        )
        
        # 测试摘要生成
        summary = ss.get_session_summary(session_id)
        print(f"Session 摘要: {summary}")
        
        # 测试系统提示构建
        base_prompt = "你是一个专业的金融分析助手。"
        system_prompt = ss.build_session_system_prompt(session_id, base_prompt)
        print(f"系统提示:\n{system_prompt}")
        
        # 验证
        assert len(summary) > 0
        assert "繁体中文" in summary or "繁體中文" in summary or "AAPL" in summary
        assert "[SESSION CONTEXT]" in system_prompt
        assert base_prompt in system_prompt
        
        # 清理
        os.unlink(db_path)
        
        print("✅ Session 上下文测试通过")
        return True
        
    except Exception as e:
        print(f"❌ Session 上下文测试失败: {e}")
        return False


def test_cli_pdf_arguments():
    """测试 5: CLI PDF 参数"""
    print("\n=== 测试 5: CLI PDF 参数 ===")
    
    try:
        from app.agent_cli import setup_argument_parser
        
        parser = setup_argument_parser()
        
        # 测试 PDF 输出格式
        args = parser.parse_args([
            "--input-type", "text",
            "--query", "/report stock AAPL --format pdf",
            "--output-format", "pdf",
            "--output-file", "/tmp/test_report.pdf"
        ])
        
        assert args.output_format == "pdf"
        assert args.output_file == "/tmp/test_report.pdf"
        
        # 测试 Session 参数
        args2 = parser.parse_args([
            "--input-type", "text",
            "--query", "测试",
            "--session-id", "test-session-123"
        ])
        
        assert args2.session_id == "test-session-123"
        
        print("✅ CLI PDF 参数测试通过")
        return True
        
    except Exception as e:
        print(f"❌ CLI PDF 参数测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("开始 PDF 报告生成和 Session 功能验收测试\n")
    
    tests = [
        test_pdf_template_registration,
        test_pdf_report_generation,
        test_markdown_to_pdf,
        test_session_context,
        test_cli_pdf_arguments
    ]
    
    results = []
    
    for test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 异常: {e}")
            results.append(False)
    
    # 总结
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== 测试总结 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
