"""
Management command to load example skills into the database
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.common.models import Organization
from apps.skills.models import Skill
import os


class Command(BaseCommand):
    help = 'Load example skills into database'

    def handle(self, *args, **options):
        # Get or create default org
        org, org_created = Organization.objects.get_or_create(
            slug='default-org',
            defaults={'name': 'Default Organization'}
        )
        
        if org_created:
            self.stdout.write(self.style.SUCCESS(f'Created organization: {org.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Using existing organization: {org.name}'))
        
        # Get first admin user, or any user
        user = User.objects.filter(is_staff=True).first()
        if not user:
            user = User.objects.first()
        
        if not user:
            self.stdout.write(self.style.ERROR('No users found. Please create a user first.'))
            return
        
        self.stdout.write(f'Using user: {user.username}')
        
        # Load Legal Decision Analysis
        legal_skill, created = Skill.objects.get_or_create(
            organization=org,
            name='Legal Decision Analysis',
            defaults={
                'description': 'Apply legal reasoning framework to decision-making, focusing on liability, compliance, and risk assessment',
                'domain': 'legal',
                'applies_to_agents': ['research', 'critique', 'brief'],
                'status': 'active',
                'owner': user,
                'created_by': user,
                'episteme_config': {
                    'signal_types': [
                        {
                            'name': 'LegalConstraint',
                            'inherits_from': 'Constraint',
                            'description': 'Legal or regulatory constraints'
                        },
                        {
                            'name': 'LiabilityRisk',
                            'inherits_from': 'Risk',
                            'description': 'Potential legal liability'
                        }
                    ],
                    'evidence_standards': {
                        'preferred_sources': ['Legal statutes', 'Case law', 'Attorney opinions'],
                        'minimum_credibility': 0.85
                    },
                    'document_template': {
                        'brief': {
                            'sections': [
                                'Legal Summary',
                                'Compliance Requirements',
                                'Risk Assessment',
                                'Recommended Actions'
                            ]
                        }
                    }
                }
            }
        )
        
        if created:
            # Load SKILL.md content
            skill_md_path = os.path.join(
                os.path.dirname(__file__),
                '../../examples/legal_decision_analysis.md'
            )

            try:
                with open(skill_md_path, 'r') as f:
                    skill_md = f.read()

                legal_skill.skill_md_content = skill_md
                legal_skill.save(update_fields=['skill_md_content'])
                self.stdout.write(self.style.SUCCESS('Created Legal Decision Analysis skill'))
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f'Could not find {skill_md_path}'))
                legal_skill.delete()
        else:
            self.stdout.write(self.style.WARNING('Legal Decision Analysis skill already exists'))
        
        # Load Product Decision Framework
        product_skill, created = Skill.objects.get_or_create(
            organization=org,
            name='Product Decision Framework',
            defaults={
                'description': 'Apply product management best practices to feature prioritization and roadmap decisions',
                'domain': 'product',
                'applies_to_agents': ['research', 'critique', 'brief'],
                'status': 'active',
                'owner': user,
                'created_by': user,
                'episteme_config': {
                    'signal_types': [
                        {
                            'name': 'UserNeed',
                            'inherits_from': 'Goal',
                            'description': 'User need or pain point'
                        },
                        {
                            'name': 'TechnicalConstraint',
                            'inherits_from': 'Constraint',
                            'description': 'Technical feasibility constraint'
                        }
                    ],
                    'evidence_standards': {
                        'preferred_sources': [
                            'User research data',
                            'Analytics data',
                            'Customer interviews'
                        ],
                        'minimum_credibility': 0.75
                    }
                }
            }
        )
        
        if created:
            skill_md_path = os.path.join(
                os.path.dirname(__file__),
                '../../examples/product_decision_framework.md'
            )

            try:
                with open(skill_md_path, 'r') as f:
                    skill_md = f.read()

                product_skill.skill_md_content = skill_md
                product_skill.save(update_fields=['skill_md_content'])
                self.stdout.write(self.style.SUCCESS('Created Product Decision Framework skill'))
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f'Could not find {skill_md_path}'))
                product_skill.delete()
        else:
            self.stdout.write(self.style.WARNING('Product Decision Framework skill already exists'))
        
        # Summary
        total_skills = Skill.objects.filter(organization=org).count()
        self.stdout.write(self.style.SUCCESS(f'\n✓ Done! Organization "{org.name}" has {total_skills} skill(s)'))
