#!/bin/bash

# Budget Famille v2.3 - Comprehensive Cache Debugging Script
# This script performs thorough cache clearing and validation

set -e

echo "🔍 Budget Famille v2.3 - Cache Debugging Script"
echo "=============================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Check for multiple versions of critical files
echo -e "\n${BLUE}Step 1: Checking for multiple versions of month.ts${NC}"
find . -name "month.ts" -type f 2>/dev/null | while read file; do
    echo "Found: $file"
    echo "Size: $(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || echo "unknown") bytes"
    echo "Modified: $(stat -c%y "$file" 2>/dev/null || stat -f%Sm "$file" 2>/dev/null || echo "unknown")"
    echo "MD5: $(md5sum "$file" 2>/dev/null || md5 "$file" 2>/dev/null || echo "checksum unavailable")"
    echo "---"
done

# Step 2: Stop any running dev server
echo -e "\n${BLUE}Step 2: Stopping any running development servers${NC}"
pkill -f "next dev" 2>/dev/null || echo "No Next.js dev server running"
pkill -f "npm run dev" 2>/dev/null || echo "No npm dev server running"
sleep 2

# Step 3: Clear all Next.js caches
echo -e "\n${BLUE}Step 3: Clearing Next.js build cache${NC}"
if [ -d ".next" ]; then
    echo "Removing .next directory..."
    rm -rf .next
    echo "✅ .next directory removed"
else
    echo "ℹ️  .next directory not found"
fi

# Step 4: Clear node_modules cache
echo -e "\n${BLUE}Step 4: Clearing node_modules cache${NC}"
if [ -d "node_modules/.cache" ]; then
    echo "Removing node_modules/.cache..."
    rm -rf node_modules/.cache
    echo "✅ node_modules/.cache removed"
else
    echo "ℹ️  node_modules/.cache not found"
fi

# Step 5: Clear npm cache
echo -e "\n${BLUE}Step 5: Clearing npm cache${NC}"
npm cache clean --force 2>/dev/null || echo "⚠️  npm cache clean failed or not needed"

# Step 6: Clear TypeScript build info
echo -e "\n${BLUE}Step 6: Clearing TypeScript build cache${NC}"
find . -name "*.tsbuildinfo" -delete 2>/dev/null && echo "✅ TypeScript build info files removed" || echo "ℹ️  No TypeScript build info files found"

# Step 7: Clear webpack cache if it exists
echo -e "\n${BLUE}Step 7: Clearing webpack cache${NC}"
if [ -d ".next/cache/webpack" ]; then
    rm -rf .next/cache/webpack
    echo "✅ Webpack cache cleared"
else
    echo "ℹ️  No webpack cache found"
fi

# Step 8: Verify critical file contents
echo -e "\n${BLUE}Step 8: Verifying month.ts contents${NC}"
if [ -f "lib/month.ts" ]; then
    echo "Current month.ts file content (first 10 lines):"
    head -10 lib/month.ts
    echo "---"
    echo "File size: $(wc -c < lib/month.ts) bytes"
    echo "Lines: $(wc -l < lib/month.ts)"
else
    echo -e "${RED}❌ lib/month.ts not found!${NC}"
    exit 1
fi

# Step 9: Check for any cached compiled versions
echo -e "\n${BLUE}Step 9: Checking for cached compiled versions${NC}"
find . -path "./node_modules" -prune -o -name "*.js.map" -print 2>/dev/null | grep -v node_modules | head -5
find . -path "./node_modules" -prune -o -name "month.js" -print 2>/dev/null | grep -v node_modules

# Step 10: Install fresh dependencies
echo -e "\n${BLUE}Step 10: Ensuring fresh dependencies${NC}"
if [ -f "package-lock.json" ]; then
    echo "Reinstalling dependencies..."
    npm ci --silent
    echo "✅ Dependencies reinstalled"
else
    echo "Installing dependencies..."
    npm install --silent
    echo "✅ Dependencies installed"
fi

# Step 11: Start dev server with cache busting
echo -e "\n${BLUE}Step 11: Starting development server${NC}"
echo "Starting Next.js dev server..."
npm run dev &
DEV_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 5

# Step 12: Validation checks
echo -e "\n${BLUE}Step 12: Validation checks${NC}"
echo "🔍 Checking if server is responding..."
if curl -s http://localhost:45678 > /dev/null; then
    echo -e "${GREEN}✅ Server is responding${NC}"
else
    echo -e "${YELLOW}⚠️  Server not yet ready, waiting...${NC}"
    sleep 3
    if curl -s http://localhost:45678 > /dev/null; then
        echo -e "${GREEN}✅ Server is now responding${NC}"
    else
        echo -e "${RED}❌ Server failed to start properly${NC}"
    fi
fi

# Step 13: Generate cache validation report
echo -e "\n${BLUE}Step 13: Cache Validation Report${NC}"
echo "================================"
echo "Timestamp: $(date)"
echo "Next.js version: $(npm list next --depth=0 2>/dev/null | grep next || echo 'Unknown')"
echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

# Check if .next was recreated
if [ -d ".next" ]; then
    echo -e "${GREEN}✅ .next directory recreated${NC}"
    echo "Build timestamp: $(stat -c%y .next 2>/dev/null || stat -f%Sm .next 2>/dev/null || echo 'Unknown')"
else
    echo -e "${RED}❌ .next directory not recreated${NC}"
fi

# Final recommendations
echo -e "\n${YELLOW}📋 Browser Cache Clearing Instructions:${NC}"
echo "1. Open Chrome/Firefox Developer Tools (F12)"
echo "2. Right-click on refresh button and select 'Empty Cache and Hard Reload'"
echo "3. Or use Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)"
echo "4. For complete clearing: DevTools > Application > Storage > Clear Storage > Clear site data"

echo -e "\n${YELLOW}🔍 Additional Debugging Steps:${NC}"
echo "1. Check Network tab in DevTools for 304 (cached) vs 200 (fresh) responses"
echo "2. Look for any webpack HMR (Hot Module Reload) errors in console"
echo "3. Verify the month.ts file timestamp in Sources tab matches file system"
echo "4. Check if useEffect errors still appear in console"

echo -e "\n${GREEN}🎯 Cache clearing complete! Server PID: $DEV_PID${NC}"
echo -e "${YELLOW}To stop server: kill $DEV_PID${NC}"

# Create a file with validation commands for manual testing
cat > cache-validation-commands.txt << EOF
# Manual Validation Commands
# Run these in browser console to verify the fix:

# 1. Check if month.ts is loaded fresh (should show current timestamp)
console.log('month.ts loaded at:', new Date().toISOString());

# 2. Verify useGlobalMonth function is working
import('../lib/month').then(m => console.log('month.ts exports:', Object.keys(m)));

# 3. Check React DevTools for component updates
# Look for MonthPicker component and verify it's using the latest code

# 4. Network tab validation
# - Look for lib/month.ts or _next/static/chunks containing month code
# - Ensure responses show 200 (not 304 cached)
# - Check Response Headers for cache-control settings

# 5. Application tab validation
# - Clear all storage if persistent issues remain
# - Check for any stored state that might interfere
EOF

echo -e "\n${BLUE}📝 Created cache-validation-commands.txt for manual browser testing${NC}"

exit 0