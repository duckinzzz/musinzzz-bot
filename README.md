# musinzzz-bot
0. Obtain token using [this guide](https://yandex-music.readthedocs.io/en/main/token.html)
1. Create `.env` based on `.env.example`.

2. Run

- Locally
```bash
pip install -r requirements.txt
python run.py
```

- Docker with hot reload (dev mode):

```bash
docker compose -f docker-compose.DEV.yml up --build
```

- Docker (prod mode):

```bash
docker compose up --build -d
```
