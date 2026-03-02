# Projecte Playmon

## Instal·lacio dependencies per si no von recordeu coxinos

```
pip install -r requirements.txt
```

## Instruccions per iniciar la App

1 - OBRIR LA BASE DE DADES
Des de la carpeta del servidor:
docker compose up -d

2 - OBRIR EL SERVIDOR
Des de la carpeta del servidor:
source playmon/bin/activate
python3 main.py

El servidor queda obert a:
http://127.0.0.1:5000

3 - OBRIR EL CLIENT (VITE)
Des de la carpeta del client:
npm install
npm run dev

El client queda obert a:
http://localhost:5173

4 - ORDRE CORRECTE

1. Base de dades
2. Servidor
3. Client

5 - ATURAR TOT
Servidor: Ctrl + C
Client: Ctrl + C
Base de dades:
docker compose down

## Endpoint nou: comptar registres d'una taula

`GET /api/stats/<table_name>/count`

Exemple:

`GET /api/stats/users/count`

Resposta:

```json
{
	"table": "users",
	"count": 4
}
```
