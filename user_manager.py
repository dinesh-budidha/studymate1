"""User manager for handling user sessions and data management."""

import uuid
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import hashlib
from datetime import datetime, timedelta
from config import USER_DATA_DIR, FAISS_INDEX_DIR


class UserManager:
    """Manages user sessions and data for StudyMate."""
    
    def __init__(self):
        self.users_file = USER_DATA_DIR / "users.json"
        self.sessions_file = USER_DATA_DIR / "sessions.json"
        
        # Load existing data
        self.users = self._load_users()
        self.sessions = self._load_sessions()
        
        # Clean up old sessions
        self._cleanup_old_sessions()
    
    def create_user_session(self, identifier: Optional[str] = None) -> str:
        """
        Create a new user session.
        
        Args:
            identifier: Optional user identifier (email, username, etc.)
        
        Returns:
            User session ID
        """
        # Generate unique user ID
        if identifier:
            # Create deterministic ID based on identifier
            user_id = hashlib.md5(identifier.encode()).hexdigest()[:16]
        else:
            # Generate random ID for anonymous users
            user_id = str(uuid.uuid4())[:16]
        
        # Create session
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "identifier": identifier,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Store session
        self.sessions[session_id] = session_data
        
        # Update user data
        if user_id not in self.users:
            self.users[user_id] = {
                "user_id": user_id,
                "identifier": identifier,
                "created_at": datetime.now().isoformat(),
                "sessions": [],
                "total_documents": 0,
                "total_queries": 0
            }
        
        self.users[user_id]["sessions"].append(session_id)
        
        # Save data
        self._save_users()
        self._save_sessions()
        
        return user_id
    
    def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active session for user."""
        # Find most recent active session
        user_sessions = []
        for session_id, session in self.sessions.items():
            if (session.get("user_id") == user_id and 
                session.get("status") == "active"):
                user_sessions.append(session)
        
        if user_sessions:
            # Return most recent session
            return max(user_sessions, key=lambda x: x["last_activity"])
        
        return None
    
    def update_user_activity(self, user_id: str):
        """Update user's last activity timestamp."""
        session = self.get_user_session(user_id)
        if session:
            session["last_activity"] = datetime.now().isoformat()
            self._save_sessions()
        
        if user_id in self.users:
            self.users[user_id]["last_activity"] = datetime.now().isoformat()
            self._save_users()
    
    def increment_user_stats(self, user_id: str, stat_type: str):
        """Increment user statistics."""
        if user_id in self.users:
            if stat_type == "documents":
                self.users[user_id]["total_documents"] += 1
            elif stat_type == "queries":
                self.users[user_id]["total_queries"] += 1
            
            self._save_users()
    
    def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data and statistics."""
        if user_id not in self.users:
            return None
        
        user_data = self.users[user_id].copy()
        
        # Add current session info
        current_session = self.get_user_session(user_id)
        user_data["current_session"] = current_session
        
        # Add data directory stats
        user_dir = FAISS_INDEX_DIR / f"user_{user_id}"
        if user_dir.exists():
            try:
                total_size = sum(f.stat().st_size for f in user_dir.rglob('*') if f.is_file())
                user_data["data_size_mb"] = total_size / (1024 * 1024)
                user_data["data_files"] = len(list(user_dir.rglob('*')))
            except:
                user_data["data_size_mb"] = 0
                user_data["data_files"] = 0
        else:
            user_data["data_size_mb"] = 0
            user_data["data_files"] = 0
        
        return user_data
    
    def delete_user_data(self, user_id: str, confirm_deletion: bool = False) -> Dict[str, Any]:
        """
        Delete all user data including FAISS indexes and sessions.
        
        Args:
            user_id: User ID to delete
            confirm_deletion: Safety flag to confirm deletion
        
        Returns:
            Result dictionary
        """
        if not confirm_deletion:
            return {
                "success": False,
                "error": "Deletion not confirmed. Set confirm_deletion=True"
            }
        
        try:
            deleted_items = []
            
            # Delete FAISS index directory
            user_dir = FAISS_INDEX_DIR / f"user_{user_id}"
            if user_dir.exists():
                import shutil
                shutil.rmtree(user_dir)
                deleted_items.append("FAISS index")
            
            # Delete user sessions
            user_sessions = [
                sid for sid, session in self.sessions.items()
                if session.get("user_id") == user_id
            ]
            
            for session_id in user_sessions:
                del self.sessions[session_id]
                deleted_items.append(f"Session {session_id}")
            
            # Delete user record
            if user_id in self.users:
                del self.users[user_id]
                deleted_items.append("User record")
            
            # Save updated data
            self._save_users()
            self._save_sessions()
            
            return {
                "success": True,
                "deleted_items": deleted_items,
                "message": f"Successfully deleted all data for user {user_id}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error deleting user data: {str(e)}"
            }
    
    def list_all_users(self) -> List[Dict[str, Any]]:
        """Get list of all users with basic info."""
        user_list = []
        
        for user_id, user_data in self.users.items():
            user_info = {
                "user_id": user_id,
                "identifier": user_data.get("identifier", "Anonymous"),
                "created_at": user_data.get("created_at"),
                "total_documents": user_data.get("total_documents", 0),
                "total_queries": user_data.get("total_queries", 0),
                "active_sessions": len([
                    s for s in self.sessions.values()
                    if s.get("user_id") == user_id and s.get("status") == "active"
                ])
            }
            
            # Add data size
            user_dir = FAISS_INDEX_DIR / f"user_{user_id}"
            if user_dir.exists():
                try:
                    total_size = sum(f.stat().st_size for f in user_dir.rglob('*') if f.is_file())
                    user_info["data_size_mb"] = round(total_size / (1024 * 1024), 2)
                except:
                    user_info["data_size_mb"] = 0
            else:
                user_info["data_size_mb"] = 0
            
            user_list.append(user_info)
        
        return sorted(user_list, key=lambda x: x["created_at"], reverse=True)
    
    def cleanup_inactive_users(self, days_inactive: int = 30) -> Dict[str, Any]:
        """Clean up users inactive for specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_inactive)
        inactive_users = []
        
        for user_id, user_data in list(self.users.items()):
            last_activity = user_data.get("last_activity", user_data.get("created_at"))
            if last_activity:
                try:
                    last_activity_date = datetime.fromisoformat(last_activity)
                    if last_activity_date < cutoff_date:
                        inactive_users.append(user_id)
                except:
                    # If date parsing fails, consider as inactive
                    inactive_users.append(user_id)
        
        # Delete inactive users
        deleted_count = 0
        errors = []
        
        for user_id in inactive_users:
            result = self.delete_user_data(user_id, confirm_deletion=True)
            if result["success"]:
                deleted_count += 1
            else:
                errors.append(f"User {user_id}: {result['error']}")
        
        return {
            "total_inactive": len(inactive_users),
            "deleted_count": deleted_count,
            "errors": errors,
            "cutoff_date": cutoff_date.isoformat()
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        active_sessions = sum(1 for s in self.sessions.values() if s.get("status") == "active")
        
        # Calculate total data size
        total_data_size = 0
        try:
            for user_dir in FAISS_INDEX_DIR.glob("user_*"):
                if user_dir.is_dir():
                    total_size = sum(f.stat().st_size for f in user_dir.rglob('*') if f.is_file())
                    total_data_size += total_size
        except:
            total_data_size = 0
        
        return {
            "total_users": len(self.users),
            "active_sessions": active_sessions,
            "total_sessions": len(self.sessions),
            "total_data_size_mb": round(total_data_size / (1024 * 1024), 2),
            "avg_documents_per_user": sum(u.get("total_documents", 0) for u in self.users.values()) / max(len(self.users), 1),
            "avg_queries_per_user": sum(u.get("total_queries", 0) for u in self.users.values()) / max(len(self.users), 1)
        }
    
    def _load_users(self) -> Dict[str, Any]:
        """Load users from file."""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading users file: {e}")
        return {}
    
    def _load_sessions(self) -> Dict[str, Any]:
        """Load sessions from file."""
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading sessions file: {e}")
        return {}
    
    def _save_users(self):
        """Save users to file."""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
        except Exception as e:
            print(f"Error saving users file: {e}")
    
    def _save_sessions(self):
        """Save sessions to file."""
        try:
            with open(self.sessions_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            print(f"Error saving sessions file: {e}")
    
    def _cleanup_old_sessions(self, max_age_days: int = 7):
        """Clean up sessions older than max_age_days."""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        old_sessions = []
        
        for session_id, session in list(self.sessions.items()):
            try:
                last_activity = datetime.fromisoformat(session.get("last_activity", session.get("created_at")))
                if last_activity < cutoff_date:
                    old_sessions.append(session_id)
            except:
                # Remove sessions with invalid dates
                old_sessions.append(session_id)
        
        # Remove old sessions
        for session_id in old_sessions:
            del self.sessions[session_id]
        
        if old_sessions:
            print(f"Cleaned up {len(old_sessions)} old sessions")
            self._save_sessions()