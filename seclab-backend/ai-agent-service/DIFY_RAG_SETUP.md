# Dify 知识库 RAG 配置说明

本文档用于指导 Dify 平台侧配置 Knowledge Retrieval，让 SecLab 的 AI 生成训练题可以使用课程知识库和规范题目库。

当前后端已经保留本地规范题目 fallback。Dify 平台侧只负责知识检索和 LLM 生成；SecLab 后端仍负责传入变量、解析输出、来源校验、安全校验、防照抄、入库，以及记录 `training_context_json`。

不要在本文档或 Dify 知识库文档中写入 Dify key、`.env` 内容、真实攻击目标、凭证材料或完整现实攻击链。

## 1. 运行模式

后端支持以下环境变量：

- `DIFY_RAG_MODE=local|hybrid|dify`
- `ENABLE_DIFY_KNOWLEDGE_RAG=true|false`
- `STRICT_SOURCE_EXAMPLE_VALIDATION=true|false`

默认行为：

- 如果没有配置任何 RAG 变量，后端默认使用 `local`。
- 如果设置了 `ENABLE_DIFY_KNOWLEDGE_RAG=true`，但没有设置 `DIFY_RAG_MODE`，后端使用 `dify`。
- `STRICT_SOURCE_EXAMPLE_VALIDATION` 默认是 `false`。

三种模式含义：

- `local`：使用本地 `standard_questions.json` 检索规范题目，并把 `exampleQuestionsJson` 传给 Dify。
- `hybrid`：同时使用本地 `exampleQuestionsJson` 和 Dify 知识库检索变量，适合过渡期。
- `dify`：不依赖本地规范题目检索，把检索变量传给 Dify Workflow，由 Dify 内部 Knowledge Retrieval 节点检索课程知识库和规范题目库。

## 2. 需要创建的 Dify 知识库

需要在 Dify 平台创建两个知识库。

### 2.1 SecLab Course Knowledge

中文建议名：`SecLab 课程知识库`

用途：

- 存放课程说明。
- 存放模块说明。
- 存放实验目标。
- 存放漏洞原理。
- 存放防御方法。
- 存放常见错误。
- 存放排查和诊断思路。

推荐 metadata：

```json
{
  "sourceType": "COURSE_KNOWLEDGE",
  "courseId": 1,
  "moduleId": 1,
  "difficulty": 3,
  "knowledgeTags": ["SQL注入", "Web安全"],
  "dimensionTags": ["knowledge_mastery", "troubleshooting"],
  "sourceDocument": "SQL注入基础实验模块"
}
```

字段说明：

- `sourceType`：来源类型，课程知识统一使用 `COURSE_KNOWLEDGE`。
- `courseId`：课程 ID。
- `moduleId`：模块 ID。
- `difficulty`：建议难度，范围建议 1-5。
- `knowledgeTags`：知识标签，例如 `SQL注入`、`Web安全`。
- `dimensionTags`：适用的画像维度，例如 `knowledge_mastery`。
- `sourceDocument`：来源说明，方便答辩时说明内容来自哪里。

### 2.2 SecLab Standard Questions

中文建议名：`SecLab 规范题目库`

用途：

- 存放规范题目范例。
- 存放标准答案。
- 存放解析。
- 存放评分规则。
- 存放题型结构。
- 存放难度标注。

推荐 metadata：

```json
{
  "sourceType": "STANDARD_QUESTION",
  "exampleQuestionId": "frontend-sqli-mcq-union-001",
  "questionType": "MCQ",
  "difficulty": 3,
  "knowledgeTags": ["SQL注入", "UNION", "Web安全"],
  "dimensionTags": ["knowledge_mastery"],
  "moduleId": 1,
  "courseId": null,
  "reviewed": false,
  "qualityLevel": "MEDIUM",
  "sourceDocument": "前端本地实验题目数据"
}
```

字段说明：

- `sourceType`：规范题目统一使用 `STANDARD_QUESTION`。
- `exampleQuestionId`：规范题目稳定 ID，后端会用它校验 `sourceExampleQuestionIds`。
- `questionType`：题型，例如 `SHORT_ANSWER`、`MCQ`、`CASE`。
- `difficulty`：题目难度，范围建议 1-5。
- `knowledgeTags`：题目关联知识标签。
- `dimensionTags`：适用画像维度。
- `moduleId`：关联模块 ID。
- `courseId`：关联课程 ID，没有可以为空。
- `reviewed`：是否教师审核。未审核题必须写 `false`。
- `qualityLevel`：质量等级，例如 `HIGH`、`MEDIUM`、`LOW`。
- `sourceDocument`：来源说明。

注意：`reviewed=false` 的题目不能描述成教师审核题。

## 3. 导入文档格式示例

### 3.1 课程知识库文档示例

