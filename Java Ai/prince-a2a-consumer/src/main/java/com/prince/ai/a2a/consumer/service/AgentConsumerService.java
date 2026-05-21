package com.prince.ai.a2a.consumer.service;

import com.alibaba.cloud.ai.graph.OverAllState;
import com.alibaba.cloud.ai.graph.agent.a2a.A2aRemoteAgent;
import com.alibaba.cloud.ai.graph.agent.a2a.AgentCardProvider;
import com.alibaba.cloud.ai.graph.exception.GraphRunnerException;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;

import java.util.Optional;

/**
 *
 * Description :  <br\>
 *
 * @author Mu.Prince <br\>
 * @since 2026/5/14 23:47
 */
@Service
@RequiredArgsConstructor
public class AgentConsumerService {

    @Qualifier("nacosAgentCardProvider")
    private final AgentCardProvider agentCardProvider;

    public void getAgentProvider() throws GraphRunnerException {

        A2aRemoteAgent remoteAgent = A2aRemoteAgent.builder()
                .name("AgentProvider")
                .description("获取天气数据")
                .instruction("instruction")
                .shareState(true)
                // 智能体卡片（远程agent的元数据）
                .agentCardProvider(agentCardProvider)
                .build();
        // OverAllState工作流状态对象
        // 工作流的每个节点的执行结果，都会更新到OverAllState工作流状态对象里，在工作流的所有节点之间进行流动，这样就能把上一个节点的执行结果传递给下一个节点
        // OverAllState是Key-Value键值对
        Optional<OverAllState> result = remoteAgent.invoke("提示词");
        if (result.isPresent()) {
            result.flatMap(state -> state.value("key")).map(v -> (String) v);
        }
    }
}
