"""
Permissions for multi-level skill access
"""
from rest_framework import permissions


class SkillPermission(permissions.BasePermission):
    """
    Permission class for multi-level skill access
    
    Rules:
    - Personal skills: Only owner can view/edit
    - Team skills: Team members can view, owner + can_edit can edit
    - Org skills: Org members can view, owner + can_edit can edit
    - Public skills: Anyone can view, only owner + can_edit can edit
    """
    
    def has_permission(self, request, view):
        """Check if user can access skill list"""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access specific skill"""
        user = request.user
        
        # Read permissions (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            if obj.scope == 'personal':
                # Personal skills: Only owner can view
                return obj.owner == user
            
            elif obj.scope == 'team':
                # Team skills: Owner, can_view users, or team members can view
                return (
                    obj.owner == user or
                    user in obj.can_view.all() or
                    (obj.team and obj.team.user == user)
                )
            
            elif obj.scope == 'organization':
                # Org skills: Owner, can_view users, or org members can view
                # TODO: Proper org membership check when user-org relationship exists
                return (
                    obj.owner == user or
                    user in obj.can_view.all() or
                    True  # For now, allow all authenticated users
                )
            
            elif obj.scope == 'public':
                # Public skills: Anyone can view
                return True
        
        # Write permissions (POST, PUT, PATCH, DELETE)
        else:
            # Owner always has write access
            if obj.owner == user:
                return True
            
            # Check can_edit list
            if user in obj.can_edit.all():
                return True
            
            # Otherwise, no write access
            return False


class SkillProposalPermission(permissions.BasePermission):
    """
    Permission class for skill proposals (future feature)
    
    Anyone who can view a skill can propose changes.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user can propose changes"""
        # For proposals, use read permission from SkillPermission
        # (If you can view, you can propose)
        skill_perm = SkillPermission()
        
        # Check using SAFE_METHODS logic (view permission)
        class MockRequest:
            method = 'GET'
            user = request.user
        
        mock_request = MockRequest()
        return skill_perm.has_object_permission(mock_request, view, obj)
