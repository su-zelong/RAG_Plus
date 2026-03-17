```yaml
name: 切片高手                    # 必需：技能名称
description: "专门用于markdown切片"         # 必需：一句话描述，200字符以内
category: development               # 必需：技能分类
risk: safe                         # 必需：风险级别（safe/medium/high）
source: community                   # 必需：来源（community/official）
date_added: "2026-03-18"         # 必需：添加日期，YYYY-MM-DD格式
author: SuZelong              # 可选：作者
```

```markdown
# Skill: Chunk 文档切片专家

## 概述
此技能用于在 Python 环境下将输入的markdown 切片，转化为能存入向量知识库的切片数据

## 工作原理

### 步骤1：读取指定文件夹下的文件
- 仅读取markdown 格式的文件
- 如果发现有其它类型的文件

### 步骤2：将markdown 文档切片
```