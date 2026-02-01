"""
Tests for Skills system
"""
from django.test import TestCase
from django.contrib.auth.models import User
from apps.common.models import Organization
from apps.skills.models import Skill, SkillVersion
from apps.skills.parser import parse_skill_md, validate_skill_md, validate_resource_files
from apps.skills.injection import build_skill_context, format_system_prompt_with_skills
from apps.skills.preview import SkillPreviewService
from apps.skills.conversion import CaseSkillConverter
from apps.skills.permissions import SkillPermission


class SkillParserTestCase(TestCase):
    """Test SKILL.md parser"""
    
    def test_parse_valid_skill_md(self):
        """Test parsing valid SKILL.md with YAML frontmatter"""
        content = """---
name: Test Skill
description: A test skill
domain: testing
episteme:
  applies_to_agents:
    - research
    - critique
---

## Test Skill Content

This is the markdown body.
"""
        result = parse_skill_md(content)
        
        self.assertEqual(result['metadata']['name'], 'Test Skill')
        self.assertEqual(result['metadata']['description'], 'A test skill')
        self.assertEqual(result['metadata']['domain'], 'testing')
        self.assertIn('Test Skill Content', result['body'])
    
    def test_parse_skill_without_frontmatter(self):
        """Test parsing skill without YAML frontmatter"""
        content = "# Just markdown\n\nNo frontmatter here."
        result = parse_skill_md(content)
        
        self.assertEqual(result['metadata'], {})
        self.assertEqual(result['body'], content)
    
    def test_validate_valid_skill(self):
        """Test validation of valid SKILL.md"""
        content = """---
name: Valid Skill
description: This is a valid skill description
---

Content here.
"""
        is_valid, errors = validate_skill_md(content)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_missing_name(self):
        """Test validation fails when name is missing"""
        content = """---
description: Missing name field
---

Content.
"""
        is_valid, errors = validate_skill_md(content)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('name' in e.lower() for e in errors))
    
    def test_validate_missing_description(self):
        """Test validation fails when description is missing"""
        content = """---
name: Test
---

Content.
"""
        is_valid, errors = validate_skill_md(content)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('description' in e.lower() for e in errors))
    
    def test_validate_name_too_long(self):
        """Test validation fails when name exceeds 64 chars"""
        long_name = "x" * 65
        content = f"""---
name: {long_name}
description: Valid description
---

Content.
"""
        is_valid, errors = validate_skill_md(content)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('64' in e for e in errors))
    
    def test_validate_description_too_long(self):
        """Test validation fails when description exceeds 200 chars"""
        long_desc = "x" * 201
        content = f"""---
name: Test
description: {long_desc}
---

Content.
"""
        is_valid, errors = validate_skill_md(content)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('200' in e for e in errors))
    
    def test_validate_invalid_agent_type(self):
        """Test validation fails with invalid agent type"""
        content = """---
name: Test
description: Valid description
episteme:
  applies_to_agents:
    - invalid_agent
---

Content.
"""
        is_valid, errors = validate_skill_md(content)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('invalid_agent' in e for e in errors))
    
    def test_validate_resource_files(self):
        """Test resource file validation"""
        resources = {
            'file1.txt': 'content here',
            'file2.md': 'more content'
        }
        
        is_valid, errors = validate_resource_files(resources)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_resource_files_too_large(self):
        """Test resource validation fails when total size exceeds limit"""
        # Create resource files that exceed 5MB total
        large_content = "x" * (3 * 1024 * 1024)  # 3MB
        resources = {
            'file1.txt': large_content,
            'file2.txt': large_content
        }
        
        is_valid, errors = validate_resource_files(resources)
        self.assertFalse(is_valid)
        self.assertTrue(any('5MB' in e for e in errors))


