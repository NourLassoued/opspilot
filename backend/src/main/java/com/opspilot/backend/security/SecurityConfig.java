package com.opspilot.backend.security;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Sécurité du Sprint 4 (HTTP Basic, sans état) :
 * - VIEWER : consulter les incidents ;
 * - ADMIN  : en plus, approuver/refuser les réparations et lancer des enquêtes à la main ;
 * - webhook Alertmanager : ouvert au niveau Spring Security, mais protégé par un jeton dans le contrôleur.
 * Au Sprint 5, l'écran de connexion Angular passera à des jetons JWT.
 */
@Configuration
public class SecurityConfig {

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable()) // API sans cookie de session : pas de risque CSRF
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/actuator/health/**", "/actuator/prometheus",
                                "/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/alerts/alertmanager").permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/incidents", "/api/incidents/*/approve",
                                "/api/incidents/*/reject").hasRole("ADMIN")
                        .anyRequest().authenticated())
                .httpBasic(Customizer.withDefaults());
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    @Bean
    UserDetailsService users(PasswordEncoder encoder,
                             @Value("${opspilot.security.admin.username}") String adminUser,
                             @Value("${opspilot.security.admin.password}") String adminPassword,
                             @Value("${opspilot.security.viewer.username}") String viewerUser,
                             @Value("${opspilot.security.viewer.password}") String viewerPassword) {
        return new InMemoryUserDetailsManager(
                User.withUsername(adminUser).password(encoder.encode(adminPassword)).roles("ADMIN", "VIEWER").build(),
                User.withUsername(viewerUser).password(encoder.encode(viewerPassword)).roles("VIEWER").build());
    }
}
