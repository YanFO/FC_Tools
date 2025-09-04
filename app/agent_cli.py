#!/usr/bin/env python3
"""
Agent CLI 介面
提供命令列方式執行 Agent 功能，支援四種輸入類型
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from functools import reduce

# 加入專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import settings

# 匯入圖物件（簡化版本）
try:
    from app.graphs.agent_graph import build_graph
    graph = build_graph()
except Exception:
    import app.graphs.agent_graph as m
    g = getattr(m, "agent_graph", None)
    if g is None:
        raise
    graph = g if hasattr(g, "invoke") or hasattr(g, "ainvoke") else (
        g.graph if hasattr(g, "graph") and (hasattr(g.graph, "invoke") or hasattr(g.graph, "ainvoke")) else g.compile()
    )


def safe_print(s: str):
    """安全輸出，避免 BrokenPipeError"""
    try:
        sys.stdout.write(s + ("\n" if not s.endswith("\n") else ""))
        sys.stdout.flush()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        finally:
            raise SystemExit(0)


def select_path(d: dict, path: str):
    """簡易 JSON 路徑選取器"""
    keys = [p for p in path.split('.') if p]
    try:
        return reduce(lambda x, k: x[int(k)] if k.isdigit() else x.get(k, None), keys, d)
    except Exception:
        return None


# 統一抽取可讀文字
def extract_textish(result: dict) -> str:
    """從結果中抽取可讀文字，提供保底輸出"""
    resp = (result.get("response") or "").strip()
    if not resp:
        msgs = result.get("messages") or []
        def _get(m):
            return getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else None)
        for m in reversed(msgs):
            text = (_get(m) or "").strip()
            if text:
                resp = text
                break
    if not resp:
        q = (result.get("query") or "").strip()
        resp = f"已接收輸入：{q[:120] or '(空白)'}，但無可用回答。"
    return resp


def setup_argument_parser() -> argparse.ArgumentParser:
    """設定命令列參數解析器"""
    parser = argparse.ArgumentParser(
        description="Agent-Only LangGraph Service CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  # 文字查詢
  python -m app.agent_cli --input-type text --query "台積電與NVDA近期財報重點？"
  
  # 檔案 QA
  python -m app.agent_cli --input-type file --file ./docs/report.pdf --query "這份報告的主要風險是什麼？"
  
  # 檔案報告生成
  python -m app.agent_cli --input-type file --file ./docs/10Q.pdf --task report --template-id market_brief
  
  # LINE 聊天分析
  python -m app.agent_cli --input-type line --user-id Uxxx --start 2025-08-20 --end 2025-09-01
  
  # 規則查詢
  python -m app.agent_cli --input-type rule --rule-file ./rules.json
        """
    )
    
    # 基本參數
    parser.add_argument(
        "--input-type",
        choices=["text", "file", "line", "rule"],
        required=True,
        help="輸入類型"
    )
    
    parser.add_argument(
        "--query",
        help="查詢文字（用於 text 和 file QA）"
    )
    
    # 檔案相關參數
    parser.add_argument(
        "--file", "--file-path",
        dest="file",
        help="檔案路徑（用於 file 類型）"
    )
    
    parser.add_argument(
        "--task",
        choices=["qa", "report"],
        default="qa",
        help="檔案處理任務類型（預設：qa）"
    )
    
    parser.add_argument(
        "--template-id",
        help="報告模板 ID（用於 report 任務）"
    )
    
    # LINE 相關參數
    parser.add_argument(
        "--user-id",
        help="LINE 使用者 ID"
    )
    
    parser.add_argument(
        "--chat-id",
        help="LINE 聊天室 ID"
    )
    
    parser.add_argument(
        "--start",
        help="開始時間（ISO 格式，如 2025-08-20T00:00:00）"
    )
    
    parser.add_argument(
        "--end",
        help="結束時間（ISO 格式，如 2025-09-01T23:59:59）"
    )
    
    # 規則相關參數
    parser.add_argument(
        "--rule-file",
        help="規則定義檔案路徑（JSON 格式）"
    )
    
    parser.add_argument(
        "--rule-json",
        help="規則定義 JSON 字串"
    )
    
    # 輸出選項
    parser.add_argument(
        "--output-format",
        choices=["json", "markdown", "plain", "pdf"],
        default="json",
        help="輸出格式（預設：json）"
    )
    
    parser.add_argument(
        "--output-file",
        help="輸出檔案路徑（可選）"
    )
    
    parser.add_argument(
        "--lang",
        default="tw",
        help="回應語言（預設：tw）"
    )
    
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="回傳結果數量（預設：5）"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細輸出模式"
    )
    
    parser.add_argument(
        "--no-sources",
        action="store_true",
        help="不包含資料來源資訊"
    )

    parser.add_argument(
        "--pretty",
        action="store_true",
        help="漂亮列印 JSON 輸出"
    )

    parser.add_argument(
        "--response-only",
        action="store_true",
        help="只輸出回應文字內容"
    )

    parser.add_argument(
        "--select",
        help="選取特定 JSON 路徑，如 final_response.response"
    )

    parser.add_argument(
        "--trace",
        action="store_true",
        help="顯示節點流與工具呼叫摘要"
    )

    parser.add_argument(
        "--recursion-limit",
        type=int,
        default=15,
        help="遞迴限制（預設：15）"
    )



    # Session 選項
    parser.add_argument(
        "--session-id",
        help="Session ID（用於對話上下文）"
    )

    parser.add_argument(
        "--history-file",
        help="本地歷史檔案路徑（用於測試）"
    )

    return parser


