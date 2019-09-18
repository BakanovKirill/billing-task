# Billing app 

## Init project:
```
$ cd billing-task
$ docker-compose build
$ docker-compose up -d postgres
$ docker-compose run app setup_db
```

Launch:
```
$ docker-compose up app
```

Launch Nginx *(optional)*:
```
$ docker-compose up web
```

*Now your django app is available on http://localhost, but it's optional for development*

## Container commands

The image has 

Run a command:
```
$ docker-compose run app  <command>
```

Makemigrations:

```
docker-compose run -u $(id -u):$(id -g) app manage makemigrations
```

Available commands:

| Command   | Description                                                                     |
|-----------|---------------------------------------------------------------------------------|
| dev       | Start a normal Django development server                                        |
| bash      | Start a bash shell                                                              |
| manage    | Start manage.py                                                                 |
| setup_db  | Setup the initial database. Configure *$POSTGRES_DB_NAME* in docker-compose.yml |
| lint      | Run pylint                                                                      |
| python    | Run a python command                                                            |
| shell     | Start a Django Python shell                                                     |
| uwsgi     | Run uwsgi server                                                                |
| help      | Show this message                                                               |
