#!/bin/bash
cd ~/llm-api
git pull origin main           # (if using git, optional)
docker build -t llm-api .
docker stop $(docker ps -q)
docker run -d --restart unless-stopped -p 443:443 llm-api
