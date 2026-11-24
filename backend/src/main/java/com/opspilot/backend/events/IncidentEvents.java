package com.opspilot.backend.events;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.opspilot.backend.incident.Incident;
import com.opspilot.backend.incident.IncidentView;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Diffusion en temps réel des changements d'incidents (Server-Sent Events).
 * Le dashboard Angular (Sprint 5) s'y abonne pour se mettre à jour sans recharger la page.
 */
@Component
public class IncidentEvents {

    private final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();
    private final ObjectMapper objectMapper;

    public IncidentEvents(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public SseEmitter subscribe() {
        SseEmitter emitter = new SseEmitter(0L); // pas d'expiration
        emitters.add(emitter);
        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> emitters.remove(emitter));
        emitter.onError(e -> emitters.remove(emitter));
        try {
            // Premier message : le navigateur sait tout de suite que le flux est bien connecté.
            emitter.send(SseEmitter.event().name("ready").data("ok"));
        } catch (Exception e) {
            emitters.remove(emitter);
        }
        return emitter;
    }

    public void publish(Incident incident) {
        IncidentView view = IncidentView.summary(incident, objectMapper);
        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event().name("incident").data(view));
            } catch (Exception e) {
                emitters.remove(emitter); // navigateur fermé : on oublie cet abonné
            }
        }
    }
}
