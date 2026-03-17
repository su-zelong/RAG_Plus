import torch
import os

from modelscope import AutoModelForCausalLM, AutoTokenizer
from transformers import AutoModel, AutoTokenizer
from FlagEmbedding import FlagReranker


class VL_model:
    """copy from: https://github.com/QwenLM/Qwen-VL/blob/master/README_CN.md"""
    def __init__(self, model_path: str = "Qwen/Qwen-VL-Chat-7B"):
        self.model_path = model_path
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        if not hasattr(self.tokenizer, "model_dir"):
            self.tokenizer.model_dir = model_path
        self.model = AutoModelForCausalLM.from_pretrained(model_path, trust_remote_code=True, device_map="auto").eval()
    
    def generate(self, prompt: str) -> str:
        response = self.model.generate(
            self.tokenizer,
            prompt,
        )
        return response


class Embed_model:
    """cpoy from: https://huggingface.co/BAAI/bge-large-en-v1.5"""
    def __init__(self, cfg):
        self.cfg = cfg
        self.model_path = cfg.get("embedder", {}).get("model_path", "BAAI/bge-large-en-v1.5")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModel.from_pretrained(self.model_path, device_map="auto").eval()
    
    def generate(self, prompt: str):
        encoded_input = self.tokenizer(prompt, padding=True, truncation=True, return_tensors='pt')
        # Compute token embeddings
        with torch.no_grad():
            model_output = self.model(**encoded_input)
            # Perform pooling. In this case, cls pooling.
            sentence_embeddings = model_output[0][:, 0]
        # normalize embeddings
        sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
        return sentence_embeddings


class DocumentReranker:
    def __init__(self, cfg: dict):
        model_name_or_path = cfg.get("reranker", {}).get("model_name_or_path", "BAAI/bge-reranker-large")
        self.reranker = FlagReranker(model_name_or_path, use_fp16=True)
        print(f"✅ Reranker model loaded from: {model_name_or_path}")

    def rerank(self, query: str, lancedb_results: list, top_n: int = 5):
        """
        对 LanceDB 返回的结果进行精细化重排
        """
        if not lancedb_results:
            return []

        # 1. 构造 (Query, Passage) 对
        # 假设你的 LanceDB 结果里文本字段是 'text'
        passages = [res["text"] for res in lancedb_results]
        query_passage_pairs = [[query, p] for p in passages]

        # 2. 计算相似度得分 (分数越高越相关)
        scores = self.reranker.compute_score(query_passage_pairs)

        # 3. 将分数写回结果并排序
        for i, res in enumerate(lancedb_results):
            res["rerank_score"] = scores[i]

        # 按得分从高到低排序
        reranked_results = sorted(lancedb_results, key=lambda x: x["rerank_score"], reverse=True)

        return reranked_results[:top_n]
