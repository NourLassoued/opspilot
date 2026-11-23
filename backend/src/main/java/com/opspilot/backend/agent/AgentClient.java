package com.opspilot.backend.agent;

import com.fasterxml.jackson.databind.JsonNode;
import com.opspilot.backend.agent.AgentDtos.InvestigateRequest;
import com.opspilot.backend.agent.AgentDtos.InvestigateResponse;
import com.opspilot.backend.agent.AgentDtos.RemediateRequest;
import com.opspilot.backend.agent.AgentDtos.RemediateResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.time.Duration;

/** Client HTTP vers l'agent IA (Python). */
@Component
public class AgentClient {

    private final RestClient restClient;
    private final String token;

    public AgentClient(@Value("${opspilot.agent.url}") String baseUrl,
                       @Value("${opspilot.agent.token:}") String token,
                       @Value("${opspilot.agent.timeout-seconds:240}") int timeoutSeconds) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(5));
        factory.setReadTimeout(Duration.ofSeconds(timeoutSeconds));
        this.restClient = RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
        this.token = token;
    }

    /** Lance une enquête : diagnostic seulement, l'agent n'exécute jamais rien ici. */
    public InvestigateResponse investigate(String namespace, String alert) {
        return restClient.post()
                .uri("/investigate")
                .contentType(MediaType.APPLICATION_JSON)
                .body(new InvestigateRequest(namespace, alert))
                .retrieve()
                .body(InvestigateResponse.class);
    }

    /** Exécute une réparation APRÈS validation humaine. Le jeton prouve à l'agent que l'appel vient du backend. */
    public RemediateResponse remediate(JsonNode remediation) {
        return restClient.post()
                .uri("/remediate")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .body(new RemediateRequest(remediation))
                .retrieve()
                .body(RemediateResponse.class);
    }
}
