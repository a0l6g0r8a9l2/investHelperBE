## Run local with docker 
(file with env params and name settings.py required)

### 1. Run mongo

`docker run --rm -d -p 27017:27017 mongo`

### 2. Build app image
   
`docker build -t notification-invest-helper-bot .`
      
### 3. Run app

`docker run -d --name notify -p 127.0.0.1:8000:80 notification:latest`

## Run with docker-compose 
(BOT_TOKEN in environment section docker-compose.yml required)

### 1. Build

`docker-compose build`

### 2. Run

`docker-compose up -d`
