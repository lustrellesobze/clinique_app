export const environment = {
  production: false,
  /**
   * Chaîne vide : les appels vont vers /api sur le même hôte que ng serve (4200).
   * Le fichier proxy.conf.json redirige /api → http://127.0.0.1:8000 (voir angular.json).
   * Évite CORS et soucis localhost / IPv6 sous Windows.
   */
  apiUrl: '',
};
