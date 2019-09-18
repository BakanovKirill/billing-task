#!/usr/bin/env bash
docker-compose stop
docker-compose start db
sleep 5
dropdb -h localhost -p 5432 -U postgres app
createdb -h localhost -p 5432 -U postgres app
docker-compose run --rm web python dev_commands.py init && docker-compose run --rm web python commands.py db stamp head


