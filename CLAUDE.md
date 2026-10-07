# Cours Docker – ESGI

Chaque TP a son propre dossier ici (`tp-docker-image/`, `tp-01-swarm-init/`, …). Les échanges se font en français.

## Méthode pour chaque TP

1. L'énoncé est une page Notion (`app.notion.com/p/sysentive/...`). WebFetch ne voit qu'une page vide, car Notion est rendu en JS. La récupérer avec l'API publique :
   `POST https://www.notion.so/api/v3/loadCachedPageChunk` avec `{"page":{"id":"<uuid de l'URL, avec tirets>"},"limit":100,"cursor":{"stack":[]},"chunkNumber":N,"verticalColumns":false}`. Boucler tant que `cursor.stack` n'est pas vide, puis parcourir `recordMap.block[*].value.value.content` dans l'ordre. Un script réutilisable existait pour le TP précédent (Python : `urllib` + `json`).
2. Exécuter réellement les commandes du TP et sauvegarder chaque sortie de terminal dans `captures/NN-<partie>.txt`. Ces captures sont les livrables.
3. Rédiger un `README.md` dans le dossier du TP : le compte rendu de chaque partie, les écarts par rapport à l'énoncé et les réponses aux « Questions de validation ».
   Modèle : `tp-docker-image/README.md`.

## Environnement

- Windows 11, Docker Desktop (WSL2), Docker Engine 29.x. Si le daemon ne répond pas, lancer `C:\Program Files\Docker\Docker\Docker Desktop.exe`.
- Docker Hub : déjà connecté avec le compte `gedeonm` (ne jamais saisir d'identifiants soi-même).
- Ports déjà occupés par les conteneurs `swala-*` d'un autre projet : 8080, 5050, 5432, 6379, 7700, 8001, 9000-9001. Ne pas toucher à ces conteneurs. Choisir un autre port côté hôte et le signaler dans le README (le TP 1 utilisait 8090 au lieu de 8080).
- Ne pas lancer `docker system prune` ni supprimer d'images ou de volumes qui ne viennent pas du TP : la machine sert à d'autres projets.
- Dans Git Bash, préfixer avec `MSYS_NO_PATHCONV=1` les commandes `docker` qui contiennent des chemins `/...`. Pour un bind mount, utiliser `$(pwd -W)`.
- Docker 29 : `.NetworkSettings.IPAddress` n'existe plus. Utiliser `{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}`.

## Avancement

- `tp-docker-image/` (Prise en main de Docker) : terminé le 05/10/2026, image publiée en `gedeonm/monsite:1.0` et `:latest`. Ses conteneurs (`web1`, `mysql1`, `mysql2`, `monsite2`) sont arrêtés, pas supprimés.
- `tp-01-swarm-init/` (Swarm 3 nœuds + résilience) : terminé le 05/10/2026. Cluster défini dans `compose.yaml` (projet `tp1-swarm`, nœuds DinD sur 172.30.0.0/24), laissé en marche avec le service `web`. Les images de `screenshots/` sont générées depuis `captures/` par `screenshots/render.py` (Pillow, venv dans le scratchpad, pas installé globalement).
