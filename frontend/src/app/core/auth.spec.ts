import { provideHttpClient, withInterceptors, HttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AuthService } from './auth';
import { authInterceptor } from './auth.interceptor';

describe('AuthService + intercepteur', () => {
  let http: HttpTestingController;
  let auth: AuthService;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([{ path: 'login', children: [] }]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
  });

  afterEach(() => http.verify());

  async function loginAs(roles: string[], expiresAt = new Date(Date.now() + 3600_000).toISOString()) {
    const done = auth.login('admin', 'secret');
    http.expectOne('/api/auth/login').flush({ token: 'jwt-123', username: 'admin', roles, expiresAt });
    await done;
  }

  it('garde le jeton et les rôles après la connexion', async () => {
    await loginAs(['ADMIN', 'VIEWER']);
    expect(auth.isLoggedIn()).toBe(true);
    expect(auth.isAdmin()).toBe(true);
    expect(auth.token()).toBe('jwt-123');
  });

  it("un viewer n'est pas admin", async () => {
    await loginAs(['VIEWER']);
    expect(auth.isAdmin()).toBe(false);
  });

  it('ajoute le jeton aux appels /api', async () => {
    await loginAs(['VIEWER']);
    TestBed.inject(HttpClient).get('/api/incidents').subscribe();
    const req = http.expectOne('/api/incidents');
    expect(req.request.headers.get('Authorization')).toBe('Bearer jwt-123');
    req.flush([]);
  });

  it('déconnecte quand le backend répond 401', async () => {
    await loginAs(['VIEWER']);
    TestBed.inject(HttpClient).get('/api/incidents').subscribe({ error: () => undefined });
    http.expectOne('/api/incidents').flush(null, { status: 401, statusText: 'Unauthorized' });
    expect(auth.isLoggedIn()).toBe(false);
  });

  it('un jeton expiré est ignoré', async () => {
    await loginAs(['ADMIN'], new Date(Date.now() - 1000).toISOString());
    expect(auth.token()).toBeNull();
    expect(auth.isLoggedIn()).toBe(false);
  });
});
