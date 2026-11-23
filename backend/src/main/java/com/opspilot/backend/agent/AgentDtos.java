package com.opspilot.backend.agent;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;

/** Les messages échangés avec l'agent Python (API FastAPI). */
public final class AgentDtos {

    private AgentDtos() {
    }

    public record InvestigateRequest(String namespace, String alert) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record InvestigateResponse(
            String namespace,
            @JsonProperty("duration_seconds") double durationSeconds,
            @JsonProperty("tool_calls") int toolCalls,
            List<Step> steps,
            JsonNode diagnosis) {

        @JsonIgnoreProperties(ignoreUnknown = true)
        public record Step(String node, String tool, JsonNode args) {
        }
    }

    public record RemediateRequest(JsonNode remediation) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record RemediateResponse(boolean success, String message) {
    }
}
