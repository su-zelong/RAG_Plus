"""
Author: SuZelong
Description: Markdown Parser class: parse markdown content into nature language text
useage:
    cfg = load_config("config.yaml")
    md_parser = MdParser(cfg, data_path="data/markdowns", output_path="output", model=qwen_vl_model)
    md_parser.parse_md_content()
"""
from tqdm import tqdm

from loguru import logger
from pathlib import Path

import marko
from marko.ext.gfm import GFM
from marko.ext.gfm.elements import Table
from marko.block import Paragraph, Heading
from marko.inline import Image


markdown_parser = marko.Markdown(extensions=[GFM])

class MdParser:
    def __init__(self, cfg: dict, data_path: str, output_path: str, model):
        """Parse markdown's content: [image, table, text...] to nature language"""
        self.data_path = Path(data_path)
        self.output_path = Path(output_path)
        self.cfg = cfg
        # load Qwen-VL model
        self.model = model   
    
    def parse_md_content(self) -> str:
        for md_file in tqdm(self.data_path.glob("*.md")):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"✅ Parsed content from {md_file.name}")
                doc = markdown_parser.parse(content)

                # step 1: parse markdown AST
                parsed_content = self._parse_markdown_ast(doc)

                # step 2: save parsed content
                self._save_result(md_file.stem, parsed_content)

    def _parse_markdown_ast(self, root):

        def __get_text(node):
            text = ""
            if isinstance(node, str):
                return node
            
            if hasattr(node, 'children'):
                if isinstance(node.children, list):
                    for child in node.children:
                        text += __get_text(child)
                elif isinstance(node.children, str):
                    text += node.children
            return text
        
        for node in root.children:
            # 解析表格
            if isinstance(node, Table):
                descrip = self._handle_table(__get_text(node))
                new_node = Paragraph(descrip)
                root.children[root.children.index(node)] = new_node
            # 解析图片
            elif isinstance(node, Paragraph):
                for line in node.children:
                    if isinstance(line, Image):
                        descrip = self._handle_image(line.dest)
                        # 用解析后的文本替换图片节点
                        new_node = Paragraph(descrip)
                        root.children[root.children.index(node)] = new_node
        return root
    
    def _handle_image(self, url: str) -> str:

        prompt = f"""

Role Definition You are a high-precision document parsing expert. Your mission is to convert images from Markdown documents into detailed, searchable text optimized for RAG systems.

Task Objective Analyze all visual and textual elements in the uploaded image. Synthesize them into a single, logically organized, and semantically rich paragraph.

Core Requirements

Full Text Extraction: Transcribe every piece of text, label, and data point verbatim. Integrate these into the narrative without omitting technical terms or codes.

Contextual Interpretation:

Flowcharts: Detail the directional flow, decision nodes, and sequence of operations.

Charts/Graphs: Identify axis titles, legends, specific data values, and the overall trend or takeaway.

Architecture Diagrams: Describe components, their spatial orientation (e.g., "on top of", "contained within"), and their interconnectivity (e.g., "connected via API").

UI/Code Snippets: Describe the interface elements or transcribe the code exactly, noting the programming language or UI context.

Tables: Describe tabular data by row-column relationships (e.g., "The row for X shows a value of Y for the Z column").

Logos/Icons: Recognize and name well-known brand logos or industry-standard icons.

Language & Style: * Maintain the original language of the text found in the image.

Be objective and exhaustive.

Ensure the flow is natural to maximize vector embedding quality for retrieval.

Output Constraints (Strictly Enforced)

NO conversational filler, preamble (e.g., "The image depicts..."), or meta-commentary.

NO line breaks, paragraph breaks, bullet points (*, -), or numbered lists.

NO Markdown formatting (no bolding, no tables, no code blocks ```).

OUTPUT FORMAT: A single, continuous block of plain text using only standard punctuation.

Image to Process: {url}
        """
        descrip = self.model.generate(prompt, image=url)
        return descrip

    def _handle_table(self, url: str) -> str:

        prompt = """

Role DefinitionYou are a mathematical and data analysis expert with high precision in symbol recognition. 

Your task is to convert table images containing complex mathematical formulas and symbols into detailed, searchable plain text.

Task ObjectiveTranscribe all data and mathematical expressions from the table image into a single, cohesive paragraph. 

You must preserve the exact logical relationship between headers, values, and mathematical symbols.Core RequirementsPrecise Symbol Recognition: 

Accurately identify and transcribe all mathematical symbols, 

including Greek letters (e.g., $\alpha, \beta$), operators (e.g., $\pm, \times, \div$), comparators, square roots, and summation symbols.

Formula Standardization: For complex formulas or variables with subscripts/superscripts, use standard LaTeX notation (enclosed in $ symbols), 

such as $x_{i}^{2}$ or $\Delta t$, to ensure scientific accuracy.Row-Column Logic Mapping: 

For every cell, explicitly link it to its corresponding row and column headers. 

Use a descriptive pattern like "In the [Row Name], the [Column Name] is [Value/Formula].

"Merged Cell Handling: If a cell spans multiple rows or columns, repeat the header information for each entry to ensure no context is lost during RAG chunking.

Units and Scientific Notation: Retain all units (e.g., $\mu m, m/s^2$) and scientific notations (e.g., $6.02 \times 10^{23}$) found in headers or cells.

Empty Cells: Describe empty or "N/A" cells as "not specified" or "no data available" instead of omitting them.

Output Constraints (Strictly Enforced)Single Paragraph Only: No line breaks, no paragraph breaks, and no bullet points or list markers.

No Preamble or Suggestions: Start directly with the data description. 

Do not include introductory phrases like "The image shows..." and do not guess the background or provide analysis.

Punctuation & Cleanliness: Use only standard punctuation (periods, commas, colons). 

No Markdown tables, no bolding, and no code block wrappers.Image to Process:

        """

        descrip = self.model.generate(prompt + url)
        return descrip

    def _save_result(self, file_stem: str, content):
        output_file = self.output_path / f"{file_stem}_parsed.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(str(content))
        logger.info(f"✅ Saved parsed content to {output_file}")


if __name__ == "__main__":
    cfg = {}
    data_path = "./data/"
    output_path = "./test/"

    parser = MdParser(cfg, data_path, output_path)
    parser.parse_md_content()