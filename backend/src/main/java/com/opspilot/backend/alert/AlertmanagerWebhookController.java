package com.opspilot.backend.alert;

import com.opspilot.backend.incident.Incident;
import com.opspilot.backend.incident.IncidentService;
import io.swagger.v3.oas.annotations.Operation;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.Map;

/** Point d'entrée des alertes Prometheus/Alertmanager. Protégé par un jeton partagé. */
@RestController
@RequestMapping("/api/alerts")
public class AlertmanagerWebhookController {

    private final IncidentService service;
    private final byte[] expectedHeader;

    public AlertmanagerWebhookController(IncidentService service,
                                         @Value("${opspilot.alertmanager.token}") String token) {
        this.service = service;
        this.expectedHeader = ("Bearer " + token).getBytes(StandardCharsets.UTF_8);
    }

    @Operation(summary = "Webhook Alertmanager : crée ou complète un incident et lance l'enquête de l'agent")
    @PostMapping("/alertmanager")
    public ResponseEntity<Map<String, Object>> receive(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @RequestBody AlertmanagerPayload payload) {
        if (!isValid(authorization)) {
            Map<String, Object> error = Map.of("error", "Jeton Alertmanager invalide");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }
        List<Long> incidents = service.handleAlertmanager(payload).stream().map(Incident::getId).toList();
        Map<String, Object> body = Map.of("incidents", incidents);
        return ResponseEntity.accepted().body(body);
    }

    private boolean isValid(String authorization) {
        // Comparaison en temps constant : ne révèle pas le jeton par le temps de réponse
        return authorization != null
                && MessageDigest.isEqual(authorization.getBytes(StandardCharsets.UTF_8), expectedHeader);
    }
}
