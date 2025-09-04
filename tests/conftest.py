"""
測試配置和共用 fixtures
"""
import pytest
from pathlib import Path


@pytest.fixture
def sample_text_input():
    """文字輸入範例"""
    return {
        "input_type": "text",
        "query": "請查詢 AAPL 的最新報價",
        "options": {}
    }


@pytest.fixture
def sample_file_input():
    """檔案輸入範例"""
    return {
        "input_type": "file",
        "file": {
            "path": "./test_document.pdf",
            "task": "qa",
            "query": "這個文件的主要內容是什麼？"
        },
        "options": {}
    }


@pytest.fixture
def sample_line_input():
    """LINE 輸入範例"""
    return {
        "input_type": "line",
        "line": {
            "user_id": "U1234567890",
            "start": "2025-08-01",
            "end": "2025-09-01"
        },
        "options": {}
    }


@pytest.fixture
def sample_rule_input():
    """規則輸入範例"""
    return {
        "input_type": "rule",
        "rule": {
            "symbols": ["AAPL", "TSLA"],
            "conditions": {
                "price_change": "> 5%"
            }
        },
        "options": {}
    }


@pytest.fixture
def mock_tool_message_data():
    """模擬工具訊息資料"""
    return {
        "ok": True,
        "source": "FMP",
        "timestamp": "2025-09-01T12:00:00Z",
        "data": [
            {
                "symbol": "AAPL",
                "price": 150.25,
                "change": 2.15,
                "changesPercentage": 1.45
            }
        ]
    }


@pytest.fixture
def test_data_dir():
    """測試資料目錄"""
    return Path(__file__).parent / "data"


@pytest.fixture
def temp_output_dir(tmp_path):
    """臨時輸出目錄"""
    output_dir = tmp_path / "outputs"
    output_dir.mkdir(exist_ok=True)
    return output_dir
