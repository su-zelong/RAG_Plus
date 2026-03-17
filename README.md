# RAG-Plus

## 更新日志：

**🚀2025/12/05 这是一个简单的实现询问本地大模型+RAG(读取本地pdf文件+embed+存入向量知识库)的项目，随着时间推移将会不断完善**

**🚀2025/03/17 整体雏形基本构建完毕**：
    1. 支持：fastapi/vllm/ollama 部署

    2. docker镜像部署云pg + redis，用于保存当前会话和历史记录

    3. mineru解析pdf文件为 markdown

    4. 解析好的md文件再次经过qwen-vl 增加图片描述

    5. 采用marko 纯原生解析md 树，并同时切片

    6. 切片结果存入lancedb 中

    7. query提问检索

**🚀2025/03/17 预计增加rag 后续skill能力，在有文档检索的基础上增加额外agent能力**
 
## 项目雏形：
1. main.py: 
    a. 负责与shell交互，启动server llm服务；
    b. 负责初始化读取配置文件，embed基本配置；llm基本配置
    c. 向量知识库的构建入口
    d. 检索+LLM的调用入口
2. server:
    a. 支持主流LLM打包：FastAPI; Ollama; Vllm...
    b. 支持流失响应
    c. 异步处理请求
    d. pg负责持久化存储聊天记录，redis负责实时sessionID的对话上下文
4. config.py: 模型相关配置项
5. src
    a. index_pipeline: 负责构建知识库，文档解析+切片+向量知识库
    b. reteive_pipeline: 负责向量索引，相似度排序+rerank，调用llm api
6. skills:
    a. 后续演进，基于rag的skill+agent能力

## 使用说明：
```bash
# 1. 如果没有llm服务，可打包本地模型服务
python server/start.py --mode [fastapi/vllm/ollama] --model_path [./custom_llm]
# 2. 
```

## 依赖安装
```bash
pip install -r requirements.txt
```