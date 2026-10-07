# TP 1 – Swarm 3 nœuds + résilience

Compte rendu du TP [Swarm 3 nœuds + résilience](https://app.notion.com/p/sysentive/TP-1-Swarm-3-n-uds-r-silience-3f0a84550c76801eae1bdb572af32657) (sysentive.link/tp-1-swarm).

- **Objectif :** monter un Swarm de 3 nœuds (1 manager, 2 workers), y déployer `web` (nginx, 4 réplicas), arrêter un worker et vérifier que Swarm replanifie les tâches perdues.
- **Date :** 05/10/2026
- **Résultat :** les 4 réplicas ont été restaurés **17,6 s** après l'arrêt du worker, dont 9,3 s pour détecter la panne.

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `compose.yaml` | Les 3 « machines » du cluster (nœuds Docker-in-Docker) |
| `cluster-status-before.txt` | Livrable : nœuds, service et répartition des tâches **avant** la panne |
| `cluster-status-after.txt` | Livrable : même chose **après** l'arrêt de `worker1` |
| `service-ps.txt` | Livrable : historique complet des tâches du service `web` (`docker service ps`) |
| `captures/` | Sorties brutes du terminal, étape par étape (`01` à `05`) |
| `screenshots/` | Captures d'écran des résultats, intégrées ci-dessous |

> Les captures d'écran sont des **rendus des sorties réelles du terminal**. Le script [`screenshots/render.py`](screenshots/render.py) (Python + Pillow) convertit les fichiers de `captures/` en images de terminal. Seule la coloration est ajoutée : le rouge et le vert mettent en évidence les lignes importantes. Le texte n'est pas modifié, à une exception près signalée par `[…]` à l'étape 1.

---

## 1) Topologie du cluster

Je n'avais pas 3 machines à disposition. J'ai donc utilisé l'option **DinD (Docker-in-Docker)** prévue par l'énoncé : chaque « machine » est un conteneur `docker:dind` privilégié qui fait tourner son propre Docker Engine. Les 3 nœuds sont décrits dans [`compose.yaml`](compose.yaml).

| Nœud | Rôle Swarm | IP (`swarm-net`) | OS | Docker Engine |
|---|---|---|---|---|
| `manager` | Manager (Leader) | 172.30.0.10 | Alpine Linux 3.24 | 29.8.2 |
| `worker1` | Worker | 172.30.0.11 | Alpine Linux 3.24 | 29.8.2 |
| `worker2` | Worker | 172.30.0.12 | Alpine Linux 3.24 | 29.8.2 |

**Hôte :** Windows 11 Enterprise et Docker Desktop (WSL2), Docker Engine 29.8.1, linux/amd64.

Points clés de `compose.yaml` :

- **`privileged: true`** est indispensable pour faire tourner un `dockerd` dans un conteneur.
- **`DOCKER_TLS_CERTDIR: ""`** désactive le TLS du daemon interne. C'est acceptable ici parce qu'**aucun port n'est publié sur l'hôte** : les daemons ne sont joignables que depuis le réseau `swarm-net`.
- Les nœuds ont des **IP fixes** sur `172.30.0.0/24`, un sous-réseau qui n'était utilisé par aucun autre réseau Docker de la machine.
- Un **healthcheck** (`docker info`) permet à `docker compose up --wait` d'attendre que les 3 `dockerd` internes soient prêts, ce qui prend environ 20 s.
- Les 3 nœuds partagent la même définition grâce à une ancre YAML (`&node`).

```bash
docker compose up -d --wait
```

![Démarrage des 3 nœuds](screenshots/01-noeuds.png)

Les lignes de progression `Creating`, `Starting` et `Waiting` sont condensées en `[…]`. La sortie complète est dans [`captures/01-preparation-noeuds.txt`](captures/01-preparation-noeuds.txt).

![OS, IP et versions des nœuds](screenshots/01b-versions.png)

---

## 2) `docker swarm init` sur le manager

Commande exacte :

```bash
docker compose exec manager docker swarm init --advertise-addr 172.30.0.10
```

![docker swarm init](screenshots/02-swarm-init.png)

`--advertise-addr` fixe l'adresse que le manager annonce aux autres nœuds pour le plan de contrôle (port 2377).

## 3) `docker swarm join` sur les 2 workers

Le worker-token se récupère sur le manager avec `docker swarm join-token worker` (`-q` pour n'afficher que le token). Commande exacte, avec le token masqué :

```bash
TOKEN=$(docker compose exec manager docker swarm join-token -q worker)
docker compose exec worker1 docker swarm join --token SWMTKN-1-45wxq7…[masqué] 172.30.0.10:2377
docker compose exec worker2 docker swarm join --token SWMTKN-1-45wxq7…[masqué] 172.30.0.10:2377
```

![docker swarm join et docker node ls](screenshots/03-swarm-join.png)

Les 3 nœuds sont `Ready`, et le manager est `Leader`.

Capture : [`captures/02-swarm-init-join.txt`](captures/02-swarm-init-join.txt)

---

## 4) Création du service `web` (4 réplicas)

```bash
docker compose exec manager docker service create --name web --replicas 4 nginx
```

![docker service create](screenshots/04-service-create.png)

Le service a convergé en environ 30 s, le temps que chaque nœud télécharge l'image `nginx`. La barre de progression, répétée plus de 100 fois, est condensée avec la mention `[répété N fois]`.

Capture : [`captures/03-service-create.txt`](captures/03-service-create.txt)

## 5) Répartition initiale

Livrable : [`cluster-status-before.txt`](cluster-status-before.txt)

![Répartition des tâches avant la panne](screenshots/05-repartition-avant.png)

| Nœud | Tâches |
|---|---|
| `manager` | `web.3` |
| `worker1` | `web.1`, `web.4` |
| `worker2` | `web.2` |

> Le manager reçoit lui aussi une tâche : par défaut, un manager est `Availability: Active` et sert également de worker. En production, on le passerait en `drain` (`docker node update --availability drain manager`) pour le réserver à l'orchestration. Je l'ai laissé tel quel pour coller à l'énoncé.

---

## 6) Simulation de la panne

J'ai arrêté **`worker1`**, le nœud qui portait le plus de tâches (2 sur 4). Dans le montage DinD, arrêter le conteneur revient à éteindre la machine : son `dockerd` et ses conteneurs nginx s'arrêtent.

```bash
docker compose stop worker1
```

Pendant ce temps, une boucle interrogeait le manager toutes les 3 s environ (`docker node ls` et `docker service ps web`). Les horodatages précis viennent ensuite de `docker inspect`, appliqué au conteneur `worker1`, au nœud et aux nouvelles tâches :

![Panne de worker1 et chronologie](screenshots/06-panne.png)

> Le compteur de la boucle affiche environ 30 s, mais il démarre au **lancement** de `docker compose stop`. Or le `dockerd` interne a mis environ 16 s à s'arrêter proprement (code de sortie 0). La panne réelle du nœud commence donc à 10:42:30.4. C'est à partir de ce moment que je mesure le délai de rétablissement.

Capture : [`captures/04-panne-worker1.txt`](captures/04-panne-worker1.txt)

## 7) État du service après la panne

Livrables : [`cluster-status-after.txt`](cluster-status-after.txt) et [`service-ps.txt`](service-ps.txt)

![État du cluster après la panne](screenshots/07-etat-apres.png)

- `worker1` est **`Down`**.
- Ses deux tâches, `web.1` et `web.4`, sont passées en *desired state* **`Shutdown`** (lignes `\_`).
- Swarm a créé deux nouvelles tâches pour les mêmes slots : `web.1` sur `manager` et `web.4` sur `worker2`.
- `--filter desired-state=running` confirme qu'il y a bien **4 tâches actives**, réparties 2 sur `manager` et 2 sur `worker2`.

---

## 8) Analyse

### Les 4 réplicas ont-ils été restaurés ? En combien de temps ?

**Oui.** Les 4 réplicas sont revenus à l'état `Running` sur `manager` et `worker2` **17,6 s** après l'arrêt effectif de `worker1` :

| Heure (UTC) | Événement | Délai |
|---|---|---|
| 10:42:30.4 | `worker1` arrêté | t = 0 |
| 10:42:39.8 | Le manager déclare `worker1` **Down** et crée 2 tâches de remplacement | **+9,3 s** (détection) |
| 10:42:48.1 | Les 2 nouvelles tâches sont `Running`, le service est de nouveau à 4 réplicas actifs | **+17,6 s** |

1. **Détection (9,3 s).** Les workers envoient des heartbeats au manager toutes les 5 s (`dispatcher heartbeat period`). Le manager attend quelques heartbeats manqués avant de déclarer le nœud `Down`.
2. **Replanification (8,3 s).** Dès que le nœud est `Down`, l'orchestrateur constate qu'il manque 2 tâches sur 4 et les crée aussitôt, à la même milliseconde. Il les place sur les nœuds `Ready` qui en ont le moins. Le reste du délai correspond au démarrage des conteneurs, y compris la vérification de l'image `nginx:latest`, déjà présente en cache sur ces nœuds.

Un premier essai, fait avec `docker run` au lieu de compose, avait donné un résultat cohérent : environ 17 s.

Pendant la panne, le service n'a jamais été complètement indisponible : 2 réplicas sur 4 tournaient toujours. Avec un port publié via le routing mesh, le trafic aurait continué d'être servi par ces 2 réplicas.

### Écart observé : `REPLICAS 6/4`

Pendant toute la durée de la panne, `docker service ls` affiche **`6/4`** (étape 7 et début du bonus). Comme `worker1` s'est arrêté sans pouvoir le signaler au manager, la dernière valeur connue du *current state* de ses tâches reste `Running`, et le compteur les compte encore. Pourtant, leur *desired state* est bien `Shutdown`. Il s'agit seulement d'un artefact d'affichage : `--filter desired-state=running` ne liste que 4 tâches. Le compteur revient à `4/4` dès que `worker1` se reconnecte et confirme l'arrêt (voir le bonus).

### Bonus : retour de `worker1`

![Retour de worker1 et rééquilibrage manuel](screenshots/08-bonus-retour-worker1.png)

- Après `docker compose start worker1`, le nœud repasse `Ready` et ses anciennes tâches passent en `Shutdown`. Le compteur revient à `4/4`, mais **aucune tâche n'y revient** : `docker ps` sur `worker1` est vide. Swarm ne rééquilibre pas automatiquement un service déjà à 4/4, pour ne pas interrompre des conteneurs qui fonctionnent.
- Pour rééquilibrer, il faut forcer un redéploiement progressif (*rolling update*) avec `docker service update --force web`. Après cette commande, `worker1` a récupéré une tâche (`web.2`).

Capture : [`captures/05-bonus-retour-worker1.txt`](captures/05-bonus-retour-worker1.txt)

### Que se passerait-il si on avait perdu le Manager à la place ?

Ce cluster n'a **qu'un seul manager**, donc aucune tolérance de panne côté orchestration :

- **Les conteneurs déjà lancés continuent de tourner** sur les workers. Le plan de données (conteneurs, réseau overlay, routing mesh sur les workers) ne dépend pas du manager à chaque instant. Ici, la tâche `web.3` qui tournait sur le manager serait perdue avec lui, et il resterait 3 réplicas sur 4.
- **En revanche, le plan de contrôle est perdu.** Plus aucune commande `docker service …` ni `docker node …` n'est possible, car les workers refusent les commandes de gestion (*This node is not a swarm manager*). La tâche perdue **ne serait pas replanifiée**, puisque c'est le manager qui fait la réconciliation. Une autre panne de worker ne serait plus compensée non plus. Enfin, impossible de mettre à jour, scaler ou déployer.
- **Pour s'en sortir :** redémarrer le manager si son état Raft (`/var/lib/docker/swarm`) est intact. Sinon, recréer un cluster avec `docker swarm init --force-new-cluster` à partir d'une sauvegarde de ce dossier, puis refaire rejoindre les workers.
- **La bonne pratique** consiste à prévoir **3 managers** (ou 5). Swarm utilise le consensus **Raft**, qui exige une majorité (quorum) de managers disponibles : avec 3 managers, le cluster supporte la perte de 1 ; avec 5, la perte de 2. Si le leader tombe, les managers restants élisent un nouveau leader en quelques secondes et la replanification continue. Un nombre pair de managers n'apporte rien : 4 managers tolèrent toujours une seule panne.

---

## Écarts par rapport à l'énoncé

- **Machines :** 3 conteneurs DinD sur un seul hôte Windows au lieu de 3 VMs. Le Swarm est réel (3 Docker Engines distincts, chacun avec son propre état), mais une panne de l'hôte ferait tomber les 3 nœuds en même temps.
- **Méthode de panne :** `docker compose stop worker1` sur le conteneur DinD. Cela équivaut à un arrêt de la machine : le daemon et ses conteneurs s'arrêtent ensemble.
- **Docker Compose** sert uniquement à provisionner les 3 machines. On ne peut pas y décrire le Swarm lui-même (`init`, `join`), qui se fait avec la CLI, et le service `web` est créé avec `docker service create`, comme le demande l'énoncé. Pour décrire des services Swarm dans un fichier, il faudrait un fichier de **stack**, au même format compose, déployé avec `docker stack deploy`.
- **Captures supplémentaires** dans `captures/` et `screenshots/`, en plus des 3 fichiers `.txt` demandés.
- Aucun port n'a été publié sur l'hôte, donc aucun conflit avec les ports déjà occupés sur ma machine.

## Reproduire / nettoyer

```bash
docker compose up -d --wait                                   # 3 nœuds healthy
docker compose exec manager docker swarm init --advertise-addr 172.30.0.10
TOKEN=$(docker compose exec manager docker swarm join-token -q worker)
docker compose exec worker1 docker swarm join --token $TOKEN 172.30.0.10:2377
docker compose exec worker2 docker swarm join --token $TOKEN 172.30.0.10:2377
docker compose exec manager docker service create --name web --replicas 4 nginx
docker compose stop worker1                                   # panne

docker compose down -v                                        # supprime nœuds, réseau et volumes /var/lib/docker
```

L'environnement est laissé en place pour la correction.