def validate_arguments(args: argparse.Namespace) -> Optional[str]:
    """驗證命令列參數"""
    
    # 文字類型驗證
    if args.input_type == "text" and not args.query:
        return "text 類型需要提供 --query 參數"
    
    # 檔案類型驗證
    if args.input_type == "file":
        if not args.file:
            return "需要 --file 指向實體檔案，例如 PDF/MD/DOCX 等（也可使用 --file-path 別名）"

        if args.task == "qa" and not args.query:
            return "file QA 任務需要提供 --query 參數"

        if args.task == "report" and not args.template_id:
            return "report 任務需要 --template-id（例如 stock）"
        
        # 檢查檔案是否存在，並處理單行路徑檔
        file_path = Path(args.file)
        if not file_path.exists():
            return f"檔案不存在: {args.file}"

        # 單行路徑檔自動解讀
        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md']:
            try:
                content = file_path.read_text(encoding='utf-8').strip()
                lines = content.split('\n')
                if len(lines) == 1 and lines[0].strip():
                    potential_path_str = lines[0].strip()
                    # 只有當內容看起來像路徑時才嘗試解析
                    if ('/' in potential_path_str or '\\' in potential_path_str or
                        potential_path_str.endswith(('.pdf', '.docx', '.txt', '.md', '.doc'))):
                        potential_path = Path(potential_path_str)
                        if potential_path.exists() and potential_path.is_file():
                            # 自動將單行路徑解析為真實檔案
                            args.file = str(potential_path)
                            print(f"自動解析單行路徑檔：{file_path} → {potential_path}", file=sys.stderr)
                        else:
                            return f"單行路徑檔中的路徑不存在: {potential_path_str}"
                    # 如果不像路徑，就繼續使用原檔案
            except Exception as e:
                # 讀取失敗，繼續使用原檔案
                pass
    
    # LINE 類型驗證
    if args.input_type == "line":
        if not args.user_id and not args.chat_id:
            return "line 類型需要提供 --user-id 或 --chat-id 參數"
    
    # 規則類型驗證
    if args.input_type == "rule":
        if not args.rule_file and not args.rule_json:
            return "rule 類型需要提供 --rule-file 或 --rule-json 參數"
        
        if args.rule_file:
            rule_path = Path(args.rule_file)
            if not rule_path.exists():
                return f"規則檔案不存在: {args.rule_file}"
    
    return None


def load_rule_definition(args: argparse.Namespace) -> Dict[str, Any]:
    """載入規則定義"""
    if args.rule_json:
        try:
            return json.loads(args.rule_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"規則 JSON 格式錯誤: {e}")
    
    elif args.rule_file:
        try:
            with open(args.rule_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"規則檔案 JSON 格式錯誤: {e}")
        except Exception as e:
            raise ValueError(f"讀取規則檔案失敗: {e}")
    
    return {}


def prepare_input_data(args: argparse.Namespace) -> Dict[str, Any]:
    """準備輸入資料"""
    input_data = {
        "input_type": args.input_type,
        "options": {
            "lang": args.lang,
            "top_k": args.top_k,
            "include_sources": not args.no_sources,
            "format": args.output_format
        }
    }
    
    # 加入查詢文字
    if args.query:
        input_data["query"] = args.query
    
    # 檔案相關資料
    if args.input_type == "file":
        input_data["file"] = {
            "path": args.file,
            "task": args.task
        }
        if args.template_id:
            input_data["file"]["template_id"] = args.template_id
    
    # LINE 相關資料
    elif args.input_type == "line":
        line_data = {}
        if args.user_id:
            line_data["user_id"] = args.user_id
        if args.chat_id:
            line_data["chat_id"] = args.chat_id
        if args.start:
            line_data["start"] = args.start
        if args.end:
            line_data["end"] = args.end
        input_data["line"] = line_data
    
    # 規則相關資料
    elif args.input_type == "rule":
        input_data["rule"] = load_rule_definition(args)
    
    return input_data


