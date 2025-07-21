#!/bin/bash

echo "Stopping all Docker containers..."
if [ "$(docker ps -q)" ]; then
  docker stop $(docker ps -q)
else
  echo "No running containers."
fi

echo "Removing all Docker containers..."
if [ "$(docker ps -aq)" ]; then
  docker rm $(docker ps -aq)
else
  echo "No containers to remove."
fi

echo "Removing unused Docker images..."
if [ "$(docker images -q)" ]; then
  docker rmi $(docker images -q)
else
  echo "No Docker images to remove."
fi

echo "Cleaning apt cache..."
sudo apt-get clean

echo "Clearing user pip and huggingface cache..."
rm -rf ~/.cache/pip/*
rm -rf ~/.cache/huggingface/*

echo "Removing temporary files (user-owned only)..."
find /tmp -user $(whoami) -delete

echo "Disk usage after cleanup:"
df -h
