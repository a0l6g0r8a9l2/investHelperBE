## Run with docker-compose 
(BOT_TOKEN in environment section docker-compose.yml required)

### 1. Build

`docker-compose build`

### 2. Run

`docker-compose up -d`

## Run local with docker 
(file with env params and name settings.py required)

### 1. Run Mongo

`docker run --rm -d -p 27017:27017 mongo`

### 2. Run Redis

`docker run --name notify-redis -d redis`

### 3. Build app image
   
`docker build -t notification-invest-helper-bot .`
      
### 4. Run app

`docker run -d --name notify -p 127.0.0.1:8000:80 notification:latest`

### 5. Build bot image

`docker build -t notification-bot .`

### 6. Run bot

`docker run -d --name notification-bot`
