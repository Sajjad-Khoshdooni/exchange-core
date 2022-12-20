
# Development
## env
```ln -s .env.development .env```


# Deployment
## RSA Keypair

### generate a private key with the correct length
```openssl genrsa -out private-key.pem 3072```

### generate corresponding public key
```openssl rsa -in private-key.pem -pubout -out public-key.pem```

# DB
### Readonly Role
```postgresql
\c mydb
CREATE ROLE bi;
ALTER ROLE bi WITH PASSWORD 'password' LOGIN;
GRANT CONNECT ON DATABASE mydb TO bi;
GRANT USAGE ON SCHEMA public TO bi;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bi;

-- if needed to exclude some
REVOKE SELECT ON excluding_table from bi;
```

# Rabbitmq
```shell
rabbitmqctl add_vhost my_vhost
rabbitmqctl set_permissions -p my_vhost rabbitmq ".*" ".*" ".*"
```
