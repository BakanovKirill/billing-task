# Billing app 

Default landing page is Swagger with all avialable endpoints.
Recommended way of testing: using Postman or similar tool because app uses JWT tokens which need to be passed in `Authorization` header.

## Init project:
```
$ cd billing-task
$ docker-compose build
$ docker-compose up -d postgres
$ docker-compose run app setup_db
```

Launch:
```
$ docker-compose up
```

*Now app is available on http://localhost*

## Container commands

The image has 

Run a command:
```
$ docker-compose run app  <command>
```

# Tests

```
$ docker-compose run app manage test billing.tests.TestAPI
```
