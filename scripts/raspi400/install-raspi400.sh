#!/usr/bin/env bash
set -e
echo "Installing lightweight Graphical Interface prerequisites..."
sudo apt update
sudo apt install -y git python3-pip lighttpd
echo "Copy GUI files..."
cp -r gui/* ~/public_html/
echo "Enable lighttpd for local web GUI..."
sudo systemctl enable lighttpd
sudo systemctl restart lighttpd