```markdown
---
sourceType: COURSE_KNOWLEDGE
courseId: 1
moduleId: 1
difficulty: 3
knowledgeTags: SQL注入,Web安全
dimensionTags: knowledge_mastery,troubleshooting
sourceDocument: SQL注入基础实验模块
---

标题：SQL注入基础实验

内容：
说明 SQL 注入在受控教学实验中的基本原理、输入边界、风险识别方式和防御思路。

实验目标：
- 理解 SQL 语句结构与用户输入之间的关系。
- 能识别不安全字符串拼接带来的风险。
- 能说明参数化查询、输入校验和最小权限等防御方法。

常见错误：
- 只记忆现象，不解释输入如何影响查询结构。
- 把教学分析写成对真实站点的操作步骤。

防御方法：
- 使用参数化查询。
- 对输入做类型、长度和格式校验。
- 避免向用户暴露详细数据库错误。
```

### 3.2 规范题目库文档示例

```markdown
---
sourceType: STANDARD_QUESTION
exampleQuestionId: frontend-sqli-mcq-union-001
questionType: MCQ
difficulty: 3
knowledgeTags: SQL注入,UNION,Web安全
dimensionTags: knowledge_mastery
moduleId: 1
courseId:
reviewed: false
qualityLevel: MEDIUM
sourceDocument: 前端本地实验题目数据
---

题目：
在受控教学实验中，判断 UNION 查询相关问题时，哪一项最能体现安全分析思路？

标准答案：
优先分析字段数量、字段类型和回显位置是否与原查询结构匹配，并说明这是教学环境中的识别与防御分析。

解析：
该题用于考查学生是否理解 UNION 查询结构约束，而不是输出真实攻击目标或完整利用链。

评分规则：
- 说明字段数量或类型匹配的关键性：40 分
- 说明受控教学环境和防御分析边界：30 分
- 表达清晰且不包含真实攻击目标：30 分
```

导入要求：

- 不要写真实攻击目标。
- 不要写真实密钥。
- 不要写完整攻击链。
- `reviewed=false` 的题目不要写成教师审核题。

## 4. Dify Workflow 节点配置

目标 Workflow 结构：

```text
Start
  -> Knowledge Retrieval：SecLab Course Knowledge
  -> Knowledge Retrieval：SecLab Standard Questions
  -> LLM：生成训练题 JSON
  -> End
```

### 4.1 Start 节点输入变量

Start 节点至少需要接收这些变量：

- `dimension`
- `difficulty`
- `questionType`
- `question_type`
- `knowledgeTags`
- `knowledge_tags`
- `moduleId`
- `courseId`
- `recommendationReason`
- `ragMode`
- `retrievalQuery`
- `retrievalMetadata`
- `prompt`
- `knowledgeUnitsJson`
- `exampleQuestionsJson`，仅 `local` 或 `hybrid` 模式需要

### 4.2 课程知识库检索节点

节点类型：Knowledge Retrieval

配置建议：

- Query 使用：`retrievalQuery`
- Knowledge 选择：`SecLab Course Knowledge`
- TopK：建议 3
- Score Threshold：建议 0.45-0.55
- 如果 Dify 当前环境支持 rerank，可以开启 rerank。

建议 metadata 过滤：

- `moduleId`
- `courseId`
- `difficulty`
- `knowledgeTags`
- `dimensionTags`

### 4.3 规范题目库检索节点

节点类型：Knowledge Retrieval

配置建议：

- Query 使用：`retrievalQuery`
- Knowledge 选择：`SecLab Standard Questions`
- TopK：建议 3
- Score Threshold：建议 0.45-0.55
- 如果 Dify 当前环境支持 rerank，可以开启 rerank。

建议 metadata 过滤：

- `questionType`
- `difficulty`
- `moduleId`
- `knowledgeTags`
- `dimensionTags`
- `reviewed`
- `qualityLevel`

### 4.4 LLM 节点要求

LLM 节点必须做到：

- 引用课程知识库检索结果。
- 引用规范题目库检索结果。
- 只输出 JSON。
- 不输出 markdown。
- 不复制范例题题干。
- 不复制范例题答案。
- 不复制范例题解析。
- 输出 `sourceKnowledgeUnitIds`。
- 输出 `sourceExampleQuestionIds`。
- 输出教学分析字段：
  - `teachingObjective`
  - `expectedSkill`
  - `difficultyReason`
  - `commonMistakes`
  - `gradingRubric`
  - `qualityScore`
  - `qualitySummary`
  - `qualityFlags`

## 5. Dify LLM 节点 Prompt 模板

下面模板可以直接粘贴到 Dify LLM 节点中。实际使用时，需要把检索节点结果占位符替换成你在 Dify Workflow 里对应节点的变量。

