1. Собрать образ
    
    `docker build -t notification .`

2. Запустить образ

    `docker run -d --name notification -p 80:80 -e MODULE_NAME="app.main"  notification`
    
3. Проверить запущен ли контейнер и узнать CONTAINERID: 

    `docker -ps`
    
4. Проверить логи:

    `docker logs -f CONTAINERID`
    
5. Остановить контейнер: 
    
    `docker stop CONTAINERID`

6. Удалить остановленные контейнеры: 

    `docker rm -v $(docker ps -aq -f status=exited)`