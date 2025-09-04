"""
測試 Session 持久化功能
驗證對話摘要、偏好抽取、parent_session_id 注入和 API 端點
"""
import pytest

from app.services.session import session_service
from app.services.database import database_service
from app.graphs.agent_graph import agent_graph


class TestSession:
    """測試 Session 功能"""
    
    @pytest.mark.asyncio
    async def test_session_summary_generation(self):
        """測試 Session 摘要生成"""
        # 模擬對話訊息（包含使用者偏好）
        messages = [
            {"type": "human", "content": "之後都用繁體中文回覆，並記得我喜歡簡短重點式整理"},
            {"type": "ai", "content": "好的，我會用繁體中文回覆，並提供簡短重點式的整理。"},
            {"type": "human", "content": "請問 AAPL 股價？"},
            {"type": "ai", "content": "AAPL 目前股價：$185.25 (+2.15%)"}
        ]
        
        # 生成摘要
        summary = await session_service.summarize_session("test_session_A", messages)
        
        assert summary is not None, "摘要不應為空"
        assert len(summary) > 0, "摘要應有內容"
        
        # 檢查摘要是否包含關鍵資訊
        summary_lower = summary.lower()
        assert any(keyword in summary_lower for keyword in ["繁體中文", "簡短", "重點", "股票"]), "摘要應包含關鍵偏好或主題"
    
    @pytest.mark.asyncio
    async def test_session_summary_persistence(self):
        """測試 Session 摘要持久化"""
        session_id = "test_session_persist"
        messages = [
            {"type": "human", "content": "我喜歡詳細的技術分析，請用條列方式回覆"},
            {"type": "ai", "content": "了解，我會提供詳細的技術分析並使用條列格式。"}
        ]
        
        # 儲存摘要
        success = await session_service.save_session_summary(session_id, messages)
        assert success, "摘要儲存應該成功"
        
        # 檢查是否能取回
        session_data = await session_service.get_session_info(session_id)
        assert session_data is not None, "應該能取回 Session 資料"
        assert session_data["session_id"] == session_id, "Session ID 應該匹配"
        assert len(session_data["summary"]) > 0, "摘要內容不應為空"
    
    @pytest.mark.asyncio
    async def test_parent_session_context_injection(self):
        """測試父 Session 上下文注入"""
        parent_session_id = "test_parent_session"
        
        # 先建立父 Session 摘要
        parent_messages = [
            {"type": "human", "content": "之後都用繁體中文回覆，並記得我喜歡簡短重點式整理"},
            {"type": "ai", "content": "好的，我會遵循您的偏好。"}
        ]
        
        await session_service.save_session_summary(parent_session_id, parent_messages)
        
        # 取得上下文
        context = await session_service.get_parent_session_context(parent_session_id)
        
        assert context is not None, "應該能取得父 Session 上下文"
        assert "前一次對話" in context, "上下文應該提及前一次對話"
        assert "偏好" in context, "上下文應該包含偏好資訊"
    
    @pytest.mark.asyncio
    async def test_system_prompt_with_context(self):
        """測試包含上下文的系統提示"""
        parent_session_id = "test_system_prompt"
        
        # 建立父 Session
        parent_messages = [
            {"type": "human", "content": "請用簡潔的方式回答，不要太冗長"},
            {"type": "ai", "content": "了解，我會保持簡潔。"}
        ]
        
        await session_service.save_session_summary(parent_session_id, parent_messages)
        
        # 建立包含上下文的系統提示
        system_prompt = await session_service.create_system_prompt_with_context(parent_session_id)
        
        assert system_prompt is not None, "系統提示不應為空"
        assert "Augment Agent" in system_prompt, "應該包含基本身份"
        assert "繁體中文" in system_prompt, "應該包含語言要求"
        assert "前一次對話" in system_prompt, "應該包含上下文資訊"
    
    @pytest.mark.asyncio
    async def test_agent_with_parent_session_style_influence(self):
        """測試 Agent 使用 parent_session_id 影響回覆風格"""
        # 第一步：建立父 Session（偏好條列式回覆）
        parent_session_id = "session_A_style"
        parent_input = {
            "input_type": "text",
            "session_id": parent_session_id,
            "query": "之後請用條列式回覆，我喜歡重點分明的格式",
            "options": {}
        }
        
        # 執行父 Session
        parent_result = await agent_graph.run(parent_input)
        assert parent_result is not None, "父 Session 執行應該成功"
        
        # 模擬儲存父 Session 摘要
        if parent_result.get("messages"):
            await session_service.save_session_summary(parent_session_id, parent_result["messages"])
        
        # 第二步：建立子 Session 並注入父 Session 上下文
        child_session_id = "session_B_style"
        child_input = {
            "input_type": "text",
            "session_id": child_session_id,
            "parent_session_id": parent_session_id,
            "query": "請總結 Agent 的主要功能",
            "options": {}
        }
        
        # 執行子 Session
        child_result = await agent_graph.run(child_input)
        assert child_result is not None, "子 Session 執行應該成功"
        
        # 檢查子 Session 是否受到父 Session 影響
        response = child_result.get("response", "")
        assert len(response) > 0, "應該有回應內容"
        
        # 檢查是否有條列式特徵（簡單的啟發式檢查）
        list_indicators = ["•", "-", "1.", "2.", "3.", "：", ":", "\n-", "\n•"]
        has_list_format = any(indicator in response for indicator in list_indicators)
        
        # 或檢查平均句長（條列式通常句子較短）
        sentences = [s.strip() for s in response.split('。') if s.strip()]
        if sentences:
            avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
            is_concise = avg_sentence_length < 50  # 簡潔的句子通常較短
        else:
            is_concise = False
        
        # 至少要有其中一個特徵
        assert has_list_format or is_concise, f"回覆應該顯示條列或簡潔特徵，實際回覆: {response[:200]}..."
    
    @pytest.mark.asyncio
    async def test_session_without_parent(self):
        """測試沒有 parent_session_id 的正常 Session"""
        input_data = {
            "input_type": "text",
            "session_id": "standalone_session",
            "query": "請問 AAPL 股價？",
            "options": {}
        }
        
        result = await agent_graph.run(input_data)
        assert result is not None, "獨立 Session 應該正常執行"
        
        # 檢查沒有上下文注入的情況下仍能正常回應
        response = result.get("response", "")
        assert len(response) > 0, "應該有回應內容"
    
    def test_simple_summary_fallback(self):
        """測試簡單摘要生成（當 LLM 不可用時）"""
        messages = [
            {"type": "human", "content": "請查 AAPL 股價"},
            {"type": "ai", "content": "AAPL 股價為 $185.25"},
            {"type": "human", "content": "謝謝，請用繁體中文"}
        ]
        
        # 測試簡單摘要
        summary = session_service._simple_summary(messages)
        
        assert summary is not None, "簡單摘要不應為空"
        assert "對話輪數" in summary, "應該包含對話統計"
        assert ("股票查詢" in summary or "一般對話" in summary), "應該包含主題分類"
    
    @pytest.mark.asyncio
    async def test_extractive_summary_no_fabrication(self):
        """測試抽取式摘要不會捏造內容"""
        messages = [
            {"type": "human", "content": "我需要美股資訊"},
            {"type": "ai", "content": "我可以幫您查詢美股資訊"}
        ]
        
        # 測試摘要不包含原始訊息中沒有的內容
        summary = await session_service.summarize_session("test_no_fab", messages)
        
        assert summary is not None, "摘要不應為空"
        
        # 檢查摘要長度合理（≤5 條 bullet 的概念）
        bullet_count = summary.count('|') + summary.count('-') + summary.count('•')
        assert bullet_count <= 10, "摘要應該簡潔，不超過合理的條目數"
        
        # 檢查不包含明顯的捏造內容
        fabricated_terms = ["假設", "可能", "估計", "大概", "應該會"]
        summary_lower = summary.lower()
        has_fabrication = any(term in summary_lower for term in fabricated_terms)
        assert not has_fabrication, f"摘要不應包含推測性內容: {summary}"
    
    @pytest.mark.asyncio
    async def test_database_session_operations(self):
        """測試資料庫 Session 操作"""
        session_id = "test_db_session"
        test_summary = "使用者偏好簡短回覆，關注股票資訊"
        message_count = 4
        
        # 儲存
        success = await database_service.save_session_summary(session_id, test_summary, message_count)
        assert success, "資料庫儲存應該成功"
        
        # 查詢
        session_data = await database_service.get_session_summary(session_id)
        assert session_data is not None, "應該能查詢到 Session"
        assert session_data["session_id"] == session_id, "Session ID 應該匹配"
        assert session_data["summary"] == test_summary, "摘要內容應該匹配"
        assert session_data["message_count"] == message_count, "訊息數量應該匹配"
    
    @pytest.mark.asyncio
    async def test_session_api_endpoint(self):
        """測試 Session API 端點"""
        # 這個測試需要實際的 HTTP 客戶端，這裡做簡化測試
        session_id = "test_api_session"
        test_summary = "API 測試摘要"
        
        # 先儲存一個 Session
        await database_service.save_session_summary(session_id, test_summary, 2)
        
        # 測試取得 Session 資訊
        session_info = await session_service.get_session_info(session_id)
        assert session_info is not None, "應該能取得 Session 資訊"
        assert session_info["session_id"] == session_id, "Session ID 應該匹配"
        assert session_info["summary"] == test_summary, "摘要應該匹配"
    
    @pytest.mark.asyncio
    async def test_session_list_functionality(self):
        """測試 Session 列表功能"""
        # 建立多個測試 Session
        test_sessions = [
            ("list_test_1", "第一個測試 Session", 2),
            ("list_test_2", "第二個測試 Session", 3),
            ("list_test_3", "第三個測試 Session", 1)
        ]
        
        for session_id, summary, count in test_sessions:
            await database_service.save_session_summary(session_id, summary, count)
        
        # 列出 Session
        sessions = await session_service.list_recent_sessions(limit=10)
        
        assert len(sessions) >= len(test_sessions), "應該包含測試 Session"
        
        # 檢查是否包含我們建立的 Session
        session_ids = [s["session_id"] for s in sessions]
        for session_id, _, _ in test_sessions:
            assert session_id in session_ids, f"應該包含 Session: {session_id}"


if __name__ == "__main__":
    # 執行測試
    pytest.main([__file__, "-v"])
