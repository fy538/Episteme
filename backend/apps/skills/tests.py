"""
Tests for Skills system
"""
from django.test import TestCase
from django.contrib.auth.models import User
from apps.common.models import Organization
from apps.skills.models import Skill
from apps.skills.parser import parse_skill_md, validate_skill_md, validate_resource_files
from apps.skills.injection import build_skill_context, format_system_prompt_with_skills
from apps.skills.preview import SkillPreviewService
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
        self.assertIsNone(context['document_template'])
    
    def test_build_skill_context_single_skill(self):
        """Test building context with single skill"""
        skill = Skill.objects.create(
            organization=self.org,
            name='Test Skill',
            description='A test skill',
            applies_to_agents=['research'],
            created_by=self.user,
            owner=self.user,
            skill_md_content="""---
name: Test Skill
description: A test skill
---

## Test Content

This is test content.
"""
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
            created_by=self.user,
            owner=self.user,
            skill_md_content="""---
name: Research Only Skill
description: Only for research agent
---

Content.
"""
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
            created_by=self.user,
            owner=self.user,
            skill_md_content="""---
name: Legal Skill
description: Legal analysis
---

Content.
"""
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
            'document_template': None
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
            applies_to_agents=['research'],
            owner=self.user,
            created_by=self.user
        )

        self.assertEqual(skill.name, 'Test Skill')
        self.assertEqual(skill.status, 'draft')

    def test_skill_unique_name_per_owner(self):
        """Test that skill names must be unique per owner"""
        Skill.objects.create(
            organization=self.org,
            owner=self.user,
            name='Duplicate Name',
            description='First skill',
            created_by=self.user
        )

        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Skill.objects.create(
                organization=self.org,
                owner=self.user,
                name='Duplicate Name',
                description='Second skill',
                created_by=self.user
            )


class SkillPermissionTestCase(TestCase):
    """Test skill permissions"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.org = Organization.objects.create(name='Test Org', slug='test-org')

    def test_owner_can_access_skill(self):
        """Test that owner can access their skills"""
        skill = Skill.objects.create(
            name='My Skill',
            description='Test',
            owner=self.user1,
            created_by=self.user1
        )

        permission = SkillPermission()

        class MockRequest:
            method = 'GET'
            user = self.user1

        self.assertTrue(
            permission.has_object_permission(MockRequest(), None, skill)
        )
