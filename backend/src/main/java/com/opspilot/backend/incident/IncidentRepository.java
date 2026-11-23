package com.opspilot.backend.incident;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface IncidentRepository extends JpaRepository<Incident, Long> {

    /** L'incident encore ouvert sur ce namespace, s'il existe (pour regrouper les alertes). */
    Optional<Incident> findFirstByNamespaceAndStatusInOrderByCreatedAtDesc(String namespace, Collection<IncidentStatus> statuses);

    List<Incident> findAllByOrderByCreatedAtDesc();
}
