# Billing app 

Covers a task for creating API for a billing system which provides the following:

- User registration/login (username, password, city, country, currency)
- Wallet of chosen currency is created for each User
- User can add money to the wallet
- User can send money from his wallet to another user wallet.
- User can see the generated report with transactions history on his wallet: 
  - without date period
  - with start date or end date or both.
  

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
