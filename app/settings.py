"""
應用程式設定模組
使用 Pydantic Settings 管理環境變數與配置
"""
import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 布林值真值集合
_truthy = {"1", "true", "yes", "on", "y", "t"}

class Settings(BaseSettings):
    """應用程式設定類別"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # Core Application
    app_name: str = Field(default="AI FC Tools", alias="APP_NAME", description="應用程式名稱")
    app_env: str = Field(default="dev", alias="APP_ENV", description="執行環境")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL", description="日誌等級")
    host: str = Field(default="0.0.0.0", alias="HOST", description="服務主機")
    port: int = Field(default=8000, alias="PORT", description="服務埠號")

    # CORS Configuration
    allowed_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", alias="ALLOWED_ORIGINS", description="允許的來源")

    # LLM Provider Configuration
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER", description="LLM 供應商 (openai/azure)")

    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY", description="OpenAI API 金鑰")

    # Azure OpenAI Configuration
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT", description="Azure OpenAI 端點")
    azure_openai_api_key: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_KEY", description="Azure OpenAI API 金鑰")
    azure_openai_deployment: str = Field(default="gpt-4o-testing", alias="AZURE_OPENAI_DEPLOYMENT", description="Azure OpenAI 部署名稱")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", alias="AZURE_OPENAI_API_VERSION", description="Azure OpenAI API 版本")

    # External APIs
    fmp_api_key: Optional[str] = Field(default=None, alias="FMP_API_KEY", description="Financial Modeling Prep API 金鑰")

    # LINE Messaging API
    line_channel_access_token: Optional[str] = Field(default=None, alias="LINE_CHANNEL_ACCESS_TOKEN", description="LINE Channel Access Token")
    line_channel_secret: Optional[str] = Field(default=None, alias="LINE_CHANNEL_SECRET", description="LINE Channel Secret")
    use_mock_line: int = Field(default=1, alias="USE_MOCK_LINE", description="使用 LINE 模擬模式 (1=模擬, 0=真實)")

    # Agent 執行控制 - 使用 alias 映射環境變數
    execute_tools: int = Field(default=1, alias="EXECUTE_TOOLS", description="工具執行控制 (1=執行工具, 0=僅規劃)")
    colloquial_enabled: int = Field(default=1, alias="COLLOQUIAL_ENABLED", description="口語化摘要啟用 (1=產生 nlg.colloquial, 0=不產生)")
    max_tool_loops: int = Field(default=3, alias="MAX_TOOL_LOOPS", description="最大工具執行循環次數")
    llm_planning_enabled: bool = Field(default=True, alias="LLM_PLANNING_ENABLED", description="LLM 規劃啟用")

    # LLM 報告增強 - 使用 alias 映射環境變數
    llm_report_enhancement: int = Field(default=1, alias="LLM_REPORT_ENHANCEMENT", description="LLM 報告增強 (1=先分析再產報告, 0=直接渲染模板)")
    llm_analysis_temperature: float = Field(default=0.3, alias="LLM_ANALYSIS_TEMPERATURE", description="LLM 分析溫度參數")
    llm_analysis_max_tokens: int = Field(default=2000, alias="LLM_ANALYSIS_MAX_TOKENS", description="LLM 分析最大 token 數")
    llm_analysis_timeout: int = Field(default=30, alias="LLM_ANALYSIS_TIMEOUT", description="LLM 分析超時秒數")

    # UI/UX Configuration (保持向後相容)
    supervisor_ui_casual: bool = Field(default=False, description="口語化回覆開關（已棄用，請使用 colloquial_enabled）")

    # 輸出與檔案設定 - 使用 alias 映射環境變數
    output_dir: str = Field(default="./outputs", alias="OUTPUT_DIR", description="輸出目錄")
    templates_dir: str = Field(default="templates/reports", alias="TEMPLATES_DIR", description="報告模板目錄")
    pdf_css_path: str = Field(default="resources/pdf/default.css", alias="PDF_CSS_PATH", description="PDF CSS 樣式路徑")
    fonts_dir: str = Field(default="resources/fonts", alias="FONTS_DIR", description="字體目錄")
    rag_index_dir: str = Field(default="data/rag_index", alias="RAG_INDEX_DIR", description="RAG 向量索引目錄")

    # PDF Configuration
    pdf_engine: str = Field(default="weasyprint", alias="PDF_ENGINE", description="PDF 渲染引擎")
    pdf_overlay_font: str = Field(default="resources/fonts/NotoSansCJK-Regular.ttf", alias="PDF_OVERLAY_FONT", description="PDF 疊印字體")

    # 參數設定
    news_topk: int = Field(default=3, description="新聞摘要取前 N 篇")
    macro_last_n: int = Field(default=6, description="總經數據取最近 N 期")

    # 口語化設定
    colloquial_system_prompt: Optional[str] = Field(default=None, description="口語化轉換的 System Prompt")

    # Session Configuration
    session_context_strategy: str = Field(default="summary", description="Session 上下文策略")
    session_history_max_turns: int = Field(default=6, description="Session 歷史最大輪數")
    session_summary_max_tokens: int = Field(default=512, description="Session 摘要最大 tokens")

    # File Storage
    upload_dir: str = Field(default="./uploads", description="檔案上傳目錄")
    output_dir: str = Field(default="./outputs", description="輸出檔案目錄")

    # Vector Store
    vector_store_path: str = Field(default="./vector_store", description="向量資料庫路徑")
    vectorstore_dir: str = Field(default="./outputs/vectorstore", description="向量儲存目錄")

    # Logging
    log_format: str = Field(default="json", description="日誌格式")
    log_file: str = Field(default="./logs/app.log", description="日誌檔案路徑")

    # Database
    database_url: str = Field(default="sqlite:///./outputs/sessions.db", description="資料庫連線 URL")

    # Misc
    seed: int = Field(default=42, description="隨機種子")

    # Agent Execution Control (已移至上方，避免重複定義)

    # LLM Planning
    llm_planning_enabled: bool = Field(default=True, description="允許 LLM 規劃（/report 會臨時關掉）")

    # NLG Configuration
    colloquial_system_prompt: str = Field(
        default=(
            "你是金融研究助理，請將模型輸出的正式摘要轉成口語、簡潔、可讀性高的中文回覆。"
            "需保留關鍵數字與日期，避免誤導語氣，不做杜撰。"
            "若屬新聞查詢：先輸出前 N 篇精簡摘要（1-2 句/則），其後列出「標題 + 來源 + 連結」。"
        ),
        description="口語化處理的系統提示"
    )

    # Data Collection Parameters
    news_topk: int = Field(default=3, description="新聞摘要取前 N 篇")
    macro_last_n: int = Field(default=6, description="總經數據取最近 N 期")
    macro_lookback_years: int = Field(default=3, description="總經數據最大回溯年數")

    # Report Generation Settings (移除重複的 pdf_engine)
    pdf_watermark_text: str = Field(default="Lens Quant", description="PDF 浮水印文字")
    pdf_default_css: str = Field(default="resources/pdf/default.css", description="PDF 預設樣式檔案")

    # 口語化設定 (已移至上方 Agent 執行控制區塊，避免重複定義)
    colloquial_system_prompt: str = Field(
        default="你是金融研究助理，請將模型輸出的正式摘要轉成口語、簡潔、可讀性高的中文回覆。需保留關鍵數字與日期，避免誤導語氣，不做杜撰。若屬新聞查詢：先輸出前 N 篇精簡摘要（1-2 句/則），其後列出「標題 + 來源 + 連結」。",
        description="口語化轉換的 System Prompt"
    )

    # 布林值轉換驗證器 - 支援 true/false/1/0 字串
    @field_validator("execute_tools", "colloquial_enabled", "llm_report_enhancement", "use_mock_line", mode="before")
    @classmethod
    def _boolish_to_int(cls, v):
        """兼容 .env 的 true/false 或 1/0，統一轉為 int"""
        if isinstance(v, bool):
            return 1 if v else 0
        if isinstance(v, int):
            return v
        if v is None:
            return 0
        s = str(v).strip().lower()
        return 1 if s in _truthy else 0
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 確保必要目錄存在
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        os.makedirs(self.vector_store_path, exist_ok=True)
    
    @property
    def api_status(self) -> dict:
        """回傳 API 金鑰狀態"""
        return {
            "openai": bool(self.openai_api_key),
            "azure_openai": bool(self.azure_openai_api_key and self.azure_openai_endpoint),
            "fmp": bool(self.fmp_api_key),
            "line": bool(self.line_channel_access_token and self.line_channel_secret),
            "llm_provider": self.llm_provider,
            "use_mock_line": bool(self.use_mock_line)
        }

    @property
    def allowed_origins_list(self) -> list:
        """回傳允許的來源列表"""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


# 全域設定實例
settings = Settings()
