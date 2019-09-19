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

# Notes:
- default superuser credentials:
    - Login: **admin**
    - Pass: **admin**

- db is populated with 2 users with 2 wallets.
- 1 user has 100$ on a wallet with a recorded transaction.


# Tests

```
$ docker-compose run app manage test billing.tests.TestAPI
```
