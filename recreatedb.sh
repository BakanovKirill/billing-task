#!/usr/bin/env bash
docker-compose stop
docker-compose up -d postgres
docker-compose run app recreate_db


