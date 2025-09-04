"""
RAG (Retrieval-Augmented Generation) 服務
提供文件嵌入、向量儲存與相似性搜尋功能
"""
import logging
import json
import pickle
from typing import List, Dict, Any, Tuple
from pathlib import Path
import numpy as np

# OpenAI 嵌入
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from app.settings import settings


logger = logging.getLogger(__name__)


class SimpleVectorStore:
    """簡單的向量儲存實作"""
    
    def __init__(self, store_path: str):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.embeddings_file = self.store_path / "embeddings.pkl"
        self.metadata_file = self.store_path / "metadata.json"
        
        # 載入現有資料
        self.embeddings = []
        self.metadata = []
        self._load_data()
    
    def _load_data(self):
        """載入儲存的向量與元資料"""
        try:
            if self.embeddings_file.exists():
                with open(self.embeddings_file, 'rb') as f:
                    self.embeddings = pickle.load(f)
            
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                    
            logger.info(f"載入 {len(self.embeddings)} 個向量")
        except Exception as e:
            logger.error(f"載入向量資料失敗: {e}")
            self.embeddings = []
            self.metadata = []
    
    def _save_data(self):
        """儲存向量與元資料"""
        try:
            with open(self.embeddings_file, 'wb') as f:
                pickle.dump(self.embeddings, f)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
                
            logger.info(f"儲存 {len(self.embeddings)} 個向量")
        except Exception as e:
            logger.error(f"儲存向量資料失敗: {e}")
    
    def add_embeddings(self, embeddings: List[List[float]], metadata: List[Dict[str, Any]]):
        """新增向量與元資料"""
        self.embeddings.extend(embeddings)
        self.metadata.extend(metadata)
        self._save_data()
    
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """搜尋最相似的向量"""
        if not self.embeddings:
            return []
        
        query_vec = np.array(query_embedding)
        similarities = []
        
        for i, embedding in enumerate(self.embeddings):
            # 計算餘弦相似度
            embed_vec = np.array(embedding)
            similarity = np.dot(query_vec, embed_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(embed_vec))
            similarities.append((self.metadata[i], float(similarity)))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def clear(self):
        """清空向量儲存"""
        self.embeddings = []
        self.metadata = []
        if self.embeddings_file.exists():
            self.embeddings_file.unlink()
        if self.metadata_file.exists():
            self.metadata_file.unlink()


