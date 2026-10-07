# TP – Prise en main de Docker

Compte rendu du TP [Prise en main de Docker](https://app.notion.com/p/sysentive/TP-Prise-en-main-de-Docker-e36a127478e04e6bb7957924a001aeb9).

- **Environnement :** Windows 11 + Docker Desktop (WSL2), Docker Engine 29.8.1
- **Date :** 05/10/2026
- La partie 1 (installation) était déjà faite ; ce compte rendu commence à la partie 2.
- Les sorties complètes du terminal sont dans le dossier [`captures/`](captures/).

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `Dockerfile` | Image `monsite` basée sur `nginx:alpine` |
| `index.html` | Page statique copiée dans l'image |
| `.dockerignore` | Exclut `mysql-data/` et `.idea/` du contexte de build |
| `nginx.conf` | Fichier copié depuis le conteneur avec `docker cp` (partie 4) |
| `mysql-data/` | Données MySQL persistées par bind mount (partie 3) |
| `captures/` | Copies du terminal pour chaque partie |

---

## 2) Démarrer son premier conteneur Docker

> ⚠️ Le port **8080** de ma machine était déjà occupé (par un conteneur Adminer d'un autre projet) :
> `Bind for 0.0.0.0:8080 failed: port is already allocated`.
> J'ai donc publié Nginx sur le port **8090**.

```bash
docker run hello-world                               # "Hello from Docker!" -> installation OK
docker run --name web1 -p 8090:80 -d nginx:alpine
docker ps
```

```
CONTAINER ID   IMAGE          STATUS         PORTS                                     NAMES
809609f3933f   nginx:alpine   Up 3 seconds   0.0.0.0:8090->80/tcp, [::]:8090->80/tcp   web1
```

http://localhost:8090 affiche la page « Welcome to nginx! ».

```bash
docker stop web1     # STATUS -> Exited (0)
docker start web1    # STATUS -> Up, même conteneur (même ID 809609f3933f)
```

Capture : [`captures/02-premier-conteneur.txt`](captures/02-premier-conteneur.txt)

---

## 3) MySQL et persistance avec un volume

### A–C) Bind mount sur un dossier de l'hôte

```bash
mkdir -p mysql-data
docker run --name mysql1 -d \
  -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=tp \
  -p 3306:3306 \
  -v "$(pwd)/mysql-data:/var/lib/mysql" \
  mysql:8
docker logs -f mysql1     # ... ready for connections. Version: '8.4.11' ... port: 3306
ls -la mysql-data
```

Le dossier `mysql-data/` de l'hôte contient bien les fichiers MySQL : `mysql/`, `performance_schema/`, `sys/`, `tp/`, `ibdata1`, `mysql.ibd`, `undo_001`, `binlog.*`, etc.

### D) Vérifier la persistance

Pour prouver la persistance, j'ai aussi inséré une donnée avant de supprimer le conteneur :

```bash
docker exec mysql1 mysql -uroot -proot tp -e "CREATE TABLE t(id INT); INSERT INTO t VALUES (42);"
docker rm -f mysql1                         # supprime le conteneur, pas le dossier
docker run --name mysql1 -d ... -v "$(pwd)/mysql-data:/var/lib/mysql" mysql:8
ls -la mysql-data                           # les fichiers sont toujours là
docker exec mysql1 mysql -uroot -proot tp -e "SELECT * FROM t;"
```

```
id
42
```

✅ La donnée survit à la suppression du conteneur, car elle est stockée sur l'hôte et non dans la couche en écriture du conteneur.

### E) Volume Docker nommé

```bash
docker volume create mysql_data
docker run --name mysql2 -d -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=tp \
  -p 3307:3306 -v mysql_data:/var/lib/mysql mysql:8
docker volume inspect mysql_data
```

```json
"Driver": "local",
"Mountpoint": "/var/lib/docker/volumes/mysql_data/_data",
"Name": "mysql_data"
```

Le volume nommé est géré par Docker. Sous Windows, il se trouve dans la VM WSL2 de Docker Desktop et n'est pas visible comme un dossier du projet.

Capture : [`captures/03-mysql-volumes.txt`](captures/03-mysql-volumes.txt)

---

## 3 bis) Commandes de base

| Action | Commande |
|---|---|
| Conteneurs en cours / tous | `docker ps` / `docker ps -a` |
| Logs (suivi en direct) | `docker logs web1` / `docker logs -f web1` |
| Arrêter / démarrer / redémarrer | `docker stop` / `docker start` / `docker restart web1` |
| Supprimer (arrêté) / en force | `docker rm web1` / `docker rm -f web1` |
| Images locales / supprimer | `docker images` / `docker rmi nginx:alpine` |
| Nettoyage | `docker system prune` |

Toutes ces commandes ont été testées sur `web1`. Deux exceptions volontaires :
- `docker rmi nginx:alpine` n'a pas été lancé, car l'image sert encore de base aux parties 4 à 6 ;
- `docker system prune` n'a pas été lancé, car il supprimerait des ressources d'autres projets présents sur la machine.

Capture : [`captures/03b-commandes-base.txt`](captures/03b-commandes-base.txt)

---

## 4) Introspecter un conteneur

```bash
docker run --name web1 -p 8090:80 -d nginx:alpine
docker inspect web1                     # configuration complète en JSON
```

**Récupérer l'IP.** La commande du TP `docker inspect -f '{{.NetworkSettings.IPAddress}}' web1` échoue avec Docker 29 :
`map has no entry for key "IPAddress"`. Ce champ, déprécié, a été retiré. Il faut lire l'IP par réseau :

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' web1
# 172.17.0.2
```

```bash
docker top web1          # 1 process master nginx (root) + 8 workers
docker stats web1        # CPU 0.00%, RAM ~7.4 MiB, 9 PIDs
docker exec -it web1 sh  # puis : uname -a ; ps aux ; ls -la /usr/share/nginx/html ; exit
```

Dans le conteneur :
- `uname -a` affiche `Linux ... 6.6.87.2-microsoft-standard-WSL2`. Le conteneur partage le noyau de la VM WSL2 ; ce n'est pas une VM à part entière.
- `ps aux` montre que le PID 1 est `nginx: master process`.
- `/usr/share/nginx/html` contient `index.html` et `50x.html`.

```bash
docker cp web1:/etc/nginx/nginx.conf ./nginx.conf   # fichier récupéré dans ce dossier
```

Capture : [`captures/04-introspection.txt`](captures/04-introspection.txt)

---

## 5) Créer sa propre image

`Dockerfile` :

```dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
```

```bash
docker build -t monsite:1.0 .
docker images | grep monsite
# monsite:1.0   b727ad4e98c3   93.6MB   26.3MB
```

Le build ne comporte que 2 étapes : la base `nginx:alpine`, déjà en cache, puis le `COPY`, qui ajoute une seule couche.

Capture : [`captures/05-build-image.txt`](captures/05-build-image.txt)

## 6) Démarrer un conteneur avec son image

```bash
docker run --name monsite1 -p 8081:80 -d monsite:1.0
curl http://localhost:8081        # -> <h1>Hello depuis mon image Docker</h1>
docker logs monsite1              # ... "GET / HTTP/1.1" 200
docker stop monsite1
docker rm monsite1
```

Capture : [`captures/06-run-image.txt`](captures/06-run-image.txt)

---

## 7) Publier l'image sur Docker Hub

Dépôt publié : **https://hub.docker.com/r/gedeonm/monsite**

```bash
docker login            # Authenticating with existing credentials... [Username: gedeonm] -> Login Succeeded
docker tag monsite:1.0 gedeonm/monsite:1.0
docker tag monsite:1.0 gedeonm/monsite:latest
docker push gedeonm/monsite:1.0
docker push gedeonm/monsite:latest
```

```
1.0: digest: sha256:b727ad4e98c39fa69d53ec54d2ca4a7de6ed93f41f07ef976dca43df2590369d size: 856
latest: digest: sha256:b727ad4e98c39fa69d53ec54d2ca4a7de6ed93f41f07ef976dca43df2590369d size: 856
```

Pendant le push, la plupart des couches s'affichent comme `Mounted from library/nginx`. Docker Hub les possédait déjà via l'image officielle Nginx, donc elles ne sont pas renvoyées. Seules les couches propres à `monsite` sont réellement envoyées (`Pushed`). Pour `latest`, tout est déjà présent (`Layer already exists`), car c'est la même image avec le même digest.

**Vérification après suppression locale :**

```bash
docker rmi gedeonm/monsite:1.0
docker pull gedeonm/monsite:1.0      # Status: Downloaded newer image for gedeonm/monsite:1.0
docker run --name monsite2 -p 8082:80 -d gedeonm/monsite:1.0
curl http://localhost:8082           # -> <h1>Hello depuis mon image Docker</h1>
```

Capture : [`captures/07-push-dockerhub.txt`](captures/07-push-dockerhub.txt)

---

## Questions de validation

**1. Quelle différence entre image et conteneur ?**
Une **image** est un modèle **en lecture seule** et immuable. Elle est faite de couches (système de fichiers, dépendances, configuration, commande de démarrage) et identifiée par un nom:tag ou un digest.
Un **conteneur** est une **instance en cours d'exécution** (ou arrêtée) d'une image. Il ajoute une couche en écriture, un état (running, exited…), des processus isolés, un réseau et des volumes.
On peut lancer plusieurs conteneurs à partir d'une même image : `web1` et `monsite1` reposent tous deux sur la base `nginx:alpine`. On peut comparer l'image à une classe et le conteneur à un objet.

**2. À quoi sert `-p 8081:80` ? Dans quel sens va le mapping ?**
Il publie un port du conteneur sur la machine hôte. Le format est `-p <port_hôte>:<port_conteneur>`.
Ici, le port **8081 de l'hôte** est redirigé vers le port **80 du conteneur**. Le trafic va donc **de l'hôte vers le conteneur** : une requête sur `http://localhost:8081` arrive sur Nginx, qui écoute sur 80 dans le conteneur.
C'est pour cela que j'ai pu utiliser 8090 au lieu de 8080 sans rien changer à Nginx : seul le côté hôte change.

**3. Différence entre `docker run` et `docker start` ?**
- `docker run` **crée un nouveau conteneur** à partir d'une image, puis le démarre. Il télécharge l'image si besoin et applique les options (`--name`, `-p`, `-e`, `-v`…).
- `docker start` **redémarre un conteneur existant** qui a été arrêté. Il garde le même ID, la même configuration et sa couche en écriture. On ne peut pas lui passer de nouvelles options.

Relancer `docker run --name web1 ...` alors que `web1` existe déjà échoue, car le nom est déjà utilisé.

**4. Quelle commande donne la configuration complète d'un conteneur ?**
`docker inspect web1`. Elle renvoie un JSON complet : état, image, commande, variables d'environnement, montages, ports, réseau, IP…
On peut extraire un champ avec `-f`/`--format` et un template Go, par exemple `docker inspect -f '{{.State.Status}}' web1`.

**5. Pourquoi tagger une image avant un `docker push` ?**
Le nom de l'image indique à Docker **vers quel registre et quel dépôt** l'envoyer : `[registre/]namespace/dépôt:tag`.
`monsite:1.0` serait interprété comme `docker.io/library/monsite`, c'est-à-dire le namespace des images officielles, où l'on n'a pas le droit d'écrire.
En taguant `<votre_dockerhub>/monsite:1.0`, on désigne son propre namespace sur Docker Hub, donc un dépôt où le push est autorisé. Le tag sert aussi à **versionner** l'image (`1.0`, `latest`).

---

## Nettoyage (optionnel)

```bash
docker rm -f web1 mysql1 mysql2 monsite2
docker volume rm mysql_data
rm -rf mysql-data
```
