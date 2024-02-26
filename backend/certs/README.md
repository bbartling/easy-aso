# SSL Certificate Generation Script

## Overview
This script is used to generate a 2048-bit RSA private key and a self-signed SSL certificate. The certificate is valid for 365 days.

## Steps Performed by the Script
- Generates a 2048-bit RSA private key (`private.key`).
- Creates a self-signed SSL certificate (`certificate.pem`). During the creation of the certificate, you will be prompted to enter some information (e.g., country, state, organization), which will be included in the certificate.

## Usage
1. Give execute permissions to the script: `$ chmod +x make_certs.sh`
2. Run the script: `$ ./make_certs.sh`


## Note
These certs are self signed so the browser doesnt think they are safe but they are free!