class RAGService:
    """RAG 服務類別"""
    
    def __init__(self):
        self.vector_store = SimpleVectorStore(settings.vector_store_path)
        self.openai_client = None
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimension = 1536
        
        # 初始化 OpenAI 客戶端
        if settings.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        elif settings.azure_openai_api_key and settings.azure_openai_endpoint:
            self.openai_client = AsyncOpenAI(
                api_key=settings.azure_openai_api_key,
                base_url=f"{settings.azure_openai_endpoint}/openai/deployments/{settings.azure_openai_deployment}",
                api_version=settings.azure_openai_api_version
            )
    
    def _check_embedding_capability(self) -> Dict[str, Any]:
        """檢查嵌入功能是否可用"""
        if not self.openai_client:
            return {
                "ok": False,
                "reason": "missing_api_key",
                "message": "OpenAI 或 Azure OpenAI API 金鑰未設定",
                "data": None
            }
        return {"ok": True}
    
    async def create_embeddings(self, texts: List[str]) -> Dict[str, Any]:
        """
        為文字列表建立嵌入向量
        
        Args:
            texts: 文字列表
            
        Returns:
            包含嵌入向量的字典
        """
        check_result = self._check_embedding_capability()
        if not check_result["ok"]:
            return check_result
        
        try:
            # 批次處理嵌入
            embeddings = []
            batch_size = 100  # OpenAI API 限制
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                response = await self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=batch_texts
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
            
            return {
                "ok": True,
                "data": {
                    "embeddings": embeddings,
                    "model": self.embedding_model,
                    "dimension": len(embeddings[0]) if embeddings else 0,
                    "count": len(embeddings)
                },
                "source": "openai_embeddings",
                "timestamp": None
            }
            
        except Exception as e:
            logger.error(f"建立嵌入向量失敗: {str(e)}")
            return {
                "ok": False,
                "reason": "embedding_failed",
                "message": f"建立嵌入向量失敗: {str(e)}",
                "data": None
            }
    
    async def add_documents(self, chunks: List[Dict[str, Any]], file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        將文件分塊加入向量儲存
        
        Args:
            chunks: 文件分塊列表
            file_info: 檔案資訊
            
        Returns:
            處理結果字典
        """
        if not chunks:
            return {
                "ok": False,
                "reason": "no_chunks",
                "message": "沒有文件分塊可處理",
                "data": None
            }
        
        # 擷取文字內容
        texts = [chunk["text"] for chunk in chunks]
        
        # 建立嵌入向量
        embedding_result = await self.create_embeddings(texts)
        if not embedding_result["ok"]:
            return embedding_result
        
        embeddings = embedding_result["data"]["embeddings"]
        
        # 準備元資料
        metadata = []
        for i, chunk in enumerate(chunks):
            metadata.append({
                "chunk_id": chunk["id"],
                "text": chunk["text"],
                "start_char": chunk["start_char"],
                "end_char": chunk["end_char"],
                "length": chunk["length"],
                "file_path": file_info["path"],
                "file_name": file_info["name"],
                "file_type": file_info["type"],
                "created_at": None
            })
        
        # 加入向量儲存
        self.vector_store.add_embeddings(embeddings, metadata)
        
        return {
            "ok": True,
            "data": {
                "chunks_added": len(chunks),
                "embeddings_created": len(embeddings),
                "file_info": file_info
            },
            "source": "rag_service",
            "timestamp": None
        }
    
    async def query_documents(self, 
                            question: str, 
                            top_k: int = 5,
                            similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """
        查詢相關文件片段
        
        Args:
            question: 查詢問題
            top_k: 回傳最相關的 k 個片段
            similarity_threshold: 相似度門檻
            
        Returns:
            查詢結果字典
        """
        # 建立查詢嵌入
        embedding_result = await self.create_embeddings([question])
        if not embedding_result["ok"]:
            return embedding_result
        
        query_embedding = embedding_result["data"]["embeddings"][0]
        
        # 搜尋相似文件
        search_results = self.vector_store.search(query_embedding, top_k)
        
        # 過濾低相似度結果
        filtered_results = [
            (metadata, similarity) 
            for metadata, similarity in search_results 
            if similarity >= similarity_threshold
        ]
        
        # 格式化結果
        relevant_chunks = []
        for metadata, similarity in filtered_results:
            relevant_chunks.append({
                "text": metadata.get("text", ""),
                "similarity": similarity,
                "source": {
                    "file_name": metadata.get("file_name", ""),
                    "file_path": metadata.get("file_path") or metadata.get("path") or metadata.get("filepath") or "",
                    "chunk_id": metadata.get("chunk_id", ""),
                    "start_char": metadata.get("start_char", 0),
                    "end_char": metadata.get("end_char", 0)
                }
            })
        
        return {
            "ok": True,
            "data": {
                "question": question,
                "relevant_chunks": relevant_chunks,
                "total_found": len(search_results),
                "filtered_count": len(filtered_results),
                "similarity_threshold": similarity_threshold
            },
            "source": "rag_service",
            "timestamp": None
        }
    
    async def answer_question(self, 
                            question: str, 
                            context_chunks: List[Dict[str, Any]],
                            max_context_length: int = 4000) -> Dict[str, Any]:
        """
        基於檢索到的文件片段回答問題
        
        Args:
            question: 問題
            context_chunks: 相關文件片段
            max_context_length: 最大上下文長度
            
        Returns:
            回答結果字典
        """
        check_result = self._check_embedding_capability()
        if not check_result["ok"]:
            return check_result
        
        if not context_chunks:
            return {
                "ok": False,
                "reason": "no_context",
                "message": "沒有找到相關的文件內容",
                "data": None
            }
        
        # 建構上下文
        context_parts = []
        current_length = 0
        
        for chunk in context_chunks:
            chunk_text = f"[來源: {chunk['source']['file_name']}]\n{chunk['text']}\n"
            if current_length + len(chunk_text) > max_context_length:
                break
            context_parts.append(chunk_text)
            current_length += len(chunk_text)
        
        context = "\n".join(context_parts)
        
        # 建構提示
        prompt = f"""基於以下文件內容回答問題。請提供準確、具體的回答，並引用相關的文件來源。

文件內容：
{context}

問題：{question}

請回答："""
        
        try:
            # 使用 OpenAI API 生成回答
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一個專業的文件分析助手，能夠基於提供的文件內容準確回答問題。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            return {
                "ok": True,
                "data": {
                    "question": question,
                    "answer": answer,
                    "sources": [chunk["source"] for chunk in context_chunks],
                    "context_length": current_length,
                    "chunks_used": len(context_parts)
                },
                "source": "rag_service",
                "timestamp": None
            }
            
        except Exception as e:
            logger.error(f"生成回答失敗: {str(e)}")
            return {
                "ok": False,
                "reason": "answer_generation_failed",
                "message": f"生成回答失敗: {str(e)}",
                "data": None
            }
    
    def get_store_stats(self) -> Dict[str, Any]:
        """取得向量儲存統計資訊"""
        return {
            "total_embeddings": len(self.vector_store.embeddings),
            "total_documents": len(set(meta.get("file_path", "") for meta in self.vector_store.metadata)),
            "store_path": str(self.vector_store.store_path),
            "embedding_model": self.embedding_model,
            "embedding_dimension": self.embedding_dimension
        }


# 全域 RAG 服務實例
rag_service = RAGService()
