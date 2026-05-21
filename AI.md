## Agent

>  产品维度

* 通用型

  > 任务发散、边界模糊的全能型智能体系统
  >
  > 开发者主要停留在“调用”层面，少有在企业内部从零构建

* 垂直型

  > 深耕细分场景的领域专家，聚焦单一业务流

> 技术架构维度

* Workflow（工作流编排）：确定性的状态机

  > 底层机制：核心为DAG（有向无环图）。开发者预定义严格的执行路径。
  >
  > 优势：具备绝对的可控性。彻底杜绝大模型因“幻觉”偏离既定流程的风险
  >
  > 适用场景：金融打款、订单审批等零容错的企业核心生产链路。在这些场景中，Workflow是目前的唯一解。
  >
  > 更适合垂直领域的Agent开发

* Agentic（智能体自驱）：黑盒决策系统

  > 底层机制：以ReAct等框架为核心。不预设固定步骤，仅提供总目标与Tools。大模型自主规划、调用、评估与重试。
  >
  > 优势：极度灵活。可解非标问题。
  >
  > 劣势：中间过程呈“黑盒”状态，极易陷入死循环或Token消耗失控。
  >
  > 适用场景：研发辅助、探索性分析。极少有架构师敢将纯Agentic逻辑直接接入核心生产数据库。
  >
  > 更适合通用型Agent开发  

### 开发方式

* 基于LLMops的可视化开发（平台级）

  > 工具：Coze、Dify、FastGPT
  >
  > 特性与场景：声明式编排，拖拉拽/适合敏捷验证MVP与非核心业务上线。Dify的私有化部署是解决中小企业数据隐私的主流方案

* 基于框架的硬核代码开发（工程级）

  > 工具：Spring AI Alibaba(Java)、LangChain(Python)
  >
  > 特性与场景：编程式调用。由后端工程师直接编写状态机，定义Function Calling接口，在代码层对接公司内网系统。

## Agent 设计模式

### Zero-Shot模式

接近C端大多数人初次体验ChatGPT时的交互模式。此模式下用户输入不增加任何Prompt template处理，直接传入大模型，并直接输出返回结果给用户

### Few-Shot模式

拥有Prompt Template逻辑，开发者可以调用大模型context-learning上下文学习能力

### ReAct模式 

>  https://arxiv.org/pdf/2210.03629
>
>  https://react-lm.github.io/

#### 原理

#### 实现

Plan and Solve

## Spring AI 

硬编码实现，灵活性低，可维护性低，需要手动管理状态，适用场景局限。若是单纯与大模型对话，已经完全足够了

## Spring AI Alibaba Agent framework

流水线方式实现，灵活性友好，可维护性友好，易用性友好，无需手动管理状态，涉及动态编排时显现不足，适用场景在不需动态Agent编排时完全足够。

Spring AI Alibaba 更推荐使用Agent Framework，基于工作流（Workflow）处理业务。它即包含Spring AI，也包含了Alibaba Graph。

## Spring AI Alibaba Graph

需要使用到动态编排，需要绝对的灵活性时

### 状态（State）

在node与edge之间传递数据，是整个Agent上下文传递数据的载体，具体实现上是一个Map<String, Object>

### 节点（Node）

Node是执行具体逻辑的单元，接受当前State作为输入，执行某些操作（如调用LLM或者自定义逻辑），并返回传递到下一个Node的State数据

### 边（Edge）

定义一个Node到下一个Node的链接，可以是固定链接（普通边），也可以是根据状态条件动态决定下一步执行路径（条件边）

## Skill

> Anthropic(Claude大模型)推出

由一个markdown文件记录需要的所有数据信息。

也可以执行一段python脚本，以cmd命令的方式执行。需要提供PythonTool工具。

内容包含两个部分：

* 元数据【名称、描述】

* 指令【编排提示词】

由大模型call_kills调用具体的Skill文件，按需加载，依旧是Function_Call调用读取文件，需要大模型支持Function call。

Skill也叫做sub-agent

Spring AI Alibaba 内置实现了Skill调用，SkillAgentHook.class

