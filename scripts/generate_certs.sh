#!/bin/bash

# Define the directory to save the certificates, relative to the script location
CERTS_DIR="$(dirname "$0")/../certs"

# Create the certs directory if it doesn't exist
mkdir -p $CERTS_DIR

# Define variables for the key and certificate with the path
KEY_FILE="${CERTS_DIR}/private.key"
CERT_FILE="${CERTS_DIR}/certificate.pem"

# Generate a private key
openssl genrsa -out $KEY_FILE 2048

# Generate a self-signed certificate
openssl req -new -x509 -sha256 -key $KEY_FILE -out $CERT_FILE -days 365

# Print the paths of the generated files
echo "Generated key: $KEY_FILE"
echo "Generated certificate: $CERT_FILE"
