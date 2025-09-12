#!/bin/bash

echo "🚀 Deploying Stacks functionality to Quest API"
echo "=============================================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the quest-api directory"
    exit 1
fi

# Check if git is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Warning: You have uncommitted changes"
    echo "   Consider committing your changes first:"
    echo "   git add ."
    echo "   git commit -m 'Add stacks functionality'"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelled"
        exit 1
    fi
fi

# Add and commit changes
echo "📝 Committing changes..."
git add .
git commit -m "Add stacks functionality

- Add Pydantic models for stacks and stack items
- Add comprehensive stacks router with CRUD operations
- Add database migration for stacks tables
- Register stacks router in main.py
- Support for creating, reading, updating, deleting stacks
- Support for adding/removing items from stacks
- Full authentication and authorization
- Row Level Security (RLS) policies"

# Push to origin
echo "📤 Pushing to origin..."
git push origin main

echo ""
echo "✅ Code pushed to repository!"
echo ""
echo "📋 Next steps:"
echo "1. The deployment should start automatically on Render"
echo "2. Run the database migration:"
echo "   - Connect to your Supabase database"
echo "   - Execute the SQL in: database/migrations/create_stacks_tables.sql"
echo "3. Test the endpoints once deployed"
echo ""
echo "🔗 Monitor deployment at: https://dashboard.render.com"
echo "📚 API docs will be available at: https://quest-api-edz1.onrender.com/docs"


