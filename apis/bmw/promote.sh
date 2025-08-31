#!/bin/bash

# BMW API Staging to Production Promotion Script
# This script promotes the staging version to production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}BMW API Staging → Production Promotion${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if staging file exists
if [ ! -f "src/staging/main_staging.py" ]; then
    echo -e "${RED}Error: Staging file not found at src/staging/main_staging.py${NC}"
    exit 1
fi

# Show current versions
echo -e "\n${GREEN}Current Status:${NC}"
echo -e "Staging file: src/staging/main_staging.py"
echo -e "Production file: src/main_stateless.py"

# Get staging version info
if [ -f ".staging-version" ]; then
    echo -e "\n${GREEN}Staging Version Info:${NC}"
    tail -1 .staging-version
fi

# Confirm promotion
echo -e "\n${YELLOW}⚠️  WARNING: This will replace production with staging!${NC}"
echo -n "Are you sure you want to promote staging to production? (yes/no): "
read -r confirmation

if [ "$confirmation" != "yes" ]; then
    echo -e "${RED}Promotion cancelled${NC}"
    exit 0
fi

# Create backup
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo -e "\n${GREEN}Creating backup...${NC}"
cp src/main_stateless.py "$BACKUP_DIR/main_stateless.py.backup"
echo -e "Backup saved to: $BACKUP_DIR/main_stateless.py.backup"

# Promote staging to production
echo -e "\n${GREEN}Promoting staging to production...${NC}"
cp src/staging/main_staging.py src/main_stateless.py

# Add promotion marker
cat >> src/main_stateless.py << EOF

# PROMOTED FROM STAGING: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# Promoted using promote.sh script
EOF

echo -e "${GREEN}✅ Staging promoted to production!${NC}"

# Update staging version file
echo "$(date +%Y%m%d.%H%M%S)|promoted|$(date -u +"%Y-%m-%d %H:%M:%S")|Promoted to production" >> .staging-version

echo -e "\n${GREEN}Next Steps:${NC}"
echo "1. Review the changes: git diff src/main_stateless.py"
echo "2. Commit the changes: git add -A && git commit -m 'Promote staging to production'"
echo "3. Push to trigger deployment: git push origin main"
echo ""
echo "Or use GitHub Actions:"
echo "gh workflow run promote-to-prod.yml"

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Promotion Complete!${NC}"
echo -e "${BLUE}========================================${NC}"