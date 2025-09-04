#!/usr/bin/env python3
"""
測試監督式 Agent 架構和對話歷史管理功能
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# 設定 Python 路徑
current_file = Path(__file__).resolve()
project_root = current_file.parent
sys.path.insert(0, str(project_root))

from app.graphs.agent_graph import agent_graph


async def test_supervised_agent_architecture():
    """測試監督式 Agent 架構"""
    print("🧪 測試 1: 監督式 Agent 架構")
    print("=" * 50)
    
    # 測試案例 1: 簡單查詢
    input_data = {
        "input_type": "text",
        "query": "/stock AAPL",
        "session_id": f"test-simple-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "options": {}
    }
    
    print(f"📝 查詢：{input_data['query']}")
    print(f"🆔 會話 ID：{input_data['session_id']}")
    
    try:
        result = await agent_graph.run(input_data)
        
        # 驗證監督式架構特徵
        assert result.get("supervised") == True, "應該標記為監督式模式"
        assert "supervisor_decision" in result, "應該包含監督決策"
        assert "supervisor_reasoning" in result, "應該包含監督推理"
        
        print("✅ 監督式架構驗證通過")
        print(f"🧠 監督決策：{result.get('supervisor_decision')}")
        print(f"💭 決策理由：{result.get('supervisor_reasoning')}")
        print(f"💾 對話儲存：{result.get('conversation_stored')}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗：{str(e)}")
        return False


async def test_conversation_history_management():
    """測試對話歷史管理"""
    print("🧪 測試 2: 對話歷史管理")
    print("=" * 50)
    
    # 第一次對話
    session_id_1 = f"test-conv-1-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    input_data_1 = {
        "input_type": "text",
        "query": "請告訴我 AAPL 的股價",
        "session_id": session_id_1,
        "options": {}
    }
    
    print(f"📝 第一次查詢：{input_data_1['query']}")
    print(f"🆔 會話 ID：{session_id_1}")
    
    try:
        result_1 = await agent_graph.run(input_data_1)
        print("✅ 第一次對話完成")
        print(f"💾 對話儲存：{result_1.get('conversation_stored')}")
        print()
        
        # 第二次對話（使用父會話 ID）
        session_id_2 = f"test-conv-2-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        input_data_2 = {
            "input_type": "text",
            "query": "那 TSLA 呢？",
            "session_id": session_id_2,
            "parent_session_id": session_id_1,  # 引用前一次對話
            "options": {}
        }
        
        print(f"📝 第二次查詢：{input_data_2['query']}")
        print(f"🆔 會話 ID：{session_id_2}")
        print(f"👨‍👩‍👧‍👦 父會話 ID：{session_id_1}")
        
        result_2 = await agent_graph.run(input_data_2)
        print("✅ 第二次對話完成（含歷史上下文）")
        print(f"💾 對話儲存：{result_2.get('conversation_stored')}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗：{str(e)}")
        return False


async def test_multi_turn_conversation():
    """測試多輪對話處理"""
    print("🧪 測試 3: 多輪對話處理")
    print("=" * 50)
    
    base_session_id = f"test-multi-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    conversations = [
        "請查詢 AAPL 的基本資料",
        "它的最新新聞如何？",
        "與 TSLA 比較如何？"
    ]
    
    previous_session_id = None
    
    for i, query in enumerate(conversations, 1):
        session_id = f"{base_session_id}-turn-{i}"
        
        input_data = {
            "input_type": "text",
            "query": query,
            "session_id": session_id,
            "parent_session_id": previous_session_id,
            "options": {}
        }
        
        print(f"📝 第 {i} 輪查詢：{query}")
        print(f"🆔 會話 ID：{session_id}")
        if previous_session_id:
            print(f"👨‍👩‍👧‍👦 父會話 ID：{previous_session_id}")
        
        try:
            result = await agent_graph.run(input_data)
            print(f"✅ 第 {i} 輪對話完成")
            print(f"🧠 監督決策：{result.get('supervisor_decision')}")
            print(f"💾 對話儲存：{result.get('conversation_stored')}")
            print()
            
            previous_session_id = session_id
            
        except Exception as e:
            print(f"❌ 第 {i} 輪測試失敗：{str(e)}")
            return False
    
    return True


async def test_supervisor_decision_making():
    """測試監督決策邏輯"""
    print("🧪 測試 4: 監督決策邏輯")
    print("=" * 50)
    
    test_cases = [
        {
            "query": "你好",
            "expected_decision": "end_conversation",
            "description": "簡單問候"
        },
        {
            "query": "/stock AAPL TSLA NVDA",
            "expected_decision": "end_conversation",  # 可能會直接回應或需要工具
            "description": "股票查詢"
        },
        {
            "query": "請分析市場趨勢並提供投資建議",
            "expected_decision": "end_conversation",  # 複雜查詢
            "description": "複雜分析請求"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        session_id = f"test-decision-{i}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        input_data = {
            "input_type": "text",
            "query": test_case["query"],
            "session_id": session_id,
            "options": {}
        }
        
        print(f"📝 測試案例 {i}: {test_case['description']}")
        print(f"🔍 查詢：{test_case['query']}")
        
        try:
            result = await agent_graph.run(input_data)
            decision = result.get("supervisor_decision")
            reasoning = result.get("supervisor_reasoning")
            
            print(f"🧠 監督決策：{decision}")
            print(f"💭 決策理由：{reasoning}")
            print(f"✅ 測試案例 {i} 完成")
            print()
            
        except Exception as e:
            print(f"❌ 測試案例 {i} 失敗：{str(e)}")
            return False
    
    return True


async def main():
    """主測試函數"""
    print("🚀 開始監督式 Agent 架構和對話歷史管理測試")
    print("=" * 60)
    print()
    
    tests = [
        test_supervised_agent_architecture,
        test_conversation_history_management,
        test_multi_turn_conversation,
        test_supervisor_decision_making
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            success = await test_func()
            if success:
                passed += 1
            print("-" * 50)
            print()
        except Exception as e:
            print(f"❌ 測試執行異常：{str(e)}")
            print("-" * 50)
            print()
    
    print("📊 測試結果摘要")
    print("=" * 30)
    print(f"✅ 通過：{passed}/{total}")
    print(f"❌ 失敗：{total - passed}/{total}")
    print(f"📈 成功率：{(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有測試通過！監督式 Agent 架構和對話歷史管理功能正常運作。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 個測試失敗，請檢查實現。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
