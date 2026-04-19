#!/usr/bin/env bash

echo "🔎 Testing RSS feeds..."
echo "----------------------------------"

FEEDS=(

  # Major Indian News RSS Feeds
https://www.thehindu.com/news/national/feeder/default.rss
https://indianexpress.com/feed/
https://feeds.feedburner.com/NDTV-LatestNews
https://www.hindustantimes.com/feeds/rss/topnews/rssfeed.xml
https://timesofindia.indiatimes.com/rssfeedstopstories.cms
https://www.indiatoday.in/rss/1206578
https://feeds.feedburner.com/ScrollinArticles.rss
https://frontline.thehindu.com/feeder/default.rss
# 💼 Business / Finance (Top tier)
https://www.livemint.com/rss/news
https://www.thehindubusinessline.com/feeder/default.rss
# 📺 Large Broadcast / Digital Networks
https://news.abplive.com/home/feed
https://www.indiatvnews.com/rssnews/topstory.xml

# General Aggregators / Portals
https://www.dnaindia.com/feeds/india.xml



    https://indianexpress.com/feed/
    https://indianexpress.com/section/india/feed/
    https://indianexpress.com/section/world/feed/
    https://indianexpress.com/section/politics/feed/
    https://indianexpress.com/section/business/feed/
    https://indianexpress.com/section/sports/feed/
    https://indianexpress.com/section/entertainment/feed/
    https://indianexpress.com/section/lifestyle/feed/
    https://indianexpress.com/section/technology/feed/
    https://indianexpress.com/section/cities/feed/
    https://indianexpress.com/section/explained/feed/
    https://indianexpress.com/section/opinion/feed/

    https://www.howtogeek.com/feed/category/smart-home/
    https://www.howtogeek.com/feed/category/streaming/
    "https://www.howtogeek.com/feed/"
    "https://www.howtogeek.com/feed/category/windows/"
    "https://www.howtogeek.com/feed/category/mac/"
    "https://www.howtogeek.com/feed/category/linux/"
    "https://www.howtogeek.com/feed/category/android/"
    "https://www.howtogeek.com/feed/category/hardware/"
    https://www.howtogeek.com/feed/

    # Desktop / OS
    https://www.howtogeek.com/feed/category/desktop/
    https://www.howtogeek.com/feed/category/windows/
    https://www.howtogeek.com/feed/category/mac/
    https://www.howtogeek.com/feed/category/linux/

    # Buying / Deals / Reviews
    https://www.howtogeek.com/feed/tag/deals/
    https://www.howtogeek.com/feed/buying-guides/
    https://www.howtogeek.com/feed/category/product-reviews/

    # News
    https://www.howtogeek.com/feed/news/

    # Tech + Science + Misc
    https://www.howtogeek.com/feed/category/automotive/
    https://www.howtogeek.com/feed/category/space/
    https://www.howtogeek.com/feed/category/cutting-edge/
    https://www.howtogeek.com/feed/category/hobbies/

    # Tags
    https://www.howtogeek.com/feed/tag/google/

    # Security / Web
    https://www.howtogeek.com/feed/category/cybersecurity/
    https://www.howtogeek.com/feed/category/web/

    # Media / Entertainment
    https://www.howtogeek.com/feed/category/streaming/
    https://www.howtogeek.com/feed/category/video-games/

    # Mobile / Ecosystem
    https://www.howtogeek.com/feed/category/ios/
    https://www.howtogeek.com/feed/category/android/
    https://www.howtogeek.com/feed/category/mobile/

    # Dev / Companies
    https://www.howtogeek.com/feed/category/programming/
    https://www.howtogeek.com/feed/category/microsoft/
)

for url in "${FEEDS[@]}"; do
    echo ""
    echo "➡️ Testing: $url"

    status=$(curl -s -o /dev/null -w "%{http_code}" "$url")

    if [ "$status" -eq 200 ]; then
        echo "✅ OK (200)"

        # Optional: check if it's actually RSS
        if curl -s "$url" | grep -qi "<rss"; then
            echo "📡 Valid RSS feed"
        else
            echo "⚠️ Not clearly RSS (no <rss tag found)"
        fi
    else
        echo "❌ Failed (HTTP $status)"
    fi
done

echo ""
echo "----------------------------------"
echo "✅ Done testing feeds"
