#!/usr/bin/env python3
"""
Create a verified test user for development and testing.
This script creates a user with email verification already completed.
"""

import asyncio
import sys
import uuid
from datetime import datetime, timezone

# Add parent directory to path to import app modules
sys.path.insert(0, '/app')

from sqlalchemy import select
from app.database import async_session_maker
from app.models.user import User
from app.models.workspace import Workspace, WorkspacePlan, WorkspaceMember, WorkspaceRole
from app.utils.auth import hash_password


async def create_test_user(
    email: str = "test@example.com",
    password: str = "Test123!",
    name: str = "Test User"
):
    """Create a verified test user with a default workspace."""

    async with async_session_maker() as db:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"⚠️  User with email '{email}' already exists.")

            # Ask if they want to delete and recreate
            response = input("   Delete and recreate? (y/N): ").strip().lower()
            if response != 'y':
                print("   Keeping existing user.")
                print(f"\n✅ Login credentials:")
                print(f"   Email:    {email}")
                print(f"   Password: {password}")
                return

            # Delete existing user and their workspace
            # First, get their workspaces
            workspace_result = await db.execute(
                select(Workspace).where(Workspace.owner_id == existing_user.id)
            )
            workspaces = workspace_result.scalars().all()

            # Delete workspace members
            for workspace in workspaces:
                member_result = await db.execute(
                    select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)
                )
                members = member_result.scalars().all()
                for member in members:
                    await db.delete(member)

            # Delete workspaces
            for workspace in workspaces:
                await db.delete(workspace)

            # Delete user
            await db.delete(existing_user)
            await db.commit()
            print("   Deleted existing user and workspace.")

        # Create new user
        user = User(
            email=email,
            password_hash=hash_password(password),
            name=name,
            email_verified=True,  # Skip OTP verification
            roles=["user"],
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        print(f"✅ Created user: {name} ({email})")

        # Create default workspace
        workspace_name = f"{name}'s Workspace"
        workspace_slug = f"{name.lower().replace(' ', '-')}-{str(user.id)[:8]}"

        workspace = Workspace(
            name=workspace_name,
            slug=workspace_slug,
            owner_id=user.id,
            plan=WorkspacePlan.STARTER,
        )
        db.add(workspace)
        await db.flush()
        await db.refresh(workspace)

        print(f"✅ Created workspace: {workspace_name}")

        # Add user as workspace owner
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=WorkspaceRole.OWNER,
            invited_at=datetime.now(timezone.utc),
            joined_at=datetime.now(timezone.utc),
        )
        db.add(member)

        await db.commit()

        print(f"\n{'='*50}")
        print("✨ Test user created successfully!")
        print(f"{'='*50}")
        print(f"\n🔐 Login credentials:")
        print(f"   Email:    {email}")
        print(f"   Password: {password}")
        print(f"\n🏢 Workspace:")
        print(f"   Name: {workspace_name}")
        print(f"   Plan: {WorkspacePlan.STARTER.value}")
        print(f"\n🌐 Login at: http://localhost:3000/login")
        print("")


async def create_admin_user():
    """Create an admin user."""
    await create_test_user(
        email="admin@example.com",
        password="Admin123!",
        name="Admin User"
    )

    async with async_session_maker() as db:
        result = await db.execute(
            select(User).where(User.email == "admin@example.com")
        )
        admin_user = result.scalar_one_or_none()

        if admin_user:
            admin_user.roles = ["user", "admin"]
            await db.commit()
            print("✅ Added admin role to user")


async def main():
    """Main entry point."""
    print("\n🔧 MRRPulse Test User Creator")
    print("="*50)
    print("")

    if len(sys.argv) > 1:
        if sys.argv[1] == "--admin":
            await create_admin_user()
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python create_test_user.py           # Create default test user")
            print("  python create_test_user.py --admin   # Create admin user")
            print("  python create_test_user.py --help    # Show this help")
        else:
            print("Invalid argument. Use --help for usage.")
    else:
        await create_test_user()


if __name__ == "__main__":
    asyncio.run(main())
