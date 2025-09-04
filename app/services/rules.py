"""
規則服務模組
處理 Agent 行為規則的載入、驗證和執行
"""
import logging
import re
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RulesService:
    """規則服務類別"""

    def __init__(self):
        self.rules_json_file = Path("rules.json")
        self.rules_md_file = Path("rules.md")
        self.rules_data = {}
        self.rules_content = ""
        self._load_rules()
    
    def _load_rules(self):
        """載入規則檔案（優先 JSON，備用 Markdown）"""
        try:
            # 優先載入 JSON 格式規則
            if self.rules_json_file.exists():
                with open(self.rules_json_file, 'r', encoding='utf-8') as f:
                    self.rules_data = json.load(f)
                logger.info("JSON 規則檔案載入成功")
            else:
                logger.warning(f"JSON 規則檔案不存在: {self.rules_json_file}")
                self.rules_data = {"rules": [], "metadata": {}}

            # 同時載入 Markdown 版本（人讀版）
            if self.rules_md_file.exists():
                with open(self.rules_md_file, 'r', encoding='utf-8') as f:
                    self.rules_content = f.read()
                logger.info("Markdown 規則檔案載入成功")
            else:
                self.rules_content = "# 預設規則\n\n嚴禁捏造任何數據。"

        except json.JSONDecodeError as e:
            logger.error(f"JSON 規則檔案格式錯誤: {str(e)}")
            self.rules_data = {"rules": [], "metadata": {}}
            self.rules_content = "# 預設規則\n\n嚴禁捏造任何數據。"
        except Exception as e:
            logger.error(f"載入規則檔案失敗: {str(e)}")
            self.rules_data = {"rules": [], "metadata": {}}
            self.rules_content = "# 預設規則\n\n嚴禁捏造任何數據。"
    
    def _check_negation(self, query: str, rule: Dict[str, Any]) -> bool:
        """檢查是否為否定句（避免誤判）"""
        # 擴充的否定詞彙
        default_negation_patterns = [
            r'不要.*?編造|不要.*?捏造|不要.*?杜撰|不要.*?虛構',
            r'不.*?編造|不.*?捏造|不.*?杜撰|不.*?虛構',
            r'別.*?編造|別.*?捏造|別.*?杜撰|別.*?虛構',
            r'禁止.*?編造|禁止.*?捏造|禁止.*?杜撰|禁止.*?虛構',
            r'避免.*?編造|避免.*?捏造|避免.*?杜撰|避免.*?虛構',
            r'不可以.*?編造|不可以.*?捏造|不可以.*?杜撰|不可以.*?虛構'
        ]

        # 合併規則中的否定模式和預設模式
        negation_patterns = rule.get("negation_patterns", []) + default_negation_patterns

        for pattern in negation_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.info(f"檢測到否定句，跳過規則檢查: {pattern}")
                return True
        return False
    
    def get_rules_summary(self) -> str:
        """取得規則摘要（最多 8 條）"""
        if not self.rules_data.get("rules"):
            return "規則載入失敗，請檢查 rules.json 檔案。"

        summary_lines = ["目前生效的 Agent 行為規則：", ""]

        rules = self.rules_data["rules"][:8]  # 最多 8 條
        for i, rule in enumerate(rules, 1):
            rule_id = rule.get("id", f"rule_{i}")
            name = rule.get("name", "未命名規則")
            description = rule.get("description", "無說明")

            summary_lines.append(f"{i}. **{name}** ({rule_id})")
            summary_lines.append(f"   {description}")
            summary_lines.append("")

        summary_lines.append("違反規則的請求將被自動拒絕並說明原因。")
        return "\n".join(summary_lines)
    
    def check_violation(self, query: str) -> Optional[Dict[str, Any]]:
        """檢查查詢是否違反規則（擴充同義詞檢測）"""
        if not self.rules_data.get("rules"):
            return None

        # 擴充的編造同義詞
        fabrication_synonyms = [
            r'編造', r'捏造', r'杜撰', r'虛構', r'猜測', r'臆測',
            r'模擬數據', r'假設', r'估算', r'推測', r'想像',
            r'fabricate', r'make up', r'fake', r'simulate'
        ]

        # 檢查編造相關違規（特殊處理）
        if self._check_fabrication_violation(query, fabrication_synonyms):
            return {
                "violated": True,
                "rule_id": "no_fabrication",
                "rule_name": "禁止編造數據",
                "message": "不可編造或捏造任何金融數據",
                "rule_explanation": self._get_violation_explanation("data_fabrication")
            }

        # 檢查其他規則
        for rule in self.rules_data["rules"]:
            # 先檢查否定模式（避免誤判）
            if self._check_negation(query, rule):
                continue

            # 檢查違規模式
            patterns = rule.get("patterns", [])
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return {
                        "violated": True,
                        "rule_id": rule.get("id"),
                        "rule_name": rule.get("name"),
                        "message": rule.get("violation_message", "此請求違反了系統規則"),
                        "rule_explanation": rule.get("violation_message", "此請求違反了系統規則")
                    }

        return None

    def _check_fabrication_violation(self, query: str, synonyms: List[str]) -> bool:
        """檢查編造相關違規（加強否定檢測）"""
        # 否定詞模式
        negation_patterns = [
            r'不要', r'不可', r'不能', r'禁止', r'避免', r'不得',
            r'don\'t', r'do not', r'never', r'avoid', r'prevent'
        ]

        # 檢查是否包含編造同義詞
        has_fabrication = False
        for synonym in synonyms:
            if re.search(synonym, query, re.IGNORECASE):
                has_fabrication = True
                break

        if not has_fabrication:
            return False

        # 檢查是否為否定句（如「不要編造」）
        for negation in negation_patterns:
            # 檢查否定詞是否在編造詞之前
            negation_match = re.search(negation, query, re.IGNORECASE)
            if negation_match:
                for synonym in synonyms:
                    fabrication_match = re.search(synonym, query, re.IGNORECASE)
                    if fabrication_match and negation_match.start() < fabrication_match.start():
                        # 這是否定句，不算違規
                        return False

        return True

    def get_system_prompt_rules(self) -> str:
        """獲取用於 System Prompt 的規則摘要"""
        if not self.rules_data.get("rules"):
            return ""

        rules_lines = ["以下是必須嚴格遵守的系統規則："]

        # 取前 8 條規則
        for i, rule in enumerate(self.rules_data["rules"][:8], 1):
            rule_name = rule.get("name", f"規則 {i}")
            rule_desc = rule.get("description", "")
            rules_lines.append(f"{i}. {rule_name}: {rule_desc}")

        return "\n".join(rules_lines)

    def get_rules_summary(self) -> str:
        """獲取規則摘要清單（供 /rules 查詢使用）"""
        if not self.rules_data.get("rules"):
            return "目前沒有載入任何規則。"

        summary_lines = ["目前生效的系統規則："]

        # 取前 8 條規則
        for rule in self.rules_data["rules"][:8]:
            rule_id = rule.get("id", "unknown")
            rule_name = rule.get("name", "未命名規則")
            rule_desc = rule.get("description", "無描述")
            summary_lines.append(f"{rule_id}｜{rule_name}｜{rule_desc}")

        return "\n".join(summary_lines)

    def reload_rules(self) -> Dict[str, Any]:
        """重新載入規則（供 API 使用）"""
        try:
            self._load_rules()
            return {
                "ok": True,
                "message": "規則已重新載入",
                "rules_count": len(self.rules_data.get("rules", []))
            }
        except Exception as e:
            return {
                "ok": False,
                "message": f"重新載入規則失敗: {str(e)}"
            }

    def _get_violation_explanation(self, violation_type: str) -> str:
        """取得違規說明"""
        explanations = {
            "data_fabrication": """
很抱歉，我無法執行此請求，因為它違反了資料真實性規則。

根據我的行為規範：
- 嚴禁捏造任何數據，包括股價、財務資訊、新聞內容等
- 當 API 金鑰缺失或外部服務不可用時，必須回傳結構化錯誤
- 絕不可編造、估算或猜測任何數值

如需查詢真實股價資訊，請確保已設定 FMP_API_KEY 環境變數。
            """.strip(),
            
            "language_violation": """
很抱歉，我無法執行此請求，因為它違反了語言使用規則。

根據我的行為規範：
- 一律使用繁體中文（#zh-TW）回應
- 所有 API 錯誤訊息、日誌輸出均使用繁體中文
- 程式內註解、文件均使用繁體中文

請使用繁體中文重新提出您的請求。
            """.strip(),
            
            "tech_violation": """
很抱歉，我無法執行此請求，因為它違反了技術規範。

根據我的行為規範：
- 一律使用 uv 進行 Python 環境管理
- 禁止使用 venv、pip、conda 等其他工具
- 所有套件安裝、環境建立均透過 uv 完成

請改用 uv 相關指令重新提出請求。
            """.strip(),
            
            "config_violation": """
很抱歉，我無法執行此請求，因為它違反了設定管理規則。

根據我的行為規範：
- 採用 Config-first 原則：.env → settings → 程式
- 嚴禁硬編碼 API 金鑰、檔案路徑等設定值
- 所有設定必須可透過環境變數覆蓋

請使用環境變數或設定檔案管理相關設定。
            """.strip()
        }
        
        return explanations.get(violation_type, "此請求違反了系統規則，無法執行。")
    
    def get_system_prompt_rules(self) -> str:
        """取得用於系統提示的規則內容"""
        return f"""
你是 Augment Agent，必須嚴格遵循以下行為規則：

1. **嚴禁捏造資料**：絕不可編造股價、財務數據、新聞等任何資訊
2. **一律繁體中文**：所有回應均使用繁體中文（#zh-TW）
3. **uv-only**：僅使用 uv 進行 Python 環境管理
4. **Config-first**：透過環境變數管理設定，禁止硬編碼
5. **PDF 浮水印**：所有 PDF 必須加上「Lens Qunat」浮水印
6. **LINE mock 模式**：USE_MOCK_LINE=1 時明確標示模擬資料

當遇到違反規則的請求時，必須拒絕並說明原因。
當 API 金鑰缺失時，回傳結構化錯誤而非猜測數據。
        """.strip()
    
    def reload_rules(self) -> bool:
        """重新載入規則檔案"""
        try:
            self._load_rules()
            logger.info("規則重新載入成功")
            return True
        except Exception as e:
            logger.error(f"重新載入規則失敗: {str(e)}")
            return False
    
    def get_full_rules(self) -> str:
        """取得完整規則內容"""
        return self.rules_content
    
    def get_rules_stats(self) -> Dict[str, Any]:
        """取得規則統計資訊"""
        return {
            "rules_json_exists": self.rules_json_file.exists(),
            "rules_md_exists": self.rules_md_file.exists(),
            "rules_json_path": str(self.rules_json_file),
            "rules_md_path": str(self.rules_md_file),
            "total_rules": len(self.rules_data.get("rules", [])),
            "rules_version": self.rules_data.get("metadata", {}).get("version", "unknown"),
            "content_length": len(self.rules_content),
            "last_loaded": "system_startup"
        }

    def get_rules_load_error(self) -> Dict[str, Any]:
        """取得規則載入錯誤資訊"""
        return {
            "ok": False,
            "reason": "rules_load_error",
            "message": "規則檔案載入失敗",
            "suggestions": [
                "檢查 rules.json 檔案是否存在",
                "檢查 JSON 格式是否正確",
                "檢查檔案權限是否可讀",
                "嘗試重新啟動服務"
            ],
            "file_path": str(self.rules_json_file)
        }


# 全域規則服務實例
rules_service = RulesService()
