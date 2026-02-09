"""
Tests for cases app
"""
from django.test import TestCase
from django.contrib.auth.models import User

from .models import Case, CaseStatus, StakesLevel
from .services import CaseService
from apps.events.models import Event, EventType


class CaseServiceTest(TestCase):
    """Test CaseService"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_create_case(self):
        """Test creating a case"""
        case = CaseService.create_case(
            user=self.user,
            title='Test Case',
            position='This is my position',
            stakes=StakesLevel.HIGH,
        )
        
        self.assertIsNotNone(case.id)
        self.assertEqual(case.title, 'Test Case')
        self.assertEqual(case.position, 'This is my position')
        self.assertEqual(case.stakes, StakesLevel.HIGH)
        self.assertEqual(case.status, CaseStatus.DRAFT)
        
        # Check event was created
        event = Event.objects.get(id=case.created_from_event_id)
        self.assertEqual(event.type, EventType.CASE_CREATED)
    
    def test_update_case(self):
        """Test updating a case"""
        case = CaseService.create_case(
            user=self.user,
            title='Test Case',
        )
        
        updated = CaseService.update_case(
            case_id=case.id,
            user=self.user,
            position='Updated position',
            user_confidence=80,
        )

        self.assertEqual(updated.position, 'Updated position')
        self.assertEqual(updated.user_confidence, 80)
        
        # Check patch event was created
        patch_event = Event.objects.filter(
            type=EventType.CASE_PATCHED,
            case_id=case.id
        ).first()
        
        self.assertIsNotNone(patch_event)
        self.assertIn('position', patch_event.payload['changes'])
    
