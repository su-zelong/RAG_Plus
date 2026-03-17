"""
@Author: SuZelong
构建索引pipeline工作流:
1. 解析data_path下的所有pdf文件为markdown
2. 解析生成的中间产物markdown 将其中的图片增加描述 输出到最终文件
3. 读md文档切片
4. 将切片存入vectoreDB
所有配置均从 config.py 中导入
"""

from pathlib import Path

from dataloader.document_parser import DocumentParser
from dataloader.md_parser import MdParser
from dataloader.chunker import Chunker
from dataloader.vector_db import VectorDatabase
from generator.utils import *


class IndexPipeline:
    def __init__(self, cfg_path: str):
        self.cfg = load_config(cfg_path)
        self.document_parser = DocumentParser(self.cfg, data_path=self.cfg.get("document_parser", {}).get("data_path", "data"), output_path=self.cfg.get("document_parser", {}).get("output_path", "output"))
        self.md_parser = MdParser(self.cfg, data_path=self.cfg.get("md_parser", {}).get("data_path", "data"), output_path=self.cfg.get("md_parser", {}).get("output_path", "output"))   # 解析md中的图片 增加图片描述
        self.chunker = Chunker(cfg=self.cfg, data_path=self.cfg.get("chunker", {}).get("data_path", "data"), output_path=self.cfg.get("chunker", {}).get("output_path", "output"))    # md文档切片
        self.vector_db = VectorDatabase(self.cfg)    # 存入知识库

    def run(self):
        # 1. 解析pdf为markdown
        self.document_parser.parse_document()
        # 2. 解析markdown 增加图片描述
        self.md_parser.parse_markdown()
        # 3. 切片并存入向量数据库
        self.chunker.chunk_documents()
        chunk_output_path = self.cfg.get("chunker", {}).get("output_path", "output")
        for chunk_file in Path(chunk_output_path).glob("*_chunks.yaml"):
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunks = yaml.safe_load(f)
                self.vector_db.add_chunks(chunks, table_name="document_chunks")
        return
