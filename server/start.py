import argparse
import logging
import torch

from pkg.fastapi_server import FastAPIServer
from pkg.ollama_server import OllamaServer
from pkg.vllm_server import VllmServer

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)

def main(args):
    mode_dict = {
        "fastapi": FastAPIServer,
        "ollama": OllamaServer,
        "vllm": VllmServer
    }
    Server = mode_dict.get(args.mode, None)
    if not Server:
        logging.error(f"{args.mode} not supprot yet! Please choice in ['fastapi', 'ollama', 'vllm'] ! ")
        return
    server = Server(args)
    server.start_server()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--mode", default="fastapi", choices=["fastapi", "ollama", "vllm"])
    parser.add_argument("--model_path", default="../../model/Qwen3_0.6B", help="")

    args = parser.parse_args()
    
    args.device = "cuda:0" if torch.cuda.is_available() else 'cpu'

    main(args)