def format_output(result: Dict[str, Any], format_type: str, verbose: bool = False) -> str:
    """格式化輸出"""
    
    if format_type == "json":
        if verbose:
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            # 簡化的 JSON 輸出
            simplified = {
                "ok": result.get("ok", False),
                "response": result.get("response", ""),
                "input_type": result.get("input_type", ""),
                "timestamp": result.get("timestamp", "")
            }
            if result.get("error"):
                simplified["error"] = result["error"]
            if result.get("warnings"):
                simplified["warnings"] = result["warnings"]
            return json.dumps(simplified, ensure_ascii=False, indent=2)
    
    elif format_type == "markdown":
        lines = []
        lines.append(f"# Agent 執行結果")
        lines.append(f"")
        lines.append(f"**狀態：** {'✅ 成功' if result.get('ok') else '❌ 失敗'}")
        lines.append(f"**輸入類型：** {result.get('input_type', 'unknown')}")
        lines.append(f"**時間：** {result.get('timestamp', 'unknown')}")
        lines.append(f"")
        
        if result.get("error"):
            lines.append(f"## 錯誤訊息")
            lines.append(f"```")
            lines.append(f"{result['error']}")
            lines.append(f"```")
            lines.append(f"")
        
        if result.get("response"):
            lines.append(f"## 回應內容")
            lines.append(f"{result['response']}")
            lines.append(f"")
        
        if result.get("warnings") and verbose:
            lines.append(f"## 警告")
            for warning in result["warnings"]:
                lines.append(f"- {warning}")
            lines.append(f"")
        
        if result.get("sources") and verbose:
            lines.append(f"## 資料來源")
            for source in result["sources"]:
                lines.append(f"- **{source.get('source', 'Unknown')}** ({source.get('timestamp', 'Unknown time')})")
            lines.append(f"")
        
        return "\n".join(lines)
    
    else:  # plain
        lines = []
        if result.get("ok"):
            lines.append("✅ 執行成功")
        else:
            lines.append("❌ 執行失敗")
        
        if result.get("error"):
            lines.append(f"錯誤: {result['error']}")
        
        if result.get("response"):
            lines.append("")
            lines.append("回應:")
            lines.append(result["response"])
        
        if result.get("warnings") and verbose:
            lines.append("")
            lines.append("警告:")
            for warning in result["warnings"]:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines)


async def main():
    """主函數"""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # 驗證參數
    validation_error = validate_arguments(args)
    if validation_error:
        print(f"❌ 參數錯誤: {validation_error}", file=sys.stderr)
        sys.exit(1)
    
    # 檢查 API 金鑰狀態
    if args.verbose:
        print("🔍 檢查 API 狀態...")
        api_status = settings.api_status
        for api, available in api_status.items():
            status = "✅" if available else "❌"
            print(f"  {api}: {status}")
        print()
    
    try:
        # 準備輸入資料
        if args.verbose:
            print("📝 準備輸入資料...")

        input_data = prepare_input_data(args)

        # 加入防呆欄位
        input_data.update({
            "messages": [],
            "warnings": [],
            "sources": [],
            "tool_loop_count": 0,
            "tool_call_sigs": []
        })
        
        if args.verbose:
            print(f"輸入類型: {input_data['input_type']}")
            if input_data.get('query'):
                print(f"查詢: {input_data['query'][:100]}...")
            print()
        
        # 執行 Agent
        if args.verbose:
            print("🤖 執行 Agent...")

        # 設定遞迴限制
        config = {"recursion_limit": args.recursion_limit}

        # 執行主要圖
        result = await graph.ainvoke(input_data, config=config)

        # 確保有可讀的回應文字
        if isinstance(result, dict):
            # 如果是 LangGraph 的狀態字典，提取 final_response
            final_response = result.get("final_response")
            if final_response:
                result = final_response
            else:
                # 建構基本回應格式
                result = {
                    "ok": True,
                    "response": extract_textish(result),
                    "input_type": result.get("input_type", input_data.get("input_type", "unknown")),
                    "warnings": result.get("warnings", []),
                    "timestamp": datetime.now().isoformat()
                }

        # 格式化輸出
        output = format_output(result, args.output_format, args.verbose)
        
        # 處理輸出格式
        final = result if isinstance(result, dict) else {"response": str(result)}

        if args.response_only:
            output_text = final.get("response", "").strip()
        elif args.select:
            selected = select_path(result, args.select)
            if selected is None:
                output_text = "null"
            elif isinstance(selected, (dict, list)):
                output_text = json.dumps(selected, ensure_ascii=False, indent=2)
            else:
                output_text = str(selected)
        elif args.pretty:
            output_text = json.dumps(final, ensure_ascii=False, indent=2)
        else:
            output_text = json.dumps(final, ensure_ascii=False)

        # 輸出結果
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(output_text)
            if args.verbose:
                safe_print(f"📄 結果已儲存至: {args.output_file}")
        else:
            safe_print(output_text)
        
        # 設定退出碼
        sys.exit(0 if result.get("ok", False) else 1)
        
    except KeyboardInterrupt:
        print("\n⏹️  使用者中斷執行", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"❌ 執行失敗: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
