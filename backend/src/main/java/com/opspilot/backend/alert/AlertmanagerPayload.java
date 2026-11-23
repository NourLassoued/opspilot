package com.opspilot.backend.alert;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.List;
import java.util.Map;

/** Format du webhook envoyé par Alertmanager (seuls les champs utiles sont lus). */
@JsonIgnoreProperties(ignoreUnknown = true)
public record AlertmanagerPayload(String status, List<Alert> alerts) {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Alert(String status, Map<String, String> labels, Map<String, String> annotations,
                        String startsAt, String fingerprint) {

        public String label(String key) {
            return labels == null ? null : labels.get(key);
        }

        public String annotation(String key) {
            return annotations == null ? null : annotations.get(key);
        }
    }
}
