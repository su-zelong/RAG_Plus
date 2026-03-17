```yaml
name: 文档解析器                    # 必需：技能名称
description: "将文档解析为markdown时调用"         # 必需：一句话描述，200字符以内
category: development               # 必需：技能分类
risk: safe                         # 必需：风险级别（safe/medium/high）
source: community                   # 必需：来源（community/official）
date_added: "2024-03-18"         # 必需：添加日期，YYYY-MM-DD格式
author: SuZelong              # 可选：作者
```

```markdown
# 文档解析器

## 概述
在RAG处理中，需要将其它类型的文档结构，例如pdf，doc，txt等文件转化为markdown格式，以便后续切片及其他操作

## 何时调用此技能
- 当用户指定需要转化的文件时使用
- 每隔6小时文件夹有新增文档时使用
- 确保待解析文档解析到了表格和图片信息

## 工作原理

### 步骤1：文档解析 (Shell 脚本规范)
- 脚本必须具备**幂等性**：如果输出目录已存在同名 Markdown，应询问或根据策略跳过。
- 参数化：支持 `$1` 作为输入路径，`$2` 作为输出目录。
- 环境隔离：脚本内部应包含对 `mineru` 命令是否可用的检查。
- 硬件检查：判断当前机器是否支持gpu，如果支持则使用`mineru -p <input_path> -o <output_path>` 否则 `mineru -p <input_path> -o <output_path> -b pipeline`

### 步骤2：存入到指定输出文件下

```