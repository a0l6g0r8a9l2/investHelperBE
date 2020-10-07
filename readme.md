1. Build image
    
    `docker build -t notification-invest-helper-bot .`

2. Login to DockerHub
    
    `docker login -u login -p password`

3. Login to Heroku (Heroku account and CLI required)

    `heroku login`
    
4. Login to Heroku container

    `heroku container:login`
    
5. Create Heroku App

    `heroku create --app notification-invest-helper-bot`
    
6. Push image to Heroku

    `heroku container:push web --app notification-invest-helper-bot`
  
7. Release Heroku App

    `heroku container:release web --app notification-invest-helper-bot`

8. Open App 

    `heroku open --app notification-invest-helper-bot`

9. Check App logs

    `heroku logs --app notification-invest-helper-bot`
