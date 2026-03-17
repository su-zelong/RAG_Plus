"""VectorDatabase wrapper for LanceDB following rag_skills.md spec.

提供异步接口：连接、幂等创建表、批量添加、删除、更新（以删+增实现）、向量检索。

使用示例见模块底部的 `async_main`。
"""
from typing import Any, Dict, List, Optional

try:
    import lancedb
except Exception as e:
    lancedb = None


class VectorDatabase:
    """Async wrapper around LanceDB that follows the rules in rag_skills.md.

    要点：
    - 使用异步连接：`lancedb.connect_async`。
    - 批量插入：`table.add(list_of_dicts)`。
    - 默认距离度量为 `cosine`，检索必须使用 `.limit(k)` 和 `.select([...])`。

    注意：此实现对 LanceDB 的具体方法做了最小封装，依赖环境中安装并提供 `lancedb` 包。
    """

    def __init__(self, db_path: str, table_name: str, distance: str = "cosine"):
        if lancedb is None:
            raise ImportError("lancedb package is required. install with `pip install lancedb`")
        self.db_path = db_path
        self.table_name = table_name
        self.distance = distance
        self.db = None
        self.table = None

    async def connect(self) -> None:
        """异步连接并打开（或创建）表，保证幂等性。"""
        # 1. 建立异步连接
        # 按 rag_skills.md 建议使用 connect_async
        self.db = await lancedb.connect_async(self.db_path)

        # 2. 幂等创建/打开表
        table_names = await self.db.table_names()
        if self.table_name not in table_names:
            # create empty table with no data; caller can add later
            # create_table 接口在不同版本中可能接受 schema 或 data
            # 此处使用最稳健的 create_table(table_name, data=None)
            self.table = await self.db.create_table(self.table_name)
        else:
            self.table = await self.db.open_table(self.table_name)

    async def add_batch(self, records: List[Dict[str, Any]]) -> None:
        """批量添加记录。records 是 dict 列表，必须包含 embedding 向量字段（例如 'embedding'）。

        要求：避免单条插入，请一次性传入列表以获得最佳性能。
        """
        if self.table is None:
            raise RuntimeError("Not connected. call connect() first")
        if not records:
            return
        await self.table.add(records)

    async def delete_by_ids(self, ids: List[Any]) -> None:
        """按 id 列表删除记录。实现依赖于 LanceDB 表的 `delete` 方法。"""
        if self.table is None:
            raise RuntimeError("Not connected. call connect() first")
        if not ids:
            return
        # 大多数 LanceDB 版本支持按 ids 删除
        await self.table.delete(ids=ids)

    async def update_by_id(self, id_value: Any, new_record: Dict[str, Any]) -> None:
        """按 id 更新记录（内部实现为删除 + 批量添加单条记录以保证幂等）。

        注意：LanceDB 的具体版本可能支持局部更新；为保证兼容性此处采用删后加实现。
        """
        if self.table is None:
            raise RuntimeError("Not connected. call connect() first")
        await self.table.delete(ids=[id_value])
        await self.table.add([new_record])

    async def query(self, query_vector: List[float], k: int = 5, select_fields: Optional[List[str]] = None):
        """按向量检索并返回结果列表。

        - 强制使用 `.limit(k)`。
        - 强制使用 `.select(select_fields)`（如果给定）以降低 I/O。
        返回异步结果 `to_list()` 的原样内容。
        """
        if self.table is None:
            raise RuntimeError("Not connected. call connect() first")
        q = await self.table.search(query_vector)
        q = q.limit(k)
        if select_fields:
            q = q.select(select_fields)
        results = await q.to_list()
        return results

    async def close(self) -> None:
        """关闭 db 连接（如果需要）。"""
        # LanceDB 的异步客户端可能不需要显式关闭，但提供占位接口以便调用方使用
        self.db = None
        self.table = None


# Example usage (for user reference)
async def async_main():
    """示例：如何使用 VectorDatabase

    - 确保在异步环境中运行（例如 asyncio.run(async_main())）。
    """
    db = VectorDatabase("./data/lancedb", "my_table")
    await db.connect()

    # 批量添加（示例）
    records = [
        {"id": 1, "text": "hello", "embedding": [0.1, 0.2, 0.3], "metadata": {"source": "doc1"}},
        {"id": 2, "text": "world", "embedding": [0.0, 0.2, 0.9], "metadata": {"source": "doc2"}},
    ]
    await db.add_batch(records)

    # 向量检索
    qvec = [0.05, 0.1, 0.2]
    results = await db.query(qvec, k=3, select_fields=["id", "text", "metadata"])
    print(results)

    # 更新与删除示例
    await db.update_by_id(1, {"id": 1, "text": "hello updated", "embedding": [0.1, 0.2, 0.31]})
    await db.delete_by_ids([2])
