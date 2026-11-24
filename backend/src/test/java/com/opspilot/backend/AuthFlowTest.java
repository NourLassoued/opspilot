package com.opspilot.backend;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.opspilot.backend.agent.AgentClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Connexion JWT de l'écran Angular. */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AuthFlowTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    ObjectMapper json;

    @MockitoBean
    AgentClient agent; // jamais appelé ici

    private String login(String user, String password) throws Exception {
        String body = mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"" + user + "\",\"password\":\"" + password + "\"}"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        return json.readTree(body).get("token").asText();
    }

    @Test
    void adminGetsTokenWithRoles() throws Exception {
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"admin\",\"password\":\"admin-pass\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.token").isNotEmpty())
                .andExpect(jsonPath("$.username").value("admin"))
                .andExpect(jsonPath("$.roles[0]").value("ADMIN"))
                .andExpect(jsonPath("$.roles[1]").value("VIEWER"));
    }

    @Test
    void wrongPasswordIsRejected() throws Exception {
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"admin\",\"password\":\"faux\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.detail").value("Identifiants invalides"));
    }

    @Test
    void tokenGivesAccessAndMeShowsRoles() throws Exception {
        String token = login("viewer", "viewer-pass");
        mvc.perform(get("/api/incidents").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk());
        mvc.perform(get("/api/auth/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("viewer"))
                .andExpect(jsonPath("$.roles[0]").value("VIEWER"));
    }

    @Test
    void viewerTokenCannotApprove() throws Exception {
        String token = login("viewer", "viewer-pass");
        mvc.perform(post("/api/incidents/1/approve").header("Authorization", "Bearer " + token))
                .andExpect(status().isForbidden());
    }

    @Test
    void forgedTokenIsRejected() throws Exception {
        String token = login("viewer", "viewer-pass");
        String forged = token.substring(0, token.length() - 4) + "AAAA"; // signature modifiée
        mvc.perform(get("/api/incidents").header("Authorization", "Bearer " + forged))
                .andExpect(status().isUnauthorized());
    }
}
