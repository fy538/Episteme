#!/usr/bin/env python
"""
Direct test of hierarchical checklist creation using view logic
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

import asyncio
from apps.cases.models import Case, ReadinessChecklistItem
from apps.cases.checklist_service import generate_smart_checklist


def test_hierarchy():
    case_id = '44896a49-e1ab-405c-8cd6-9af17d207d28'
    case = Case.objects.get(id=case_id)

    # Clear existing
    ReadinessChecklistItem.objects.filter(case=case).delete()
    print(f"Testing with case: {case.title}\n")

    # Generate items
    items_data = asyncio.run(generate_smart_checklist(case))
    print(f"Service returned {len(items_data)} items\n")

    # Use the EXACT view logic (copied from views.py)
    created_items = []
    parent_map = {}
    max_order = case.readiness_checklist.order_by('-order').values_list('order', flat=True).first() or -1

    # Pass 1: Create parent items
    print("Pass 1: Creating parents...")
    for idx, item_data in enumerate(items_data):
        if not item_data.get('parent_description_matched'):
            print(f"  Creating parent: {item_data['description']}")
            item = ReadinessChecklistItem.objects.create(
                case=case,
                description=item_data['description'],
                is_required=item_data.get('is_required', True),
                why_important=item_data.get('why_important', ''),
                linked_inquiry_id=item_data.get('linked_inquiry_id'),
                item_type=item_data.get('item_type', 'custom'),
                order=max_order + idx + 1,
                created_by_ai=True,
                parent=None,
            )
            created_items.append(item)
            parent_map[item_data['description']] = item

    print(f"\nCreated {len(parent_map)} parents\n")

    # Pass 2: Create child items
    print("Pass 2: Creating children...")
    child_order = len(created_items)
    for item_data in items_data:
        parent_desc = item_data.get('parent_description_matched')
        if parent_desc and parent_desc in parent_map:
            parent_item = parent_map[parent_desc]
            print(f"  Creating child: {item_data['description']}")
            print(f"    → under parent: {parent_desc}")
            item = ReadinessChecklistItem.objects.create(
                case=case,
                description=item_data['description'],
                is_required=item_data.get('is_required', True),
                why_important=item_data.get('why_important', ''),
                linked_inquiry_id=item_data.get('linked_inquiry_id'),
                item_type=item_data.get('item_type', 'custom'),
                order=max_order + child_order + 1,
                created_by_ai=True,
                parent=parent_item,
            )
            created_items.append(item)
            child_order += 1
        elif parent_desc:
            print(f"  WARNING: Could not find parent '{parent_desc}' for child '{item_data['description']}'")
            print(f"  Available parents: {list(parent_map.keys())}")

    print(f"\nCreated {len(created_items) - len(parent_map)} children\n")
    print(f"Total: {len(created_items)} items ({len(parent_map)} parents, {len(created_items) - len(parent_map)} children)\n")

    # Verify in database
    all_items = ReadinessChecklistItem.objects.filter(case=case)
    parents = [i for i in all_items if not i.parent]
    children = [i for i in all_items if i.parent]

    print("=" * 80)
    print(f"DATABASE VERIFICATION: {len(parents)} parents, {len(children)} children")
    print("=" * 80)
    print()

    for parent in parents:
        parent_children = [c for c in children if c.parent_id == parent.id]
        print(f"PARENT: {parent.description}")
        for child in parent_children:
            print(f"  → CHILD: {child.description}")
        print()


if __name__ == '__main__':
    test_hierarchy()
