#!/bin/bash
#
# Automated installation script for KlikAanKlikUit device naming fix
# Run this from your Home Assistant config directory
#

echo "============================================================"
echo "KlikAanKlikUit Device Naming Fix - Auto Installer"
echo "============================================================"
echo ""

# Check if we're in the right place
if [ ! -d "custom_components/kaku_ics2000" ]; then
    echo "❌ Error: custom_components/kaku_ics2000 directory not found!"
    echo "   Please run this script from your Home Assistant config directory."
    echo "   Usually: /config or /home/homeassistant/.homeassistant"
    exit 1
fi

echo "✅ Found KlikAanKlikUit integration"
echo ""

# Create backup
echo "📦 Creating backup of current hub.py..."
if [ -f "custom_components/kaku_ics2000/hub.py" ]; then
    cp custom_components/kaku_ics2000/hub.py custom_components/kaku_ics2000/hub_backup_$(date +%Y%m%d_%H%M%S).py
    echo "   Backup created with timestamp"
else
    echo "   ⚠️  No existing hub.py found - this might be a fresh installation"
fi

echo ""
echo "📝 Applying the fix..."
echo ""

# Download the fixed hub.py (you'll need to host this or use the one generated above)
echo "Please copy the hub_fixed.py file to:"
echo "  custom_components/kaku_ics2000/hub.py"
echo ""
echo "After copying the file:"
echo ""
echo "🔄 Next steps:"
echo "   1. Restart Home Assistant"
echo "   2. Go to Settings → Devices & Services"
echo "   3. Find 'KlikAanKlikUit ICS-2000'"
echo "   4. Click the 3 dots menu → Reload"
echo ""
echo "   OR (for a clean start):"
echo ""
echo "   1. Delete the integration"
echo "   2. Restart Home Assistant" 
echo "   3. Re-add the integration with your credentials"
echo ""
echo "Your devices should now show with proper names! 🎉"
