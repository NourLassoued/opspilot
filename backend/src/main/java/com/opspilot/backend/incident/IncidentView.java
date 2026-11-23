package com.opspilot.backend.incident;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.Instant;
import java.util.List;

/** Ce que l'API renvoie pour un incident (la liste n'inclut ni le diagnostic complet ni les étapes). */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record IncidentView(
        Long id,
        String namespace,
        List<String> alerts,
        String severity,
        String summary,
        IncidentStatus status,
        String category,
        String rootCause,
        Double confidence,
        String remediationAction,
        JsonNode remediation,
        Integer toolCalls,
        Double durationSeconds,
        String actionResult,
        String errorMessage,
        String decidedBy,
        Instant decidedAt,
        Instant createdAt,
        Instant updatedAt,
        JsonNode diagnosis,
        List<StepView> steps) {

    public record StepView(int order, String node, String tool, JsonNode args, Instant at) {
    }

    public static IncidentView summary(Incident i, ObjectMapper mapper) {
        return of(i, mapper, false, null);
    }

    public static IncidentView detail(Incident i, List<AgentStep> steps, ObjectMapper mapper) {
        return of(i, mapper, true, steps.stream()
                .map(s -> new StepView(s.getStepOrder(), s.getNode(), s.getTool(), parse(s.getArgsJson(), mapper), s.getCreatedAt()))
                .toList());
    }

    private static IncidentView of(Incident i, ObjectMapper mapper, boolean withDiagnosis, List<StepView> steps) {
        return new IncidentView(i.getId(), i.getNamespace(), i.alertNameList(), i.getSeverity(), i.getSummary(),
                i.getStatus(), i.getCategory(), i.getRootCause(), i.getConfidence(), i.getRemediationAction(),
                parse(i.getRemediationJson(), mapper), i.getToolCalls(), i.getDurationSeconds(), i.getActionResult(),
                i.getErrorMessage(), i.getDecidedBy(), i.getDecidedAt(), i.getCreatedAt(), i.getUpdatedAt(),
                withDiagnosis ? parse(i.getDiagnosisJson(), mapper) : null, steps);
    }

    private static JsonNode parse(String json, ObjectMapper mapper) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return mapper.readTree(json);
        } catch (Exception e) {
            return null;
        }
    }
}
