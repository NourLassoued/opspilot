package com.opspilot.backend.incident;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.opspilot.backend.agent.AgentClient;
import com.opspilot.backend.agent.AgentDtos.RemediateResponse;
import com.opspilot.backend.alert.AlertmanagerPayload;
import com.opspilot.backend.events.IncidentEvents;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.task.TaskExecutor;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.Set;

@Service
public class IncidentService {

    /** Statuts « ouverts » : une nouvelle alerte sur le même namespace est rattachée à cet incident. */
    static final Set<IncidentStatus> OPEN = EnumSet.of(
            IncidentStatus.INVESTIGATING, IncidentStatus.AWAITING_APPROVAL, IncidentStatus.EXECUTING);

    /** Alertes techniques qui ne signalent pas une panne. */
    static final Set<String> IGNORED_ALERTS = Set.of("Watchdog", "InfoInhibitor");

    private final IncidentRepository incidents;
    private final AgentStepRepository steps;
    private final InvestigationRunner runner;
    private final AgentClient agent;
    private final IncidentEvents events;
    private final ObjectMapper objectMapper;
    private final TaskExecutor executor;
    private final boolean async;

    public IncidentService(IncidentRepository incidents, AgentStepRepository steps, InvestigationRunner runner,
                           AgentClient agent, IncidentEvents events, ObjectMapper objectMapper,
                           @Qualifier("applicationTaskExecutor") TaskExecutor executor,
                           @Value("${opspilot.investigation.async:true}") boolean async) {
        this.incidents = incidents;
        this.steps = steps;
        this.runner = runner;
        this.agent = agent;
        this.events = events;
        this.objectMapper = objectMapper;
        this.executor = executor;
        this.async = async;
    }

    /**
     * Reçoit les alertes d'Alertmanager. Les alertes d'un même namespace sont REGROUPÉES dans un seul
     * incident : une panne déclenche souvent 4 ou 5 alertes, mais il n'y a qu'une seule cause.
     */
    public List<Incident> handleAlertmanager(AlertmanagerPayload payload) {
        Map<String, List<AlertmanagerPayload.Alert>> byNamespace = new LinkedHashMap<>();
        if (payload.alerts() != null) {
            for (AlertmanagerPayload.Alert alert : payload.alerts()) {
                String name = alert.label("alertname");
                String namespace = alert.label("namespace");
                if (!"firing".equals(alert.status()) || name == null || namespace == null || IGNORED_ALERTS.contains(name)) {
                    continue;
                }
                byNamespace.computeIfAbsent(namespace, k -> new ArrayList<>()).add(alert);
            }
        }

        List<Incident> touched = new ArrayList<>();
        byNamespace.forEach((namespace, alerts) -> {
            Incident incident = incidents.findFirstByNamespaceAndStatusInOrderByCreatedAtDesc(namespace, OPEN).orElse(null);
            boolean isNew = incident == null;
            if (isNew) {
                AlertmanagerPayload.Alert first = alerts.get(0);
                incident = new Incident(namespace, first.label("alertname"), first.label("severity"), first.annotation("summary"));
            }
            for (AlertmanagerPayload.Alert alert : alerts) {
                incident.addAlert(alert.label("alertname"));
            }
            incident = incidents.save(incident);
            events.publish(incident);
            touched.add(incident);
            if (isNew) {
                launchInvestigation(incident.getId());
            }
        });
        return touched;
    }

    /** Déclenchement manuel (tests, démo) sans passer par Alertmanager. */
    public Incident createManual(String namespace, String alertName) {
        Incident incident = incidents.save(new Incident(namespace, alertName, "manual", "Enquête déclenchée à la main"));
        events.publish(incident);
        launchInvestigation(incident.getId());
        return incident;
    }

    public List<Incident> findAll() {
        return incidents.findAllByOrderByCreatedAtDesc();
    }

    public Incident get(Long id) {
        return incidents.findById(id).orElseThrow(() -> new NoSuchElementException("Incident " + id + " introuvable"));
    }

    public List<AgentStep> stepsOf(Long id) {
        return steps.findByIncidentIdOrderByStepOrderAsc(id);
    }

    /** Un humain approuve la réparation : le backend demande à l'agent de l'exécuter. */
    public Incident approve(Long id, String user) {
        Incident incident = requireAwaitingApproval(id);
        incident.setStatus(IncidentStatus.EXECUTING);
        incident.setDecidedBy(user);
        incident.setDecidedAt(Instant.now());
        events.publish(incidents.save(incident));
        try {
            RemediateResponse result = agent.remediate(objectMapper.readTree(incident.getRemediationJson()));
            incident.setStatus(result != null && result.success() ? IncidentStatus.RESOLVED : IncidentStatus.FAILED);
            incident.setActionResult(result == null ? "Réponse vide de l'agent" : result.message());
        } catch (Exception e) {
            incident.setStatus(IncidentStatus.FAILED);
            incident.setActionResult("Échec de l'appel à l'agent : " + e.getMessage());
        }
        Incident saved = incidents.save(incident);
        events.publish(saved);
        return saved;
    }

    /** Un humain refuse la réparation : rien n'est modifié dans le cluster. */
    public Incident reject(Long id, String user) {
        Incident incident = requireAwaitingApproval(id);
        incident.setStatus(IncidentStatus.REJECTED);
        incident.setDecidedBy(user);
        incident.setDecidedAt(Instant.now());
        incident.setActionResult("Réparation refusée par " + user + " : rien n'a été modifié.");
        Incident saved = incidents.save(incident);
        events.publish(saved);
        return saved;
    }

    private Incident requireAwaitingApproval(Long id) {
        Incident incident = get(id);
        if (incident.getStatus() != IncidentStatus.AWAITING_APPROVAL) {
            throw new IllegalStateException("L'incident " + id + " n'attend pas de validation (statut " + incident.getStatus() + ")");
        }
        return incident;
    }

    private void launchInvestigation(Long incidentId) {
        if (async) {
            executor.execute(() -> runner.run(incidentId));
        } else {
            runner.run(incidentId);
        }
    }
}
