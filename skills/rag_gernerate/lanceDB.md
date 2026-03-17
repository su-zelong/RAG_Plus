# Skill: LanceDB 向量数据库专家

## 概述
此技能用于在 Python 环境下高效驱动 LanceDB，涵盖表管理、向量搜索、混合搜索以及大规模数据入库（Ingestion）的性能优化。

## 何时使用此技能
- 需要在 RAG Plus 项目中定义或初始化向量表 Schema 时。
- 需要将文档分块（Chunks）及其 Embedding 向量持久化到本地或云端时。
- 需要实现基于语义相似度（ANN）或全文检索（FTS）的混合召回逻辑时。

## 工作原理

### 步骤1：连接与 Schema 定义
- 使用 `lancedb.connect()` 建立异步连接。
- 使用 `Pydantic` 或 `PyArrow` 显式定义 Schema，确保维度（Dimension）与模型匹配。

### 步骤2：高效入库 (Vibe: 批量优先)
- 避免循环单条插入，必须使用 `table.add(list_of_dicts)` 进行批量操作。
- 入库前检查数据去重，防止同一文档重复向量化。

### 步骤3：智能检索
- 默认使用 `cosine` 距离。
- 必须通过 `.limit(k)` 限制召回数量。
- 必须使用 `.select(["field1", "field2"])` 仅返回必要字段，减少 I/O 开销。

## 示例：标准异步搜索与插入

```python
import lancedb
import pandas as pd
from typing import List, Dict

async def manage_vector_data(db_path: str, table_name: str, data: List[Dict]):
    # 1. 连接数据库
    db = await lancedb.connect_async(db_path)
    
    # 2. 幂等创建/打开表 (Vibe: 显式处理 Schema)
    if table_name not in await db.table_names():
        table = await db.create_table(table_name, data=data)
    else:
        table = await db.open_table(table_name)
    
    # 3. 批量添加数据
    await table.add(data)

async def perform_hybrid_search(table_name: str, query_vec: List[float]):
    db = await lancedb.connect_async("./data/lancedb")
    table = await db.open_table(table_name)
    
    # 4. 向量检索 (Vibe: 只选需要的字段)
    results = await table.search(query_vec) \
        .limit(5) \
        .select(["id", "text", "metadata"]) \
        .to_list()
    
    return results