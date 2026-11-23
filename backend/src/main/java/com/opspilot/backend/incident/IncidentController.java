package com.opspilot.backend.incident;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.opspilot.backend.events.IncidentEvents;
import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.security.Principal;
import java.util.List;
import java.util.NoSuchElementException;

@RestController
@RequestMapping("/api/incidents")
public class IncidentController {

    private final IncidentService service;
    private final IncidentEvents events;
    private final ObjectMapper objectMapper;

    public IncidentController(IncidentService service, IncidentEvents events, ObjectMapper objectMapper) {
        this.service = service;
        this.events = events;
        this.objectMapper = objectMapper;
    }

    public record ManualIncidentRequest(
            @NotBlank @Pattern(regexp = "[a-z0-9-]{1,63}") String namespace,
            @NotBlank String alert) {
    }

    @Operation(summary = "Liste des incidents, du plus récent au plus ancien")
    @GetMapping
    public List<IncidentView> list() {
        return service.findAll().stream().map(i -> IncidentView.summary(i, objectMapper)).toList();
    }

    @Operation(summary = "Détail d'un incident : diagnostic complet et étapes de l'agent")
    @GetMapping("/{id}")
    public IncidentView get(@PathVariable Long id) {
        return IncidentView.detail(service.get(id), service.stepsOf(id), objectMapper);
    }

    @Operation(summary = "Flux temps réel des incidents (Server-Sent Events)")
    @GetMapping(path = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream() {
        return events.subscribe();
    }

    @Operation(summary = "Déclencher une enquête à la main (démo, tests)")
    @PostMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    public IncidentView create(@Valid @RequestBody ManualIncidentRequest request) {
        return IncidentView.summary(service.createManual(request.namespace(), request.alert()), objectMapper);
    }

    @Operation(summary = "Approuver la réparation proposée (rôle ADMIN)")
    @PostMapping("/{id}/approve")
    public IncidentView approve(@PathVariable Long id, Principal principal) {
        return IncidentView.summary(service.approve(id, principal.getName()), objectMapper);
    }

    @Operation(summary = "Refuser la réparation proposée (rôle ADMIN)")
    @PostMapping("/{id}/reject")
    public IncidentView reject(@PathVariable Long id, Principal principal) {
        return IncidentView.summary(service.reject(id, principal.getName()), objectMapper);
    }

    @ExceptionHandler(NoSuchElementException.class)
    ProblemDetail notFound(NoSuchElementException e) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage());
    }

    @ExceptionHandler(IllegalStateException.class)
    ProblemDetail conflict(IllegalStateException e) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, e.getMessage());
    }
}
