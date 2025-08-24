#!/bin/bash

# KodeKloud Scraper Runner
# ========================
# High-performance hybrid scraper for comprehensive content extraction

echo "🚀 KodeKloud Content Scraper"
echo "=" * 30
echo "⚡ High-performance hybrid approach"
echo "📊 Extracts 10,000+ chapters from 117 courses"
echo "⏱️  Estimated time: ~90-120 minutes"
echo "=" * 30

# Setup environment
if [ ! -d "venv" ]; then
    echo "Setting up environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
else
    source venv/bin/activate
fi

echo ""
echo "🚀 Starting scraper..."
python kodekloud_scraper.py

echo ""
echo "✅ Scraping completed!"
echo "📄 Results saved to: kodekloud_content.csv"
