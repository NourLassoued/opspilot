package com.opspilot.backend.incident;

import com.fasterxml.jackson.databind.JsonNode;
import com.opspilot.backend.agent.AgentClient;
import com.opspilot.backend.agent.AgentDtos.InvestigateResponse;
import com.opspilot.backend.events.IncidentEvents;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Set;

/** Fait enquêter l'agent sur un incident, puis enregistre les étapes et le diagnostic. */
@Component
public class InvestigationRunner {

    /** Réparations que l'agent sait exécuter (après validation humaine). */
    static final Set<String> AUTO_ACTIONS = Set.of("git_revert", "argocd_sync");

    private static final Logger log = LoggerFactory.getLogger(InvestigationRunner.class);

    private final IncidentRepository incidents;
    private final AgentStepRepository steps;
    private final AgentClient agent;
    private final IncidentEvents events;

    public InvestigationRunner(IncidentRepository incidents, AgentStepRepository steps,
                               AgentClient agent, IncidentEvents events) {
        this.incidents = incidents;
        this.steps = steps;
        this.agent = agent;
        this.events = events;
    }

    public void run(Long incidentId) {
        Incident incident = incidents.findById(incidentId).orElseThrow();
        try {
            InvestigateResponse response = agent.investigate(incident.getNamespace(), incident.getAlertNames());
            saveSteps(incident.getId(), response);
            incident.setToolCalls(response.toolCalls());
            incident.setDurationSeconds(response.durationSeconds());
            applyDiagnosis(incident, response.diagnosis());
        } catch (Exception e) {
            log.warn("Enquête impossible pour l'incident {} : {}", incidentId, e.getMessage());
            incident.setStatus(IncidentStatus.FAILED);
            incident.setErrorMessage("Agent injoignable ou en erreur : " + e.getMessage());
        }
        events.publish(incidents.save(incident));
    }

    private void saveSteps(Long incidentId, InvestigateResponse response) {
        if (response.steps() == null) {
            return;
        }
        int order = 1;
        for (InvestigateResponse.Step step : response.steps()) {
            String args = step.args() == null || step.args().isNull() ? null : step.args().toString();
            steps.save(new AgentStep(incidentId, order++, step.node(), step.tool(), args));
        }
    }

    private void applyDiagnosis(Incident incident, JsonNode diagnosis) {
        if (diagnosis == null || diagnosis.isNull()) {
            incident.setStatus(IncidentStatus.DIAGNOSED);
            incident.setCategory("none");
            incident.setRootCause("Aucun pod en difficulté trouvé par l'agent.");
            return;
        }
        incident.setDiagnosisJson(diagnosis.toString());
        incident.setCategory(diagnosis.path("category").asText(null));
        incident.setRootCause(diagnosis.path("root_cause").asText(null));
        JsonNode confidence = diagnosis.path("confidence");
        incident.setConfidence(confidence.isNumber() ? confidence.asDouble() : null);

        JsonNode remediation = diagnosis.path("remediation");
        String action = remediation.path("action").asText("none");
        incident.setRemediationAction(action);
        if (remediation.isObject()) {
            incident.setRemediationJson(remediation.toString());
        }
        incident.setStatus(AUTO_ACTIONS.contains(action) ? IncidentStatus.AWAITING_APPROVAL : IncidentStatus.DIAGNOSED);
    }
}