class SkillInjectionTestCase(TestCase):
    """Test skill context injection"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )
    
    def test_build_skill_context_empty(self):
        """Test building context with no skills"""
        context = build_skill_context([], 'research')
        
        self.assertEqual(context['system_prompt_extension'], '')
        self.assertEqual(context['custom_signal_types'], [])
        self.assertEqual(context['evidence_standards'], {})
        self.assertIsNone(context['artifact_template'])
    
    def test_build_skill_context_single_skill(self):
        """Test building context with single skill"""
        skill = Skill.objects.create(
            organization=self.org,
            name='Test Skill',
            description='A test skill',
            applies_to_agents=['research'],
            created_by=self.user
        )
        
        skill_md = """---
name: Test Skill
description: A test skill
---

## Test Content

This is test content.
"""
        
        SkillVersion.objects.create(
            skill=skill,
            version=1,
            skill_md_content=skill_md,
            created_by=self.user
        )
        
        context = build_skill_context([skill], 'research')
        
        self.assertIn('Test Skill', context['system_prompt_extension'])
        self.assertIn('test content', context['system_prompt_extension'].lower())
    
    def test_build_skill_context_filters_by_agent_type(self):
        """Test that skills are filtered by agent type"""
        skill = Skill.objects.create(
            organization=self.org,
            name='Research Only Skill',
            description='Only for research agent',
            applies_to_agents=['research'],  # Only research
            created_by=self.user
        )
        
        skill_md = """---
name: Research Only Skill
description: Only for research agent
---

Content.
"""
        
        SkillVersion.objects.create(
            skill=skill,
            version=1,
            skill_md_content=skill_md,
            created_by=self.user
        )
        
        # Should include when agent type matches
        context_research = build_skill_context([skill], 'research')
        self.assertIn('Research Only Skill', context_research['system_prompt_extension'])
        
        # Should not include when agent type doesn't match
        context_critique = build_skill_context([skill], 'critique')
        self.assertEqual(context_critique['system_prompt_extension'], '')
    
    def test_build_skill_context_custom_signal_types(self):
        """Test extracting custom signal types from skill config"""
        skill = Skill.objects.create(
            organization=self.org,
            name='Legal Skill',
            description='Legal analysis',
            applies_to_agents=['research'],
            episteme_config={
                'signal_types': [
                    {'name': 'LegalConstraint', 'inherits_from': 'Constraint'},
                    {'name': 'LiabilityRisk', 'inherits_from': 'Risk'}
                ]
            },
            created_by=self.user
        )
        
        skill_md = """---
name: Legal Skill
description: Legal analysis
---

Content.
"""
        
        SkillVersion.objects.create(
            skill=skill,
            version=1,
            skill_md_content=skill_md,
            created_by=self.user
        )
        
        context = build_skill_context([skill], 'research')
        
        self.assertEqual(len(context['custom_signal_types']), 2)
        self.assertEqual(context['custom_signal_types'][0]['name'], 'LegalConstraint')
        self.assertEqual(context['custom_signal_types'][1]['name'], 'LiabilityRisk')
    
    def test_format_system_prompt_with_skills(self):
        """Test formatting system prompt with skill context"""
        base_prompt = "You are a research agent."
        
        skill_context = {
            'system_prompt_extension': "\n## Legal Framework\n\nUse legal reasoning.",
            'custom_signal_types': [
                {'name': 'LegalConstraint', 'description': 'A legal constraint'}
            ],
            'evidence_standards': {
                'preferred_sources': ['Case law', 'Statutes'],
                'minimum_credibility': 0.85
            },
            'artifact_template': None
        }
        
        enhanced = format_system_prompt_with_skills(base_prompt, skill_context)
        
        self.assertIn("You are a research agent.", enhanced)
        self.assertIn("Legal Framework", enhanced)
        self.assertIn("legal reasoning", enhanced.lower())
        self.assertIn("LegalConstraint", enhanced)
        self.assertIn("Case law", enhanced)
        self.assertIn("0.85", enhanced)


class SkillModelTestCase(TestCase):
    """Test Skill model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org'
        )
    
    def test_create_skill(self):
        """Test creating a skill"""
        skill = Skill.objects.create(
            organization=self.org,
            name='Test Skill',
            description='A test skill',
            domain='testing',
            applies_to_agents=['research', 'critique'],
            created_by=self.user
        )
        
        self.assertEqual(skill.name, 'Test Skill')
        self.assertEqual(skill.current_version, 1)
        self.assertEqual(skill.status, 'draft')
    
    def test_create_skill_version(self):
        """Test creating a skill version"""
        skill = Skill.objects.create(
            organization=self.org,
            name='Test Skill',
            description='A test skill',
            created_by=self.user
        )
        
        version = SkillVersion.objects.create(
            skill=skill,
            version=1,
            skill_md_content="# Test\n\nContent",
            created_by=self.user,
            changelog="Initial version"
        )
        
        self.assertEqual(version.version, 1)
        self.assertEqual(version.skill, skill)
    
    def test_skill_unique_name_per_org(self):
        """Test that skill names must be unique within an organization"""
        Skill.objects.create(
            organization=self.org,
            owner=self.user,
            name='Duplicate Name',
            description='First skill',
            scope='organization',
            created_by=self.user
        )
        
        # Should raise IntegrityError when trying to create duplicate with same owner+name+scope
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Skill.objects.create(
                organization=self.org,
                owner=self.user,
                name='Duplicate Name',
                description='Second skill',
                scope='organization',
                created_by=self.user
            )


