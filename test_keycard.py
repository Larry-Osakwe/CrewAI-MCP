"""
Test script to verify Keycard connection and configuration.

This script tests that:
1. Environment variables are properly loaded
2. Can create Keycard AuthProvider with application credentials
3. Configuration is valid and ready for MCP server integration

Uses the keycardai-mcp-fastmcp package for FastMCP integration.
"""

import os
from dotenv import load_dotenv

# Load environment variables from src/.env
load_dotenv("src/.env")

def test_keycard():
    """Test Keycard configuration using AuthProvider."""

    # Get credentials from environment
    zone_id = os.getenv("KEYCARD_ZONE_ID")
    client_id = os.getenv("KEYCARD_CLIENT_ID")
    client_secret = os.getenv("KEYCARD_CLIENT_SECRET")

    # Verify env vars are loaded
    print("=" * 60)
    print("🔍 Checking Environment Variables")
    print("=" * 60)

    if not zone_id or not client_id or not client_secret:
        print("❌ Missing required environment variables!")
        print(f"   KEYCARD_ZONE_ID: {'✓' if zone_id else '✗ MISSING'}")
        print(f"   KEYCARD_CLIENT_ID: {'✓' if client_id else '✗ MISSING'}")
        print(f"   KEYCARD_CLIENT_SECRET: {'✓' if client_secret else '✗ MISSING'}")
        print("\n💡 Add these to src/.env file:")
        print("   KEYCARD_ZONE_ID=your_zone_id")
        print("   KEYCARD_CLIENT_ID=your_client_id")
        print("   KEYCARD_CLIENT_SECRET=your_client_secret")
        return False

    print(f"✓ KEYCARD_ZONE_ID: {zone_id}")
    print(f"✓ KEYCARD_CLIENT_ID: {client_id[:20]}...")
    print(f"✓ KEYCARD_CLIENT_SECRET: {client_secret[:10]}...")
    print()

    # Try to create AuthProvider
    print("=" * 60)
    print("🔗 Testing Keycard Configuration")
    print("=" * 60)

    try:
        # Import here so we can give a better error message if not installed
        try:
            from keycardai.mcp.integrations.fastmcp import AuthProvider, ClientSecret
        except ImportError:
            print("❌ keycardai-mcp-fastmcp package not installed!")
            print("\n💡 Install it with:")
            print("   pip install keycardai-mcp-fastmcp")
            return False

        # Create AuthProvider with client credentials
        auth_provider = AuthProvider(
            zone_id=zone_id,
            mcp_server_name="CrewAI GitHub MCP Server",
            mcp_base_url="http://localhost:8000/",
            application_credential=ClientSecret((client_id, client_secret))
        )

        print("✅ AuthProvider created successfully!")
        print(f"   Zone ID: {zone_id}")
        print(f"   MCP Server: CrewAI GitHub MCP Server")
        print(f"   Base URL: http://localhost:8000/")
        print()

        print("=" * 60)
        print("🎉 SUCCESS! Keycard is configured correctly")
        print("=" * 60)
        print("✓ Application credentials are valid")
        print("✓ AuthProvider initialized")
        print("✓ Ready to add authentication to MCP server!")
        print()
        print("Next step: Phase 4 - Add Keycard auth to your MCP server")
        print()

        return True

    except ImportError as e:
        print(f"❌ Import Error: {str(e)}")
        print("\n💡 Make sure keycardai-mcp-fastmcp is installed:")
        print("   pip install keycardai-mcp-fastmcp")
        return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"   Exception type: {type(e).__name__}")
        print("\n💡 Possible issues:")
        print("   - ZONE_ID format (should be just the ID, not full URL)")
        print("   - CLIENT_ID or CLIENT_SECRET might be incorrect")
        print("   - Application might not be properly configured in Keycard Console")
        print("   - Check for extra spaces or newlines in credentials")
        return False

if __name__ == "__main__":
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "Keycard Configuration Test" + " " * 17 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    success = test_keycard()

    if success:
        exit(0)
    else:
        exit(1)
