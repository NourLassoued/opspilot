package com.opspilot.backend.incident;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.Instant;

/** Une étape de l'enquête de l'agent : un outil appelé (ou la rédaction du diagnostic). */
@Entity
@Table(name = "agent_step")
public class AgentStep {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "incident_id", nullable = false)
    private Long incidentId;

    @Column(name = "step_order", nullable = false)
    private Integer stepOrder;

    @Column(nullable = false)
    private String node;

    private String tool;

    @Column(name = "args_json", columnDefinition = "TEXT")
    private String argsJson;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    protected AgentStep() {
        // pour JPA
    }

    public AgentStep(Long incidentId, int stepOrder, String node, String tool, String argsJson) {
        this.incidentId = incidentId;
        this.stepOrder = stepOrder;
        this.node = node;
        this.tool = tool;
        this.argsJson = argsJson;
    }

    @PrePersist
    void onCreate() {
        createdAt = Instant.now();
    }

    public Long getId() { return id; }
    public Long getIncidentId() { return incidentId; }
    public Integer getStepOrder() { return stepOrder; }
    public String getNode() { return node; }
    public String getTool() { return tool; }
    public String getArgsJson() { return argsJson; }
    public Instant getCreatedAt() { return createdAt; }
}
