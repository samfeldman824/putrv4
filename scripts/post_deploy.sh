#!/bin/bash
# Post-deployment script to import player data from backup

set -e  # Exit on error

echo "🚀 Running post-deployment tasks..."

# Check if this is the first deployment or if we should reimport
if [ "$FORCE_IMPORT" = "true" ] || [ ! -f /opt/render/project/.import_done ]; then
    echo "📊 Importing player data from full_backup.json..."
    python -m src.import_csv
    
    # Mark import as done
    touch /opt/render/project/.import_done
    echo "✅ Import completed successfully"
else
    echo "⏭️  Skipping import (already done). Set FORCE_IMPORT=true to reimport."
fi

echo "✨ Post-deployment tasks completed!"
