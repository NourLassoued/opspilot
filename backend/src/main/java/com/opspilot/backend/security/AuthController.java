package com.opspilot.backend.security;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** Connexion de l'écran Angular : nom + mot de passe → jeton JWT. */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    public record LoginRequest(@NotBlank String username, @NotBlank String password) {
    }

    public record Me(String username, List<String> roles) {
    }

    private final AuthenticationConfiguration authenticationConfiguration;
    private final TokenService tokens;

    public AuthController(AuthenticationConfiguration authenticationConfiguration, TokenService tokens) {
        this.authenticationConfiguration = authenticationConfiguration;
        this.tokens = tokens;
    }

    @Operation(summary = "Se connecter : renvoie un jeton JWT à mettre dans l'en-tête Authorization: Bearer ...")
    @PostMapping("/login")
    public TokenService.IssuedToken login(@Valid @RequestBody LoginRequest request) throws Exception {
        Authentication authentication = authenticationConfiguration.getAuthenticationManager().authenticate(
                UsernamePasswordAuthenticationToken.unauthenticated(request.username(), request.password()));
        return tokens.issue(authentication);
    }

    @Operation(summary = "Qui suis-je ? (nom et rôles de l'utilisateur connecté)")
    @GetMapping("/me")
    public Me me(Authentication authentication) {
        return new Me(authentication.getName(), TokenService.rolesOf(authentication));
    }

    @ExceptionHandler(AuthenticationException.class)
    ProblemDetail badCredentials(AuthenticationException e) {
        // Même message pour un mauvais nom ou un mauvais mot de passe : on ne révèle pas lequel est faux.
        return ProblemDetail.forStatusAndDetail(HttpStatus.UNAUTHORIZED, "Identifiants invalides");
    }
}
