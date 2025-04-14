#!/usr/bin/env python
"""Test the static directory path."""

import os
import sys

def main():
    """Main entry point."""
    # Get current working directory
    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")
    
    # Check if static directory exists
    static_dir = "arbitrage_bot/dashboard/frontend/static"
    static_dir_abs = os.path.abspath(static_dir)
    print(f"Static directory (relative): {static_dir}")
    print(f"Static directory (absolute): {static_dir_abs}")
    print(f"Static directory exists: {os.path.exists(static_dir_abs)}")
    
    # List files in static directory
    if os.path.exists(static_dir_abs):
        print("\nFiles in static directory:")
        for root, dirs, files in os.walk(static_dir_abs):
            for file in files:
                print(f"  {os.path.join(root, file)}")
    
    # Check if index.html exists
    index_html = os.path.join(static_dir_abs, "index.html")
    print(f"\nindex.html exists: {os.path.exists(index_html)}")
    
    # Check if CSS directory exists
    css_dir = os.path.join(static_dir_abs, "css")
    print(f"CSS directory exists: {os.path.exists(css_dir)}")
    
    # Check if styles.css exists
    styles_css = os.path.join(css_dir, "styles.css")
    print(f"styles.css exists: {os.path.exists(styles_css)}")
    
    # Check if bootstrap.min.css exists
    bootstrap_css = os.path.join(css_dir, "bootstrap.min.css")
    print(f"bootstrap.min.css exists: {os.path.exists(bootstrap_css)}")
    
    # Check if JS directory exists
    js_dir = os.path.join(static_dir_abs, "js")
    print(f"JS directory exists: {os.path.exists(js_dir)}")
    
    # Check if app.js exists
    app_js = os.path.join(js_dir, "app.js")
    print(f"app.js exists: {os.path.exists(app_js)}")
    
    # Check if img directory exists
    img_dir = os.path.join(static_dir_abs, "img")
    print(f"img directory exists: {os.path.exists(img_dir)}")
    
    # Check if favicon.ico exists
    favicon = os.path.join(img_dir, "favicon.ico")
    print(f"favicon.ico exists: {os.path.exists(favicon)}")

if __name__ == "__main__":
    main()
