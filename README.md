# project/SpringAi-project 说明

## model工程
由于原本模型依赖引入之后需要配置对应的API_KEY，否则会启动报错。
利用spring自动装配过滤器AutoConfigurationImportFilter排除原有自动装配类，防止不配置的情况下启动报错。
重写原有的自动装配类，使其在项目中配置了对应的API_KEY,则自动装配对应的模型。
对应配置项key：
* DashScope：spring.ai.dashscope.api-key
* OpenAi：spring.ai.openai.api-key
* DeepSeek：spring.ai.deepseek.api-key

根据上述实现之后，项目中可能会存在多个ChatClientBuilder实例，采用ChatClientBuilderBeanFactory实现自动注入时不做任何指定也能完成注入。
在注入ChatClientBuilder时，可使用@Qualifier注解指定注入实例（openAiChatClientBuilder、dashScopeChatClientBuilder、deepSeekChatClientBuilder）,在不指定的情况下会根据（1.DashScope；2.OpenAi；3.DeepSeek）顺序实现自动选择注入

目前引入依赖：
1. spring-ai-alibaba-starter-dashscope
2. spring-ai-starter-model-openai
3. spring-ai-starter-model-deepseek

## Memory工程

## Tool工程

## MCP工程

## rag工程
