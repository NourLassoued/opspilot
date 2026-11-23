package com.opspilot.backend.incident;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.Arrays;
import java.util.List;

@Entity
@Table(name = "incident")
public class Incident {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String namespace;

    /** Alertes regroupées dans cet incident, séparées par des virgules. */
    @Column(name = "alert_names", nullable = false, columnDefinition = "TEXT")
    private String alertNames;

    private String severity;

    @Column(columnDefinition = "TEXT")
    private String summary;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private IncidentStatus status;

    private String category;

    @Column(name = "root_cause", columnDefinition = "TEXT")
    private String rootCause;

    private Double confidence;

    @Column(name = "diagnosis_json", columnDefinition = "TEXT")
    private String diagnosisJson;

    @Column(name = "remediation_action")
    private String remediationAction;

    @Column(name = "remediation_json", columnDefinition = "TEXT")
    private String remediationJson;

    @Column(name = "tool_calls")
    private Integer toolCalls;

    @Column(name = "duration_seconds")
    private Double durationSeconds;

    @Column(name = "action_result", columnDefinition = "TEXT")
    private String actionResult;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "decided_by")
    private String decidedBy;

    @Column(name = "decided_at")
    private Instant decidedAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected Incident() {
        // pour JPA
    }

    public Incident(String namespace, String alertName, String severity, String summary) {
        this.namespace = namespace;
        this.alertNames = alertName;
        this.severity = severity;
        this.summary = summary;
        this.status = IncidentStatus.INVESTIGATING;
    }

    @PrePersist
    void onCreate() {
        createdAt = Instant.now();
        updatedAt = createdAt;
    }

    @PreUpdate
    void onUpdate() {
        updatedAt = Instant.now();
    }

    /** Ajoute une alerte à l'incident si elle n'y est pas déjà (regroupement du « bruit » d'alertes). */
    public void addAlert(String alertName) {
        if (!alertNameList().contains(alertName)) {
            alertNames = alertNames + "," + alertName;
        }
    }

    public List<String> alertNameList() {
        return Arrays.stream(alertNames.split(",")).map(String::trim).filter(s -> !s.isEmpty()).toList();
    }

    public Long getId() { return id; }
    public String getNamespace() { return namespace; }
    public String getAlertNames() { return alertNames; }
    public String getSeverity() { return severity; }
    public String getSummary() { return summary; }
    public IncidentStatus getStatus() { return status; }
    public void setStatus(IncidentStatus status) { this.status = status; }
    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }
    public String getRootCause() { return rootCause; }
    public void setRootCause(String rootCause) { this.rootCause = rootCause; }
    public Double getConfidence() { return confidence; }
    public void setConfidence(Double confidence) { this.confidence = confidence; }
    public String getDiagnosisJson() { return diagnosisJson; }
    public void setDiagnosisJson(String diagnosisJson) { this.diagnosisJson = diagnosisJson; }
    public String getRemediationAction() { return remediationAction; }
    public void setRemediationAction(String remediationAction) { this.remediationAction = remediationAction; }
    public String getRemediationJson() { return remediationJson; }
    public void setRemediationJson(String remediationJson) { this.remediationJson = remediationJson; }
    public Integer getToolCalls() { return toolCalls; }
    public void setToolCalls(Integer toolCalls) { this.toolCalls = toolCalls; }
    public Double getDurationSeconds() { return durationSeconds; }
    public void setDurationSeconds(Double durationSeconds) { this.durationSeconds = durationSeconds; }
    public String getActionResult() { return actionResult; }
    public void setActionResult(String actionResult) { this.actionResult = actionResult; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public String getDecidedBy() { return decidedBy; }
    public void setDecidedBy(String decidedBy) { this.decidedBy = decidedBy; }
    public Instant getDecidedAt() { return decidedAt; }
    public void setDecidedAt(Instant decidedAt) { this.decidedAt = decidedAt; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