class CaseSkillConversionTestCase(TestCase):
    """Test case-to-skill and skill-to-case conversion"""
    
    def setUp(self):
        """Set up test data"""
        from apps.cases.models import Case
        from apps.events.models import Event
        from apps.signals.models import Signal
        
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.org = Organization.objects.create(name='Test Org', slug='test-org')
        
        # Create event for provenance
        event = Event.objects.create(
            user=self.user,
            event_type='test_event',
            metadata={}
        )
        
        # Create test case
        self.case = Case.objects.create(
            title='Test FDA Decision',
            position='Evaluate regulatory pathway',
            stakes='high',
            user=self.user,
            created_from_event_id=event.id
        )
        
        # Add some signals
        Signal.objects.create(
            event=event,
            type='Constraint',
            text='Must comply with FDA regulations',
            thread=None,
            case=self.case,
            confidence=0.9
        )
        Signal.objects.create(
            event=event,
            type='Goal',
            text='Achieve 510(k) approval',
            thread=None,
            case=self.case,
            confidence=0.85
        )
    
    def test_case_to_skill_conversion(self):
        """Test converting a case to a skill"""
        skill = CaseSkillConverter.case_to_skill(
            case=self.case,
            skill_name='FDA Approval Framework',
            scope='personal',
            user=self.user
        )
        
        self.assertIsNotNone(skill)
        self.assertEqual(skill.name, 'FDA Approval Framework')
        self.assertEqual(skill.scope, 'personal')
        self.assertEqual(skill.owner, self.user)
        self.assertEqual(skill.source_case, self.case)
        
        # Check case was updated
        self.case.refresh_from_db()
        self.assertTrue(self.case.is_skill_template)
        self.assertEqual(self.case.became_skill, skill)
    
    def test_skill_to_case_spawning(self):
        """Test spawning a new case from a skill"""
        from apps.events.models import Event
        
        # Create a skill first
        skill = Skill.objects.create(
            name='Test Framework',
            description='A test framework',
            scope='personal',
            owner=self.user,
            applies_to_agents=['research'],
            created_by=self.user
        )
        
        SkillVersion.objects.create(
            skill=skill,
            version=1,
            skill_md_content='---\nname: Test\n---\nContent',
            created_by=self.user
        )
        
        # Spawn case from skill
        new_case = CaseSkillConverter.skill_to_case(
            skill=skill,
            case_title='New Test Decision',
            user=self.user,
            position='Test position'
        )
        
        self.assertIsNotNone(new_case)
        self.assertEqual(new_case.title, 'New Test Decision')
        self.assertEqual(new_case.based_on_skill, skill)
        self.assertIn(skill, new_case.active_skills.all())
    
    def test_skill_forking(self):
        """Test forking a skill"""
        # Create original skill
        original = Skill.objects.create(
            name='Original Skill',
            description='Original',
            scope='organization',
            owner=self.user,
            organization=self.org,
            created_by=self.user
        )
        
        SkillVersion.objects.create(
            skill=original,
            version=1,
            skill_md_content='---\nname: Original\n---\nContent',
            created_by=self.user
        )
        
        # Fork it
        forked = CaseSkillConverter.fork_skill(
            original_skill=original,
            new_name='My Fork',
            user=self.user,
            scope='personal'
        )
        
        self.assertIsNotNone(forked)
        self.assertEqual(forked.name, 'My Fork')
        self.assertEqual(forked.scope, 'personal')
        self.assertEqual(forked.forked_from, original)
        self.assertEqual(forked.owner, self.user)
    
    def test_skill_promotion(self):
        """Test promoting a skill to higher scope"""
        skill = Skill.objects.create(
            name='Personal Skill',
            description='Test',
            scope='personal',
            owner=self.user,
            created_by=self.user
        )
        
        SkillVersion.objects.create(
            skill=skill,
            version=1,
            skill_md_content='---\nname: Test\n---\nContent',
            created_by=self.user
        )
        
        # Promote to team
        promoted = CaseSkillConverter.promote_skill(
            skill=skill,
            new_scope='organization',
            user=self.user
        )
        
        self.assertEqual(promoted.scope, 'organization')
        self.assertEqual(promoted.current_version, 2)  # New version created
    
    def test_skill_preview_from_case(self):
        """Test generating skill preview from case"""
        preview = SkillPreviewService.analyze_case(self.case)
        
        self.assertIn('signal_types', preview)
        self.assertIn('suggested_name', preview)
        self.assertIn('suggested_description', preview)
        self.assertIn('stats', preview)
        
        # Should suggest framework name
        self.assertIn('Framework', preview['suggested_name'])


