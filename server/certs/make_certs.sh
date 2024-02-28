#!/bin/bash

# Define variables for the key and certificate
KEY_FILE="private.key"
CERT_FILE="certificate.pem"

# Generate a private key
openssl genrsa -out $KEY_FILE 2048

# Generate a self-signed certificate
openssl req -new -x509 -sha256 -key $KEY_FILE -out $CERT_FILE -days 365

# Print the paths of the generated files
echo "Generated key: $KEY_FILE"
echo "Generated certificate: $CERT_FILE"
