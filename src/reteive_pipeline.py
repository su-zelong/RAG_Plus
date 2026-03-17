import loguru
from dataloader.vector_db import VectorDatabase
from generator.llm_loader import Embed_model, DocumentReranker


class RetrievePipeline:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.VectorDatabase = VectorDatabase(self.cfg)
        self.Embedding = Embed_model(self.cfg)
        self.Rerank = DocumentReranker(self.cfg)

    def run(self, query: str):
        # 从向量数据库中检索相关切片
        query_vector = self.Embedding.generate(query)
        chunks = self.VectorDatabase.search_chunks(query_vector, table_name="document_chunks")
        # rerank 排序
        rerank_res = self.Rerank.rerank(query, chunks, top_n=5)
        content_list = []
        for i, res in enumerate(rerank_res):
            loguru.logger.info(f"Rank {i+1}: Score={res['rerank_score']:.4f}, Text={res['text'][:100]}...")
            text = res.get("text", "")
            document_id = res.get("metadata", {}).get("document_id", "unknown_doc")
            heading_path = res.get("metadata", {}).get("heading_path", [])
            heading_level = res.get("metadata", {}).get("heading_level", 0)
            content_list.append(f"""Document ID: {document_id}\nHeading Path: {' > '.join(heading_path)}\nHeading Level: {heading_level}\nContent: {text}\n""")

        context_str = "\n---\n".join(content_list)

        prompt = f"""
### SYSTEM INSTRUCTION
You are a highly precise Technical Support Specialist operating as a Retrieval-Augmented Generation (RAG) agent. Your primary objective is to provide accurate, evidence-based answers derived exclusively from the provided Context.

### OPERATIONAL CONSTRAINTS
1. **Source Fidelity**: Your response must be strictly grounded in the [REFERENCE CONTEXT] below. If the provided context does not contain sufficient information to address the query, explicitly state: "I apologize, but the provided documentation does not contain sufficient information to answer this request."
2. **Strict Non-Hallucination**: Do not utilize external knowledge or assume facts beyond the provided text.
3. **Citation Protocol**: Every factual claim or data point must be followed by a citation in square brackets corresponding to the source index, e.g., [1], [2].
4. **Tone and Style**: Maintain a professional, objective, and concise tone. Use Markdown formatting (bullet points, bold text) to improve readability where appropriate.

---

### [REFERENCE CONTEXT]
{context_str}

---

### [USER QUERY]
{query}

---

### FINAL RESPONSE
"""
        return prompt
