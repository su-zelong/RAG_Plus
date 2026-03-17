import sys
import torch
import logging
import argparse

from generator.config import Config
from dataloader.chunker import Chunker
from dataloader.vector_db import VectorDB
from src.index_pipeline import IndexPipeline
from src.reteive_pipeline import RetrievePipeline

config = Config()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)

def main(args, query: str):
    # 构建向量索引
    if not config.get("skip_indexing", False):
        index_pipeline = IndexPipeline(cfg_path="./rag_config.yaml")
        index_pipeline.run()

    # 检索相关切片
    retrieve_pipeline = RetrievePipeline(cfg=config.cfg)
    results = retrieve_pipeline.run(query)
    print(results)


if __name__ == "__main__":

    parse = argparse.ArgumentParser()

    parse.add_argument("--model_name", default="Qwen3_0.6B", help="")
    parse.add_argument("--embed_model_name", default="bge", help="")
    parse.add_argument("--reranking_model", default="coBERT", help="")
    parse.add_argument("--query", default="What is the main topic of the document?", help="Query string for retrieval")

    args = parse.parse_args()

    args.device = 'cuda' if torch.cuda.is_available() else 'cpu'

    main(args, query=args.query)
