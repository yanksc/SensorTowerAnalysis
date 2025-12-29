#!/bin/bash
# Script to run the SensorTower Scraper web app

cd "$(dirname "$0")"
source venv/bin/activate
streamlit run app.py

