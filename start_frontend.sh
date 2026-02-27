#!/bin/bash
# Start GenXSOP Frontend Dev Server
cd "$(dirname "$0")/frontend"
echo "Starting GenXSOP Frontend on http://localhost:5173 ..."
npm run dev
