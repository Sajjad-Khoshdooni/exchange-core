
# Development
## env
```ln -s .env.development .env```


# Deployment
## RSA Keypair

### generate a private key with the correct length
```openssl genrsa -out private-key.pem 3072```

### generate corresponding public key
```openssl rsa -in private-key.pem -pubout -out public-key.pem```