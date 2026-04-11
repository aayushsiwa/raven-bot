#!/usr/bin/env bash

echo "🔎 Testing RSS feeds..."
echo "----------------------------------"

FEEDS=(
    https://www.howtogeek.com/feed/category/security/
    https://www.howtogeek.com/feed/category/privacy/
    https://www.howtogeek.com/feed/category/how-to/
    https://www.howtogeek.com/feed/category/internet/
    https://www.howtogeek.com/feed/category/gaming/
    https://www.howtogeek.com/feed/category/iphone-ipad/
    https://www.howtogeek.com/feed/category/smart-home/
    https://www.howtogeek.com/feed/category/apps/
    https://www.howtogeek.com/feed/category/software/
    https://www.howtogeek.com/feed/category/productivity/
    https://www.howtogeek.com/feed/category/windows-11/
    https://www.howtogeek.com/feed/category/chrome/
    https://www.howtogeek.com/feed/category/microsoft-office/
    https://www.howtogeek.com/feed/category/streaming/
    "https://www.howtogeek.com/feed/"
    "https://www.howtogeek.com/feed/category/windows/"
    "https://www.howtogeek.com/feed/category/mac/"
    "https://www.howtogeek.com/feed/category/linux/"
    "https://www.howtogeek.com/feed/category/android/"
    "https://www.howtogeek.com/feed/category/iphone-ipad/"
    "https://www.howtogeek.com/feed/category/security/"
    "https://www.howtogeek.com/feed/category/privacy/"
    "https://www.howtogeek.com/feed/category/how-to/"
    "https://www.howtogeek.com/feed/category/hardware/"
    "https://www.howtogeek.com/feed/category/internet/"
    "https://www.howtogeek.com/feed/category/gaming/"
    https://www.howtogeek.com/feed/

    # Desktop / OS
    https://www.howtogeek.com/feed/category/desktop/
    https://www.howtogeek.com/feed/category/windows/
    https://www.howtogeek.com/feed/category/mac/
    https://www.howtogeek.com/feed/category/linux/
    https://www.howtogeek.com/feed/category/chromeos/

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
    https://www.howtogeek.com/feed/category/audio/
    https://www.howtogeek.com/feed/category/streaming/
    https://www.howtogeek.com/feed/category/video-games/

    # Mobile / Ecosystem
    https://www.howtogeek.com/feed/category/cellular/
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