class SkillPermissionTestCase(TestCase):
    """Test skill permissions"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.org = Organization.objects.create(name='Test Org', slug='test-org')
    
    def test_personal_skill_permissions(self):
        """Test that only owner can access personal skills"""
        skill = Skill.objects.create(
            name='Personal Skill',
            description='Test',
            scope='personal',
            owner=self.user1,
            created_by=self.user1
        )
        
        permission = SkillPermission()
        
        # Owner can read
        class MockRequest:
            method = 'GET'
            user = self.user1
        
        self.assertTrue(
            permission.has_object_permission(MockRequest(), None, skill)
        )
        
        # Other user cannot read
        MockRequest.user = self.user2
        self.assertFalse(
            permission.has_object_permission(MockRequest(), None, skill)
        )
    
    def test_public_skill_permissions(self):
        """Test that anyone can view public skills"""
        skill = Skill.objects.create(
            name='Public Skill',
            description='Test',
            scope='public',
            owner=self.user1,
            created_by=self.user1
        )
        
        permission = SkillPermission()
        
        class MockRequest:
            method = 'GET'
            user = self.user2
        
        # Any user can view public skills
        self.assertTrue(
            permission.has_object_permission(MockRequest(), None, skill)
        )
        
        # But only owner can edit
        MockRequest.method = 'PUT'
        self.assertFalse(
            permission.has_object_permission(MockRequest(), None, skill)
        )
    
    def test_can_edit_permissions(self):
        """Test that can_edit users can edit skills"""
        skill = Skill.objects.create(
            name='Team Skill',
            description='Test',
            scope='team',
            owner=self.user1,
            created_by=self.user1
        )
        
        # Add user2 to can_edit
        skill.can_edit.add(self.user2)
        
        permission = SkillPermission()
        
        class MockRequest:
            method = 'PUT'
            user = self.user2
        
        # User2 can edit because they're in can_edit
        self.assertTrue(
            permission.has_object_permission(MockRequest(), None, skill)
        )
