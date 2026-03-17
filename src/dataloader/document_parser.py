"""
Author: SuZelong
Description: Document Parser class: parse documents into md
Reference from: https://github.com/opendatalab/MinerU/blob/master/demo/demo.py 
Usage:
    cfg = load_config("config.yaml")
    doc_parser = DocumentParser(cfg, data_path="data/documents", output_path="output")
    doc_parser.parse_document()
"""
import yaml
import json
import os
import dotenv
from pathlib import Path
from tqdm import tqdm
from loguru import logger

from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, prepare_env, read_fn
from mineru.data.data_reader_writer import FileBasedDataWriter
from mineru.utils.draw_bbox import draw_layout_bbox, draw_span_bbox
from mineru.utils.enum_class import MakeMode
from mineru.backend.vlm.vlm_analyze import doc_analyze as vlm_doc_analyze
from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make

dotenv.load_dotenv()
os.environ["MINERU_MODEL_SOURCE"] = "modelscope"
os.environ["HF_TOKEN"] = ""
os.environ["HF_HOME"] = r"D:\\szl\\mineru"

class DocumentParser:
    """
    Document Parser class: parse documents into md
    reference from: https://github.com/opendatalab/MinerU/blob/master/demo/demo.py 
    """
    def __init__(self, cfg: dict, data_path: str, output_path: str):
        self.cfg = cfg
        self.data_path = Path(data_path)
        self.output_path = Path(output_path)

        self.server_url = cfg.get("document_parser", {}).get("server_url", "")
        if not self.server_url:
            logger.error("❌  Document parser server_url is not configured.")
            raise ValueError("Document parser server_url is required in config.")
            
        self.backend = cfg.get("document_parser", {}).get("backend", "vlm-http-engine")
        logger.info(f"🚀  Document Parser initialized with backend: {self.backend}")
        if self.backend == "":
            logger.error(f"❌  Unsupported document parser backend: {self.backend}")
            raise ValueError(f"Unsupported document parser backend: {self.backend}")

        self.parse_method = cfg.get("document_parser", {}).get("parse_method", "auto")
        self.f_draw_layout_bbox = cfg.get("document_parser", {}).get("f_draw_layout_bbox", False)
        self.f_draw_span_bbox = cfg.get("document_parser", {}).get("f_draw_span_bbox", False)
        self.f_dump_middle_json = cfg.get("document_parser", {}).get("f_dump_middle_json", False)
        self.f_dump_model_output = cfg.get("document_parser", {}).get("f_dump_model_output", False)
        self.f_dump_orig_pdf = cfg.get("document_parser", {}).get("f_dump_orig_pdf", False)
        self.f_dump_content_list = cfg.get("document_parser", {}).get("f_dump_content_list", False)
        self.f_dump_md = cfg.get("document_parser", {}).get("f_dump_md", True)
        self.f_make_md_mode = MakeMode.MM_MD
        self.is_pipeline = False  # 默认使用 VLM，非 pipeline

    def parse_document(self):
        """解析文件夹下的所有 PDF 文件"""
        try:
            # 从路径提取语言标识（路径最后一级作为语言）
            lang = self.data_path.name
            logger.info(f"📂  Starting to parse documents in language: {lang}")

            if not self.data_path.exists():
                raise FileNotFoundError(f"data_path not found: {self.data_path}")

            # 遍历文件夹下的所有 PDF 文件
            pdf_files = sorted(self.data_path.glob("*.pdf"))
            if not pdf_files:
                logger.warning(f"⚠️   No PDF files found in {self.data_path}")
                return

            for pdf_file_path in tqdm(pdf_files, desc=f"Processing {lang}"):
                try:
                    # step 1: 用 VLM 解析文档
                    pdf_info, pdf_byte, pdf_file_name, local_md_dir, local_image_dir, md_writer, middle_json, infer_result = self.parse_with_vlm(
                        pdf_file_path, lang
                    )
                    logger.info(f"✅  Document parsed successfully: {pdf_file_name} in {lang}")

                    # step 2: 保存输出文件
                    self.process_output(
                        pdf_info, pdf_byte, pdf_file_name, local_md_dir, local_image_dir, 
                        md_writer, middle_json, infer_result
                    )
                    logger.info(f"✅  Document processed successfully: {pdf_file_name} in {lang}")

                except Exception as e:
                    logger.exception(f"❌  Failed processing {pdf_file_path}: {e}")
                    continue

        except Exception as e:
            logger.exception(f"❌  Document parsing failed: {e}")
    
    # visual language model 解析文档
    def parse_with_vlm(self, file_path: Path, lang: str):
        """用 VLM 后端解析文档"""
        file_path = Path(file_path)
        pdf_file_name = file_path.stem  # data.pdf -> data
        logger.info(f"📄  Processing document: {file_path.name} in {lang}")
        
        # 读取 PDF 二进制数据
        pdf_byte = read_fn(str(file_path))
        pdf_byte = convert_pdf_bytes_to_bytes_by_pypdfium2(
            pdf_byte, 
            self.cfg.get("start_page_id", 0), 
            self.cfg.get("end_page_id", None)
        )
        
        # 准备输出目录
        local_image_dir, local_md_dir = prepare_env(str(self.output_path), pdf_file_name, self.parse_method)
        logger.info(f"📝  Parsing document: {file_path.name} with {self.parse_method} method")
        
        # 初始化数据写入器
        image_writer = FileBasedDataWriter(local_image_dir)
        md_writer = FileBasedDataWriter(local_md_dir)
        
        # 调用 VLM 解析
        middle_json, infer_result = vlm_doc_analyze(
            pdf_byte, 
            image_writer=image_writer, 
            backend=self.backend, 
            server_url=self.server_url
        )
        pdf_info = middle_json.get("pdf_info", {})

        return pdf_info, pdf_byte, pdf_file_name, local_md_dir, local_image_dir, md_writer, middle_json, infer_result

    def process_output(self, pdf_info, pdf_byte, pdf_file_name, local_md_dir, local_image_dir, md_writer, middle_json, infer_result):
        """处理和保存输出文件"""
        try:
            if self.f_draw_layout_bbox:
                draw_layout_bbox(pdf_info, pdf_byte, local_md_dir, f"{pdf_file_name}_layout.pdf")

            if self.f_draw_span_bbox:
                draw_span_bbox(pdf_info, pdf_byte, local_md_dir, f"{pdf_file_name}_span.pdf")

            if self.f_dump_orig_pdf:
                md_writer.write(
                    f"{pdf_file_name}_origin.pdf",
                    pdf_byte,
                )

            image_dir = str(os.path.basename(local_image_dir))

            if self.f_dump_md:
                make_func = pipeline_union_make if self.is_pipeline else vlm_union_make
                md_content_str = make_func(pdf_info, self.f_make_md_mode, image_dir)
                md_writer.write_string(
                    f"{pdf_file_name}.md",
                    md_content_str,
                )

            if self.f_dump_content_list:
                make_func = pipeline_union_make if self.is_pipeline else vlm_union_make
                content_list = make_func(pdf_info, MakeMode.CONTENT_LIST, image_dir)
                md_writer.write_string(
                    f"{pdf_file_name}_content_list.json",
                    json.dumps(content_list, ensure_ascii=False, indent=4),
                )

            if self.f_dump_middle_json:
                md_writer.write_string(
                    f"{pdf_file_name}_middle.json",
                    json.dumps(middle_json, ensure_ascii=False, indent=4),
                )

            if self.f_dump_model_output:
                md_writer.write_string(
                    f"{pdf_file_name}_model.json",
                    json.dumps(infer_result, ensure_ascii=False, indent=4),
                )

            logger.info(f"✅  Output processed for document: {pdf_file_name}")
        except Exception as e:
            logger.exception(f"❌  Error processing output for {pdf_file_name}: {e}")

if __name__ == "__main__":
    cfg = yaml.safe_load(open("rag_config.yaml", "r", encoding="utf-8"))
    doc_parser = DocumentParser(cfg, data_path="data/en", output_path="test")
    doc_parser.parse_document()