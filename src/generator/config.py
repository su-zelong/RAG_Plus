'''
Author: @ccmmy
'''

import os
from server.pkg.fastapi_server import FastAPIServer
from server.pkg.ollama_server import OllamaServer
from server.pkg.vllm_server import VllmServer

class Config():
    def __init__(self):
        # log
        self.log_path = "../log"
        
        # default model config
        self.model_path = "./model/Qwen3_0.6B"
        self.max_new_token = 32768    # 模型最大生成字节数（影响性能） from Qwen3
        self.top_p = 0.9    # 在累计概率为 top_p 中选下一个词
        self.temperature = 0.7  # 模型创造性等级 0-2
        self.top_k = 10   # 生成概率最高的 k 个词中选下一个词
        self.dp_sample = True   # 是否使用概率输出
        self.repetition_penalty = 1    # 越大越降低重复输出
        self.torch_dtype = "auto"
        self.device_map = "auto"

        self.skip_indexing = False  # 是否跳过索引构建
