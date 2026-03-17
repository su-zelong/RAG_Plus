'''
Author: @SuZelong
所有的打包本地llm方法都要继承此类
'''
import logging
from modelscope import AutoModelForCausalLM, AutoTokenizer


logger = logging.getLogger(__name__)

class BasicServer():
    def __init__(self, model_path: str, device: str = 'cuda:0'):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.device = device

    def _load_llm_model(self, torch_dtype: str = "auto", device_map: str = "auto", iseval: bool = True):
        try:
            logger.info(f"Loading tokenizer from {self.model_path}...")
            self.tokenizer = self._load_tokenizer()
            logger.info(f"Loading model from {self.model_path}...")
            self.model = self._load_model(iseval, torch_dtype, device_map)

            logger.info("Model and tokenizer loaded successfully")
        except Exception as e:  
            logger.error(f"Failed to load LLM: {e}")
            raise

    # 通用方法--调用本地LLM
    def _run_llm(self, prompt, history, max_new_tokens, temperature, top_k, top_p, do_sample, repetition_penalty):
        if self.tokenizer is None or self.model is None:
            raise RuntimeError("Model not loaded. Call _load_llm_model() first.")
        try:
            logger.info(f"Running LLM inference for prompt: {prompt[:50]}...")
            message = history + [{"role": "user", "content": prompt}]   # 需要拼接history + prompt
            inputs = self.tokenizer.apply_chat_template(
                    message,
                    tokenize=False,
                    add_generation_prompt=False,
                    enable_thinking=True    # 默认开启思考模式
                )
            input_token_count = len(self.tokenizer.tokenize(inputs))                
            model_inputs = self.tokenizer([inputs], return_tensors="pt").to(self.device)
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                do_sample=do_sample,
                repetition_penalty=repetition_penalty 
            )
            output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
            try:
                index = len(output_ids) - output_ids[::-1].index(151668)
            except ValueError:
                index = 0
            
            thinking_content = self.tokenizer.decode(
                output_ids[:index],
                skip_special_tokens=True
            ).strip()
            content = self.tokenizer.decode(
                output_ids[index:],
                skip_special_tokens=True
            ).strip()
            logger.info(f"✓ Response generated successfully")

            output_token_count = len(self.tokenizer.tokenize(content))

            return thinking_content, content, input_token_count, output_token_count
        
        except Exception as e:
            logger.error(f"LLM inference failed: {e}", exc_info=True)
            raise

    def _run_demo(self) -> str:
        query = "Hello, how are you?"
        think_ans, ans, _, _ = self._run_llm(query, history=[], max_new_tokens=50, temperature=1.0, top_k=50, top_p=1.0, do_sample=True, repetition_penalty=1.0)
        return bool(ans) and bool(think_ans)

    # tokenizer
    def _load_tokenizer(self) -> AutoTokenizer:
        return AutoTokenizer.from_pretrained(self.model_path)

    # model
    def _load_model(self, iseval: bool, torch_dtype: str, device_map: str) -> AutoModelForCausalLM:
        model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch_dtype,
            device_map=device_map
        )
        return model if not iseval else model.eval()
