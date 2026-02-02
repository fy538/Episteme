# Migration for requiring projects and removing linked_thread

from django.db import migrations, models
import django.db.models.deletion


def create_default_projects_and_assign_cases(apps, schema_editor):
    """
    Create a default project for each user and assign their orphaned cases to it.
    """
    User = apps.get_model('auth', 'User')
    Project = apps.get_model('projects', 'Project')
    Case = apps.get_model('cases', 'Case')
    
    for user in User.objects.all():
        # Create or get default project for this user
        default_project, created = Project.objects.get_or_create(
            user=user,
            title=f"{user.username}'s Default Project",
            defaults={
                'description': 'Auto-created default project for organizing cases',
                'is_archived': False,
            }
        )
        
        # Assign all cases without a project to the default project
        orphaned_cases = Case.objects.filter(user=user, project__isnull=True)
        orphaned_cases.update(project=default_project)


class Migration(migrations.Migration):

    atomic = False  # Run operations outside transaction to avoid lock issues

    dependencies = [
        ('cases', '0004_case_active_skills_case_based_on_skill_and_more'),
        ('projects', '0002_add_evidence_signal_links'),
    ]

    operations = [
        # Run data migration to create default projects and assign cases
        migrations.RunPython(
            create_default_projects_and_assign_cases,
            reverse_code=migrations.RunPython.noop,
        ),
        
        # Make Case.project required (null=False, blank=False)
        migrations.AlterField(
            model_name='case',
            name='project',
            field=models.ForeignKey(
                help_text='Project this case belongs to (REQUIRED)',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cases',
                to='projects.project'
            ),
        ),
        
        # Remove the index on linked_thread first
        migrations.RemoveIndex(
            model_name='case',
            name='cases_case_linked__841724_idx',
        ),
        
        # Remove Case.linked_thread field
        migrations.RemoveField(
            model_name='case',
            name='linked_thread',
        ),
    ]
