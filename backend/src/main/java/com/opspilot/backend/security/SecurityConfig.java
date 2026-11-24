package com.opspilot.backend.security;

import jakarta.servlet.DispatcherType;
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
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter;
import org.springframework.security.oauth2.server.resource.web.BearerTokenResolver;
import org.springframework.security.oauth2.server.resource.web.DefaultBearerTokenResolver;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Sécurité (sans état, aucune session côté serveur) :
 * - écran Angular : connexion par /api/auth/login → jeton JWT envoyé ensuite en "Authorization: Bearer ..." ;
 * - curl / scripts : HTTP Basic (-u admin:...) reste accepté.
 * Rôles :
 * - VIEWER : consulter les incidents ;
 * - ADMIN  : en plus, approuver/refuser les réparations et lancer des enquêtes à la main ;
 * - webhook Alertmanager : ouvert au niveau Spring Security, mais protégé par un jeton dans le contrôleur.
 */
@Configuration
public class SecurityConfig {

    private static final String ALERTMANAGER_WEBHOOK = "/api/alerts/alertmanager";

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable()) // API sans cookie de session : pas de risque CSRF
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        // fin d'un flux SSE / page d'erreur : la requête d'origine a déjà été vérifiée
                        .dispatcherTypeMatchers(DispatcherType.ASYNC, DispatcherType.ERROR).permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/auth/login").permitAll()
                        .requestMatchers("/actuator/health/**", "/actuator/prometheus",
                                "/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
                        .requestMatchers(HttpMethod.POST, ALERTMANAGER_WEBHOOK).permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/incidents", "/api/incidents/*/approve",
                                "/api/incidents/*/reject").hasRole("ADMIN")
                        .anyRequest().authenticated())
                .httpBasic(Customizer.withDefaults())
                .oauth2ResourceServer(oauth -> oauth
                        .bearerTokenResolver(bearerTokens())
                        .jwt(jwt -> jwt.jwtAuthenticationConverter(jwtRoles())));
        return http.build();
    }

    /**
     * Le webhook Alertmanager envoie AUSSI "Authorization: Bearer ...", mais avec SON jeton (pas un JWT).
     * Sans cette règle, Spring essaierait de le lire comme un JWT et répondrait 401.
     * Ce jeton est vérifié par AlertmanagerWebhookController.
     */
    private static BearerTokenResolver bearerTokens() {
        DefaultBearerTokenResolver jwtResolver = new DefaultBearerTokenResolver();
        return request -> request.getRequestURI().endsWith(ALERTMANAGER_WEBHOOK) ? null : jwtResolver.resolve(request);
    }

    /** Lit la liste "roles" du jeton (ex. ["ADMIN","VIEWER"]) et la transforme en ROLE_ADMIN, ROLE_VIEWER. */
    private static JwtAuthenticationConverter jwtRoles() {
        JwtGrantedAuthoritiesConverter roles = new JwtGrantedAuthoritiesConverter();
        roles.setAuthoritiesClaimName("roles");
        roles.setAuthorityPrefix("ROLE_");
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(roles);
        return converter;
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
