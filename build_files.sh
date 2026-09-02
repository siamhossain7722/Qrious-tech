#!/bin/bash
echo "Building Vercel Deployment for Qrious Tech..."
python3.11 -m pip install -r requirements.txt
python3.11 manage.py collectstatic --noinput --clear
python3.11 manage.py migrate --noinput
echo "Build Complete!"
