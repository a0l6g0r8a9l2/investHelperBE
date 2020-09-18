1. Build image
    
    `docker build -t MyApp .`

2. Login to DockerHub
    
    `docker login -u login -p password`

3. Login to Heroku (Heroku account and CLI required)

    `heroku login`
    
4. Login to Heroku container

    `heroku container:login`
    
5. Create Heroku App

    `heroku create --app MyApp`
    
6. Push image to Heroku

    `heroku container:push web --app MyApp`
  
7. Release Heroku App

    `heroku container:release --app MyApp`

8. Open App 

    `heroku open --app MyApp`

9. Check App logs

    `heroku logs --app MyApp`
