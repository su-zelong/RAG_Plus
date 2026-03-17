"""
Author: @ccmmy
FastAPI server for LLM inference
"""
import logging
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException

from pkg.basic_server import BasicServer
from pkg.types import FastAPIRequest, FastAPIResponse, HealthResponse, SessionRequest, SessinoResponse
from db.sessionmanager import SessionManager

logger = logging.getLogger(__name__)

class FastAPIServer(BasicServer):
    def __init__(self, args):
        super().__init__(args.model_path, args.device)
        self.host = getattr(args, 'host', '0.0.0.0')
        self.port = getattr(args, 'port', 8000)
        
        self.app = FastAPI(
            title="Mini-RAG LLM Server",
            description="Local LLM inference service"
        )
        self.__setup_routes()
        self.__setup_events()
        self.session_manager = SessionManager()

    def __setup_events(self):
        @self.app.on_event("startup")
        async def startup_event():
            logger.info("=" * 50)
            logger.info("Server starting, loading model...")
            try:
                await asyncio.to_thread(super(FastAPIServer, self)._load_llm_model)
                logger.info("✓ Model loaded successfully")
            except Exception as e:
                logger.error(f"✗ Failed to load model: {e}", exc_info=True)
                raise

        @self.app.on_event("shutdown")
        async def shutdown_event():
            logger.info("=" * 50)
            logger.info("Server shutting down, releasing resources...")
            try:
                if self.model is not None:
                    del self.model
                    logger.info("✓ Model released")
                if self.tokenizer is not None:
                    del self.tokenizer
                    logger.info("✓ Tokenizer released")
            except Exception as e:
                logger.error(f"✗ Error during shutdown: {e}")

    def __setup_routes(self):
        
        '''健康检查接口'''
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            if not (self.tokenizer or self.model):
                return HealthResponse(health=False)
            url = self.host + ":" + str(self.port)
            request = FastAPIRequest(prompt="Hello, world!")   # 错误，应该构造json给端口发请求
            resp = await generate_response(request)
            status = bool(resp.status_code == 200 and resp.code == 0)
            return HealthResponse(health=status)

        '''LLM 生成接口'''
        @self.app.post("/generate", response_model=FastAPIResponse)
        async def generate_response(request: FastAPIRequest):
            try:
                if not request.prompt.strip():
                    raise HTTPException(
                        status_code=400,
                        detail="Sorry? What did you say?"
                    )
                logger.info(f"Generating response for prompt: {request.prompt[:50]}...")
                
                # 根据request中的session_id加载历史对话
                if not request.session_id:
                    session_id = self.session_manager.create_session()
                    request.session_id = session_id
                    history = []
                else:
                    history = self.session_manager._load_session(request.session_id)

                # 异步生成思考过程和回答
                thinking_content, content, input_token_count, output_token_count = await asyncio.to_thread(
                    super(FastAPIServer, self)._run_llm,
                    request.prompt,
                    history=history,
                    max_new_tokens=request.max_new_tokens,
                    temperature=request.temperature,
                    top_k=request.top_k,
                    top_p=request.top_p,
                    do_sample=request.do_sample,
                    repetition_penalty=request.repetition_penalty
                )                
                return FastAPIResponse(
                    code=0,
                    input_token_count=input_token_count,
                    output_token_count=output_token_count,
                    thinking_content=thinking_content,
                    content=content
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to generate answer: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Generation failed: {str(e)}"
                )

        @self.app.get("/model_info")
        async def model_info():
            if self.model is None or self.tokenizer is None:
                raise HTTPException(
                    status_code=503,
                    detail="Model not loaded"
                )
            return {
                "model_name": self.model_path.split("/")[-1],
                "vocab_size": self.tokenizer.vocab_size,
                "model_config": self.model.config.to_dict()
            }
    
        @self.app.post("/end_session", response_class=SessinoResponse)
        async def end_session(request: SessionRequest):
            logger.info("Ending session...")
            if not request.session_id:
                raise HTTPException(
                    status_code=400,
                    detail="Session ID is required to end session"
                )
            # 1. 将session相关的资源释放掉
            self.session_manager.end_session(request.session_id)
            # 2. 从session管理器中移除该session
            # 3. 将session_id对应的结果保存进pg


    def start_server(self, reload: bool = False):
        logger.info(f"Starting FastAPI server on {self.host}:{self.port}")
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            reload=reload
        )
