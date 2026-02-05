#!/usr/bin/env python
"""
Test script for smart readiness checklist generation
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

import asyncio
from django.contrib.auth.models import User
from apps.cases.models import Case, ReadinessChecklistItem
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.cases.checklist_service import generate_smart_checklist


def test_checklist_generation():
    """Test the smart checklist generation"""

    # Get the test case we created
    case_id = '44896a49-e1ab-405c-8cd6-9af17d207d28'

    try:
        case = Case.objects.get(id=case_id)
        print(f"✓ Found test case: {case.title}")
        print(f"  Decision question: {case.decision_question}")
        print()

        # Add some inquiries to make the generation more interesting
        print("Creating test inquiries...")
        user = case.user

        inquiry1 = Inquiry.objects.create(
            case=case,
            user=user,
            title="What are the costs of migrating to microservices?",
            status=InquiryStatus.OPEN,
        )
        print(f"  ✓ Created inquiry: {inquiry1.title}")

        inquiry2 = Inquiry.objects.create(
            case=case,
            user=user,
            title="What is our current technical debt?",
            status=InquiryStatus.OPEN,
        )
        print(f"  ✓ Created inquiry: {inquiry2.title}")

        inquiry3 = Inquiry.objects.create(
            case=case,
            user=user,
            title="Do we have the team capacity for this migration?",
            status=InquiryStatus.OPEN,
        )
        print(f"  ✓ Created inquiry: {inquiry3.title}")
        print()

        # Test the generation service
        print("Generating smart checklist...")
        items_data = asyncio.run(generate_smart_checklist(case))

        print(f"✓ Generated {len(items_data)} checklist items")
        print()

        # Create the checklist items
        print("Creating checklist items in database...")
        from django.db.models import Max
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

        print(f"✓ Created {len(created_items)} items in database")
        print()

        # Display the generated checklist
        print("=" * 80)
        print("GENERATED READINESS CHECKLIST")
        print("=" * 80)
        print()

        required_items = [i for i in created_items if i.is_required]
        optional_items = [i for i in created_items if not i.is_required]

        if required_items:
            print("CRITICAL ITEMS:")
            for item in required_items:
                print(f"\n  [{' ' if not item.is_complete else 'X'}] {item.description}")
                if item.why_important:
                    print(f"      Why: {item.why_important}")
                if item.linked_inquiry:
                    print(f"      Linked to: {item.linked_inquiry.title}")

        if optional_items:
            print("\n\nRECOMMENDED ITEMS:")
            for item in optional_items:
                print(f"\n  [{' ' if not item.is_complete else 'X'}] {item.description}")
                if item.why_important:
                    print(f"      Why: {item.why_important}")
                if item.linked_inquiry:
                    print(f"      Linked to: {item.linked_inquiry.title}")

        print("\n" + "=" * 80)
        print()

        # Test auto-completion
        print("Testing auto-completion...")
        linked_item = next((i for i in created_items if i.linked_inquiry), None)

        if linked_item:
            print(f"  Found item linked to inquiry: {linked_item.linked_inquiry.title}")
            print(f"  Resolving inquiry...")

            # Resolve the inquiry
            linked_item.linked_inquiry.status = InquiryStatus.RESOLVED
            linked_item.linked_inquiry.conclusion = "Migration costs estimated at $500K over 6 months with team of 5 engineers."
            linked_item.linked_inquiry.save()

            # Refresh the item to see if it auto-completed
            linked_item.refresh_from_db()

            if linked_item.is_complete:
                print(f"  ✓ Item auto-completed!")
                print(f"  Completion note: {linked_item.completion_note}")
            else:
                print(f"  ✗ Item did NOT auto-complete (check signal handler)")
        else:
            print(f"  No items were linked to inquiries")

        print()
        print("✓ All tests completed successfully!")

    except Case.DoesNotExist:
        print(f"✗ Case {case_id} not found")
        print("  Run the create_test_case.py script first")
        return


if __name__ == '__main__':
    test_checklist_generation()
