'''
@Author: SuZelong
解析模型响应
'''
from pydantic import BaseModel
from typing import Optional

class FastAPIRequest(BaseModel):
    """生成请求模型"""
    prompt: str
    top_k: int = 50
    top_p: float = 0.9
    max_new_tokens: int = 512
    temperature: float = 0.7
    do_sample: bool = True
    repetition_penalty: float = 1.0
    session_id: Optional[str] = None


class FastAPIResponse(BaseModel):
    """生成响应模型"""
    code: int
    input_token_count: int
    output_token_count: int
    thinking_content: str
    content: str

# session 相关请求模型
class SessionRequest(BaseModel):
    session_id: Optional[str] = None

class SessinoResponse(BaseModel):
    success: bool

# 健康检查
class HealthResponse(BaseModel):
    health: bool