> Skill文件默认目录
>
> * 用户路径/saa/skills
> * 应用根目录/skills

需要提供 SkillsAgentHook、ShellToolAgentHook、PythonTool（如果需要执行python代码需要提供）

可以在skill.sh网站搜索已有skill

## Tools(Function call)

解决如何调用业务系统的方法

## MCP协议（调用外部tool）

规定了如何调用第三方tool方法，返回什么样的数据。

提供两种方式。stdio和http（sse/streamble）

MCP协议层约定了响应数据的统一格式。

MCP传输层约定了响应数据的传输机制。

> Stdio同一台机器上进程间交互
>
> Http协议（sse协议 单向实时通信，由服务端以流的方式多次向客户端发送数据）

## A2A协议

## ReactAgent

> 能够自主规划，自主决策，能执行工具，有记忆能力，感知周边环境的智能体

ReactAgent.builider().build();创建，在ai和webflux框架中存在大量的建造者模式。

### name

智能体名称

### model

指定使用的大模型

### tool

可以使用的工具

### 远程Agent获取流程

1. 服务提供者将智能体卡牌存储到注册中心
2. 服务消费者通过AgentCardProvider的getAgentCard方法基于远程智能体的name获取对应的智能体卡片
3. 注册中心根据获取到的卡片，告诉远程Agent执行消费者的任务

## LLM参数调优

* Temperature

  > 温度。调整候选Token集合的概率分布
  >
  > 低值（0.2）适用于标准化回答。如退货政策查询
  >
  > 高值（0.8）适用于创意场景。如促销文案生成

* Top_p

  > 控制候选Token的采样范围

* Top_k

  > 在通义千问系列模型中，参数topk也有类似topp的能力。
  >
  > 它是一种通过采样机制，从概率排名前k的Token中选择一个进行输出
  >
  > topk越大，生成内容越多样，topk越小，内容越固定
  >
  > topk设置为1时，仅选择概率最高的Token进行输出，内容更加稳定，但也缺乏变化和创意。

## Higress AI网关

## Rag知识库，相似性检索

> 向量、向量模型、向量数据库

> 余弦相似度：通过从0点坐标到任意两个空间之间的夹角来判断相似度，夹角度数越小越相似

## 分片

> 企业级RAG最佳分片策略？
>
> 建议提供多种分片策略拱用户自行选择，并提供自由填写参数和分片预览

### 固定长度

无视语义，按既定字符数或token数执行硬性物理切分

### 结构感知切分

将文档结构标记（如Headers、HTML标签）作为硬性语义边界进行切分

### 语义切分

实时计算文本向量，基于embedding相似度的剧烈变化点进切分

* 按照特定标点符号
* 按照自然语言处理工具或框架。如：Apatch NLP
* 按照文本向量计算余弦相似度

### 递归字符切分

分治法。遵循优雅的降级策略：先按段落切分，失败则按句子分，再失败则按词切分。

### LLM-based Chunking（基于大模型的智能切分）

代理化。让LLM深度阅读并理解上下文逻辑后，自主决定切分边界。

## RAG知识库问题

1. 跨片段topk上限

   * 适当调大
   * 分而治之。分批处理，无限扩展

2. 聚合问题。text-to-sql(查询关系型数据库)

   > 多路召回

   * super-sql。RAG，首次启动时读取指定的数据库所有的表结构，将每一张表的信息（表名、字段名、字段类型...）存储到向量数据库中。
   * 大模型处理用户输入，检查是否是一个聚合问题，RAG检索相关的表信息，将检索到的表信息告诉LLM，LLM利用表信息生成SQL语句并验证SQL语句的有效性，最终执行SQL语句，从数据库中获取数据

3. 噪音问题

   * 知识库隔离（进行分类）
   * 元数据过滤（filterExpression）

4. 知识库文档更新

   * 文件传错。删除对应的文档（向量、物理文件、数据库信息）
   * 文件过期。不需要删除，预留检索往期文档，上传新文档，注意区分新旧文档

5. 幻觉问题

## LangChain

 

### Anaconda3

```cmd

conda create -n evn_name python=3.10 
conda activate env_name

conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --set show_channel_urls yes 
```





































