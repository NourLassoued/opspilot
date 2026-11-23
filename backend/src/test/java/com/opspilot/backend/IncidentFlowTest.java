package com.opspilot.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.opspilot.backend.agent.AgentClient;
import com.opspilot.backend.agent.AgentDtos.InvestigateResponse;
import com.opspilot.backend.agent.AgentDtos.RemediateResponse;
import com.opspilot.backend.incident.IncidentRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Parcours complet : alerte → enquête (agent simulé) → validation humaine → réparation. */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class IncidentFlowTest {

    private static final String ALERTS = """
            {"status": "firing", "alerts": [
              {"status": "firing", "labels": {"alertname": "PodImagePullFailed", "namespace": "jobradar",
                                              "pod": "jobradar-backend-abc", "severity": "critical"},
               "annotations": {"summary": "Impossible de télécharger l'image"}},
              {"status": "firing", "labels": {"alertname": "PodNotReady", "namespace": "jobradar"}},
              {"status": "firing", "labels": {"alertname": "Watchdog"}}
            ]}""";

    private static final String AGENT_RESPONSE = """
            {"namespace": "jobradar", "duration_seconds": 8.1, "tool_calls": 2,
             "steps": [{"node": "investigate", "tool": "list_pods", "args": {"namespace": "jobradar"}},
                       {"node": "investigate", "tool": "get_git_commit_diff", "args": {"sha": "7117d0b"}},
                       {"node": "diagnose"}],
             "diagnosis": {"category": "image", "root_cause": "L'image 9.9.9 n'existe pas.", "confidence": 0.96,
                           "evidence": ["ImagePullBackOff"], "affected_resources": ["deployment/jobradar-backend"],
                           "suggested_fix": "Annuler le commit.", "fix_commands": [],
                           "remediation": {"action": "git_revert", "commit_sha": "7117d0b",
                                           "file_path": "base/backend.yaml", "explanation": "Commit fautif."}}}""";

    @Autowired
    MockMvc mvc;

    @Autowired
    ObjectMapper objectMapper;

    @Autowired
    IncidentRepository incidents;

    @MockitoBean
    AgentClient agent;

    @BeforeEach
    void setUp() throws Exception {
        incidents.deleteAll();
        when(agent.investigate(anyString(), anyString()))
                .thenReturn(objectMapper.readValue(AGENT_RESPONSE, InvestigateResponse.class));
        when(agent.remediate(any(JsonNode.class))).thenReturn(new RemediateResponse(true, "Commit 7117d0b annulé"));
    }

    private Long sendAlerts() throws Exception {
        String body = mvc.perform(post("/api/alerts/alertmanager")
                        .header("Authorization", "Bearer test-am-token")
                        .contentType(MediaType.APPLICATION_JSON).content(ALERTS))
                .andExpect(status().isAccepted())
                .andReturn().getResponse().getContentAsString();
        return objectMapper.readTree(body).path("incidents").get(0).asLong();
    }

    @Test
    void webhookRefusesWrongToken() throws Exception {
        mvc.perform(post("/api/alerts/alertmanager").header("Authorization", "Bearer faux")
                        .contentType(MediaType.APPLICATION_JSON).content(ALERTS))
                .andExpect(status().isUnauthorized());
        verify(agent, never()).investigate(anyString(), anyString());
    }

    @Test
    void alertsAreGroupedIntoOneIncidentAndInvestigated() throws Exception {
        Long id = sendAlerts();

        mvc.perform(get("/api/incidents/{id}", id).with(httpBasic("viewer", "viewer-pass")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("AWAITING_APPROVAL"))
                .andExpect(jsonPath("$.alerts.length()").value(2))          // Watchdog ignorée, 2 alertes regroupées
                .andExpect(jsonPath("$.rootCause").value("L'image 9.9.9 n'existe pas."))
                .andExpect(jsonPath("$.remediation.commit_sha").value("7117d0b"))
                .andExpect(jsonPath("$.steps.length()").value(3))
                .andExpect(jsonPath("$.steps[1].tool").value("get_git_commit_diff"));

        // Une nouvelle alerte sur le même namespace ne crée PAS un 2e incident
        Long sameId = sendAlerts();
        assertThat(sameId).isEqualTo(id);
        verify(agent, times(1)).investigate(eq("jobradar"), anyString());
    }

    @Test
    void viewerCannotApprove() throws Exception {
        Long id = sendAlerts();
        mvc.perform(post("/api/incidents/{id}/approve", id).with(httpBasic("viewer", "viewer-pass")))
                .andExpect(status().isForbidden());
        verify(agent, never()).remediate(any());
    }

    @Test
    void adminApprovesAndRepairIsExecuted() throws Exception {
        Long id = sendAlerts();
        mvc.perform(post("/api/incidents/{id}/approve", id).with(httpBasic("admin", "admin-pass")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("RESOLVED"))
                .andExpect(jsonPath("$.decidedBy").value("admin"))
                .andExpect(jsonPath("$.actionResult").value("Commit 7117d0b annulé"));
        verify(agent, times(1)).remediate(any());

        // On ne peut pas approuver deux fois
        mvc.perform(post("/api/incidents/{id}/approve", id).with(httpBasic("admin", "admin-pass")))
                .andExpect(status().isConflict());
    }

    @Test
    void adminRejectsAndNothingIsExecuted() throws Exception {
        Long id = sendAlerts();
        mvc.perform(post("/api/incidents/{id}/reject", id).with(httpBasic("admin", "admin-pass")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("REJECTED"));
        verify(agent, never()).remediate(any());
    }

    @Test
    void agentFailureMarksIncidentFailed() throws Exception {
        when(agent.investigate(anyString(), anyString())).thenThrow(new RuntimeException("Connection refused"));
        Long id = sendAlerts();
        mvc.perform(get("/api/incidents/{id}", id).with(httpBasic("viewer", "viewer-pass")))
                .andExpect(jsonPath("$.status").value("FAILED"))
                .andExpect(jsonPath("$.errorMessage").value("Agent injoignable ou en erreur : Connection refused"));
    }

    @Test
    void anonymousCannotReadIncidents() throws Exception {
        mvc.perform(get("/api/incidents")).andExpect(status().isUnauthorized());
    }
}
