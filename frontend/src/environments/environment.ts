export const environment = {
  production: false,
  /**
   * Comme en développement : URL relative + proxy (proxy.conf.json → 127.0.0.1:8000).
   * Évite les soucis CORS (localhost vs 127.0.0.1) pendant ng serve.
   */
  apiUrl: '',
};
