"""
Django management command to test checklist generation
"""
import asyncio
from django.core.management.base import BaseCommand
from django.db.models import Max
from apps.cases.models import Case, ReadinessChecklistItem
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.cases.checklist_service import generate_smart_checklist


class Command(BaseCommand):
    help = 'Test smart readiness checklist generation'

    def add_arguments(self, parser):
        parser.add_argument('case_id', type=str, help='Case ID to test with')

    def handle(self, *args, **options):
        case_id = options['case_id']

        try:
            case = Case.objects.get(id=case_id)
            self.stdout.write(self.style.SUCCESS(f'✓ Found test case: {case.title}'))
            self.stdout.write(f'  Decision question: {case.decision_question}\n')

            # Create test inquiries
            self.stdout.write('Creating test inquiries...')

            # Get next sequence index
            max_seq = Inquiry.objects.filter(case=case).aggregate(
                max_seq=Max('sequence_index')
            )['max_seq']
            next_seq = (max_seq + 1) if max_seq is not None else 0

            inquiry1 = Inquiry.objects.create(
                case=case,
                title='What are the costs of migrating to microservices?',
                status=InquiryStatus.OPEN,
                elevation_reason='user_created',
                sequence_index=next_seq,
            )
            self.stdout.write(f'  ✓ Created inquiry: {inquiry1.title}')

            inquiry2 = Inquiry.objects.create(
                case=case,
                title='What is our current technical debt?',
                status=InquiryStatus.OPEN,
                elevation_reason='user_created',
                sequence_index=next_seq + 1,
            )
            self.stdout.write(f'  ✓ Created inquiry: {inquiry2.title}')

            inquiry3 = Inquiry.objects.create(
                case=case,
                title='Do we have the team capacity for this migration?',
                status=InquiryStatus.OPEN,
                elevation_reason='user_created',
                sequence_index=next_seq + 2,
            )
            self.stdout.write(f'  ✓ Created inquiry: {inquiry3.title}\n')

            # Generate checklist
            self.stdout.write('Generating smart checklist...')
            items_data = asyncio.run(generate_smart_checklist(case))
            self.stdout.write(self.style.SUCCESS(f'✓ Generated {len(items_data)} checklist items\n'))

            # Create items in database
            self.stdout.write('Creating checklist items in database...')
            max_order = ReadinessChecklistItem.objects.filter(case=case).aggregate(
                max_order=Max('order')
            )['max_order'] or 0

            created_items = []
            for idx, item_data in enumerate(items_data):
                item = ReadinessChecklistItem.objects.create(
                    case=case,
                    description=item_data['description'],
                    is_required=item_data.get('is_required', True),
                    why_important=item_data.get('why_important', ''),
                    linked_inquiry_id=item_data.get('linked_inquiry_id'),
                    order=max_order + idx + 1,
                    created_by_ai=True,
                )
                created_items.append(item)

            self.stdout.write(self.style.SUCCESS(f'✓ Created {len(created_items)} items in database\n'))

            # Display the generated checklist
            self.stdout.write('=' * 80)
            self.stdout.write(self.style.SUCCESS('GENERATED READINESS CHECKLIST'))
            self.stdout.write('=' * 80)
            self.stdout.write('')

            required_items = [i for i in created_items if i.is_required]
            optional_items = [i for i in created_items if not i.is_required]

            if required_items:
                self.stdout.write(self.style.WARNING('CRITICAL ITEMS:'))
                for item in required_items:
                    check = 'X' if item.is_complete else ' '
                    self.stdout.write(f'\n  [{check}] {item.description}')
                    if item.why_important:
                        self.stdout.write(f'      Why: {item.why_important}')
                    if item.linked_inquiry:
                        self.stdout.write(self.style.NOTICE(f'      Linked to: {item.linked_inquiry.title}'))

            if optional_items:
                self.stdout.write('\n\nRECOMMENDED ITEMS:')
                for item in optional_items:
                    check = 'X' if item.is_complete else ' '
                    self.stdout.write(f'\n  [{check}] {item.description}')
                    if item.why_important:
                        self.stdout.write(f'      Why: {item.why_important}')
                    if item.linked_inquiry:
                        self.stdout.write(self.style.NOTICE(f'      Linked to: {item.linked_inquiry.title}'))

            self.stdout.write('\n' + '=' * 80 + '\n')

            # Test auto-completion
            self.stdout.write('Testing auto-completion...')
            linked_item = next((i for i in created_items if i.linked_inquiry), None)

            if linked_item:
                self.stdout.write(f'  Found item linked to inquiry: {linked_item.linked_inquiry.title}')
                self.stdout.write(f'  Resolving inquiry...')

                # Resolve the inquiry
                linked_item.linked_inquiry.status = InquiryStatus.RESOLVED
                linked_item.linked_inquiry.conclusion = "Migration costs estimated at $500K over 6 months with team of 5 engineers."
                linked_item.linked_inquiry.save()

                # Refresh the item to see if it auto-completed
                linked_item.refresh_from_db()

                if linked_item.is_complete:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Item auto-completed!'))
                    self.stdout.write(f'  Completion note: {linked_item.completion_note}')
                else:
                    self.stdout.write(self.style.ERROR(f'  ✗ Item did NOT auto-complete (check signal handler)'))
            else:
                self.stdout.write('  No items were linked to inquiries')

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✓ All tests completed successfully!'))

        except Case.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ Case {case_id} not found'))
            self.stdout.write('  Run the create_test_case.py script first')
