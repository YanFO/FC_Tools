"""
設定映射測試
測試 settings.py 中的 alias 映射與布林字串解析功能
"""
import pytest
import os
from unittest.mock import patch
from app.settings import Settings


class TestSettingsMapping:
    """測試設定映射與型別轉換"""

    def test_alias_mapping(self):
        """測試環境變數 alias 映射"""
        env_vars = {
            "EXECUTE_TOOLS": "1",
            "COLLOQUIAL_ENABLED": "1", 
            "MAX_TOOL_LOOPS": "5",
            "LLM_REPORT_ENHANCEMENT": "1",
            "OPENAI_API_KEY": "test-key",
            "FMP_API_KEY": "test-fmp-key",
            "OUTPUT_DIR": "test-output",
            "TEMPLATES_DIR": "test-templates",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            # 測試 alias 映射生效
            assert settings.execute_tools == 1
            assert settings.colloquial_enabled == 1
            assert settings.max_tool_loops == 5
            assert settings.llm_report_enhancement == 1
            assert settings.openai_api_key == "test-key"
            assert settings.fmp_api_key == "test-fmp-key"
            assert settings.output_dir == "test-output"
            assert settings.templates_dir == "test-templates"

    def test_boolean_string_parsing_true_values(self):
        """測試布林字串解析 - 真值"""
        true_values = ["1", "true", "True", "TRUE", "yes", "Yes", "on", "y", "t"]
        
        for value in true_values:
            env_vars = {
                "EXECUTE_TOOLS": value,
                "COLLOQUIAL_ENABLED": value,
                "LLM_REPORT_ENHANCEMENT": value,
            }
            
            with patch.dict(os.environ, env_vars, clear=True):
                settings = Settings()
                
                assert settings.execute_tools == 1, f"Failed for value: {value}"
                assert settings.colloquial_enabled == 1, f"Failed for value: {value}"
                assert settings.llm_report_enhancement == 1, f"Failed for value: {value}"

    def test_boolean_string_parsing_false_values(self):
        """測試布林字串解析 - 假值"""
        false_values = ["0", "false", "False", "FALSE", "no", "No", "off", "n", "f", ""]
        
        for value in false_values:
            env_vars = {
                "EXECUTE_TOOLS": value,
                "COLLOQUIAL_ENABLED": value,
                "LLM_REPORT_ENHANCEMENT": value,
            }
            
            with patch.dict(os.environ, env_vars, clear=True):
                settings = Settings()
                
                assert settings.execute_tools == 0, f"Failed for value: {value}"
                assert settings.colloquial_enabled == 0, f"Failed for value: {value}"
                assert settings.llm_report_enhancement == 0, f"Failed for value: {value}"

    def test_integer_values(self):
        """測試整數值直接設定"""
        env_vars = {
            "EXECUTE_TOOLS": "1",
            "COLLOQUIAL_ENABLED": "0",
            "MAX_TOOL_LOOPS": "10",
            "LLM_REPORT_ENHANCEMENT": "1",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.execute_tools == 1
            assert settings.colloquial_enabled == 0
            assert settings.max_tool_loops == 10
            assert settings.llm_report_enhancement == 1

    def test_default_values(self):
        """測試預設值（忽略 .env 檔案）"""
        # 創建一個不讀取 .env 檔案的 Settings 實例
        from pydantic_settings import SettingsConfigDict

        class TestSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=None,  # 不讀取 .env 檔案
                env_file_encoding="utf-8",
                case_sensitive=False,
                extra="ignore",
                populate_by_name=True,
            )

        with patch.dict(os.environ, {}, clear=True):
            settings = TestSettings()

            # 測試預設值
            assert settings.execute_tools == 1
            assert settings.colloquial_enabled == 1
            assert settings.max_tool_loops == 3
            assert settings.llm_report_enhancement == 1
            assert settings.openai_api_key is None
            assert settings.fmp_api_key is None
            assert settings.output_dir == "./outputs"
            assert settings.templates_dir == "templates/reports"

    def test_mixed_types(self):
        """測試混合型別設定"""
        env_vars = {
            "EXECUTE_TOOLS": "true",  # 字串布林值
            "COLLOQUIAL_ENABLED": "1",  # 字串數字
            "MAX_TOOL_LOOPS": "7",  # 字串數字
            "LLM_REPORT_ENHANCEMENT": "false",  # 字串布林值
            "OUTPUT_DIR": "./custom-output",  # 字串
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.execute_tools == 1
            assert settings.colloquial_enabled == 1
            assert settings.max_tool_loops == 7
            assert settings.llm_report_enhancement == 0
            assert settings.output_dir == "./custom-output"

    def test_case_insensitive(self):
        """測試大小寫不敏感"""
        env_vars = {
            "execute_tools": "1",  # 小寫環境變數名
            "COLLOQUIAL_ENABLED": "TRUE",  # 大寫值
            "max_tool_loops": "3",  # 小寫環境變數名
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            # 由於 populate_by_name=True，應該能正確映射
            assert settings.execute_tools == 1
            assert settings.colloquial_enabled == 1
            assert settings.max_tool_loops == 3
