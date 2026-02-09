"""
Management command to seed default skills (General Research, etc.)

Creates public skills from templates if they don't already exist.
Safe to run multiple times — uses get_or_create.

Usage:
    python manage.py seed_default_skills
"""
import os

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from apps.common.models import Organization
from apps.skills.models import Skill
from apps.skills.parser import parse_skill_md, validate_skill_md


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../templates")


class Command(BaseCommand):
    help = "Seed default skills (General Research, etc.) into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate templates without creating database records",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # ── Find templates ───────────────────────────────────────────
        template_dir = os.path.normpath(TEMPLATE_DIR)
        if not os.path.isdir(template_dir):
            self.stdout.write(self.style.ERROR(f"Template directory not found: {template_dir}"))
            return

        templates = sorted(
            f for f in os.listdir(template_dir) if f.endswith(".md")
        )

        if not templates:
            self.stdout.write(self.style.WARNING("No .md templates found"))
            return

        self.stdout.write(f"Found {len(templates)} template(s) in {template_dir}")

        # ── Validate all templates first ─────────────────────────────
        valid_templates = []
        for filename in templates:
            path = os.path.join(template_dir, filename)
            with open(path, "r") as f:
                content = f.read()

            is_valid, errors = validate_skill_md(content)
            if not is_valid:
                self.stdout.write(self.style.ERROR(f"  {filename}: INVALID"))
                for err in errors:
                    self.stdout.write(self.style.ERROR(f"    - {err}"))
                continue

            parsed = parse_skill_md(content)
            metadata = parsed["metadata"]
            self.stdout.write(self.style.SUCCESS(f"  {filename}: OK ({metadata.get('name', '?')})"))
            valid_templates.append((filename, content, metadata))

        if dry_run:
            self.stdout.write(self.style.WARNING("\n--dry-run: No database changes made"))
            return

        if not valid_templates:
            self.stdout.write(self.style.ERROR("No valid templates to seed"))
            return

        # ── Get or create org + user ─────────────────────────────────
        org, _ = Organization.objects.get_or_create(
            slug="default-org",
            defaults={"name": "Default Organization"},
        )

        user = User.objects.filter(is_staff=True).first() or User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("No users found. Create a user first."))
            return

        # ── Seed each template ───────────────────────────────────────
        created_count = 0

        for filename, content, metadata in valid_templates:
            name = metadata["name"]
            description = metadata.get("description", "")
            domain = metadata.get("domain", "general")
            episteme = metadata.get("episteme", {})
            applies_to = episteme.get("applies_to_agents", ["research"])

            skill, created = Skill.objects.get_or_create(
                organization=org,
                name=name,
                defaults={
                    "description": description,
                    "domain": domain,
                    "applies_to_agents": applies_to,
                    "status": "active",
                    "owner": user,
                    "created_by": user,
                    "episteme_config": episteme,
                    "skill_md_content": content,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created: {name}"))
                created_count += 1
            else:
                self.stdout.write(self.style.WARNING(f"  Exists:  {name} (skipped)"))

        # ── Summary ──────────────────────────────────────────────────
        total = Skill.objects.filter(organization=org).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Created {created_count} skill(s). "
                f"Organization '{org.name}' now has {total} skill(s)."
            )
        )
