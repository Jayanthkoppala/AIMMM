#!/usr/bin/env python3
"""
Environment Variable Validation Script
Validates that all required environment variables are set before starting the application.
This ensures Railway deployments fail fast with clear error messages if variables are missing.
"""
import os
import sys

# Required environment variables
REQUIRED_VARS = [
    "DATABASE_URL",
    "OPENROUTER_API_KEY",
]

# Recommended but optional
RECOMMENDED_VARS = [
    "CORS_ORIGINS",
]

def validate_environment():
    """Validate environment variables and exit with error if required ones are missing."""
    missing_required = []
    missing_recommended = []
    
    # Check required variables
    for var in REQUIRED_VARS:
        value = os.getenv(var, "").strip()
        if not value:
            missing_required.append(var)
    
    # Check recommended variables
    for var in RECOMMENDED_VARS:
        value = os.getenv(var, "").strip()
        if not value:
            missing_recommended.append(var)
    
    # Print status
    print("=" * 60)
    print("Environment Variable Validation")
    print("=" * 60)
    
    if missing_required:
        print("\n❌ CRITICAL ERROR: Missing required environment variables:")
        for var in missing_required:
            print(f"   - {var}")
        
        print("\n📋 How to fix:")
        print("   1. Go to Railway dashboard: https://railway.app")
        print("   2. Select your project and service")
        print("   3. Go to 'Variables' tab")
        print("   4. Click 'New Variable'")
        print("   5. Add each missing variable:")
        for var in missing_required:
            print(f"      - Name: {var}")
            print(f"        Value: [your value]")
        print("   6. Save and redeploy")
        print("\n💡 Tip: Make sure you're adding variables to the correct service!")
        print("=" * 60)
        sys.exit(1)
    
    # Show loaded variables (masked)
    print("\n✅ Required environment variables:")
    for var in REQUIRED_VARS:
        value = os.getenv(var, "")
        if var == "DATABASE_URL":
            # Show only hostname
            try:
                from urllib.parse import urlparse
                parsed = urlparse(value)
                print(f"   ✓ {var} = postgresql://***@{parsed.hostname}:{parsed.port or 5432}/...")
            except:
                print(f"   ✓ {var} = [SET]")
        elif "API_KEY" in var or "SECRET" in var or "PASSWORD" in var:
            # Mask API keys
            masked = "***" + value[-4:] if len(value) > 4 else "***"
            print(f"   ✓ {var} = {masked}")
        else:
            print(f"   ✓ {var} = [SET]")
    
    if missing_recommended:
        print("\n⚠️  Warning: Missing recommended variables:")
        for var in missing_recommended:
            print(f"   - {var}")
        print("   (Application may not work correctly without these)")
    else:
        print("\n✅ Recommended environment variables:")
        for var in RECOMMENDED_VARS:
            value = os.getenv(var, "")
            if var == "CORS_ORIGINS":
                origins = [o.strip() for o in value.split(",") if o.strip()] if value else []
                print(f"   ✓ {var} = {len(origins)} origin(s) configured")
            else:
                print(f"   ✓ {var} = [SET]")
    
    print("\n" + "=" * 60)
    print("✅ All required environment variables are set!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    validate_environment()

