import redis
import json
import uuid
import logging
from psycopg2 import connect, extras
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLevelName(__name__)

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
PG_DBNAME = 'LLM'
PG_USER = 'root'
PG_PASSWORD = '123456'
PG_HOST = 'localhost'
PG_MIN_CONN = 2
PG_MAX_CONN = 10

# redis默认过期时间
SESSION_TTL_SECONDS = 30 * 60 

class SessionManager:

    '''初始化redis/pg 连接池'''    
    def __init__(self):
        # Redis 连接池
        self._redis_pool = redis.ConnectionPool(
            host=REDIS_HOST, 
            port=REDIS_PORT, 
            decode_responses=True
        )
        self.redis_client = redis.Redis(connection_pool=self._redis_pool)

        # PG 连接池
        try:
            self._pg_pool = ThreadedConnectionPool(
                PG_MIN_CONN,
                PG_MAX_CONN,
                dbname=PG_DBNAME,
                user=PG_USER,
                password = PG_PASSWORD,
                host = PG_HOST
            )
            logger.info(f"PostgreSQL initiated successful, max connection clients: {PG_MAX_CONN}, min connection clients: {PG_MIN_CONN}")
        except Exception as e:
            logger.errorf(f"Initiate pg failed, reason is {e}")
            raise
        
        # 确保可持久化
        self._ensure_pg_table()

    '''从pg连接池中获取链接'''
    def _get_pg_connection(self):
        return self._pg_pool.getconn()

    '''释放pg连接回连接池'''
    def _put_pg_conneciton(self, conn):
        self._pg_pool.putconn(conn)

    """确保pg中有session表 所有会话都存在session表中"""
    def _ensure_pg_table(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(50), 
            data JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            conn = self._get_pg_connection()
            with conn.cursor() as cur:
                cur.execute(create_table_sql)
            conn.commit()
        except Exception as e:
            logger.errorf(f"Error ensuring PG table: {e}")
        finally:
            if conn:
                self._put_pg_conneciton(conn)

    """从 PostgreSQL 加载 Session 数据"""
    def load_session_from_pg(self, session_id: str):
        sql = "SELECT data FROM sessions WHERE session_id = %s;"
        try:
            conn = self._get_pg_connection()
            with conn.cursor(cursor_factory=extras.DictCursor) as cur:
                cur.execute(sql, (session_id,))
                result = cur.fetchone()
                return result['data'] if result else None
        except Exception as e:
            logger.errorf(f"Error loading session {session_id} from PG: {e}")
            return None
        finally:
            if conn:
                self._put_pg_conneciton(conn)

    """将 Session 数据保存/更新到 PostgreSQL"""
    def _save_session_to_pg(self, session_id: str, data: json, user_id: str = None):
        sql = """
        INSERT INTO sessions (session_id, user_id, data, updated_at) 
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (session_id) DO UPDATE SET
            data = EXCLUDED.data,
            updated_at = EXCLUDED.updated_at
        ;
        """
        try:
            if not data:
                logger.errorf(f"Can't save session to pg! data={data}")
                raise ValueError(f"Save empty! f{data}")
            conn = self._get_pg_connection()
            with conn.cursor() as cur:
                cur.execute(sql, (session_id, user_id, data))
            conn.commit()
        except Exception as e:
            logger.errorf(f"Error saving session {session_id} to PG: {e}")
        finally:
            if conn:
                self._put_pg_conneciton(conn)

    """创建新会话"""
    def create_session(self, initial_data: dict = None, user_id: str = None) -> str:
        session_id = str(uuid.uuid4())
        data = initial_data if initial_data is not None else [{"role": "user", "content": "让我们说中文！"}]

        self.redis_client.rpush(session_id, json.dumps(data))
        self.redis_client.expire(session_id, SESSION_TTL_SECONDS)

        # 创建redis的同时添加 pg 表中本次会话
        self._save_session_to_pg(session_id, json.dumps(data), user_id)

        return session_id

    """获取当前会话历史"""
    def get_current_history(self, session_id: str) -> list:
        redis_data = self.redis_client.lrange(session_id, 0, -1)
        
        if redis_data:
            self.redis_client.expire(session_id, SESSION_TTL_SECONDS)
            history = [json.loads(item) for item in redis_data]
            return json.dumps(history)
        else:
            logger.errorf(f"Get Current history failed !")
            return json.dumps({})

    '''更新redis'''
    def update_session(self, session_id: str, query: str, answer: str):
        user_history = {"role": "user", "content": query}
        assistant_history = {"role": "assistant", "content": answer}
        self.redis_client.rpush(session_id, json.dumps(user_history))
        self.redis_client.rpush(session_id, json.dumps(assistant_history))
        self.redis_client.expire(session_id, SESSION_TTL_SECONDS)

    """删除 Session 同时从 Redis 和 PostgreSQL 中删除"""
    def delete_session(self, session_id: str):
        # 删除redis 的sessionID
        self.redis_client.delete(session_id)

        sql = "DELETE FROM sessions WHERE session_id = %s;"
        try:
            # 删除pg 对应的sessionID
            conn = self._get_pg_connection()
            with conn.cursor() as cur:
                cur.execute(sql, (session_id,))
            conn.commit()
        except Exception as e:
            logger.errorf(f"Error deleting session {session_id} from PG: {e}")
        finally:
            if conn:
                self._put_pg_conneciton(conn)
    
    '''结束session 删除redis缓存 释放资源池 同步数据到pg'''
    def end_session(self, session_id):
        history = self.get_current_history(session_id)
        self._save_session_to_pg(session_id, history, None)
        self.redis_client.delete(session_id)
        # 释放pg连接池
        self._pg_pool.closeall()
        self._pg_pool = None
