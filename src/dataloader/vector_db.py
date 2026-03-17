"""
Author: SuZelong
Description: Vector Database class: store and retrieve document chunks with vector embeddings
useage:
    cfg = load_config("config.yaml")
    vector_db = VectorDatabase(cfg, db_path="./vector_db")
    vector_db.add_chunks(chunks, table_name="document_chunks")
    results = vector_db.search_chunks(query_vector, table_name="document_chunks")
"""
import lancedb

from lancedb.pydantic import Vector, LanceModel
from typing import List
from loguru import logger

# 1. 定义元数据结构
class ChunkMetadata(LanceModel):
    document_id: str
    chunk_index: str
    block_type: str
    heading_path: List[str]
    heading_level: int
    image_url: str

# 2. 定义主表结构
class ChunkSchema(LanceModel):
    chunk_id: str
    text: str
    vector: Vector(1024) # type: ignore 假设 BGE-Large 输出是 1024 维，BGE-Small 则是 384
    metadata: ChunkMetadata


class VectorDatabase:
    def __init__(self, cfg: dict):
        self.db_path = cfg.get("vector_database", {}).get("db_path", "./vector_db/lancedb")
        self.db = lancedb.connect(self.db_path)
        self.top_k = int(cfg.get("vector_database", {}).get("top_k", 5))

    # lancedb 添加切片
    def add_chunks(self, chunks, table_name: str):
        if table_name not in self.db.list_tables():
            logger.info(f"🚀  Creating new table: {table_name}")
            table = self.db.create_table(table_name, ChunkSchema)
        else:
            logger.info(f"🚀  Using existing table: {table_name}")
            table = self.db.get_table(table_name)
        table.add(chunks)
        logger.info(f"✅  Added {len(chunks)} chunks to table: {table_name}")
    
    # lancedb 向量检索
    def search_chunks(self, query_vector, table_name: str):
        if table_name not in self.db.list_tables():
            logger.error(f"❌  Table {table_name} does not exist in the database.")
            return []
        
        table = self.db.get_table(table_name)
        results = table.search(query_vector, limit=self.top_k).to_list()
        logger.info(f"✅  Retrieved {len(results)} chunks from table: {table_name}")
        return results

