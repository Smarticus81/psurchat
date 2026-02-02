"""
Setup and Installation Script
Multi-Agent PSUR System
"""

import subprocess
import sys
import os


def run_command(cmd, description):
    """Run a command and print status"""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")
    try:
        subprocess.run(cmd, check=True, shell=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False


def main():
    """Main setup process"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗                                                
    ║   Multi-Agent PSUR System - Setup & Installation            ║
    ║   MCP-Powered Autonomous Regulatory Document Generator      ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Check Python version
    print(f"\n🐍 Python version: {sys.version}")
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ required. Please upgrade Python.")
        return False
    
    print("✅ Python version OK")
    
    # Step 1: Create virtual environment (optional but recommended)
    create_venv = input("\n📦 Create virtual environment? (recommended) [Y/n]: ").strip().lower()
    if create_venv != 'n':
        if not run_command("python -m venv venv", "Creating virtual environment"):
            return False
        
        activate_script = "venv\\Scripts\\activate" if os.name == 'nt' else "source venv/bin/activate"
        print(f"\n💡 To activate: {activate_script}")
    
    # Step 2: Install Python dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Step 3: Setup environment variables
    print(f"\n{'='*60}")
    print("🔑 Environment Configuration")
    print(f"{'='*60}")
    
    if not os.path.exists(".env"):
        print("\n📝 Creating .env file from template...")
        subprocess.run("copy .env.example .env" if os.name == 'nt' else "cp .env.example .env", shell=True)
        print("\n⚠️  IMPORTANT: Edit .env file and add your API keys:")
        print("   - OPENAI_API_KEY")
        print("   - ANTHROPIC_API_KEY")
        print("   - GOOGLE_API_KEY")
        print("   - PERPLEXITY_API_KEY")
        print("   - WOLFRAM_API_KEY")
        input("\nPress Enter after you've added your API keys...")
    else:
        print("✅ .env file already exists")
    
    # Step 4: Database setup instructions
    print(f"\n{'='*60}")
    print("💾 Database Setup")
    print(f"{'='*60}")
    print("\nPostgreSQL setup required:")
    print("1. Install PostgreSQL 14+")
    print("2. Create database: createdb psur_system")
    print("3. Update DATABASE_URL in .env if needed")
    print("\nDefault: postgresql://postgres:postgres@localhost:5432/psur_system")
    
    setup_db = input("\nRun database initialization? [Y/n]: ").strip().lower()
    if setup_db != 'n':
        if not run_command("python -c \"from backend.database.session import init_db; init_db()\"", 
                          "Initializing database"):
            print("\n⚠️  Database initialization failed. Make sure PostgreSQL is running.")
    
    # Step 5: Redis setup instructions
    print(f"\n{'='*60}")
    print("🔴 Redis Setup")
    print(f"{'='*60}")
    print("\nRedis setup required for agent communication:")
    print("- Windows: Download from https://github.com/microsoftarchive/redis/releases")
    print("- Linux/Mac: sudo apt-get install redis-server")
    print("\nDefault: redis://localhost:6379/0")
    
    # Final instructions
    print(f"\n{'='*60}")
    print("🎉 Setup Complete!")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("1. ✅ Verify API keys in .env")
    print("2. ✅ Start PostgreSQL")
    print("3. ✅ Start Redis")
    print("4. 🚀 Run: python backend/main.py")
    print("\nThe backend will start on http://localhost:8000")
    print("Visit http://localhost:8000 for health check")
    print(f"\n{'='*60}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
