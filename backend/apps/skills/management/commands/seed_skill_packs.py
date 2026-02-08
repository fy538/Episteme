"""
Management command to seed the Consulting Starter Pack and its 3 composable skills.

Idempotent — safe to run multiple times. Updates existing skills on re-run.
"""
import os

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from apps.common.models import Organization
from apps.skills.models import Skill, SkillVersion, SkillPack, SkillPackMembership
from apps.skills.parser import parse_skill_md


# Each entry: (filename, role in pack, order)
PACK_SKILLS = [
    ('market_entry_assessment.md', 'domain', 0),
    ('consulting_research_standards.md', 'methodology', 1),
    ('high_stakes_decision_quality.md', 'quality', 2),
]

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')


class Command(BaseCommand):
    help = 'Seed the Consulting Starter Pack with 3 composable skills'

    def handle(self, *args, **options):
        # Resolve user
        user = User.objects.filter(is_staff=True).first() or User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('No users found. Create a user first.'))
            return

        self.stdout.write(f'Using user: {user.username}')

        # Resolve organization
        org, _ = Organization.objects.get_or_create(
            slug='default-org',
            defaults={'name': 'Default Organization'},
        )

        with transaction.atomic():
            created_skills = []

            for filename, role, order in PACK_SKILLS:
                skill = self._ensure_skill(filename, org, user)
                if skill:
                    created_skills.append((skill, role, order))

            if not created_skills:
                self.stdout.write(self.style.ERROR('No skills were created/found. Aborting pack creation.'))
                return

            # Create or update the Consulting Starter Pack
            pack, pack_created = SkillPack.objects.update_or_create(
                slug='consulting-starter',
                defaults={
                    'name': 'Consulting Starter Pack',
                    'description': (
                        'Domain expertise for market entry analysis, '
                        'consulting-grade research methodology, '
                        'and high-stakes decision quality standards.'
                    ),
                    'scope': 'public',
                    'icon': '\U0001f3af',
                    'status': 'active',
                    'created_by': user,
                    'organization': org,
                },
            )

            if pack_created:
                self.stdout.write(self.style.SUCCESS('Created Consulting Starter Pack'))
            else:
                self.stdout.write(self.style.WARNING('Updated Consulting Starter Pack'))

            # Ensure memberships (update order/role if they changed)
            for skill, role, order in created_skills:
                _, m_created = SkillPackMembership.objects.update_or_create(
                    pack=pack,
                    skill=skill,
                    defaults={'order': order, 'role': role},
                )
                if m_created:
                    self.stdout.write(f'  + Added {skill.name} as {role} (order={order})')
                else:
                    self.stdout.write(f'  ~ Updated {skill.name} as {role} (order={order})')

        # Summary (outside transaction)
        member_count = SkillPackMembership.objects.filter(pack=pack).count()
        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone! Pack "{pack.name}" has {member_count} skill(s)'
            )
        )

    def _ensure_skill(self, filename: str, org, user) -> Skill | None:
        """Load a SKILL.md, create or update the corresponding Skill + SkillVersion."""
        filepath = os.path.normpath(os.path.join(EXAMPLES_DIR, filename))

        try:
            with open(filepath, 'r') as f:
                skill_md = f.read()
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {filepath}'))
            return None

        parsed = parse_skill_md(skill_md)
        meta = parsed['metadata']
        episteme = meta.get('episteme', {})

        skill_name = meta.get('name', filename.replace('.md', '').replace('_', ' ').title())

        skill, created = Skill.objects.update_or_create(
            organization=org,
            name=skill_name,
            defaults={
                'description': meta.get('description', ''),
                'domain': meta.get('domain', ''),
                'applies_to_agents': episteme.get('applies_to_agents', ['research', 'critique', 'brief']),
                'episteme_config': episteme,
                'scope': 'public',
                'status': 'active',
                'created_by': user,
                'owner': user,
            },
        )

        if created:
            # Brand-new skill: create version 1
            SkillVersion.objects.create(
                skill=skill,
                version=1,
                skill_md_content=skill_md,
                created_by=user,
                changelog='Seeded from examples',
            )
            self.stdout.write(self.style.SUCCESS(f'Created skill: {skill_name}'))
        else:
            # Existing skill: ensure SkillVersion exists; update content if changed
            version, v_created = SkillVersion.objects.get_or_create(
                skill=skill,
                version=skill.current_version,
                defaults={
                    'skill_md_content': skill_md,
                    'created_by': user,
                    'changelog': 'Re-seeded from examples',
                },
            )
            if not v_created and version.skill_md_content != skill_md:
                # Content changed: bump version
                new_ver = SkillVersion.objects.create(
                    skill=skill,
                    version=skill.current_version + 1,
                    skill_md_content=skill_md,
                    created_by=user,
                    changelog='Updated from re-seed',
                )
                skill.current_version = new_ver.version
                skill.save(update_fields=['current_version', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(f'Updated skill content: {skill_name} -> v{new_ver.version}'))
            else:
                self.stdout.write(self.style.WARNING(f'Skill already exists (unchanged): {skill_name}'))

        return skill
