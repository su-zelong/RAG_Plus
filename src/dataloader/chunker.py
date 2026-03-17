"""
Author: SuZelong
Description: Chunker class: chunk documents into small pieces for retrieval
使用marko 解析markdown AST树 根据块类型和标题进行切分 生成切片的元信息包括 文档id、切片id、块类型、标题路径、标题等级等
useage:
    chunker = Chunker(data_path="./data/", output_path="./test", cfg={})
    chunker.chunk_documents()
"""
import yaml
import hashlib
from pathlib import Path
from tqdm import tqdm

import marko
from marko.ext.gfm import GFM
from marko.ext.gfm.elements import Table
from marko.block import Paragraph, Heading, List, Quote
from marko.inline import Image
from loguru import logger


markdown_parser = marko.Markdown(extensions=[GFM])

"""TODO: 当前的chunk根据块类型和标题进行划分 应该增加 chunk_size 和 overlap 的限制"""
class Chunker:
    def __init__(self, data_path: str, output_path: str, cfg: dict):
        self.data_path = Path(data_path)
        self.output_path = Path(output_path)
        self.max_token = int(cfg.get("max_token", "512"))    # 最大切片token数
        self.overlap = int(cfg.get("overlap", "50"))    # 切片重叠token数
    
    def chunk_documents(self):
        for doc in tqdm(self.data_path.glob("*.md"), desc="Chunking documents"):
            doc_id = hashlib.md5(doc.name.encode('utf-8')).hexdigest()
            with open(doc, 'r', encoding='utf-8') as f:
                content = f.read()
                # Implement chunking logic here
                logger.info(f"Chunking document {doc_id}...")
                doc = markdown_parser.parse(content)
                chunks = self._chunk_content(doc, doc_id)
                # Save or process chunks as needed
                logger.info(f"Document {doc_id} chunked into {len(chunks)} chunks... Saving results to {self.output_path}...")
                self._save_chunks(doc_id, chunks)

    def _chunk_content(self, root, document_id: str):
        chunks = []
        chunk_index = 0
        heading_path = []

        # 创建单一切片
        def __create_chunk(text: str, block_type: str):
            nonlocal chunk_index, document_id
            chunk = {
                "chunk_id": str(document_id) + "_" + str(chunk_index),
                "text": text.strip(),    # 切片文本
                "metadata": {
                    "document_id": str(document_id),    # 文档id
                    "chunk_index": str(chunk_index),    # 切片id
                    "block_type": str(block_type),    # 块类型
                    "heading_path": heading_path[:],    # 标题路径
                    "heading_level": len(heading_path),   # 标题等级
                    "image_url": "",    # 图片链接
                }
            }
            # 每创建一个chunk对应id自动 + 1
            chunk_index += 1
            return chunk

        # 迭代挖出纯文本 node类型为block--找出对应 inline elemet
        def __get_text(node):
            text = ""
            if isinstance(node, str):
                return node
            
            if hasattr(node, 'children'):
                if isinstance(node.children, list):
                    for child in node.children:
                        text += __get_text(child)
                elif isinstance(node.children, str):
                    text += node.children
                    
            return text
    
        # 更新chunk
        def __update_chunk(text: str, block_type: str):
            if not text: return 
            # 新加入的文本块与上个切片的文本块类型相同，且标题路径一致，认为是同一个子标题下的内容，直接追加
            if chunks and block_type == chunks[-1]["metadata"]["block_type"] and chunks[-1]["metadata"]["heading_path"] == heading_path:
                chunks[-1]["text"] += text
            else:
                chunk = __create_chunk(text, block_type)
                chunks.append(chunk)
            return

        def dfs(node):
            nonlocal heading_path, chunks

            # 处理有序/无序列表
            if isinstance(node, List):
                text = __get_text(node)
                __update_chunk(text, "List")
            # 处理标题，维护全局标题表
            elif isinstance(node, Heading):
                head = __get_text(node)    # 必定是单标题
                # 退栈
                while heading_path and len(heading_path) >= node.level:
                    heading_path.pop()
                heading_path.append(head)
            # 处理段落，Table/image 已转化为文字 
            elif isinstance(node, Paragraph):
                text = __get_text(node)
                __update_chunk(text, "Paragraph")
            # 处理引用
            elif isinstance(node, Quote):
                text = __get_text(node)
                __update_chunk(text, "Quote")
            elif hasattr(node, 'children') and isinstance(node.children, list):
                # 处理 Document 等容器节点
                for child in node.children:
                    dfs(child)
        
        dfs(root)
        return chunks

    def _save_chunks(self, name: str, chunks: list):
        output_file = self.output_path + f"/{name}_chunks.yaml"
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(chunks, f, allow_unicode=True)
        logger.info(f"✅ Saved {len(chunks)} chunks to {output_file}")


if __name__ == "__main__":
    chunker = Chunker(data_path="../../data/", output_path="../../test", cfg={})
    chunker.chunk_documents()