```text
你是 SecLab 网络安全教学训练题生成器。

你的任务是在授权实验、靶场、教学和防御语境下，基于输入变量、课程知识库检索结果和规范题目库检索结果，生成 1 道新的个性化训练题。

安全边界：
- 严禁生成真实攻击目标、真实公网 URL、真实公网 IP 或真实域名。
- 严禁生成真实漏洞利用链、免杀、后门、持久化、凭证窃取、数据窃取、反弹 shell、绕过检测等内容。
- SQL 注入、XSS、文件上传、命令执行等术语只能用于受控教学、防御解释、识别思路或修复建议。
- 不要输出 markdown。
- 不要输出解释性前后缀。
- 只输出严格 JSON。

输入变量：
- dimension: {{dimension}}
- difficulty: {{difficulty}}
- questionType: {{questionType}}
- knowledgeTags: {{knowledgeTags}}
- moduleId: {{moduleId}}
- courseId: {{courseId}}
- recommendationReason: {{recommendationReason}}
- ragMode: {{ragMode}}
- retrievalQuery: {{retrievalQuery}}
- retrievalMetadata: {{retrievalMetadata}}
- localKnowledgeUnitsJson: {{knowledgeUnitsJson}}
- localExampleQuestionsJson: {{exampleQuestionsJson}}

课程知识库检索结果：
{{SecLab Course Knowledge retrieval result}}

规范题目库检索结果：
{{SecLab Standard Questions retrieval result}}

使用规则：
- 课程知识库用于确定考查内容、知识边界、实验目标和防御方法。
- 规范题目库只用于参考题型结构、难度、答案组织和评分规则。
- 不得复制范例题题干。
- 不得复制范例题标准答案。
- 不得复制范例题解析。
- 必须生成新题。
- sourceKnowledgeUnitIds 必须来自本次可见的课程知识来源或本地 knowledgeUnitsJson。
- sourceExampleQuestionIds 必须来自本次规范题目库检索结果 metadata.exampleQuestionId 或本地 exampleQuestionsJson。

输出 JSON 字段：
{
  "title": "...",
  "stem": "...",
  "questionType": "SHORT_ANSWER|MCQ|CASE",
  "difficulty": 3,
  "dimension": "...",
  "knowledgeTags": ["..."],
  "standardAnswer": "...",
  "explanation": "...",
  "sourceKnowledgeUnitIds": ["..."],
  "sourceExampleQuestionIds": ["..."],
  "validationHints": {
    "keywords": ["..."],
    "minLength": 10
  },
  "teachingObjective": "...",
  "expectedSkill": "...",
  "difficultyReason": "...",
  "commonMistakes": ["..."],
  "gradingRubric": [
    {"point": "...", "score": 40},
    {"point": "...", "score": 60}
  ],
  "qualityScore": 86,
  "qualitySummary": "...",
  "qualityFlags": []
}
```

## 6. 后端校验逻辑

Dify 返回结果后，SecLab 后端会做这些校验：

- 校验返回内容是否是合法 JSON。
- 校验安全边界。
- 校验 `sourceKnowledgeUnitIds` 是否来自后端本地检索到的知识单元。
- 尽量校验 `sourceExampleQuestionIds` 是否来自本地规范题目库。
- 如果本地 `standard_questions.json` 没有对应 ID，但 Dify metadata 里能看到这些 ID，并且没有开启严格校验，则允许通过。
- 如果完全无法验证 `sourceExampleQuestionIds`，会加入质量提示 warning。
- 如果能拿到本地范例题或 Dify 检索片段，会做防照抄相似度检查。
- 把 RAG 上下文写入 `training_context_json`。

## 7. 真实验收清单

注意：只有 Dify Workflow 里真的配置了两个 Knowledge Retrieval 节点，并且下面清单跑通后，才能说 Dify 平台 RAG 已通过。

1. 启动 `ai-agent-service`。
2. 设置运行变量：
   - `DIFY_RAG_MODE=dify`
   - `ENABLE_DIFY_KNOWLEDGE_RAG=true`
   - `STRICT_SOURCE_EXAMPLE_VALIDATION=false`
   - `ENABLE_FAKE_LLM_FOR_TEST=false`
3. 使用真实学生账号登录。
4. 打开 `User/Profile`。
5. 点击推荐卡片里的“生成训练题”。
6. 确认前端请求：`POST /api/training/generate-question`。
7. 确认 Dify 返回真实生成的 JSON。
8. 确认响应 metadata 中有 `generator=dify_chat`，或对应的 workflow generator。
9. 查询 `generated_question`，确认：
   - `generated_question_id` 存在。
   - `source_model` 是 Dify 生成来源。
   - `raw_ai_json` 包含教学分析字段。
   - `raw_ai_json.sourceExampleQuestionIds` 非空，或者 `qualityFlags` 中包含来源校验 warning。
   - `training_context_json.ragMode=dify`。
   - `training_context_json.retrievalQuery` 存在。
   - 如果 Dify metadata 提供了 ID，`training_context_json.difySourceExampleQuestionIds` 应存在。
10. 确认 `User/Profile` 页面展示：
    - 标题和题干
    - 难度
    - 知识标签
    - 教学分析
    - 答案与解析
11. 确认没有使用前端 mock 数据。

## 8. 本地 fallback

必须保留本地规范题目 fallback：

- `standard_question_repository.py`
- `standard_questions.json`
- `GET /api/standard-questions`

如果 Dify Workflow 还没有配置 Knowledge Retrieval 节点，先使用：

- `DIFY_RAG_MODE=local`

或者：

- `DIFY_RAG_MODE=hybrid`

等 Dify 平台侧配置完成后，再切换到：

- `DIFY_RAG_MODE=dify`
